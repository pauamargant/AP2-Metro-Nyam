import json
import requests  # type: ignore
from dataclasses import dataclass
from typing import Optional, List, Tuple, Dict, Union
from typing_extensions import TypeAlias
import math
import re
from fuzzysearch import find_near_matches  # type: ignore
import pandas as pd  # type: ignore
from constants import *


RESTAURANT_FILE = "restaurants.csv"
# Informació extra api YELP
api_key = 'fKX1kpm-0ZL6ks4ZFucWXiFtpZOPmf06_kPJz3i73A-k1hM34oQy2OdKL9Sd0XQYKS3gujj7UQ9-pCsJrk9qJvNMIBd9Ph8Ywp3nrp-7V5bP5ljv7OIbYaBkoPiFYnYx'
headers = {'Authorization': 'Bearer %s' % api_key}
url = 'https://api.yelp.com/v3/businesses/search'


@dataclass
class Adress:
    '''
        DataClass used to store adress information

        Attributes
        ----------
        road_id: int
        road_name: str
        street_n: Union[int,Tuple[int,int]]     It stores either a number or a tuple of street numbers
        nb_id: int
        nb_name: str
        dist_id: int
        dist_name: str
        zip_code: int
    '''
    road_id: int
    road_name: str
    street_n: Union[int, Tuple[int, int]]
    nb_id: int  # Id del barri
    nb_name: str  # nom del barri
    dist_id: int
    dist_name: str
    zip_code: int


@dataclass
class Restaurant:
    '''
        Class used to store restaurants

        Attributes
        ----------
        id: int
        name: str
        adress: Adress
        tlf: str
        coords: Tuple[float,float]
    '''
    id: int
    name: str
    adress: Adress
    tlf: str
    coords: Tuple[float, float]

    def __eq__(self, other) -> bool:
        return self.id == other.id

    def __hash__(self) -> int:
        return self.id


Restaurants: TypeAlias = List[Restaurant]
Operand: TypeAlias = Optional[Union[str, Restaurants]]


def create_restaurant(row) -> Optional[Restaurant]:
    """Creates a restaurant from a row of the read data, returns None if the
    restaurant data is invalid

    Parameters
    ----------
    row: row in a dataframe of containing restaurant data

    Returns
    -------
    Optional[Restaurant]
        If possible Restaurant created from row data, else None 
    """

    if math.isnan(row['addresses_start_street_number']):
        if 'Notícia' in row['name']:
            return None  # It is not a restaurant
        row['addresses_start_street_number'] = -1
    # We create an Adress, taking a different approach depending on the
    # data available.
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
    """
    Reads data from the open data restaurants.csv file the and returns a list with all the valid Restaurants
    """
    rest_data = pd.read_csv(RESTAURANT_FILE, delimiter=",", encoding='latin-1')
    rest_lst: Restaurants = []
    for index, row in rest_data.iterrows():
        if not rest_lst or row['register_id'] != rest_lst[-1].id:
            res: Optional[Restaurant] = create_restaurant(row)
            if res is not None:
                rest_lst.append(res)
    return rest_lst


def is_interesting(query: str, res: Restaurant) -> bool:
    """
    Returns whether a restaurant is interesting according to the query

    Parameters
    ----------
    query:str
    res: Restaurant

    Returns
    -------
    bool
    """

    query = normalize_str(query)  # We normalize the query to improve results
    terms_of_interest = [res.name, res.adress.nb_name,
                         res.adress.dist_name, res.adress.road_name]
    for t in terms_of_interest:
        if len(find_near_matches(query, normalize_str(t), max_l_dist=MAX_L, max_deletions=MAX_DEL)) > 0:
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


def search_in_rsts(query: str, restaurants: Restaurants) -> Restaurants:
    '''
    Given a query and a list of restaurants returns a list of the restaurants which are "interesting"
    according to the query
    '''
    return [restaurant for restaurant in restaurants if is_interesting(query, restaurant)]


def is_operator(expression: str) -> bool:
    '''
    Given a string checks if it's a valid operator. 
    The following operators are accepted: "and","or","not"
    '''
    if isinstance(expression, str):
        expression_dict = {"and": True, "or": True, "not": True}
        return expression_dict.get(expression, False)
    return False


def perform_operation(rests: Restaurants, operator: str, operand_1: Operand, operand_2: Operand) -> Restaurants:
    '''
        Given an operator and one/two operands performs the operation on the opperand/s.
        Given an operator, if it's either "or" or "and" it performs the operation between the two
        operands. If it's "not" only one operand is needed.

        Operations are performed between lists of restaurants. If an operand is a string (a query) then
        it is replaced with the according list of restaurants. 
        The "not" operation is defined as the complement of the operand in set of all restaurants.

        Parameters
        ----------
        rests: Restaurants
        operator: str
        operand_1: Operand
        operand_2: Operand

        Returns
        -------
        Restaurants
    '''

    # The operands can be either a query (string) or a list of restaurants. If it's a query, we solve it and s
    # substitute it by the according list of restaurants
    if (operand_1 and isinstance(operand_1, str)):
        operand_1 = search_in_rsts(operand_1, rests)
    if (operand_2 and isinstance(operand_2, str)):
        operand_2 = search_in_rsts(operand_2, rests)
    if operator == "and":
        return list(set(operand_1).intersection(operand_2))
    if operator == "or":
        return list(set(operand_1).union(operand_2))
    if operator == "not":
        return list(set(rests) - set(operand_1))
    return []


def rec_search(query, rsts):
    current = query[0]
    query = query[1:]
    if is_operator(current):
        return rec_search((query, rsts), rec_search(query, rsts))
    return multiword_search(current, rsts)


def multiword_search(query, rst) -> Restaurants:
    '''
        Given a list of queries, performs the intersection of the results of 
        all the queries.
    '''
    query_list = query.split()
    results: Restaurants = rst
    print(query_list)
    for q in query_list:
        results = list(set(results).intersection(search_in_rsts(q, rst)))
    return results


def find(query: str, rsts: Restaurants) -> Optional[Restaurants]:
    '''
    Searchs restaurants based on a query which is an expression in a set algebra.
    If the query is a set of words separated by spaces, it is interpreted as ands.

    Parameters
    ----------
    query: str
    rsts: Restaurants

    Returns
    -------
    Optional[Restaurants]

    '''
    # We first eliminate divide the query in operands and operators
    list_of_query: List[str] = [
        op for op in re.split('[,)()]', query) if op != ""]
    return rec_search(list_of_query, rsts)
    # We check whether the query has any operator and whether it's a set of words separated by spaces.
    # If it has no operators it is interpeted as "and" between the words in the query

    # We performs the operations. As the operators are in preorder, we
    # traverse the list of query in reverse order

    # if(len(list_of_query) == 1):
    #     return multiword_search(list_of_query[0].split(), rsts)

    # stack: List[Operand] = []
    # operand_1: Operand
    # operand_2: Operand

    # for w in reversed(list_of_query):
    #     # If it's an operator we operate the last two elements in the stack
    #     if is_operator(w):
    #         if w == "not":
    #             operand_1, operand_2 = stack.pop(), None
    #         else:
    #             operand_1, operand_2 = stack.pop(), stack.pop()
    #         stack.append(perform_operation(
    #             rsts, w, operand_1, operand_2))
    #     # If it is an operand we add it to the stack
    #     else:
    #         stack.append(w)

    # if isinstance(stack[0], str):
    #     return search_in_rsts(stack[0], rsts)
    # else:
    #     return stack[0]


def yelp_info(rst: Restaurant) -> Optional[Dict[str, str]]:
    '''
        If possible find information about a restaurant using the Yelp API
        (OPTIONAL FEATURE)    
    '''
    try:
        params = {'term': rst.name,
                  'location': "barcelona"}
        req = requests.get(url, params=params, headers=headers)
        print('Request made with code {}'.format(req.status_code))
        if(req.status_code == 200):
            parsed = json.loads(req.text)
            info_rst = parsed["businesses"]
            if len(info_rst) > 0:
                return info_rst[0]
            return None
    except Exception as e:
        print("Error al realizar la request a l'API de YELP".format(e))
        return None


def info_message(rst: Restaurant, additional_info: Optional[Dict[str, str]]) -> str:
    message: str = f"Nom: {rst.name}\nAdreça: {rst.adress.road_name}, nº{rst.adress.street_n}\nBarri: {rst.adress.nb_name}\nDistricte: {rst.adress.dist_name}\nTelèfon: {rst.tlf}"
    if additional_info is not None:
        if additional_info["rating"] is not None:
            message += f"\n Valoració {additional_info['rating']}"
        if additional_info["price"] is not None:
            message += f"\n Preu {additional_info['price']}"
    return message


def main(query):
    lst = read()
    x = find(query, lst)
    for res in x:
        print(res.name)
    rst = x[0]
    print(yelp_info(rst))


def test(query):
    lst = read()
    for r in search_in_rsts(query, lst):
        print(r.name)
