# importa l'API de Telegram
from dataclasses import dataclass
from pandas import concat
import metro
import city
from telegram.ext import Updater, CommandHandler, Filters, MessageHandler
import logging
import random
from dataclasses import dataclass
from typing import Optional, TextIO, List, Tuple, Dict, Union
from typing_extensions import TypeAlias
import os.path

import restaurants
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

Coord: TypeAlias = Tuple[float, float]
NodeID: TypeAlias = int
Path: TypeAlias = List[NodeID]

# declara una constant amb el access token que llegeix de token.txt
TOKEN = open('token.txt').read().strip()

# INICIALITZACIÓ:

metro_graph = metro.get_metro_graph()
city_osmnx = city.get_osmnx_graph()
city_graph = city.build_city_graph(city_osmnx, metro_graph)


@dataclass
class user:
    location: Coord
    current_search: restaurants
    name: str


def start(update, context):
    current_user = user(None, None, "usuari")
    context.user_data["user"] = current_user
    context.bot.send_message(
        chat_id=update.effective_chat.id, text="Hola! Soc un bot bàsic.")


def help(update, context):
    context.bot.send_message(
        chat_id=update.effective_chat.id, text="Ajuda inexistent aquí"
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
        text='Localització rebuda ACTUALITZADA?')


def plot_metro(update, context):
    try:
        file = "%d.png" % random.randint(1000000, 9999999)
        metro.plot(g, file)
        context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=open(file, 'rb'))
        os.remove(file)
    except Exception as e:
        print(e)
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='💣')


def find(update, context):
    try:
        query = ""
        for word in context.args:
            query += (" "+word)
        rest = restaurants.read()
        search = restaurants.find(query, rest)
        message = ""
        for i in range(len(search)):
            res = search[i]
            message += str(i)+". "+res.name+"\n"
        context.user_data['user'].current_search = search
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message
        )
    except Exception as e:
        print(e)
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='💣')


def info(update, context):
    try:
        if len(context.args) != 1:
            context.bot.send_message(
                chat_id=update.effective_chat.id, text="Arguments incorrectes")
        else:
            restaurant = context.user_data['user'].current_search[int(
                context.args[0])]
            message = restaurant.name
            context.bot.send_message(
                chat_id=update.effective_chat.id, text=message)
    except Exception as e:
        print(e)


def guide(update, context):
    try:
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
    except Exception as e:
        print(e)
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='💣')


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
dispatcher.add_handler(MessageHandler(Filters.location, where))
dispatcher.add_handler(CommandHandler('info', info))
dispatcher.add_handler(CommandHandler('guide', guide))

# engega el bot
updater.start_polling()
updater.idle()
