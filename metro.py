#IMPORTS
import pandas as pd
import osmnx as ox
import networkx as nx
import matplotlib.pyplot as plt

from dataclasses import dataclass
from typing import Optional, TextIO, List, Tuple

#Definim classes

Point = Tuple[int,int]
    
@dataclass
class Station:
    #SHA DE MIRAR TEMA TIPUS DE DADES DE LES ID
    id: str
    group_code: int
    name: str #A LA VERSIO FINAL TREURE IUSAR UN DICCIONARI SI FA FALTA (ESTALVIAR MEMORIA)
    line_name: str
    line_id: int
    line_order: int
    accessibility: str
    position: Point
    connections: list[str] #list of the ids of the stations connected in the same line
    accesses: list[str] #list of the accesses id that go to the station
    line_changes: list[str] #List of the ids of the "transbords"
    # def __init__(self, row):
    #     self.id = row["ID_ESTACIO"]
    #     self.group_code = row["CODI_GRUP_ESTACIO"]
    #     self.name = row["NOM_ESTACIO"]
    #     self.line_name = row["NOM_LINIA"]
    #     self.line_id = row["ID_LINIA"]
    #     self.line_order = row["ORDRE_LINIA"]
    #     self.accessibility = row["ACCESSIBILITAT"]
    #     self.position = row["GEOMETRY"]
    #     self.connections = []
    #     self.accesses = []
    #     self.line_changes = []
    

    def __hash__(self):
        return st_id

@dataclass
class Access:
    code: int #FAIG SERVIR CODE PQ SI POSO ID ES LIA AMB LES ESTACIONS. SOLUCIO??
    name: str
    station_id: int
    station_name: int
    group_code: int
    accessibility: int
    position: Point
    
Stations = List[Station]

Accesses = List[Access]

#COM FER EL TYPE HINTING AMB PANDAS?
def create_station(row)-> Station:
    p = row["GEOMETRY"]
    p=tuple(map(float,(p.split('(')[1].split(')')[0].split())))
    return Station(row["CODI_ESTACIO"],row["CODI_GRUP_ESTACIO"],row["NOM_ESTACIO"],row["NOM_LINIA"],row["ID_LINIA"],row["ORDRE_LINIA"],row["NOM_TIPUS_ACCESSIBILITAT"],p,[],[],[])

def read_stations() -> Stations:
    stations_df = pd.read_csv("data/estacions.csv") #canviar per agafar de internet
    station_list: Stations = []
    for index,row in stations_df.iterrows():
        station_list.append(create_station(row))
    return station_list

def create_access(row)->Access:
    p = row["GEOMETRY"]
    p=tuple(map(float,(p.split('(')[1].split(')')[0].split())))
    return Access(row["CODI_ACCES"],row["NOM_ACCES"],row["ID_ESTACIO"],row["NOM_ESTACIO"],row["CODI_GRUP_ESTACIO"],row["NOM_TIPUS_ACCESSIBILITAT"],p)

def read_accesses()->Accesses:
    accesses_df = pd.read_csv("data/accessos.csv")# CANVIAR!
    access_list: Accesses = []
    for index,row in accesses_df.iterrows():
        
        access_list.append(create_access(row))

    return access_list

def create_graph ( station_list: Stations, access_list:Stations):
    Metro = nx.Graph()
    lines = [] #hi guardem temporalment les arestes corresponents a la connexio en metro entre estacions de una mateixa linia
    i = 0
    prev_id = None
    for station in station_list:
        Metro.add_node(station.id,pos = station.position, tipus = "station") #AQUI HAUREM DE VEURE QUE FA FALTA AFEGIR A LA LLARGA  
        # if(station.line_order>1 and station.line_id == prev_line):
        #     lines.append([prev_id,station.id])
        if(prev_id!= None and station.line_id == prev_line):
            lines.append([prev_id,station.id])
        prev_id = station.id
        prev_line = station.line_id
    Metro.add_edges_from(lines)
    lines = []
    for access in access_list:
        Metro.add_node(access.code,pos = access.position, tipus = "access")
        lines.append([access.code,access.station_id])
    Metro.add_edges_from(lines)
    return Metro


def main():
#Llegim les addes
    station_list: Stations = read_stations()
    access_list: Accesses = read_accesses()
    Metro = create_graph(station_list,access_list)
    for i in station_list:
        if(i==None):
            print("merda ",i)
    for i in access_list:
        if(i==None):
            print("merda ",i)
    positions = nx.get_node_attributes(Metro,"pos")
    fig,ax=plt.subplots()
    nx.draw(Metro,pos=positions,font_size   = 10,
        node_color  = "blue",
        node_size   = 50,)
    plt.show()


main()
