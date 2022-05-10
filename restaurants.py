from dataclasses import dataclass
from typing import Optional, List, Tuple, Dict, TypeAlias

import pandas as pd


@dataclass
class Restaurant:
    ...


Restaurants: TypeAlias = List[Restaurant]


def read() -> Restaurants:
    url = 'https://raw.githubusercontent.com/jordi-petit/ap2-metro-nyam-2022/main/data/restaurants.csv'
    return pd.read_csv(url, usecols=['name'])


def find(query: str, restaurants: Restaurants) -> Restaurants: ...


lst = read()
print(lst)
