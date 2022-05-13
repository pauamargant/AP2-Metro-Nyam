from dataclasses import dataclass
from typing import Optional, List, Tuple, Dict, Union
from typing_extensions import TypeAlias
import math
import pandas as pd


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
    return [restaurant for restaurant in restaurants if interesting(query, restaurant)]


lst = read()
x = find('King', lst)
for res in x:
    print(res.name)
