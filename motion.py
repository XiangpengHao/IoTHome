import RPi.GPIO as GPIO
import time
from telegram.ext import CommandHandler, Updater
import requests
import datetime
import logging
import threading

from config import TOKEN, IFTTT
from display import Display

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

updater = Updater(token=TOKEN)
dispatcher = updater.dispatcher

GPIO.setmode(GPIO.BCM)
GPIO.setup(23, GPIO.IN)

IFTTT_URL = 'https://maker.ifttt.com/trigger/{event}/with/key/{key}'

TIME_LIMIT = 10 * 60
DND = (0, 8)

light_status = 'light_off'

def set_light(status):
    global light_status
    if status == light_status:
        return
    light_status = status
    logging.warn("set light to %s", status)
    requests.get(IFTTT_URL.format(event=status, key=IFTTT))

def motion_thread():
    logging.info("begin to detect motion...")
    counter = 0
    while True:
        if GPIO.input(23):
            now = datetime.datetime.now()
            logging.info("Motion detected: %s", now)
            if now.hour not in DND:
                set_light('light_on')
            time.sleep(5)
            counter = 0
        time.sleep(1)
        counter += 1
        if counter >= TIME_LIMIT:
            set_light('light_off')
            counter = 0

def display_thread():
    global light_status
    dp = Display()
    while True:
        dp.draw_weather(light_status=="light_on")
        time.sleep(10*60)
        logging.info("Refreshing... %s", datetime.datetime.now())

def light_on(bot, update):
    set_light('light_on')
    bot.send_message(chat_id=update.message.chat_id, text="light is on")

def light_off(bot, update):
    set_light('light_off')
    bot.send_message(chat_id=update.message.chat_id, text="light is off")


light_on_handler = CommandHandler('light_on', light_on)
light_off_handler = CommandHandler('light_off', light_off)

dispatcher.add_handler(light_on_handler)
dispatcher.add_handler(light_off_handler)

updater.start_polling()
logging.info("start polling...")

threading.Thread(target=motion_thread).start()
threading.Thread(target=display_thread).start()

