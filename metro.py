# IMPORTS
import pandas as pd
import networkx as nx
from staticmap import StaticMap, CircleMarker, Line
import matplotlib.pyplot as plt
from dataclasses import dataclass
from typing import List, Tuple, Dict
from typing_extensions import TypeAlias
from haversine import haversine


# Constants
STATION_FILE: str = "estacions.csv"
ACCESS_FILE: str = "accessos.csv"
SIZE_X: int = 1500
SIZE_Y: int = 1500
WALKING_SPEED: float = 1.42  # m/s
SUBWAY_SPEED: float = 7.22222222  # m/s
SUBWAY_WAITING: float = 60  # seconds
TRANSFER_TIME: float = 30  # seconds

Coord: TypeAlias = Tuple[float, float]
MetroGraph: TypeAlias = nx.Graph
NodeID: TypeAlias = int  # We use integers as ids

#   *****************
#   Class definitions
#   *****************


@dataclass
class Station:
    '''
    Class used to store subway stations.

    Attributes
    ----------
    id: int
    group_code: int
    name: str
    line_name: str
    line_id: int
    line_order: int
    line_colour: str
    line_orig: str
    line_dest: str
    accessibility: int
    position: Coord
    connections: List[int]
    accesses: List[int]
    line_transfers: List[int]
    '''
    id: int
    group_code: int
    name: str
    line_name: str
    line_id: int
    line_order: int
    line_colour: str
    line_orig: str
    line_dest: str
    accessibility: int
    position: Coord
    # list of the ids of the stations connected in the same line
    connections: List[int]
    accesses: List[int]  # List of the accesses id that go to the station
    line_transfers: List[int]  # List of the ids of the "transbords"


@dataclass
class Access:
    '''
    Class used to store subway access

    Attributes
    ----------
    code: int
    name: str
    station_id: int
    station_name: int
    group_code: int
    accessibility: int
    position: Coord
    '''
    code: int
    name: str
    station_id: int
    station_name: int
    group_code: int
    accessibility: int
    position: Coord


Stations: TypeAlias = List[Station]
Accesses: TypeAlias = List[Access]

#   *****************************
#   Reading stations and accesses
#   *****************************


def string_to_point(point_str: str) -> Coord:
    '''
    Given a string following the pattern "POINT (X Y)" returns a tuple (X,Y)

    Parameters
    ----------
    point_str: str

    Returns
    -------
    coordinates: Coord

    '''
    point: List[str] = point_str.split('(')[1].split(')')[0].split()
    return (float(point[0]), float(point[1]))


def create_station(row: pd.Series) -> Station:
    '''
    Given station information in a dataframe row, returns a Station with the
    relevant information.
    The given row is assumed to be of the expected format

    Parameters
    ----------
    row: pd.Series

    Returns
    -------
    station: Optional[Station]


    '''
    try:
        return Station(row["CODI_ESTACIO"], row["CODI_GRUP_ESTACIO"],
                       row["NOM_ESTACIO"], row["NOM_LINIA"], row["ID_LINIA"],
                       row["ORDRE_LINIA"], row["COLOR_LINIA"],
                       row["ORIGEN_SERVEI"], row["DESTI_SERVEI"],
                       row["ID_TIPUS_ACCESSIBILITAT"],
                       string_to_point(row["GEOMETRY"]), [], [], [])
    except Exception:
        raise TypeError("station row has the wrong format or incomplete data")


def read_stations() -> Stations:
    '''
    Reads all the stations from the STATION_FILE file and returns a list
    of Stations.

    Returns
    -------
    Stations
        List with all the valid stations in the file
    '''

    stations_df = pd.read_csv(STATION_FILE)
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
        return Access(row["CODI_ACCES"], row["NOM_ACCES"], row["ID_ESTACIO"],
                      row["NOM_ESTACIO"], row["CODI_GRUP_ESTACIO"],
                      row["ID_TIPUS_ACCESSIBILITAT"],
                      string_to_point(row["GEOMETRY"]))
    except Exception:
        print("access row has the wrong format or is incomplete")
        assert False


def read_accesses() -> Accesses:
    '''
    Reads all the accesses from a file (ACCESS_FILE) and returns
    a list of Accesses.

    Returns
    -------
    accesses: Accesses

    '''
    accesses_df = pd.read_csv(ACCESS_FILE)  # Encoding
    access_list: Accesses = []
    for index, row in accesses_df.iterrows():

        access_list.append(create_access(row))

    return access_list

#   **************
#   Creating graph
#   **************


def line_distance(g: MetroGraph, orig_id: NodeID, dest_id: NodeID) -> float:
    '''
        Calculates the distance (in meters) between two nodes in the given
        graph.

        Parameters
        ----------
        g: MetroGraph
        orig_id: NodeID
        dest_id: NOdeID

        Returns
        -------
        float
            Distance between orig_id and dest_id in g.
    '''
    return haversine(g.nodes[orig_id]["pos"],
                     g.nodes[dest_id]["pos"], unit="m")


def accessible_time(Metro: MetroGraph, orig_id: NodeID, dest_id: NodeID,
                    distance: float) -> float:
    '''
        Given a graph, two station/access nodes and a distance returns the
        travel time if both stations are accessible, if either of them is
        not accessible returns infinity.

        Parameters
        ----------
        Metro: MetroGraph
        orig_id: NodeID
        dest_id: NodeID
        distance: float

        Returns
        -------
        travel_time: float
    '''
    if(Metro.nodes[orig_id]["accessibility"] == 1 and
            Metro.nodes[dest_id]["accessibility"] == 1):
        return distance/SUBWAY_SPEED
    return float('inf')


def get_metro_graph() -> MetroGraph:
    '''
    Reads station and access data from STATION_FILE and ACCESS_FILE and
    creates a graph with the following characteristics:
    -Stations and accesses are nodes in the graph.
    -There is and edge between each access and its corresponding station
    -Subway lines are represented as edges between contiguous stations
     in the line.
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

    # We store line_transfers for each station group in a dict
    # in order to be more efficient
    line_transfers: Dict[int, List[NodeID]] = dict()

    # In order to connect subway lines we take adavantadge of the fact that
    # they are stored in order
    # We add the first station of the list before iterating through the rest
    s1: Station = station_list[0]
    prev_id: NodeID = s1.id
    prev_line: NodeID = s1.line_id
    Metro.add_node(s1.id, pos=s1.position, type="station", name=s1.name,
                   accessibility=s1.accessibility, line=s1.line_id,
                   line_name=s1.line_name, line_dest=s1.line_dest)
    line_transfers[s1.group_code] = [s1.id]
    distance: float
    for station in station_list[1:]:
        # We create the station node
        # If an station with the same id has previously been added, we still
        # add the new station but with the id being negative
        # This happens with some stations in lines L9, L10.
        id: NodeID = station.id
        if Metro.has_node(id):
            id = -id
        Metro.add_node(id, pos=station.position, type="station",
                       name=station.name, accessibility=station.accessibility,
                       line=station.line_id, line_name=station.line_name,)

        # We connect it with the previous station if they are in the same line
        if(station.line_id == prev_line):
            distance = line_distance(Metro, prev_id, id)
            Metro.add_edge(prev_id, id, type="line",
                           line_name=station.line_name,
                           line_colour=station.line_colour,
                           distance=distance, line_orig=station.line_orig,
                           line_dest=station.line_dest,
                           orientation=(prev_id, id),
                           travel_time=distance/SUBWAY_SPEED,
                           acc_travel_time=distance/SUBWAY_SPEED)
        prev_id, prev_line = id, station.line_id

        # If we have previously read a station in the same group we append
        # the current station id to the list of transfers.
        # Otherwise we create a new entry in the dict
        if line_transfers.get(station.group_code) is None:
            line_transfers[station.group_code] = [id]
        else:
            line_transfers[station.group_code].append(id)

    # We add the nodes corresponding to the accesses and connect each access
    # with its station
    for access in access_list:
        Metro.add_node(access.code, pos=access.position,
                       station=access.station_name,
                       accessibility=access.accessibility, type="access")
        distance = line_distance(
            Metro, access.code, access.station_id)

        Metro.add_edge(access.code, access.station_id, type="access",
                       distance=distance, travel_time=distance/WALKING_SPEED,
                       acc_travel_time=accessible_time(Metro, access.code,
                                                       access.station_id,
                                                       distance))

    # We connect stations which are in the same station group but are of
    # a different line
    for item in line_transfers.items():
        for id1, i1 in enumerate(item[1]):
            for i2 in item[1][id1+1:]:
                if(i1 != i2):
                    distance = line_distance(
                        Metro, i1, i2)
                    Metro.add_edge(
                        i1, i2, type="transfer",
                        line_name=Metro.nodes[i2]["line_name"],
                        distance=distance,
                        travel_time=distance/WALKING_SPEED + TRANSFER_TIME,
                        acc_travel_time=accessible_time(
                            Metro, i1, i2, distance) + TRANSFER_TIME)

    return Metro

#   ********************
#   Plotting and showing
#   ********************


def plot(g: MetroGraph, filename: str) -> None:
    '''
    Given a MetroGraph g and a filename we create an image of the graph
    g and save it with the corresponding filename.

    Parameters
    ----------
    g: Metrograph
        the graph we want to plot
    filename: str
        name of the file we create
    '''

    map: StaticMap = StaticMap(
        SIZE_X, SIZE_Y,
        url_template='http://a.tile.osm.org/{z}/{x}/{y}.png')
    for pos in nx.get_node_attributes(g, "pos").values():
        map.add_marker(CircleMarker(pos, 'red', 6))
    for edge in g.edges:
        map.add_line(
            Line([g.nodes[edge[0]]['pos'],
                  g.nodes[edge[1]]['pos']], 'blue', 3))
    try:
        image = map.render()
        image.save(filename)
    except Exception:
        print("Could not render or save image")


def show(g: MetroGraph) -> None:
    '''
    Given a MetroGraph g plots it interactively.

    Parameters
    ----------
    g: MetroGraph
        the graph to plot interactively
    '''
    positions: Dict[int, Coord] = nx.get_node_attributes(g, "pos")
    try:
        nx.draw(g, pos=positions, font_size=10,
                node_color="blue",
                node_size=50,)
        plt.show()
    except Exception:
        print("Could not show interactive plot")
