import lib_metro as metro

import pandas as pd
import osmnx as ox
import networkx as nx
from staticmap import StaticMap, CircleMarker, Line
import matplotlib.pyplot as plt
from dataclasses import dataclass
from typing import Optional, TextIO, List, Tuple, Dict
from typing_extensions import TypeAlias
import pickle as pkl

CityGraph: TypeAlias = nx.Graph
OsmnxGraph: TypeAlias = nx.MultiDiGraph

Point = Tuple[int, int]
MetroGraph: TypeAlias = nx.Graph


def get_osmnx_graph() -> OsmnxGraph:
    graph = ox.graph_from_place(
        "Barcelona", network_type='walk', simplify=True)

    for u, v, key, geom in graph.edges(data="geometry", keys=True):
        if geom is not None:
            del(graph[u][v][key]["geometry"])
    graph.remove_edges_from(nx.selfloop_edges(graph))

    # x = nx.get_node_attributes(graph, "x")
    # y = nx.get_node_attributes(graph, "y")
    # pos = dict()
    # for key in x.keys():
    #     pos[key] = (x[key], y[key])
    # nx.set_node_attributes(graph, pos)
    return graph

# AFEGIR OS.PATH.EXISTS!!!!!!


def save_osmnx_graph(g: OsmnxGraph, filename: str) -> None:
    pickle_out = open(filename, "wb")
    pkl.dump(g, pickle_out)
    pickle_out.close()


def load_osmnx_graph(filename: str) -> OsmnxGraph:
    pickle_in = open(filename, "rb")
    return pkl.load(pickle_in)


def build_city_graph(g1: OsmnxGraph, g2: MetroGraph) -> CityGraph:
    nodes = []
    X, Y = [], []
    for node in g2.nodes():
        value = g2.nodes[node]
        if value["type"] == "access":
            coords = value["pos"]
            X.append(coords[0])
            Y.append(coords[1])
            nodes.append(node)
    nearest, distances = ox.distance.nearest_nodes(g1, X, Y, return_dist=True)
    g1 = nx.Graph(g1)

    city = nx.union(g1, g2)
    # AQUI TEMA VELOCITAT
    city.add_edges_from(zip(nearest, nodes), type="Street", distance=distances)
    return city


g2 = metro.get_metro_graph()
# save_osmnx_graph(get_osmnx_graph(), "barcelona.pickle")
# g1=get_osmnx_graph()
# save_osmnx_graph(g1,"city.pickle")
g1 = load_osmnx_graph("city.pickle")
for node in g1.nodes():
    g1.nodes[node]["pos"] = (g1.nodes[node]["x"], g1.nodes[node]["y"])
g1.remove_edges_from(nx.selfloop_edges(g1))


city = build_city_graph(g1, g2)

positions = nx.get_node_attributes(city, "pos")

nx.draw(city, pos=positions, node_size=5)
plt.show()
