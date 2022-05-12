import metro

import pandas as pd
import osmnx as ox
import networkx as nx
from staticmap import StaticMap, CircleMarker, Line
import matplotlib.pyplot as plt
from dataclasses import dataclass
from typing import Optional, TextIO, List, Tuple, Dict
from typing_extensions import TypeAlias
import pickle as pkl
import os.path

CityGraph: TypeAlias = nx.Graph
OsmnxGraph: TypeAlias = nx.MultiDiGraph

# CONSTANTS
FILENAME: str = "city.pickle"
SIZE_X: int = 1500
SIZE_Y: int = 1500


# Definim classes

Coord: TypeAlias = Tuple[float, float]
MetroGraph: TypeAlias = nx.Graph


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
                "Barcelona", network_type='walk', simplify=True)

            for u, v, key, geom in graph.edges(data="geometry", keys=True):
                if geom is not None:
                    del(graph[u][v][key]["geometry"])
            graph.remove_edges_from(nx.selfloop_edges(graph))

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
    nodes: List[int] = [node for node in g2.nodes()]
    X: List[float] = []
    Y: List[float] = []
    for node in nodes:
        value = g2.nodes[node]
        if value["type"] == "access":
            coords = value["pos"]
            X.append(coords[0])
            Y.append(coords[1])
    nearest, distances = ox.distance.nearest_nodes(g1, X, Y, return_dist=True)
    return nodes, nearest, distances


def weighted_distance(city: CityGraph, p1: Coord, p2: Coord): ...


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
    for node in g1.nodes():
        g1.nodes[node]["pos"] = (g1.nodes[node]["x"], g1.nodes[node]["y"])

    # We convert g1 from Multidigraph to graph
    g1 = nx.Graph(g1)

    city = nx.union(g1, g2)

    # function that will take care of setting in an atribute the time which it takes to traverse things
    # TO BE DONE

    city.add_edges_from(zip(nearest, nodes), type="Street", distance=distances)
    return city


def show(g: CityGraph) -> None:
    '''Shows the CityGraph g in a interative window'''
    positions = nx.get_node_attributes(g, "pos")
    nx.draw(g, positions, node_size=5)
    plt.show()


def test():
    g2 = metro.get_metro_graph()
    # save_osmnx_graph(get_osmnx_graph(), "barcelona.pickle")
    # g1=get_osmnx_graph()
    # save_osmnx_graph(g1,"city.pickle")
    g1 = load_osmnx_graph("city.pickle")
    city = build_city_graph(g1, g2)
    show(city)
