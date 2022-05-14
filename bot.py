# importa l'API de Telegram
from pandas import concat
import metro
import city
from telegram.ext import Updater, CommandHandler, Filters, MessageHandler
import logging
import random

import restaurants
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
# defineix una funció que saluda i que s'executarà quan el bot rebi el missatge /start

# declara una constant amb el access token que llegeix de token.txt
TOKEN = open('token.txt').read().strip()


def start(update, context):
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
    context.user_data['location'] = (lat, lon)
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text='Localització rebuda ACTUALITZADA?')


def plot_metro(update, context):
    try:
        file = "%d.png" % random.randint(1000000, 9999999)
        g = metro.get_metro_graph()
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
        for res in search:
            message += res.name+"\n"
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message
        )
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
# engega el bot
updater.start_polling()
updater.idle()
