from dataclasses import dataclass
from typing import Optional, List, Tuple, Dict, Union
from typing_extensions import TypeAlias
import math
from fuzzysearch import find_near_matches
import pandas as pd
# PREGUNTAR SI PODEM FER SERVIR; ES ESTANDARD
import difflib
from heapq import nlargest


@dataclass
class Adress:
    road_id: int
    road_name: str
    street_n: Union[int, Tuple[int, int]]  # si es un rang guarda el rang
    nb_id: int  # Id del barri
    nb_name: str  # nom del barri
    dist_id: int
    dist_name: str
    zip_code: int


@dataclass
class Restaurant:
    id: int
    name: str
    adress: Adress
    tlf: str
    coords: Tuple[float, float]


Restaurants: TypeAlias = List[Restaurant]


def create_restaurant(row) -> Optional[Restaurant]:
    """Creates a restaurant from a row of the read data, returns None if the
    restaurant data is invalid"""
    try:
        adress = Adress(int(row['addresses_road_id']),
                        str(row['addresses_road_name']),
                        int(row['addresses_start_street_number']),
                        int(row['addresses_neighborhood_id']),
                        str(row['addresses_neighborhood_name']),
                        int(row['addresses_district_id']),
                        str(row['addresses_district_name']),
                        int(row['addresses_zip_code']))
        if not math.isnan(row['addresses_end_street_number']):
            adress.street_n = (int(row['addresses_start_street_number']),
                               int(row['addresses_end_street_number']))
        return Restaurant(int(row['register_id'][1:]),
                          str(row['name']),
                          adress,
                          str(row['values_value']),
                          (float(row['geo_epgs_4326_x']), float(row['geo_epgs_4326_y'])))
    except Exception:  # the restaurant's data is incomplete
        return None


def read() -> Restaurants:
    """Reads the open data and returns a list of all restaurants in barcelona """
    rest_data = pd.read_csv(
        "https://raw.githubusercontent.com/jordi-petit/ap2-metro-nyam-2022/main/data/restaurants.csv")
    rest_lst: Restaurants = []
    for index, row in rest_data.iterrows():
        if not rest_lst or row['register_id'] != rest_lst[-1].id:
            res = create_restaurant(row)
            if res is not None:
                rest_lst.append(create_restaurant(row))
    return rest_lst  # mirar lo de los acentos en nombres


def interesting(query: str, res: Restaurant) -> bool:
    """returns if the restaurant is interesting according to the query"""
    # comenzamos con búsqueda básica, a mejorar más adelante
    return query in res.name + res.adress.dist_name + res.adress.nb_name + res.adress.road_name


def find(query: str, restaurants: Restaurants) -> Restaurants:
    # Original implementation
    # return [restaurant for restaurant in restaurants if interesting(query, restaurant)]

    # Retornem els 12 elements amb més "importancia"
    return nlargest(12, restaurants, key=lambda res: importance(query, res))


def importance(query: str, res: Restaurant):
    '''
    Returns a value which determines the relevance of a restaurant
    '''

    # CONSTANTS:
    DN = 4  # Per donar mes relevancia al nom
    DA = 1  # Per modificar la reelvancia de la adreça
    MIN_N = 0.8  # Ratio minima per considerar un "Match" al nom
    MIN_A = 0.8  # Ratio minima per un match a l'adreça

    # Per cada paraula de la query calculem primer la ratio de match amb cada paraula del nom del restaurant
    # Despres fem el mateix amb les adreçes
    value = 0
    for q in query.split():
        max = 0
        for w in res.name.split():
            val = DN*difflib.SequenceMatcher(lambda x: x == " ", q, w).ratio()
            if(val is not None and val > 0.6 and val > max):
                if val > MIN_N:
                    max = 4*val
                else:
                    max = val
        value += max
        for w in (res.adress.nb_name + res.adress.road_name).split():
            val = DA*difflib.SequenceMatcher(lambda x: x == " ", q, w).ratio()
            if(val is not None and val > MIN_A and val > max):
                max = val
        value += max
    return value


def test(query):
    lst = read()
    x = find(query, lst)
    for res in x:
        print(res.name)
