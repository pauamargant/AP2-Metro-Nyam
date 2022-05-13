# IMPORTS
from logging import exception
import pandas as pd
import osmnx as ox
import networkx as nx
from staticmap import StaticMap, CircleMarker, Line
import matplotlib.pyplot as plt
from dataclasses import dataclass
from typing import Optional, TextIO, List, Tuple, Dict
from typing_extensions import TypeAlias


# CONSTANTS

SIZE_X: int = 1500
SIZE_Y: int = 1500


# Definim classes

Coord: TypeAlias = Tuple[float, float]
MetroGraph: TypeAlias = nx.Graph


@dataclass
class Station:
    '''
    Class used to store subway stations.
    '''
    id: int
    group_code: int
    name: str
    line_name: str
    line_id: int
    line_order: int
    line_colour: str
    accessibility: str
    position: Coord
    # list of the ids of the stations connected in the same line
    connections: List[int]
    accesses: List[int]  # List of the accesses id that go to the station
    line_transfers: List[int]  # List of the ids of the "transbords"
    # Not used:
    # def __hash__(self):
    #   return st_id


@dataclass
class Access:
    '''
    Class used to store subway access
    '''
    code: int  # FAIG SERVIR CODE PQ SI POSO ID ES LIA AMB LES ESTACIONS. SOLUCIO??
    name: str
    station_id: int
    station_name: int
    group_code: int
    accessibility: int
    position: Coord


Stations = List[Station]

Accesses = List[Access]


def string_to_point(point_str: str) -> Coord:
    '''
    Given a string following the pattern "POINT (X Y)" returns a tuple (X,Y)

    Parameters
    ----------
    point_str: str

    Returns
    -------
    coordinates: Coords

    '''
    point: List[str] = point_str.split('(')[1].split(')')[0].split()
    return (float(point[0]), float(point[1]))


# COM FER EL TYPE HINTING AMB PANDAS?
def create_station(row: pd.Series) -> Station:
    '''
    Given station information in a dataframe row, returns a Station with the relevant information
    The given row is assumed to be of the expected format

    Parameters
    ----------
    row: pd.Series

    Returns
    -------
    station: Station


    '''
    try:
        return Station(row["CODI_ESTACIO"], row["CODI_GRUP_ESTACIO"], row["NOM_ESTACIO"],
                       row["NOM_LINIA"], row["ID_LINIA"], row["ORDRE_LINIA"], row["COLOR_LINIA"],
                       row["NOM_TIPUS_ACCESSIBILITAT"], string_to_point(row["GEOMETRY"]), [], [], [])
    except Exception:
        print("station row has the wrong format or incomplete data")


def read_stations() -> Stations:
    '''
    Reads all the stations from the estations.csv file and returns a list of Stations
    '''
    # AL FINAL CANVIAR DE ON SE AGAFA?
    stations_df = pd.read_csv("data/estacions.csv", encoding='latin1')
    station_list: Stations = []
    for index, row in stations_df.iterrows():
        station_list.append(create_station(row))
    return station_list


def create_access(row: pd.Series) -> Access:
    '''
    Given a row in a dataframe of access returns an Access

    Parameters
    ----------
    row: pd.Series

    Returns
    -------
    access: Access
    '''
    try:
        return Access(row["CODI_ACCES"], row["NOM_ACCES"], row["ID_ESTACIO"], row["NOM_ESTACIO"], row["CODI_GRUP_ESTACIO"],
                      row["NOM_TIPUS_ACCESSIBILITAT"], string_to_point(row["GEOMETRY"]))
    except Exception:
        print("access row has the wrong format or is incomplete")


def read_accesses() -> Accesses:
    # A QUIN ARXIU AL FINAL?
    '''
    Reads all the accesses in the file ###NOM### and returns a list of Accesses.
    '''
    accesses_df = pd.read_csv(
        "data/accessos.csv", encoding='latin1')  # CANVIAR!
    access_list: Accesses = []
    for index, row in accesses_df.iterrows():

        access_list.append(create_access(row))

    return access_list


def get_metro_graph() -> MetroGraph:
    '''
    Reads station and access data from STATION_FILE and ACCESS_FILE and creates a graph with the
    following characteristics:
    -Stations and accesses are nodes in the graph. 
    -There is and edge between each access and its corresponding station
    -Subway lines are represented as edges between contiguous stations in the line.
    -Stations of the same group but different line are connected by an edge.

    Returns
    -------
    Metro: MetroGraph
    '''
    # We read the data
    station_list: Stations = read_stations()
    access_list: Accesses = read_accesses()

    # We create the graph
    Metro: MetroGraph = nx.Graph()
    # We will store line_transfers for each station group in a dict
    # in order to be more efficient
    line_transfers: Dict[int, List[int]] = dict()

    # In order to connect subway lines we take adavantadge of the fact that they are
    # stored in order
    # We add the first station of the list before iterating through the others
    s1 = station_list[0]
    prev_id: Optional[int]= s1.id
    prev_line: Optional[int] = s1.line_id
    Metro.add_node(s1.id, pos=s1.position, type="station",
                       accessibility=s1.accessibility, line=s1.line_id)
    line_transfers[s1.group_code] = [s1.id]
    
    for station in station_list[1:]:
        # We create the station node
        Metro.add_node(station.id, pos=station.position, type="station",
                       accessibility=station.accessibility, line=station.line_id)

        # If the previous station is in the same line, we connect them
        if(station.line_id == prev_line):
            Metro.add_edge(prev_id, station.id, type="line",
                           line_name=station.line_name, line_colour=station.line_colour)
        prev_id, prev_line = station.id, station.line_id

        # If we have previously read a station in the same group we append the current
        # station id to the list of transfers. Otherwise we create a new entry in the dict
        if line_transfers.get(station.group_code) is None:
            line_transfers[station.group_code] = [station.id]
        else:
            line_transfers[station.group_code].append(station.id)

    # We add the nodes corresponding to the accesses and connect each access with its station
    for access in access_list:
        Metro.add_node(access.code, pos=access.position, type="access")
        Metro.add_edge(access.code, access.station_id, type="access")

    # We connect stations which are in the same station group but are of a different line

    # PODEM FERHO MILLOR??????????????????????????????????????
    for item in line_transfers.items():
        for id1, i1 in enumerate(item[1]):
            for i2 in item[1][id1+1:]:
                if(i1 != i2):
                    Metro.add_edge(i1, i2, type="transbord")

    return Metro


def plot(g: MetroGraph, filename: str) -> None:
    '''
    Given a MetroGraph g and a filename we create an image of the graph
    g and save it with the corresponding filename
    '''

    map: StaticMap = StaticMap(SIZE_X, SIZE_Y)
    for pos in nx.get_node_attributes(g, "pos").values():
        map.add_marker(CircleMarker(pos, 'red', 6))
    for edge in g.edges:
        map.add_line(
            Line([g.nodes[edge[0]]['pos'], g.nodes[edge[1]]['pos']], 'blue', 3))
    image = map.render()
    image.save(filename)


def show(g: MetroGraph) -> None:
    '''
    Given a MetroGraph g plots it interactively
    '''
    positions: Dict[int, Coord] = nx.get_node_attributes(g, "pos")
    nx.draw(g, pos=positions, font_size=10,
            node_color="blue",
            node_size=50,)
    #plt.show()
    plt.savefig('plot.svg')

