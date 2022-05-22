from ast import Raise
import metro

import time  # temporal, solo para medir tiempos de ejecuciones
import pandas as pd
import osmnx as ox
import networkx as nx
from staticmap import StaticMap, CircleMarker, Line, IconMarker
import matplotlib.pyplot as plt
from dataclasses import dataclass
from typing import Optional, TextIO, List, Tuple, Dict, Union
from typing_extensions import TypeAlias
import pickle as pkl
import os.path
from datetime import datetime, timedelta
from haversine import haversine, Unit
from constants import *

CityGraph: TypeAlias = nx.Graph
OsmnxGraph: TypeAlias = nx.MultiDiGraph

# CONSTANTS
PICKLE_FILENAME: str = "barcelona.grf"


# Definim classes

Coord: TypeAlias = Tuple[float, float]
MetroGraph: TypeAlias = nx.Graph
NodeID: TypeAlias = int
Path: TypeAlias = List[NodeID]


def get_osmnx_graph() -> OsmnxGraph:
    '''
    Downloads and returns the OsmnxGraph of Barcelona.
    It removes unnecessary information and deletes selfloops.
    It adds pos, type and travel time attributes

    Returns
    -------
    graph: OsmxnGraph
    '''
    try:
        if not os.path.exists(PICKLE_FILENAME):
            graph = ox.graph_from_place(
                "Barcelona, Spain", network_type="walk", simplify=True)
            for u, v, key, geom in graph.edges(data="geometry", keys=True):
                if geom is not None:
                    del(graph[u][v][key]["geometry"])
            for node in graph.nodes():
                graph.nodes[node]["pos"] = (
                    graph.nodes[node]["x"], graph.nodes[node]["y"])
                graph.nodes[node]["type"] = "street_intersection"

            # graph.remove_edges_from(nx.selfloop_edges(graph))

            for edge in graph.edges:
                distance = haversine(graph.nodes[edge[0]]["pos"],
                                     graph.nodes[edge[1]]["pos"], unit="m")
                graph.edges[edge]["distance"] = distance
                graph.edges[edge]["travel_time"] = distance/WALKING_SPEED
                graph.edges[edge]["acc_travel_time"] = distance/WALKING_SPEED
                graph.edges[edge]["type"] = "street"

            save_osmnx_graph(graph, PICKLE_FILENAME)
            return graph
        else:
            return load_osmnx_graph(PICKLE_FILENAME)

    except Exception:
        print("Could not retrieve the graph")


def save_osmnx_graph(g: OsmnxGraph, filename: str) -> None:
    '''
        Saves the OsmnxGraph g as Filename to the current directory
    '''
    if not isinstance(g, OsmnxGraph):
        raise TypeError("g has to be an OsmnxGraph")

    try:
        pickle_out = open(filename, "wb")
        pkl.dump(g, pickle_out)
        pickle_out.close()
    except Exception as error:
        print("Error while saving osmnx_graph".format(error))


def load_osmnx_graph(filename: str) -> OsmnxGraph:
    '''
        Loads an OsmnxGraph from filename and returns the retrieved graph.

        Parameters
        ----------
        filename:str

        Returns
        -------
        OxmnxGraph

    '''
    if not os.path.exists(filename):
        raise ValueError("filename does not exist")
    else:
        try:
            pickle_in = open(filename, "rb")
            return pkl.load(pickle_in)
        except Exception as error:
            print("Could not retrieve osmnx graph".format(error))


def nearest_nodes(g1: OsmnxGraph, g2: MetroGraph) -> Tuple[List[int], List[int], List[float]]:
    '''
    Given a OsmnxGraph g1 and a MetroGraph g2 returns a list which contains a list with the ids of the access nodes,
    a list with the nearest node in g1 to each access node in g2 tohether with a list which contains the corresponding
    distances
    '''
    if not isinstance(g1, OsmnxGraph):
        raise TypeError("g1 must be an OsmnxGraph")
    if not isinstance(g2, MetroGraph):
        raise TypeError("g2 must be a MetroGraph")
    nodes = []
    X, Y = [], []
    for node, value in g2.nodes(data=True):
        if value["type"] == "access":
            coords = value["pos"]
            X.append(coords[0])
            Y.append(coords[1])
            nodes.append(node)
    nearest, distances = ox.distance.nearest_nodes(g1, X, Y, return_dist=True)
    return nodes, nearest, distances


# def walking_street_distance(g: OsmnxGraph, orig_id: int, dest_id: int) -> float:
#     return haversine(g.nodes[orig_id]["pos"],
#                      g.nodes[dest_id]["pos"], unit="m")


def build_city_graph(g1: OsmnxGraph, g2: MetroGraph) -> CityGraph:
    '''
    Given a OsmnxGraph g1 and a MetroGraph g2, unites both Graphs and connects each access in g2 to the
    nearest node in g1.

    Parameters
    ----------
    g1: OsmnxGraph
    g2: MetroGraph

    Returns
    -------
    city: CityGraph

    '''

    nodes, nearest, distances = nearest_nodes(g1, g2)

    # We convert g1 from Multidigraph to graph
    g1 = nx.Graph(g1)
    city = nx.union(g1, g2)
    distances = [distance/WALKING_SPEED for distance in distances]
    for e1, e2, d in zip(nodes, nearest, distances):
        city.add_edge(e1, e2, type="Street", distance=d,
                      travel_time=d/WALKING_SPEED, acc_travel_time=d/WALKING_SPEED)
    return city


def find_path(ox_g: OsmnxGraph, g: CityGraph, src: Coord, dst: Coord, accessibility: bool = False) -> Path:
    '''
    Given a CityGraph g, a starting point src and a destination point dst we
    generate the shortest path (in travel time) between the two positions and
    we return the path
    '''
    src_node: NodeID = ox.distance.nearest_nodes(ox_g, src[1], src[0])
    dst_node: NodeID = ox.distance.nearest_nodes(ox_g, dst[1], dst[0])
    weight_parameter = 'acc_travel_time' if accessibility else 'travel_time'
    p: Path = nx.shortest_path(g, src_node, dst_node, weight=weight_parameter)
    return p


def plot(g: MetroGraph, filename: str) -> None:
    '''
    Given a CityGraph g and a filename we create an image of the graph
    g and save it with the corresponding filename
    '''
    # color for each set of edges, blue is the default

    colorEdges = {'line': 'blue', 'street': 'yellow',
                  'transfer': 'orange', 'Street': 'orange', 'access': 'blue'}
    colorNodes = {'station': 'red', 'access': 'black',
                  'street_intersection': 'green'}
    map: StaticMap = StaticMap(
        SIZE_X, SIZE_Y, url_template='http://a.tile.osm.org/{z}/{x}/{y}.png')
    for u, node in g.nodes(data=True):
        map.add_marker(CircleMarker(node.get('pos'),
                       colorNodes.get(node.get('type'), 'green'), 4))
    edgetypes = set()
    for edge in g.edges(data=True):
        edgetypes.add(edge[2].get('type'))
        n0, n1 = g.nodes[edge[0]], g.nodes[edge[1]]
        map.add_line(Line([n0['pos'], n1['pos']],
                     colorEdges[edge[2]['type']], 2))
    try:
        image = map.render()
        image.save(filename)
    except Exception as error:
        print("Could not render or save image".format(error))


def edge_color(g: CityGraph, n1: NodeID, n2: NodeID) -> str:
    '''Returns the appropiate color for an edge'''
    try:
        edge = g.edges[(n1, n2)]
        if edge['type'] == 'line':
            return "#"+edge['line_colour']
        elif edge['type'] == 'transfer':
            return TRANSFER_COLOR
        elif edge['type'] == 'access':
            return ACCESS_COLOR
        return STREET_COLOR
    except Exception as e:
        print(e)
        return 'black'


def plot_path(g: CityGraph, p: Path, filename: str, orig: Coord, dest: Coord) -> None:

    map: StaticMap = StaticMap(
        SIZE_X, SIZE_Y, padding_x=PADDING, padding_y=PADDING, url_template='http://a.tile.osm.org/{z}/{x}/{y}.png')
    if p:
        for prev_node, node in zip(p, p[1:]):
            map.add_line(Line([g.nodes[prev_node]['pos'], g.nodes[node]['pos']],
                              edge_color(g, prev_node, node), 4))

        map.add_marker(CircleMarker(g.nodes[p[0]]['pos'], 'blue', 10))
        map.add_marker(CircleMarker(g.nodes[p[-1]]['pos'], 'red', 10))
    try:
        image = map.render()
        image.save(filename)
    except Exception as error:
        print("Could not render or save image".format(error))


def time_txt(t: float) -> str:
    """generates a text with the correct format from the time in seconds"""
    t = round(t/60)  # en minuts
    return f"{t} min" if t <= 60 else f"{t//60} h {t%60} min"


def dist_txt(dist: float) -> str:
    """generates a text with the correct format from the distance in meters"""
    dist = round(dist)
    return f"{dist} m" if dist < 1000 else f"{dist//1000} km {dist%1000} m"


def path_txt(g: CityGraph, p: Path, orig: Coord, dest: Coord) -> str:
    """generates a text of the resumed path"""
    now = datetime.now()
    path_txt = f"🔵 La teva ubicació\n"
    i, n = 1, len(p)
    street_types = ['street', 'Street', 'access']
    # for x in zip(p, p[1:]):
    #     print(g.edges[x]['type'])
    while i < n:
        edge = g.edges[p[i-1], p[i]]
        dist, t = 0, 0
        if edge['type'] in street_types:
            while edge['type'] in street_types:
                dist += edge['distance']
                t += edge['travel_time']

                i += 1
                if i >= n:
                    break
                edge = g.edges[p[i-1], p[i]]
            # we update the message
            path_txt += f"🚶‍ {now.strftime('%H:%M')} | Camina {time_txt(t)} ({dist_txt(dist)})\n"
            now += timedelta(seconds=t)
            dist, t = 0, 0

        fst_edge, stops = edge, 0
        if edge['type'] == 'line':
            path_txt += f"Ⓜ️  {now.strftime('%H:%M')} | Agafa la linea {edge['line_name']} en {g.nodes[p[i-1]]['name']}, amb direcció "
            path_txt += f"{edge['line_dest' if edge['orientation'] == (p[i-1], p[i]) else 'line_orig']}\n"
            while edge['type'] == 'line':
                dist += edge['distance']
                t += edge['travel_time']
                i += 1
                stops += 1
                if i >= n:
                    break
                edge = g.edges[p[i-1], p[i]]
            # we update the message
            now += timedelta(seconds=t)
            path_txt += f"🚊 Espera't {stops} parades ({time_txt(t)}) i baixa't a {g.nodes[p[i-1]]['name']}\n"

        if edge['type'] == 'transfer':
            i += 1
            edge = g.edges[p[i-1], p[i]]
            if fst_edge['line_name'] != edge['line_name']:
                path_txt += f"🔳 {now.strftime('%H:%M')} | Transbord de la línia {fst_edge['line_name']} a la línia {edge['line_name']}\n"
            now += timedelta(seconds=edge['travel_time'])

    return path_txt + f"📍 {now.strftime('%H:%M')}"

    # for pos in p:
    #     if(g.nodes[pos]['type'] == 'station'):
    #         print(g.nodes[pos])


def path_stats(g: CityGraph, p: Path, src: Coord, dst: Coord):
    '''Return stats of the path: walking time and subway time'''
    walk_time = 0
    walk_distance = 0
    subway_time = 0
    subway_distance = 0
    if not p:
        return 0, 0
    src = (src[1], src[0])
    dst = (dst[1], dst[0])
    walk_distance += haversine(src, g.nodes[p[0]]["pos"], unit="m")
    walk_time = walk_distance/WALKING_SPEED
    for id0, id1 in zip(p, p[1:]):
        if g.edges[(id0, id1)]["type"] in ("street", "access", "transfer"):
            walk_distance += g.edges[(id0, id1)]["distance"]
            walk_time += g.edges[(id0, id1)]["travel_time"]
        else:
            subway_distance += g.edges[(id0, id1)]["distance"]
            subway_time += g.edges[(id0, id1)]["travel_time"]

    return walk_time, walk_distance, subway_time, subway_distance


def path_time_dist(g: CityGraph, p: Path, src: Coord, dst: Coord) -> Tuple[float, int]:
    '''Returns to total time and distance for a path'''
    wt, wd, st, sd = path_stats(g, p, src, dst)
    return wt+st, wd+sd


def show(g: CityGraph) -> None:
    '''Shows the CityGraph g in a interative window'''
    positions = nx.get_node_attributes(g, "pos")
    nx.draw(g, positions, node_size=5)
    plt.show()


def main():
    g2 = metro.get_metro_graph()
    g1 = get_osmnx_graph()
    city = build_city_graph(g1, g2)
    orig = (41.388492, 2.113043)
    dest = (41.3733898465379, 2.136240845303527)
    t1 = time.time()
    p: Path = find_path(g1, city, orig, dest)
    # print(path_stats(city, p, orig, dest))
    # print(path_time_dist(city, p, orig, dest))
    # # show(city)
    # # plot_path(city, p, "path.png",  orig, dest)
    # plot(city, 'cityTest.png')
    # print(time.time()-t1)
    plot_path(city, p, 'borrame.png', orig, dest)
    print(path_txt(city, p, orig, dest))


if __name__ == "__main__":
    main()
