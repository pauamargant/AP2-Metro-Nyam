# importa l'API de Telegram
from dataclasses import dataclass
import sys
import os
from telegram.ext import Updater, CommandHandler, Filters, MessageHandler
import logging
import random
from dataclasses import dataclass
from typing import Optional, TextIO, List, Tuple, Dict, Union
from typing_extensions import TypeAlias
import traceback

import metro
import city
import restaurants
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

Coord: TypeAlias = Tuple[float, float]
NodeID: TypeAlias = int
Path: TypeAlias = List[NodeID]

# declara una constant amb el access token que llegeix de token.txt
try:
    TOKEN = open('token.txt').read().strip()
except IOError:
    print("Could not read the token.txt file")
    sys.exit()

# INICIALITZACIÓ:

metro_graph: metro.MetroGraph = metro.get_metro_graph()
city_osmnx = city.get_osmnx_graph()
city_graph: city.CityGraph = city.build_city_graph(city_osmnx, metro_graph)
rest: restaurants.Restaurants = restaurants.read()


@dataclass
class User:
    location: Coord
    current_search: restaurants.Restaurants
    name: str


def exception_handler(func):
    """Decorator that handles the exceptions error for the bot functions"""
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

        except TypeError as e:
            print('TypeError:', e)
            if not context.user_data["user"].current_search:
                context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text='Unexisting search\nUse command /find to search restaurants')
            elif not context.user_data["user"].location:
                context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"/{func.__name__} function needs to acces your location\nSend your location in order to use it")

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
                    text=f"/{func.__name__} command needs arguments")

        except Exception as e:
            print('General exception:', e)
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text='💣')

    return custom_exception


def start(update, context):
    current_user = User(None, None, update['message']['chat']['first_name'])
    context.user_data["user"] = current_user
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Hi {current_user.name}, welcome to Nyam Bot\nType /help to see al the avaliable commands.")


def help(update, context):
    with open('help_msg.txt', 'r') as msg:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text=msg.read(), parse_mode='Markdown'
        )


def author(update, context):
    context.bot.send_message(
        chat_id=update.effective_chat.id, text="Autors: TEXT"
    )


def where(update, context):
    lat, lon = update.message.location.latitude, update.message.location.longitude
    context.user_data['user'].location = (lat, lon)
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text='Updated location 📍')


@exception_handler
def plot_metro(update, context):
    file = "%d.png" % random.randint(1000000, 9999999)
    metro.plot(metro_graph, file)
    context.bot.send_photo(
        chat_id=update.effective_chat.id,
        photo=open(file, 'rb'))
    os.remove(file)


@exception_handler
def find(update, context):
    query = update.message.text[6:]
    assert len(query) != 0, '/find needs to have at least one argument'
    print(query)
    search = restaurants.find(query, rest)
    msg = "".join([str(i)+". "+res.name+"\n" for i, res in enumerate(search)])
    context.user_data['user'].current_search = search
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=msg
    )


@exception_handler
def info(update, context):
    search = context.user_data['user'].current_search
    assert len(
        context.args) == 1, f"/info command must have an argument between 0 and {len(search)-1}"
    restaurant = context.user_data['user'].current_search[int(
        context.args[0])]
    message = f"*Name*: {restaurant.name}\n*Adress*: {restaurant.adress.road_name}, nº{restaurant.adress.street_n}\n*Neighborhood*: {restaurant.adress.nb_name}\n*District*: {restaurant.adress.dist_name}\n*Phone*: {restaurant.tlf}"
    context.bot.send_message(
        chat_id=update.effective_chat.id, text=message, parse_mode='Markdown')


@exception_handler
def guide(update, context):
    file = "%d.png" % random.randint(1000000, 9999999)
    src: Coord = context.user_data['user'].location
    dst: Coord = context.user_data['user'].current_search[int(
        context.args[0])].coords
    Path = city.find_path(city_osmnx, city_graph, src, dst)
    print("path trobat")
    city.plot_path(city_graph, Path, file, src, dst)
    context.bot.send_photo(
        chat_id=update.effective_chat.id,
        photo=open(file, 'rb'))
    os.remove(file)
    # time = city.path_time(city_graph, Path, src, dst)
    # context.bot.send_message(
    #     chat_id=update.effective_chat.id, text="Temps estimat és "+str(time))
    print("enviat")


def main():
    # crea objectes per treballar amb Telegram
    updater = Updater(token=TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    # indica que quan el bot rebi la comanda /start s'executi la funció start
    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('help', help))
    dispatcher.add_handler(CommandHandler('author', author))
    dispatcher.add_handler(MessageHandler(Filters.location, where))
    dispatcher.add_handler(CommandHandler('plot_metro', plot_metro))
    dispatcher.add_handler(CommandHandler('find', find))
    dispatcher.add_handler(CommandHandler('info', info))
    dispatcher.add_handler(CommandHandler('guide', guide))

    # engega el bot
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
