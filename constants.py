SIZE_X: int = 1500
SIZE_Y: int = 1500
HD_SIZE_X: int = 2500
HD_SIZE_Y: int = 2500
WALKING_SPEED: float = 1.42  # m/s
SUBWAY_SPEED: float = 7.22222222  # m/s
TRANSFER_COLOR = 'red'
STREET_COLOR = 'black'
ACCESS_COLOR = 'grey'

PADDING = 50
MAX_L = 1
INF = 9999999999

# PER AFEGIR WAITING TIMES PODRIEM USAR "GHOST STATION NODES" es a dir, que donaada una estacio, aquesta no estigui
# conectada a la linia de metro sino que es connecti a una "ghost station" situada a la mateixa pisicio amb una aresta
# amb pes temps d'espera i que sigui la ghost station la connectada a la linia demetro

SUBWAY_WAITING=60#segons