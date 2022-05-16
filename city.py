from tkinter.messagebox import NO
import metro

import pandas as pd
import osmnx as ox
import networkx as nx
from staticmap import StaticMap, CircleMarker, Line
import matplotlib.pyplot as plt
from dataclasses import dataclass
from typing import Optional, TextIO, List, Tuple, Dict, Union
from typing_extensions import TypeAlias
import pickle as pkl
import os.path
from haversine import haversine, Unit


CityGraph: TypeAlias = nx.Graph
OsmnxGraph: TypeAlias = nx.MultiDiGraph

# CONSTANTS
FILENAME: str = "city.pickle"

SIZE_X: int = 3000
SIZE_Y: int = 3000
WALKING_SPEED: float = 1.42
SUBWAY_SPEED: float = 7.22222222


# Definim classes

Coord: TypeAlias = Tuple[float, float]
MetroGraph: TypeAlias = nx.Graph
NodeID: TypeAlias = int
Path: TypeAlias = List[NodeID]


def get_osmnx_graph() -> OsmnxGraph:
    '''
    Downloads and returns the OsmnxGraph of Barcelona.
    It removes unnecessary information and deletes selfloops.

    Returns
    -------
    graph: OsmxnGraph
    '''
    try:
        if not os.path.exists(FILENAME):
            graph = ox.graph_from_place(
                "Barcelona, Spain", network_type="walk", simplify=True)
            for u, v, key, geom in graph.edges(data="geometry", keys=True):
                if geom is not None:
                    del(graph[u][v][key]["geometry"])
            for node in graph.nodes():
                graph.nodes[node]["pos"] = (
                    graph.nodes[node]["x"], graph.nodes[node]["y"])

            graph.remove_edges_from(nx.selfloop_edges(graph))

            for edge in graph.edges:
                graph.edges[edge]["travel_time"] = walking_street_distance(
                    graph, edge[0], edge[1])

            save_osmnx_graph(graph, FILENAME)
            return graph

        else:
            return load_osmnx_graph(FILENAME)
    except Exception:
        print("Could not retrieve the graph")

# AFEGIR OS.PATH.EXISTS!!!!!!


def save_osmnx_graph(g: OsmnxGraph, filename: str) -> None:
    '''
        Saves the OsmnxGraph g as Filename to the current directory
    '''

    pickle_out = open(filename, "wb")
    pkl.dump(g, pickle_out)
    pickle_out.close()


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
        pickle_in = open(filename, "rb")
        return pkl.load(pickle_in)


def nearest_nodes(g1: OsmnxGraph, g2: MetroGraph) -> [List[int], List[int], List[float]]:
    '''
    Given a OsmnxGraph g1 and a MetroGraph g2 returns a list which contains a list with the ids of the access nodes,
    a list with the nearest node in g1 to each access node in g2 tohether with a list which contains the corresponding
    distances
    '''
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


def walking_street_distance(g: OsmnxGraph, orig_id: int, dest_id: int) -> float:
    d: float = haversine(g.nodes[orig_id]["pos"],
                         g.nodes[dest_id]["pos"], unit="m")
    time: float = d / WALKING_SPEED

    return time


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

    # We create a new attribute which stores x and y in a tuple
    # for node in g1.nodes():
    #     g1.nodes[node]["pos"] = (g1.nodes[node]["x"], g1.nodes[node]["y"])
    # g1.remove_edges_from(nx.selfloop_edges(g1))

    # for edge in g1.edges:
    #     g1.edges[edge]["distance"] = walking_street_distance(
    #         g1, edge[0], edge[1])

    # We convert g1 from Multidigraph to graph
    g1 = nx.Graph(g1)

    city = nx.union(g1, g2)

    # function that will take care of setting in an atribute the time which it takes to traverse things
    # TO BE DONE

    city.add_edges_from(zip(nearest, nodes), type="Street", distance=distances)
    return city


def find_path(ox_g: OsmnxGraph, g: CityGraph, src: Coord, dst: Coord) -> Path:
    print(src)
    print(dst)
    src_node: NodeID = ox.distance.nearest_nodes(ox_g, src[1], src[0])
    dst_node: NodeID = ox.distance.nearest_nodes(ox_g, dst[1], dst[0])
    print("source "+str(src_node)+" dest "+str(dst_node))
    p: Path = nx.shortest_path(g, src_node, dst_node, weight='travel_time')
    print(p)
    return p


def plot(g: MetroGraph, filename: str) -> None:
    '''
    Given a CityGraph g and a filename we create an image of the graph
    g and save it with the corresponding filename
    '''

    map: StaticMap = StaticMap(SIZE_X, SIZE_Y)
    for u, node in g.nodes(data=True):
        map.add_marker(CircleMarker(node.get('pos'),
                       colorNodes.get(node.get('type')), 4))
    for edge in g.edges:
        t = (g.nodes[edge[0]].get('type'), g.nodes[edge[1]].get('type'))
        types.add(t)
        map.add_line(
            Line([g.nodes[edge[0]]['pos'], g.nodes[edge[1]]['pos']], colorTypes.get(t, 'blue'), 2))
    print(types)
    image = map.render()
    image.save(filename)


def plot_path(g: CityGraph, p: Path, filename: str, orig: Coord, dest: Coord) -> None:

    map: StaticMap = StaticMap(SIZE_X, SIZE_Y)
    prev_pos = g.nodes[p[0]]['pos']
    for node in p:
        current_pos = g.nodes[node]['pos']
        map.add_line(Line([prev_pos, current_pos],
                     'blue', 2))
        prev_pos = current_pos

    # map.add_line(Line([prev_pos, current_pos], 'black', 2))
    image = map.render()
    image.save(filename)


def show(g: CityGraph) -> None:
    '''Shows the CityGraph g in a interative window'''
    positions = nx.get_node_attributes(g, "pos")
    nx.draw(g, positions, node_size=5)
    plt.show()


def test():
    g2 = metro.get_metro_graph()
    # save_osmnx_graph(get_osmnx_graph(), "barcelona.pickle")
    g1 = get_osmnx_graph()
    # save_osmnx_graph(g1,"city.pickle")
    # g1 = load_osmnx_graph("city.pickle")
    city = build_city_graph(g1, g2)
    orig = (41.388606, 2.112741)
    dest = (41.413816960390676, 2.1814567039217905)
    # print("buscant path")
    # positions = nx.get_node_attributes(g1, "pos")
    # print(positions)
    p = find_path(g1, city, orig, dest)
    # show(city)
    print(p)
    # print("creant mapa")
    # plot_path(city, p, "path.png",  orig, dest)
    # show(city)
    # print('plotting')
    # plot(city, 'cityTest.png')
