import json
from dataclasses import dataclass
from typing import Optional, List, Tuple, Dict, Union, Set
import math
import requests
from typing_extensions import TypeAlias
import re
from fuzzysearch import find_near_matches
import pandas as pd


# Constants
RESTAURANT_FILE = "restaurants.csv"
MAX_L = 1
MAX_DEL = 5

Coord: TypeAlias = Tuple[float, float]


#   ************************
#   Additional Functionality
#   ************************
#   Without using any external package (only requests which is already)
#   required by the osmnx package, we use the Yelp (an online restaurant
#   rating platform) and its API to obtain additional information about
#   restaurants when using /info in the bot.
#   Not all restaurants can be found in Yelp, therefore if no information is
#   found we use the information from opendata barcelona.
#
#   More information about the api usage can be found at:
#   https://www.yelp.com/developers/documentation/v3/business_search
api_key = 'fKX1kpm-0ZL6ks4ZFucWXiFtpZOPmf06_kPJz3i73A-k1hM34oQy2OdKL9Sd0XQYKS\
3gujj7UQ9-pCsJrk9qJvNMIBd9Ph8Ywp3nrp-7V5bP5ljv7OIbYaBkoPiFYnYx'
headers = {'Authorization': 'Bearer %s' % api_key}
url = 'https://api.yelp.com/v3/businesses/search'


#   *****************
#   Class definitions
#   *****************

@dataclass
class Adress:
    '''
        DataClass used to store adress information

        Attributes
        ----------
        road_id: int
        road_name: str
            (It stores either a number or a tuple of street numbers):
            street_n: Union[int,Tuple[int,int]]
        nb_id: int
            Neighborhood id
        nb_name: str
            Neighborhood name
        dist_id: int
            District id
        dist_name: str
            District name
        zip_code: int
    '''
    road_id: int
    road_name: str
    street_n: Union[int, Tuple[int, int]]
    nb_id: int
    nb_name: str
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
    coords: Coord

    def __eq__(self, other) -> bool:
        return self.id == other.id

    def __hash__(self) -> int:
        return self.id


Restaurants: TypeAlias = List[Restaurant]


#   *******************
#   Reading restaurants
#   *******************

def read() -> Restaurants:
    """
    Reads data from the open data RESTAURANT_FILE file the and returns a list
    with all the valid Restaurants.
    We assume that the restaurant file has the expected format and structure

    Returns
    -------
    Restaurants
    """
    rest_data = pd.read_csv(
        RESTAURANT_FILE, delimiter=",", encoding='latin-1')
    rest_lst: Restaurants = []
    for _, row in rest_data.iterrows():
        if not rest_lst or row['register_id'] != rest_lst[-1].id:
            res: Optional[Restaurant] = create_restaurant(row)
            if res is not None:
                rest_lst.append(res)
    return rest_lst


def create_restaurant(row: pd.Series) -> Optional[Restaurant]:
    """
    Creates a restaurant from a row of the read data, returns None if the
    restaurant data is invalid

    Parameters
    ----------
    row: row in a dataframe of containing restaurant data

    Returns
    -------
    Optional[Restaurant]
        If possible Restaurant created from row data, else None
    """
    try:
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
                          (float(row['geo_epgs_4326_x']),
                          float(row['geo_epgs_4326_y'])))
    except Exception:
        print("Could not create restaurant. Check format of row data")
        return None

#   *******************************************
#   Finding restaurants and getting information
#   *******************************************


def find(query: str, rsts: Restaurants) -> Restaurants:
    '''
    Searchs restaurants based on a query which is an expression in a set
    algebra. If the query is a set of words separated by spaces, it is
    interpreted as ands.

    Parameters
    ----------
    query: str
    rsts: Restaurants

    Returns
    -------
    Restaurants

    '''

    # We first eliminate divide the query in operands and operators
    list_of_query: List[str] = [
        op for op in re.split('[,)()]', query) if op != ""]
    return list(rec_search(list_of_query, set(rsts)))


def rec_search(query: List[str], rsts: Set[Restaurant]) -> Set[Restaurant]:
    '''
    Given a query, peform recursively a restaurant search from a logical
    expression. The input is expected to be a list of str which consist of
    supported operators (and, or, not) and operands (search terms) in the
    correct order. The input is expected to come from the "find" function.

    Parameters
    ----------
    query: List[str]
    rsts: Set[Restaurant]

    Returns
    -------
    Set[Restaurants]
    '''
    current = query.pop(0)
    if current == "and":
        return rec_search(query, rsts).intersection(rec_search(query, rsts))
    if current == "or":
        return rec_search(query, rsts).union(rec_search(query, rsts))
    if current == "not":
        return rsts - rec_search(query, rsts)
    return multiword_search(current, rsts)


def multiword_search(query: str, rst: Set[Restaurant]) -> Set[Restaurant]:
    '''
        Given a query finds restaurants which satisfy the query. If the query
        consists of more than one word it fins restauants which satisfty all
        the words.

        Parameters
        ----------
        query: str
        rst: Set[Restaurant]
            Set of restaurants in which to perform the search

        Returns
        -------
        Set[Restaurants]
            List of restaurants which match the query. None if
            no restaurants match the query.
    '''
    query_list = query.split()
    if not query_list:
        return set()  # no elements to search
    results: Set[Restaurant] = set(search_in_rsts(query_list[0], rst))
    for q in query_list[1:]:
        results = results.intersection(search_in_rsts(q, rst))
    return results


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
        # If the length of the return of find_near_matches is greater than 0
        # it means that it has found at least one match.
        if len(find_near_matches(query, normalize_str(t), max_l_dist=MAX_L,
                                 max_deletions=MAX_DEL)) > 0:
            return True
    return False


def search_in_rsts(query: str, rest: Set[Restaurant]) -> Set[Restaurant]:
    '''
    Given a query and a list of restaurants returns a list of the restaurants
    which are "interesting" according to the query
    '''
    return set([restaurant for restaurant in rest if is_interesting(
        query, restaurant)])


def normalize_str(string: str) -> str:
    '''
    Normalizes a string (removes accents and some special characters)

    Parameters
    ----------
    string: str

    Returns
    -------
    str

    '''
    normalizeMap = {'à': 'a', 'á': 'a', 'ä': 'a',
                    'è': 'e', 'é': 'e', 'ë': 'e',
                    'í': 'i', 'ï': 'i',
                    'ò': 'o', 'ó': 'o', 'ö': 'o',
                    'ú': 'u', 'ü': 'u',
                    }
    return ''.join([normalizeMap.get(c, c) for c in string.lower()])


def get_yelp_info(rst: Restaurant) -> Optional[Dict[str, str]]:
    '''
        If possible find information about a restaurant using the Yelp API
        (OPTIONAL FEATURE)


        Parameters
        ----------
        rst: Restaurant

        Returns
        -------
        Optional[Dict[str,str]]
            If possible, a dictionary with information about the restaurant.
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
    except Exception:
        print("Error al realizar la request a l'API de YELP")
        return None


def get_info_message(rst: Restaurant) -> Tuple[str, Optional[str]]:
    '''
        Given a restaurant returns a string with formatted
        information about the restaurant.
        If possible tries to find additional informations.

        Parameters
        ----------
        rst: Restaurant

        Returns
        -------
        str
            Formatted string with information
        str
            Image url or None if the url is unexisting

    '''
    message = (f"Nom: {rst.name}\n"
               f"Adreça: {rst.adress.road_name}, nº{rst.adress.street_n}\n"
               f"Barri: {rst.adress.nb_name}\n"
               f"Districte: {rst.adress.dist_name}\n"
               f"Telèfon: {rst.tlf}\n")

    extra_info: Optional[Dict[str, str]] = get_yelp_info(rst)
    if extra_info is not None:
        if extra_info.get("rating") is not None:
            message += f"\nValoració {extra_info['rating']}"
        if extra_info.get("price") is not None:
            message += f"\nPreu {extra_info['price']}"
        return message, extra_info["image_url"]
    return message, None
