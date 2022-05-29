from ast import Raise

from pyrsistent import b
import metro

# import pandas as pd
import osmnx as ox
import networkx as nx
from staticmap import StaticMap, CircleMarker, Line
import matplotlib.pyplot as plt
from dataclasses import dataclass
from typing import Optional, TextIO, List, Tuple, Dict, Union
from typing_extensions import TypeAlias
import pickle as pkl
import os.path
from datetime import datetime, timedelta
from haversine import haversine, Unit
from constants import *


PICKLE_FILENAME: str = "barcelona.grf"


# We define necessary TypeAlias
CityGraph: TypeAlias = nx.Graph
OsmnxGraph: TypeAlias = nx.MultiDiGraph
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
            graph: OsmnxGraph = ox.graph_from_place(
                "Barcelona, Spain", network_type="walk", simplify=True)
            for u, v, key, geom in graph.edges(data="geometry", keys=True):
                if geom is not None:
                    del(graph[u][v][key]["geometry"])
            for node in graph.nodes():
                graph.nodes[node]["pos"] = (
                    graph.nodes[node]["x"], graph.nodes[node]["y"])
                graph.nodes[node]["type"] = "street_intersection"

            # Necessary to remove self loops
            graph.remove_edges_from(nx.selfloop_edges(graph))

            for edge in graph.edges:
                distance: float = haversine(graph.nodes[edge[0]]["pos"],
                                            graph.nodes[edge[1]]["pos"],
                                            unit="m")
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
        pickle_out: IO = open(filename, "wb")
        pkl.dump(g, pickle_out)
        pickle_out.close()
    except Exception as error:
        print("Error while saving osmnx_graph")


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
            pickle_in: IO = open(filename, "rb")
            return pkl.load(pickle_in)
        except Exception as error:
            print("Could not retrieve osmnx graph")


def nearest_nodes(g1: OsmnxGraph, g2: MetroGraph) \
        -> Tuple[List[NodeID], List[NodeID], List[float]]:
    '''
    Given a OsmnxGraph g1 and a MetroGraph g2 finds for each access in g2 the
    nearest node to that access in g2, together with the distance to it.

    Parameters
    ----------
    g1: OsmnxGraph
    g2: MetroGraph

    Returns
    -------
    List[Tuple[NodeID,NodeID,float]
        A list with contains for each acces in g2 a tupple with the access
        node id, the id of the nearest node in g1 and the distance to it.
    '''
    if not isinstance(g1, OsmnxGraph):
        raise TypeError("g1 must be an OsmnxGraph")
    if not isinstance(g2, MetroGraph):
        raise TypeError("g2 must be a MetroGraph")
    nodes: List[NodeID] = []
    X: List[float] = []
    Y: List[float] = []
    for node, value in g2.nodes(data=True):
        coords = value["pos"]
        X.append(coords[0])
        Y.append(coords[1])
        nodes.append(node)
    nearest, distances = ox.distance.nearest_nodes(g1, X, Y, return_dist=True)
    return nodes, nearest, distances


def build_city_graph(g: OsmnxGraph, g2: MetroGraph) -> CityGraph:
    '''
    Given a OsmnxGraph g1 and a MetroGraph g2, unites both Graphs and connects
    each access in g2 to the nearest node in g1.

    Parameters
    ----------
    g1: OsmnxGraph
    g2: MetroGraph

    Returns
    -------
    city: CityGraph

    '''
    nodes, nearest, distances = nearest_nodes(g, g2)

    # We convert g1 from Multidigraph to graph
    g1: CityGraph = nx.Graph(g)
    city: CityGraph = nx.union(g1, g2)
    for n1, n2, d in zip(nodes, nearest, distances):
        city.add_edge(n1, n2, type="Street", distance=d,
                      travel_time=d/WALKING_SPEED,
                      acc_travel_time=d/WALKING_SPEED)
    return city


def find_path(ox_g: OsmnxGraph, g: CityGraph, src: Coord, dst: Coord,
              accessibility: bool = False) -> Path:
    '''
    Given a CityGraph g, a starting point src and a destination point dst we
    generate the shortest path (in travel time) between the two positions and
    we return the path.
    Depending on the accessibility parameter (which is false by default) will
    be accessible or not.

    Parameters:
    -----------
    ox:g: OsmnxGraph
    g: CityGraph
    src: Coord
        Coordinates of the source point.
    dst:Coord
        Coordinates of the destination.
    accessibility: bool
        False by default

    Returns
    -------
    p: Path
    '''
    src_node: NodeID = ox.distance.nearest_nodes(ox_g, src[1], src[0])
    dst_node: NodeID = ox.distance.nearest_nodes(ox_g, dst[1], dst[0])
    weight_param: str = 'acc_travel_time' if accessibility else 'travel_time'
    p: Path = nx.shortest_path(g, src_node, dst_node, weight=weight_param)
    return p


def plot(g: MetroGraph, filename: str) -> None:
    '''
    Given a CityGraph g and a filename we create an image of the graph
    g and save it with the corresponding filename
    '''
    # color for each set of edges, blue is the default

    colorEdges: Dict[str, str] = {'line': 'blue', 'street': 'yellow',
                                  'transfer': 'orange', 'Street': 'orange',
                                  'access': 'blue'}
    colorNodes: Dict[str, str] = {'station': 'red', 'access': 'black',
                                  'street_intersection': 'green'}
    map: StaticMap = StaticMap(
        SIZE_X, SIZE_Y, url_template='http://a.tile.osm.org/{z}/{x}/{y}.png')
    for u, node in g.nodes(data=True):
        map.add_marker(CircleMarker(node.get('pos'),
                       colorNodes.get(node.get('type'), 'green'), 4))
    for edge in g.edges(data=True):
        n0: NodeID = g.nodes[edge[0]]
        n1: NodeID = g.nodes[edge[1]]
        map.add_line(Line([n0['pos'], n1['pos']],
                     colorEdges[edge[2]['type']], 2))
    try:
        image = map.render()
        image.save(filename)
    except Exception as error:
        print("Could not render or save image")


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


def plot_path(g: CityGraph, p: Path, filename: str,
              orig: Coord, dest: Coord) -> None:
    '''
        Given a path p plots it using the citygraph and the orig and dest
        coordinates and saves it into a file.

        Parameters
        ----------
        g: CityGraph
        p: Path
        filename: str
            The filenamen of the saved image
        orig: Coord
        dest: Coord
    '''

    map: StaticMap = StaticMap(
        SIZE_X, SIZE_Y, padding_x=PADDING, padding_y=PADDING,
        url_template='http://a.tile.osm.org/{z}/{x}/{y}.png')
    if p:
        for prev_node, node in zip(p, p[1:]):
            map.add_line(Line([g.nodes[prev_node]['pos'],
                               g.nodes[node]['pos']],
                              edge_color(g, prev_node, node), 6))

        map.add_marker(CircleMarker(g.nodes[p[0]]['pos'], 'blue', 10))
        map.add_marker(CircleMarker(g.nodes[p[-1]]['pos'], 'red', 10))
    try:
        image = map.render()
        image.save(filename)
    except Exception as error:
        print("Could not render or save image")


def time_dist_txt(g: CityGraph, p: Path, orig: Coord):
    '''
        Given a path and a CityGraph calculates the time and distance of the
        path

        Parameters
        ----------
        g: CityGraph
        p: Path
        orig: Coord

        Returns
        -------
        text: str
    '''
    dist: float = haversine(
        (orig[1], orig[0]), g.nodes[p[0]]["pos"], unit='m')
    t: float = dist/WALKING_SPEED
    for id1, id2 in zip(p, p[1:]):
        dist += g.edges[(id1, id2)]['distance']
        t += g.edges[(id1, id2)]['travel_time']

    return f"⏳  Temps total {time_txt(t)}, distància {dist_txt(dist)}"


def time_txt(t: float) -> str:
    """
    Generates a text with the correct format from the time in seconds.

    Parameters
    ----------
    t: float
        time in seconds

    Returns
    -------
    str
        Formatted message with the time in format

    """
    if t < 60:
        return f"{t} s"
    t = round(t/60)
    return f"{t} min" if t <= 60 else f"{t//60} h {t%60} min"


def dist_txt(dist: float) -> str:
    """
    generates a text with the correct format from the distance in meters

    Parameters
    ----------
    dist: float
        distance in meters

    Returns
    -------
    str
        Formatted distance text

    """
    dist = round(dist)
    return f"{dist} m" if dist < 1000 else f"{dist//1000} km {dist%1000} m"


def path_txt(g: CityGraph, p: Path, orig: Coord, dest: Coord) -> str:
    '''
        Generates a resumed set of instructions from a Path in form of a
        text message

        Parameters
        ----------
        g: CityGraph
        p: Path
        orig: Coord
        dest: Coord

        Returns
        -------
        A message of the resumed path (street and time)
    '''
    try:
        now: datetime = datetime.now()
        path_txt: str = f"{time_dist_txt(g, p, orig)}\n🔵 La teva ubicació\n"
        i: int = 1
        n: int = len(p)
        street_types: List[str] = ['street', 'Street', 'access']
        dist: float = haversine(
            (orig[1], orig[0]), g.nodes[p[0]]["pos"], unit='m')
        t: float = 0
        while i < n:
            edge = g.edges[p[i-1], p[i]]
            if edge['type'] in street_types:
                while edge['type'] in street_types:
                    dist += edge['distance']
                    t += edge['travel_time']
                    i += 1
                    if i >= n:
                        break
                    edge = g.edges[p[i-1], p[i]]
                # we update the message
                path_txt += (f"🚶‍ {now.strftime('%H:%M')} | "
                             f"Camina {time_txt(t)} ({dist_txt(dist)})\n")
                now += timedelta(seconds=t)
                dist, t = 0, 0

            fst_edge = edge
            stops: int = 0
            if edge['type'] == 'line':
                line_dest = edge['line_dest'
                                 if edge['orientation'] == (p[i-1], p[i])
                                 else 'line_orig']
                path_txt += (f"Ⓜ️ {now.strftime('%H:%M')} | Agafa la linea "
                             f"{edge['line_name']} en "
                             f"{g.nodes[p[i-1]]['name']}, amb direcció "
                             f"{line_dest}\n")
                while edge['type'] == 'line':
                    dist += edge['distance']
                    t += edge['travel_time']
                    i += 1
                    stops += 1
                    if i >= n:
                        break
                    edge = g.edges[p[i-1], p[i]]
                # we update the message
                path_txt += (f"🚊 Espera't {stops} parades ({time_txt(t)}) i "
                             f"baixa't a {g.nodes[p[i-1]]['name']}\n")
                now += timedelta(seconds=t)
                dist, t = 0, 0

            if edge['type'] == 'transfer':
                i += 1
                edge = g.edges[p[i-1], p[i]]
                dist += edge['distance']
                t += edge['travel_time']
                if fst_edge['type'] == edge['type'] == 'line' and\
                        fst_edge['line_name'] != edge['line_name']:
                    path_txt += (f"🔳 {now.strftime('%H:%M')} | Transbord de "
                                 f"la línia {fst_edge['line_name']} a la "
                                 f"línia {edge['line_name']}\n")
                now += timedelta(seconds=edge['travel_time'])

            dist = 0

        return path_txt + f"📍 {now.strftime('%H:%M')}"
    except Exception as e:
        print(e)
        print("Could not create elaborate message, returning simple message")
        return time_dist_txt(g, p, orig)


def show(g: CityGraph) -> None:
    '''Shows the CityGraph g in a interative window'''
    positions: Dict[NodeID, str] = nx.get_node_attributes(g, "pos")
    nx.draw(g, positions, node_size=5)
    plt.show()


def main():
    g2 = metro.get_metro_graph()
    g1 = get_osmnx_graph()
    city = build_city_graph(g1, g2)
    orig = (41.388492, 2.113043)
    dest = (41.3733898465379, 2.136240845303527)
    p: Path = find_path(g1, city, orig, dest)
    # print(path_stats(city, p, orig, dest))
    # print(path_time_dist(city, p, orig, dest))
    # # show(city)
    # # plot_path(city, p, "path.png",  orig, dest)
    # plot(city, 'cityTest.png')
    # print(time.time()-t1)
    plot_path(city, p, 'borrame.png', orig, dest)
    print(path_txt(city, p, orig, dest))


# if __name__ == "__main__":
#     main()
