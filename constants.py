SIZE_X: int = 1500
SIZE_Y: int = 1500
HD_SIZE_X: int = 2500
HD_SIZE_Y: int = 2500
WALKING_SPEED: float = 1.42  # m/s
SUBWAY_SPEED: float = 7.22222222  # m/s o 8.61111111
TRANSFER_COLOR = 'orange'
STREET_COLOR = 'black'
ACCESS_COLOR = 'grey'

ID_OFFSET = 1000000


PADDING = 10
MAX_L = 1
MAX_DEL = 5
INF = 2147483647  # maximo de un int de 8 bits, quizás es más eficiente de cara a los cálculos

# PER AFEGIR WAITING TIMES PODRIEM USAR "GHOST STATION NODES" es a dir, que donaada una estacio, aquesta no estigui
# conectada a la linia de metro sino que es connecti a una "ghost station" situada a la mateixa pisicio amb una aresta
# amb pes temps d'espera i que sigui la ghost station la connectada a la linia demetro

SUBWAY_WAITING = 60  # segons
# tiempo de transfers, temporal, lo podemos remplazar por lo de las ghost stations
TRANSFER_TIME = 10
