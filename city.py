# from tkinter.messagebox import NO
from lib2to3.pytree import Node
import metro

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

            graph.remove_edges_from(nx.selfloop_edges(graph))

            for edge in graph.edges:
                distance = walking_street_distance(graph, edge[0], edge[1])
                graph.edges[edge]["distance"] = distance
                graph.edges[edge]["travel_time"] = distance/WALKING_SPEED
                graph.edges[edge]["type"] = 'street'

            save_osmnx_graph(graph, PICKLE_FILENAME)
            return graph

        else:
            graph = load_osmnx_graph(PICKLE_FILENAME)
            return graph
    except Exception:
        print("Could not retrieve the graph")


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


def nearest_nodes(g1: OsmnxGraph, g2: MetroGraph) -> Tuple[List[int], List[int], List[float]]:
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
    time: float = d

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

    # We convert g1 from Multidigraph to graph
    g1 = nx.Graph(g1)
    city = nx.union(g1, g2)
    for i in range(len(distances)):
        distances[i] = distances[i]/WALKING_SPEED
    city.add_edges_from(zip(nearest, nodes), type="Street", distance=distances)
    return city


def find_path(ox_g: OsmnxGraph, g: CityGraph, src: Coord, dst: Coord) -> Path:
    src_node: NodeID = ox.distance.nearest_nodes(ox_g, src[1], src[0])
    dst_node: NodeID = ox.distance.nearest_nodes(ox_g, dst[1], dst[0])
    p: Path = nx.shortest_path(g, src_node, dst_node, weight='travel_time')
    return p


def plot(g: MetroGraph, filename: str) -> None:
    '''
    Given a CityGraph g and a filename we create an image of the graph
    g and save it with the corresponding filename
    '''
    # color for each set of edges, blue is the default

    colorEdges = {(None, None): 'yellow', (None, 'access'): 'orange',
                  (None, 'station'): 'orange'}
    colorNodes = {'station': 'red', 'access': 'black', None: 'green'}
    map: StaticMap = StaticMap(
        SIZE_X, SIZE_Y, url_template='http://a.tile.osm.org/{z}/{x}/{y}.png')
    for u, node in g.nodes(data=True):
        map.add_marker(CircleMarker(node.get('pos'),
                       colorNodes.get(node.get('type')), 4))
    for edge in g.edges:
        n0, n1 = g.nodes[edge[0]], g.nodes[edge[1]]
        map.add_line(Line([n0['pos'], n1['pos']], colorEdges.get(
            (n0.get('type'), n1.get('type')), 'blue'), 2))
    image = map.render()
    image.save(filename)


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
    prev_node: NodeID = p[0]
    for node in p:
        map.add_line(Line([g.nodes[prev_node]['pos'], g.nodes[node]['pos']],
                     edge_color(g, prev_node, node), 2))
        prev_node = node

    map.add_marker(CircleMarker(g.nodes[p[0]]['pos'], 'blue', 10))
    map.add_marker(CircleMarker(g.nodes[p[-1]]['pos'], 'red', 10))

    image = map.render()
    image.save(filename)


def path_time_dist(g: CityGraph, p: Path, src: Coord, dst: Coord) -> Tuple[float, int]:
    '''Returns time and distance for a path'''
    time = 0

    if len(p) != 0:
        dist = haversine(src, g[p[0]]["pos"], unit="m")
        distance += dist
        time += dist/WALKING_SPEED
        dist = haversine(g[p[len(p)-1]]["pos"], dst, unit="m")
        distance += dist
        time += dist/WALKING_SPEED
        n1 = p[0]
    for id in p[1:]:
        distance += g.edges[(n1, id)]["distance"]
        time += g.edges[(n1, id)]["travel_time"]
    return distance, time


def show(g: CityGraph) -> None:
    '''Shows the CityGraph g in a interative window'''
    positions = nx.get_node_attributes(g, "pos")
    nx.draw(g, positions, node_size=5)
    plt.show()


def test():
    g2 = metro.get_metro_graph()
    g1 = get_osmnx_graph()
    city = build_city_graph(g1, g2)
    orig = (41.388606, 2.112741)
    dest = (41.413816960390676, 2.1814567039217905)
    p: Path = find_path(g1, city, orig, dest)
    # show(city)
    plot_path(city, p, "path.png",  orig, dest)
    # plot(city, 'cityTest.png')
