# importa l'API de Telegram
from bdb import effective
from dataclasses import dataclass
import sys
import os
import time
from sklearn.metrics import homogeneity_completeness_v_measure
from telegram import Location
from telegram.ext import Updater, CommandHandler, Filters, MessageHandler
import logging
import random
from dataclasses import dataclass
from typing import Optional, TextIO, List, Tuple, Dict, Union
from typing_extensions import TypeAlias
import traceback
from haversine import haversine

# We import the base modules
import metro
import city
import restaurants


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

Coord: TypeAlias = Tuple[float, float]
NodeID: TypeAlias = int
Path: TypeAlias = List[NodeID]


# We import the token
try:
    TOKEN = open('token.txt').read().strip()
except IOError:
    print("Could not read the token.txt file")
    sys.exit()

#   **************
#   INITIALIZATION
#   **************

print("Initializing bot\n ----------------")
t1 = time.time()
metro_graph: metro.MetroGraph = metro.get_metro_graph()
print('get_metro_graph time:', time.time() - t1)
t2 = time.time()
city_osmnx = city.get_osmnx_graph()
print('get_osmnx_graph time:', time.time() - t2)
t2 = time.time()
city_graph: city.CityGraph = city.build_city_graph(city_osmnx, metro_graph)
print('build_city_graph time:', time.time() - t2)
t2 = time.time()
rest: restaurants.Restaurants = restaurants.read()
print('restaurants.read time:', time.time() - t2)
print('initialization time:', time.time() - t1)


help_txt = {}
with open('help_msg.txt', 'r') as msg:
    help_txt = {line.split()[0][1:].replace(':', ''): line for line in msg}


@ dataclass
class User:
    location: Coord
    current_search: restaurants.Restaurants
    name: str
    accessibility: bool = False


def exception_handler(func):
    """Decorator that handles the exceptions exceptions of the bot functions"""
    def custom_exception(*args):
        update, context = args[0], args[1]
        try:
            func(*args)

        except KeyError as e:
            print('KeyError:', e)
            if e.args[0] == "user":
                context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text='Unexisting user, you need to be registered to use the bot\nUse command /start to register')
                # register_user(update, context)
                # func(*args)
            else:
                print(traceback.format_exc())

        except TypeError as e:
            print('TypeError:', e)
            if not context.user_data["user"].current_search:
                context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text='Unexisting search\nUse command /find to search restaurants')
            elif not context.user_data["user"].location:
                context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"/{func.__name__} function needs to acces your location\nShare your location in order to use it")

        except ValueError as e:
            print('ValueError', e)
            if 'invalid literal for int()' in traceback.format_exc():
                context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text='Wrong parameters type, expected integers')

        except AssertionError as e:
            print('AssertionError', e)
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=e.args[0])

        except IndexError as e:
            print('IndexError:', e)
            if not context.args:
                context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"/{func.__name__} requires extra arguments arguments\nLook in /help for more information")

        except Exception as e:
            print('General exception:', e)
            print(traceback.format_exc())
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text='💣')

    return custom_exception


def time_function(func):
    def temp_func(*args):
        t1: float = time.time()
        func(*args)
        print(f"{func.__name__} time is: {time.time() - t1}")
    return temp_func

# ES MEJOR REGISTRAR AL USUARIO EN VEZ DE DAR ERROR?
# PAU: JO CREC QUE SI


def register_user(update, context) -> User:
    """registers a new user and returns the user"""
    context.user_data["user"] = User(
        None, None, update['message']['chat']['first_name'], False)
    return context.user_data["user"]


@ time_function
@ exception_handler
def start(update, context):
    '''
        Registers (if already registered) a new user and greets him
    '''
    if not "user" in context.user_data:
        register_user(update, context)
    current_user = context.user_data["user"]
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Hola {current_user.name} 🖖, benvingut a Nyam Bot\nUtilitza /help per veure totes les comandes disponibles :)")


@ time_function
@ exception_handler
def help(update, context):
    '''
        Sends help message to the user
    '''
    help_msg: str = ""
    if not context.args:
        help_msg = "".join([line+'\n' for line in help_txt.values()])
    else:
        help_msg = help_txt.get(context.args[0].replace('/', ''))
        if help_msg is None:
            help_msg = f"la comanda {context.args[0]} no existeix, utilitza /help per veure una llista de totes les comandes disponibles :)"
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=help_msg)


def author(update, context):
    '''
        Sends to the user information about the authors and project
    '''
    link: str = "<a href='https://github.com/pauamargant/AP2-Metro-Nyam/'>Github</a>"
    context.bot.send_message(
        chat_id=update.effective_chat.id, text="Autors\n Joel Sole \n Pau Amargant \n Més informació a "+link
    )


@ time_function
@ exception_handler
def update_location(update, context):
    '''
        Saves user location or updates it if already saved
    '''
    lat: float = update.message.location.latitude
    long: float = update.message.location.longitude
    context.user_data['user'].location = (lat, lon)
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text='Localització actualitzada 📍')


@ time_function
@ exception_handler
def plot_metro(update, context):
    '''
        Send metro plot image to the user
    '''
    file = "%d.png" % random.randint(1000000, 9999999)
    metro.plot(metro_graph, file)
    context.bot.send_photo(
        chat_id=update.effective_chat.id,
        photo=open(file, 'rb'))
    os.remove(file)


def sort_rsts(rsts, loc, dist=True):
    if dist:
        rsts = [rst for rst in rsts if rst is not None]
        return sorted(rsts, key=lambda rst: haversine((loc[1], loc[0]), (rst.coords[1], rst.coords[0])))
    else:
        return rsts


@ time_function
@ exception_handler
def find(update, context):
    '''
        Given a query sends to the user a list of up to 12 restaurants which match the query.
    '''
    query = update.message.text[6:]
    assert query, '/find ha de tenir al menys un argument 🤨'
    print(query)
    search = restaurants.find(query, rest)
    user: User = context.user_data['user']
    # If we have the location we sort results by distance
    if (user.location is not None and len(search) > 0):
        search = sort_rsts(search, user.location)[:12]
    user.current_search = search
    msg = "".join([str(i)+". "+res.name+"\n" for i, res in enumerate(search)])
    assert msg, f"no s'han pogut trobar restaurants amb la cerca: {query} 🤷‍♂️"
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=msg
    )


@ exception_handler
@time_function
def accessibility(update, context):
    '''
        Toggles the accessibility option. If accessibility is enabled the bot will only
        use subway stations and accesses which are accessible. 
    '''
    old_acc: bool = context.user_data['user'].accessibility
    context.user_data['user'].accessibility = not old_acc
    if not old_acc:
        print("Accessibility enabled")
        message = "Accessibilitat activada"
    else:
        print("Accessibility disabled")
        message = "Accessiblitat desactivada"
    context.bot.send_message(chat_id=update.effective_chat.id, text=message)


@ time_function
@ exception_handler
def info(update, context):
    '''
        Sends additional information about a given restaurant. The user sends the command
        with argument a number, which is expected to be a search result number in the results 
        of a previous use of the /find command.
    '''
    search = context.user_data['user'].current_search
    num = int(context.args[0])
    assert 0 <= num < len(
        search), f"/info ha de tenir com argument un enter entre 0 i {len(search)-1} 😬"
    restaurant = context.user_data['user'].current_search[num]

    message, photo_url = restaurants.info_message(restaurant)
    if photo_url is not None:
        context.bot.send_photo(
            chat_id=update.effective_chat.id, photo=photo_url, caption=message)
    else:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text=message)


@ time_function
@ exception_handler
def guide(update, context):
    '''
        Guides the user from its location to a restaurant. 
    '''
    t1 = time.time()
    # flags = context.args
    file = "%d.png" % random.randint(1000000, 9999999)
    user: User = context.user_data['user']
    assert 0 <= int(context.args[0]) < len(
        user.current_search), f"/guide ha de tenir com argument un enter entre 0 i {len(user.current_search)-1} 😬"
    src: Coord = user.location
    dst: Coord = user.current_search[int(context.args[0])].coords
    print('antes de path:', time.time()-t1)
    Path = city.find_path(city_osmnx, city_graph, src, dst, user.accessibility)
    print("path trobat")
    print(time.time()-t1)
    city.plot_path(city_graph, Path, file, src, dst)
    print('path plotted', time.time()-t1)
    context.bot.send_photo(
        chat_id=update.effective_chat.id,
        photo=open(file, 'rb'))
    os.remove(file)
    print('foto enviada:', time.time()-t1)

    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"{city.path_txt(city_graph, Path, src, dst)} | Ja has arribat a {user.current_search[int(context.args[0])].name}")

    print("enviat")


@ time_function
@ exception_handler
def default_location(update, context):
    """localización de la uni, función de debugging"""
    context.user_data['user'].location = (41.388492, 2.113043)
    context.bot.send_message(
        chat_id=update.effective_chat.id, text="Default ubication set: UPC")


def main():
    # crea objectes per treballar amb Telegram
    updater = Updater(token=TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    # indica que quan el bot rebi la comanda /start s'executi la funció start
    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('help', help))
    dispatcher.add_handler(CommandHandler('author', author))
    dispatcher.add_handler(MessageHandler(Filters.location, update_location))
    dispatcher.add_handler(CommandHandler('plot_metro', plot_metro))
    dispatcher.add_handler(CommandHandler('find', find))
    dispatcher.add_handler(CommandHandler('info', info))
    dispatcher.add_handler(CommandHandler('guide', guide))
    dispatcher.add_handler(CommandHandler('accessibilitat', accessibility))
    dispatcher.add_handler(CommandHandler('default', default_location))
    dispatcher.add_handler(MessageHandler(Filters.command, help))

    # engega el bot
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
