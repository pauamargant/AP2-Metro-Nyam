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


find()-....

# Retornem els 12 elements amb més "importancia"
    # return [rst for rst in nlargest(1000, restaurants, key=lambda res: importance(query, res)) if importance(query, rst) > 0]

#IMPLEMENTACIO NORMAL

def interesting(query: str, res: Restaurant) -> bool:
    """returns if the restaurant is interesting according to the query"""
    # comenzamos con búsqueda básica, a mejorar más adelante
    query = normalize_str(query)
    return query in normalize_str(res.name) + normalize_str(res.adress.dist_name) + normalize_str(res.adress.nb_name) + normalize_str(res.adress.road_name)
