from dataclasses import dataclass
from turtle import st
from typing import Optional, List, Tuple, Dict, Union
from typing_extensions import TypeAlias
import math
import re
from fuzzysearch import find_near_matches  # type: ignore
import pandas as pd  # type: ignore
from constants import *


# Informació extra api YELP
import requests  # type: ignore
import json
api_key = 'fKX1kpm-0ZL6ks4ZFucWXiFtpZOPmf06_kPJz3i73A-k1hM34oQy2OdKL9Sd0XQYKS3gujj7UQ9-pCsJrk9qJvNMIBd9Ph8Ywp3nrp-7V5bP5ljv7OIbYaBkoPiFYnYx'
headers = {'Authorization': 'Bearer %s' % api_key}
url = 'https://api.yelp.com/v3/businesses/search'


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

    def __eq__(self, other) -> bool:
        return self.id == other.id

    def __hash__(self) -> int:
        return self.id


Restaurants: TypeAlias = List[Restaurant]
Operand: TypeAlias = Optional[Union[str, Restaurants]]


def create_restaurant(row) -> Optional[Restaurant]:
    """Creates a restaurant from a row of the read data, returns None if the
    restaurant data is invalid"""
    if math.isnan(row['addresses_start_street_number']):
        if 'Notícia' in row['name']:
            return None  # no es un restaurant
        row['addresses_start_street_number'] = -1

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


def read() -> Restaurants:
    """Reads the open data and returns a list of all restaurants in barcelona """
    rest_data = pd.read_csv(
        "data/restaurants.csv")  # https://raw.githubusercontent.com/jordi-petit/ap2-metro-nyam-2022/main/data/restaurants.csv")
    rest_lst: Restaurants = []
    for index, row in rest_data.iterrows():
        if not rest_lst or row['register_id'] != rest_lst[-1].id:
            res: Optional[Restaurant] = create_restaurant(row)
            if res is not None:
                rest_lst.append(res)
    return rest_lst  # mirar lo de los acentos en nombres


def interesting(query: str, res: Restaurant) -> bool:
    """returns if the restaurant is interesting according to the query"""
    # comenzamos con búsqueda básica, a mejorar más adelante
    query = normalize_str(query)
    terms = [res.name, res.adress.nb_name,
             res.adress.dist_name, res.adress.road_name]
    for t in terms:
        if len(find_near_matches(query, normalize_str(t), max_l_dist=MAX_L)) > 0:
            return True
    return False


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


def search_in_rests(query: str, restaurants: Restaurants) -> Restaurants:
    '''
    Given a query and a list of restaurants returns a list of the restaurants which are "interesting"
    according to the query
    '''
    return [restaurant for restaurant in restaurants if interesting(query, restaurant)]


def is_operator(expression: str) -> bool:
    '''
    Given a string checks if it's a valid operator. 
    The following operators are accepted: "and","or","not"
    '''
    expression_dict = {"and": True, "or": True, "not": True}
    return expression_dict.get(expression, False)


def perform_operation(rests: Restaurants, current_operator: str, operand_1: Operand, operand_2: Operand) -> Restaurants:
    '''
        Given an operator and one/two operands performs the operation on the opperand/s.
    '''
    # The operands can be either a query (string) or a list of restaurants. If it's a query, we solve it and s
    # substitute it by the according list of restaurants

    if (operand_1 and isinstance(operand_1, str)):
        operand_1 = search_in_rests(operand_1, rests)
    if (operand_2 and isinstance(operand_2, str)):
        operand_2 = search_in_rests(operand_2, rests)
    if current_operator == "and":
        return list(set(operand_1).intersection(operand_2))
    if current_operator == "or":
        return list(set(operand_1).union(operand_2))
    if current_operator == "not":
        return list(set(rests) - set(operand_1))
    return []


def multiword_search(query_list, rst) -> Restaurants:
    '''
        Given a list of queries, performs the intersection of the results of 
        all the queries.
    '''
    results: Restaurants = rst
    for q in query_list:
        results = list(set(results).intersection(search_in_rests(q, rst)))
    return results


def find(query: str, rst: Restaurants) -> Optional[Restaurants]:
    '''Searchs restaurants based on a query which is a logical expression. If the query is a set of 
    words separated by spaces, it is interpreted as ands'''
    # Dividim el query en els operadors i operants
    list_of_query: List[str] = [
        op for op in re.split('[,)()]', query) if op != ""]
    # Comprovem si la query no conte operadors logic i per tant no s'ha separat i a més a més
    # esta formada per varies paraules sep per espais. Ho interpretem com la interseccio de totes les
    # paraules

    if(len(list_of_query) == 1 and len(list_of_query[0].split()) > 1):
        return multiword_search(list_of_query[0].split(), rst)
    stack: List[Operand] = []
    operand_1: Operand
    operand_2: Operand
    for w in reversed(list_of_query):
        if is_operator(w):
            if w == "not":
                operand_1, operand_2 = stack.pop(), None
            else:
                operand_1, operand_2 = stack.pop(), stack.pop()
            stack.append(perform_operation(
                rst, w, operand_1, operand_2))
        else:
            stack.append(w)

    if isinstance(stack[0], str):
        return search_in_rests(stack[0], rst)
    else:
        return stack[0]


def yelp_info(rst: Restaurant):
    params = {'term': rst.name,
              'location': 'Barcelona'}
    req = requests.get(url, params=params, headers=headers)
    print('The status code is {}'.format(req.status_code))
    if(req.status_code == 200):
        parsed = json.loads(req.text)
        info_rst = parsed["businesses"]
        if len(info_rst) > 0:
            print(info_rst[0])


def main(query):
    lst = read()
    x = find(query, lst)
    for res in x:
        print(res.name)
    rst = x[0]
    print(yelp_info(rst))


def test(query):
    lst = read()
    for r in search_in_rests(query, lst):
        print(r.name)
