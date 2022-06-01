from dataclasses import dataclass
import sys
import os
import time
from telegram.ext import Updater, CommandHandler, Filters, MessageHandler, CallbackContext
import logging
import random
from typing import Optional, List, Tuple, Dict, Union, Callable
from typing_extensions import TypeAlias
import traceback
from haversine import haversine

# We import the base modules
import metro
import city
import restaurants

Restaurant: TypeAlias = restaurants.Restaurant
Restaurants: TypeAlias = restaurants.Restaurants

Coord: TypeAlias = Tuple[float, float]
NodeID: TypeAlias = int
Path: TypeAlias = List[NodeID]


@ dataclass
class User:
    location: Optional[Coord]
    current_search: Optional[restaurants.Restaurants]
    name: str
    accessibility: bool = False


class Exception_messages:

    @ staticmethod
    def type_error(update: Updater, context: CallbackContext, func: Callable) -> None:
        assert not(update.effective_chat is None or context.user_data is None)
        if not context.user_data["user"].current_search:
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=("Cerca inexistent 🤷‍♂️\nUtilitza la comanda /find per "
                      "buscar restaurants :)"))
        elif not context.user_data["user"].location:
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=(f"La comanda /{func.__name__} necessita accedir a la "
                      f"teva ubicació 🤦‍♂️\nComparteix la teva ubicació per "
                      f"fer servir la comanda /{func.__name__}"))
        else:
            Exception_messages.general(update, context)

    @ staticmethod
    def key_error(update: Updater, context: CallbackContext, e: KeyError) -> None:
        assert not(update.effective_chat is None or context.user_data is None)
        if e.args[0] == "user":
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=("Usuari inexistent 🙎‍♂️, necessites estar registrat per"
                      "fer servir bot\nUtilitza la comanda /start per "
                      "registrar-te"))
        else:
            Exception_messages.general(update, context)

    @ staticmethod
    def value_error(update: Updater, context: CallbackContext) -> None:
        assert not(update.effective_chat is None or context.user_data is None)
        if 'invalid literal for int()' in traceback.format_exc():
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Tipus de parametre incorrecte, s'esperaven enters 🤦‍♂️")
        else:
            Exception_messages.general(update, context)

    @ staticmethod
    def assertion_error(update: Updater, context: CallbackContext, e: AssertionError) -> None:
        print(e.args[0])
        Exception_messages.general(update, context)

    @ staticmethod
    def index_error(update: Updater, context: CallbackContext, func: Callable) -> None:
        assert not(update.effective_chat is None or context.user_data is None)
        if not context.args:
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=(f"/{func.__name__} necessita més arguments\nMira"
                      f" en '/help {func.__name__}' per a més informació"))
        else:
            Exception_messages.general(update, context)

    @ staticmethod
    def general(update: Updater, context: CallbackContext) -> None:
        '''
        Message for a general error

        Parameters
        ----------
        update : Update
            _description_
        context : CallbackContext
            _description_
        '''
        assert not(update.effective_chat is None or context.user_data is None)
        print(traceback.format_exc())
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='Commanda incorrecte 💣')


def exception_handler(func: Callable):
    '''
    Decorator that handles the exceptions of the bot functions

    Parameters
    ----------
    func : Callable
        The function we will handle the exceptions from
    '''

    def custom_exception(*args):
        update: Update = args[0]
        context: CallbackContext = args[1]
        try:
            if "user" not in context.user_data:
                register_user(update, context)
            func(*args)

        except KeyError as e:
            print('KeyError:', e)
            Exception_messages.key_error(update, context, e)

        except TypeError as e:
            print('TypeError:', e)
            Exception_messages.type_error(update, context, func)

        except ValueError as e:
            print('ValueError', e)
            Exception_messages.value_error(update, context)

        except AssertionError as e:
            print('AssertionError', e)
            Exception_messages.assertion_error(update, context, e)

        except IndexError as e:
            print('IndexError:', e)
            Exception_messages.index_error(update, context, func)

        except Exception as e:
            print('General exception:', e)
            Exception_messages.general(update, context)

    return custom_exception


def register_user(update: Updater, context: CallbackContext) -> None:
    '''
    Registers a new user

    Parameters
    ----------
    update : Update
        _description_
    context : CallbackContext
        _description_
    '''
    assert context.user_data is not None and update is not None
    try:
        context.user_data["user"] = User(
            None, None, update['message']['chat']['first_name'], False)
    except Exception:
        context.user_data["user"] = User(None, None, "", False)


@ exception_handler
def start(update: Updater, context: CallbackContext) -> None:
    '''
    Registers (if not registered yet) a new user and greets him

    Parameters
    ----------
    update : Update
        _description_
    context : CallbackContext
        _description_
    '''
    assert not(context.user_data is None or update.effective_chat is None)
    if "user" not in context.user_data:
        register_user(update, context)
    current_user = context.user_data["user"]
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=(f"Hola {current_user.name} 🖖, benvingut a Nyam Bot\nUtilitza"
              f" /help per veure totes les comandes disponibles :)"))


@ exception_handler
def help(update: Updater, context: CallbackContext) -> None:
    '''
    Sends the user a help message about all the avaliable commands, or about
    some specific command if it's specified after the /help

    Parameters
    ----------
    update : Update
        _description_
    context : CallbackContext
        _description_
    '''
    help_msg: str = ""
    if not context.args:
        help_msg = "".join([line+'\n' for line in help_txt.values()])
    else:
        help_msg = help_txt.get(context.args[0].replace('/', ''), '')
        if help_msg == '':
            help_msg = (f"la comanda {context.args[0]} no existeix, utilitza"
                        f"/help per veure una llista de totes les comandes "
                        f"disponibles :)")
    assert update.effective_chat is not None
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=help_msg)


def author(update: Updater, context: CallbackContext) -> None:
    '''
    Sends to the user information about the authors and project

    Parameters
    ----------
    update : Update
        _description_
    context : CallbackContext
        _description_
    '''
    link: str = "<a href='https://github.com/pauamargant/AP2-Metro-Nyam/'>Github</a>"  # noqa
    assert update.effective_chat is not None
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Autors\n Joel Sole \n Pau Amargant \n Més informació a "+link
    )


@ exception_handler
def update_location(update: Updater, context: CallbackContext) -> None:
    '''
    Saves user location or updates it if already saved

    Parameters
    ----------
    update : Update
        _description_
    context : CallbackContext
        _description_
    '''
    assert not(
        update.message is None or update.message.location is None or context.user_data is None or update.effective_chat is None)
    lat: float = update.message.location.latitude
    lon: float = update.message.location.longitude
    context.user_data['user'].location = (lat, lon)
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text='Localització actualitzada 📍')


@ exception_handler
def plot_metro(update: Updater, context: CallbackContext) -> None:
    '''
    Send metro plot image to the user

    Parameters
    ----------
    update : Update
        _description_
    context : CallbackContext
        _description_
    '''
    file: str = "%d.png" % random.randint(1000000, 9999999)
    metro.plot(metro_graph, file)
    assert update.effective_chat is not None
    context.bot.send_photo(
        chat_id=update.effective_chat.id,
        photo=open(file, 'rb'))
    os.remove(file)


def sort_rsts(rsts: Restaurants, loc: Coord, dist=True) -> Restaurants:
    if rsts and dist:
        rsts = [rst for rst in rsts if rst is not None]
        return sorted(rsts, key=lambda rst:
                      haversine((loc[1], loc[0]),
                                (rst.coords[1], rst.coords[0])))
    return rsts


@ exception_handler
def find(update: Updater, context: CallbackContext) -> None:
    '''
    Given a query sends to the user a list of up to 12 restaurants which
    match the query.

    Parameters
    ----------
    update : Update
        _description_
    context : CallbackContext
        _description_
    '''
    assert not(
        update.message is None or update.message.text is None or context.user_data is None or update.effective_chat is None)
    query: str = update.message.text[6:]
    assert query, '/find ha de tenir al menys un argument 🤨'
    print(query)
    search: Restaurants = restaurants.find(query, rest)
    user: User = context.user_data['user']
    # If we have the location we sort results by distance
    if (user.location is not None and len(search) > 0):
        search = sort_rsts(search, user.location)
    search = search[:12]
    user.current_search = search
    msg: str = "".join(
        [str(i)+". "+res.name+"\n" for i, res in enumerate(search)])
    assert msg,\
        f"no s'han pogut trobar restaurants amb la cerca: {query} 🤷‍♂️"
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=msg
    )


@ exception_handler
def accessibility(update: Updater, context: CallbackContext) -> None:
    '''
    Toggles the accessibility option. If accessibility is enabled the bot
    will only use subway stations and accesses which are accessible.

    Parameters
    ----------
    update : Update
        _description_
    context : CallbackContext
        _description_
    '''
    assert not(context.user_data is None or update.effective_chat is None)
    old_acc: bool = context.user_data['user'].accessibility
    context.user_data['user'].accessibility = not old_acc
    if old_acc:
        print("Accessibility disabled")
        message = "Accessiblitat desactivada ❌"
    else:
        print("Accessibility enabled")
        message: str = "Accessibilitat activada ⭕"
    context.bot.send_message(chat_id=update.effective_chat.id, text=message)


@ exception_handler
def info(update: Updater, context: CallbackContext) -> None:
    '''
    Sends additional information about a given restaurant. The user sends the
    command with argument a number, which is expected to be a search result
    number in the results of a previous use of the /find command.

    Parameters
    ----------
    update : Update
        _description_
    context : CallbackContext
        _description_
    '''
    assert not(
        context.user_data is None or context.args is None or update.effective_chat is None)
    search: Restaurants = context.user_data['user'].current_search
    if not search:
        Exception_messages.type_error(update, context, info)
        return
    num: int = int(context.args[0])
    assert 0 <= num < len(search),\
        (f"/ info ha de tenir com argument un enter entre 0"
         f" i {len(search)-1} 😬")
    restaurant: Restaurant = context.user_data['user'].current_search[num]
    message: str
    photo_url: Optional[str]
    message, photo_url = restaurants.info_message(restaurant)
    if photo_url is not None:
        context.bot.send_photo(
            chat_id=update.effective_chat.id, photo=photo_url, caption=message)
    else:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text=message)


@ exception_handler
def guide(update: Updater, context: CallbackContext) -> None:
    '''
    Guides the user from its location to a restaurant.

    Parameters
    ----------
    update : Update
        _description_
    context : CallbackContext
        _description_
    '''
    assert not(
        context.user_data is None or context.args is None or update.effective_chat is None)
    if not user.current_search:
        Exception_messages.type_error(update, context, guide)
        return
    t1: float = time.time()
    filename: str = "%d.png" % random.randint(1000000, 9999999)
    user: User = context.user_data['user']
    assert 0 <= int(context.args[0]) < len(user.current_search),\
        (f"/ guide ha de tenir com argument un enter "
         f"entre 0 i {len(user.current_search)-1} 😬")
    src: Coord = user.location
    dst: Coord = user.current_search[int(context.args[0])].coords
    print('antes de path:', time.time()-t1)
    path: city.Path = city.find_path(
        city_osmnx, city_graph, src, dst, user.accessibility)
    print("path trobat")
    print(time.time()-t1)
    city.plot_path(city_graph, path, filename, src, dst)
    print('path plotted', time.time()-t1)
    context.bot.send_photo(
        chat_id=update.effective_chat.id,
        photo=open(filename, 'rb'))
    os.remove(filename)
    print('foto enviada:', time.time()-t1)

    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=(f"{city.path_txt(city_graph, path, src, dst)} | Ja has arribat"
              f"a {user.current_search[int(context.args[0])].name}"))

    print("enviat")


@ exception_handler
def default_location(update: Updater, context: CallbackContext) -> None:
    """localización de la uni, función de debugging"""
    assert not(context.user_data is None or context.user_data['user'] is None or context.user_data['user']
               .location is None or update.effective_chat is None)
    context.user_data['user'].location = (41.388492, 2.113043)
    context.bot.send_message(
        chat_id=update.effective_chat.id, text="Default ubication set: UPC")


def main():

    # crea objectes per treballar amb Telegram
    updater = Updater(token=TOKEN, use_context=True)
    dispatcher = updater.dispatcher
    print(f"{'-'*13}\nBot is active\n{'-'*13}")

    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('help', help))
    dispatcher.add_handler(CommandHandler('author', author))
    dispatcher.add_handler(MessageHandler(Filters.location, update_location))
    dispatcher.add_handler(CommandHandler('plot_metro', plot_metro))
    dispatcher.add_handler(CommandHandler('find', find))
    dispatcher.add_handler(CommandHandler('info', info))
    dispatcher.add_handler(CommandHandler('guide', guide))
    dispatcher.add_handler(CommandHandler('accessibility', accessibility))
    dispatcher.add_handler(CommandHandler('default', default_location))
    dispatcher.add_handler(MessageHandler(Filters.command, help))

    # engega el bot
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    logging.basicConfig(format=(f"%(asctime)s - %(name)s - %(levelname)s -"
                                f" %(message)s"), level=logging.INFO)
    # We import the token
    try:
        TOKEN = open('token.txt').read().strip()
    except IOError:
        print("Could not read the token.txt file")  # PEL CANAL D'ERRORS MILLOR
        sys.exit()

    #   **************
    #   INITIALIZATION
    #   **************
    print(f"{'*'*16}\nInitializing bot\n{'*'*16}")
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
    print('Total initialization time:', time.time() - t1)
    print(f"{'*'*54}\n")

    help_txt = {}
    with open('help_msg.txt', 'r') as msg:
        help_txt = {line.split()[0][1:].replace(':', ''): line for line in msg}

    main()
