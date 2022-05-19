from dataclasses import dataclass
from turtle import st
from typing import Optional, List, Tuple, Dict, Union
from typing_extensions import TypeAlias
import math
import re
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
    # Usat a la cerca (POTSER??)

    # def __eq__(self, other: Restaurant) -> bool:
    #     return self.id == other.id


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


def normalize_str(string):
    '''
    Normalizes a string
    '''
    normalMap = {'à': 'a', 'á': 'a', 'ä': 'a',
                 'è': 'e', 'é': 'e', 'ë': 'e',
                 'í': 'i', 'ï': 'i',
                 'ò': 'o', 'ó': 'o', 'ö': 'o',
                 'ú': 'u', 'ü': 'u',
                 }
    return string.lower().translate(str.maketrans(normalMap))


def find(query: str, restaurants: Restaurants) -> Restaurants:
    # Original implementation
    # return [restaurant for restaurant in restaurants if interesting(query, restaurant)]

    # Retornem els 12 elements amb més "importancia"
    return [rst for rst in nlargest(12, restaurants, key=lambda res: importance(query, res)) if importance(query, rst) > 0]


# def is_operator(expression: str) -> bool:
#     expression_dict = {"and": True, "or": True, "not": True}
#     return expression_dict.get(expression, False)


# def perform_operation(rst, current_operator: str, current_operands: Tuple[str]) -> Restaurants:
#     if current_operator == "and":
#         search_1, search_2 = find(current_operands[0], restaurants), find(
#             current_operands[1], restaurants)
#         return list(set(search_1).intersection(search_2))
#     if current_operator == "or":


# def search(query: str, restaurants: Restaurants) -> Restaurants:
#     # Dividim el query en els operadors i operants
#     query = [op for op in re.split('[,)()]', query) if op != ""]

#     stack = []
#     current_operator = ""
#     rst = Restaurants
#     for w in query:
#         if is_operator(w):
#             current_operator = w
#             current_operands = stack.pop(), stack.pop()
#             stack.append(perform_operation(
#                 rst, current_operator, current_operands))
#         else:
#             stack.append(w)


def importance(query: str, res: Restaurant):
    '''
    Returns a value which determines the relevance of a restaurant
    '''

    value = 0
    query = normalize_str(query)
    for q in query.split():
        match = find_near_matches(q, normalize_str(res.name), max_l_dist=1)
        if match:
            value += 2*(2-match[0].dist)
        match = find_near_matches(q, normalize_str(
            res.adress.nb_name), max_l_dist=1)
        if match:
            value += (2-match[0].dist)
    return value


def test(query):
    lst = read()
    x = find(query, lst)
    for res in x:
        print(res.name)
