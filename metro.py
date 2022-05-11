# IMPORTS
import pandas as pd
import osmnx as ox
import networkx as nx
from staticmap import StaticMap, CircleMarker, Line
import matplotlib.pyplot as plt
from dataclasses import dataclass
from typing import Optional, TextIO, List, Tuple, Dict
from typing_extensions import TypeAlias

# Definim classes

Point = Tuple[float, float]  # -- float?
MetroGraph: TypeAlias = nx.Graph


@dataclass
class Station:
    # SHA DE MIRAR TEMA TIPUS DE DADES DE LES ID
    id: int
    group_code: int
    # A LA VERSIO FINAL TREURE IUSAR UN DICCIONARI SI FA FALTA (ESTALVIAR MEMORIA)
    name: str
    line_name: str
    line_id: int
    line_order: int
    line_colour: str
    accessibility: str
    position: Point
    # list of the ids of the stations connected in the same line
    connections: List[int]
    accesses: List[int]  # List of the accesses id that go to the station
    line_changes: List[int]  # List of the ids of the "transbords"

    def __hash__(self):
        return st_id


@dataclass
class Line:
    line_name: str
    line_colour: str


@dataclass
class Access:
    code: int  # FAIG SERVIR CODE PQ SI POSO ID ES LIA AMB LES ESTACIONS. SOLUCIO??
    name: str
    station_id: int
    station_name: int
    group_code: int
    accessibility: int
    position: Point


Stations = List[Station]

Accesses = List[Access]


def string_to_point(p: str) -> Point:
    # -- pq map?
    pt = p.split('(')[1].split(')')[0].split()
    return (float(pt[0]), float(pt[1]))


# COM FER EL TYPE HINTING AMB PANDAS?
def create_station(row) -> Station:
    return Station(row["CODI_ESTACIO"], row["CODI_GRUP_ESTACIO"], row["NOM_ESTACIO"],
                   row["NOM_LINIA"], row["ID_LINIA"], row["ORDRE_LINIA"], row["COLOR_LINIA"], row["NOM_TIPUS_ACCESSIBILITAT"], string_to_point(row["GEOMETRY"]), [], [], [])


def read_stations() -> Stations:
    # canviar per agafar de internet
    stations_df = pd.read_csv("data/estacions.csv")
    station_list: Stations = []
    for index, row in stations_df.iterrows():
        station_list.append(create_station(row))
    return station_list


def create_access(row) -> Access:
    return Access(row["CODI_ACCES"], row["NOM_ACCES"], row["ID_ESTACIO"], row["NOM_ESTACIO"], row["CODI_GRUP_ESTACIO"],
                  row["NOM_TIPUS_ACCESSIBILITAT"], string_to_point(row["GEOMETRY"]))


def read_accesses() -> Accesses:
    accesses_df = pd.read_csv("data/accessos.csv")  # CANVIAR!
    access_list: Accesses = []
    for index, row in accesses_df.iterrows():

        access_list.append(create_access(row))

    return access_list


def create_graph(station_list: Stations, access_list: Accesses):
    Metro = nx.Graph()
    transbord: Dict[int, List[int]] = dict()
    prev_id = None
    for station in station_list:
        # AQUI HAUREM DE VEURE QUE FA FALTA AFEGIR A LA LLARGA
        Metro.add_node(station.id, pos=station.position, type="station")
        if(prev_id != None and station.line_id == prev_line):
            Metro.add_edge(prev_id, station.id, type="line",
                           line=Line(station.line_name, station.line_order))
        prev_id = station.id
        prev_line = station.line_id
        if transbord.get(station.group_code, None) == None:
            transbord[station.group_code] = [station.id]
        else:
            transbord[station.group_code].append(station.id)

    for access in access_list:
        Metro.add_node(access.code, pos=access.position, type="access")
        Metro.add_edge(access.code, access.station_id,
                       type="access")  # -- tipus?

    for item in transbord.items():
        for id1 in range(len(item[1])):
            for id2 in range(id1+1, len(item[1])):
                if(item[1][id1] != item[1][id2]):
                    Metro.add_edge(item[1][id1], item[1]
                                   [id2], type="transbord")

    return Metro


def get_metro_graph() -> MetroGraph:
    station_list: Stations = read_stations()
    access_list: Accesses = read_accesses()
    # CANVIAR QUE RETORNI FUNCIO I POSAR COSA DE LA FUNCIO A DINS
    return create_graph(station_list, access_list)


def plot(g: MetroGraph, filename: str) -> None:

    map = StaticMap(3000, 3000)
    for pos in nx.get_node_attributes(g, "pos").values():
        map.add_marker(CircleMarker(pos, 'red', 6))
    for edge in g.edges:
        l = Line([g.nodes[edge[0]]['pos'], g.nodes[edge[1]]['pos']], 'blue', 3)
        map.add_line(l)
    image = map.render()
    image.save("prova.png")


def show(g: MetroGraph) -> None:
    positions = nx.get_node_attributes(g, "pos")
    fig, ax = plt.subplots()
    nx.draw(g, pos=positions, font_size=10,
            node_color="blue",
            node_size=50,)
    plt.show()


# def main():
    # Llegim les addes
station_list: Stations = read_stations()
access_list: Accesses = read_accesses()
Metro = create_graph(station_list, access_list)
# plot(Metro,"prova.png")
show(Metro)

# main()
