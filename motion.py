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
DND = range(0, 8)

class Light:
    def __init__(self, on_event, off_event):
        self.light_status = False
        self.on_event = on_event
        self.off_event = off_event

    def on(self):
        if self.light_status:
            return
        self.light_status = True
        logging.warn("%s triggered", self.on_event)
        requests.get(IFTTT_URL.format(event=self.on_event, key=IFTTT))

    def off(self):
        if not self.light_status:
            return
        self.light_status = False 
        logging.warn("%s triggered", self.off_event)
        requests.get(IFTTT_URL.format(event=self.off_event, key=IFTTT))

    def bot_on(self, bot, update):
        self.on()
        bot.send_message(chat_id=update.message.chat_id, text="%s triggered"%(self.on_event))

    def bot_off(self, bot, update):
        self.off()
        bot.send_message(chat_id=update.message.chat_id, text="%s triggered"%(self.off_event))



room_light = Light("light_on", "light_off")
plant_light = Light("plant_on", "plant_off")

def motion_thread():
    logging.info("begin to detect motion...")
    counter = 0
    while True:
        if GPIO.input(23):
            now = datetime.datetime.now()
            logging.info("Motion detected: %s", now)
            if now.hour not in DND:
                room_light.on()
                plant_light.off()
            time.sleep(5)
            counter = 0
        time.sleep(1)
        counter += 1
        if counter >= TIME_LIMIT:
            room_light.off()
            if now.hour not in DND:
                plant_light.on()
            else:
                plant_light.off()
            counter = 0

def display_thread():
    dp = Display()
    while True:
        dp.draw_weather(room_light.light_status)
        time.sleep(10*60)
        logging.info("Refreshing... %s", datetime.datetime.now())

dispatcher.add_handler(CommandHandler('light_on', room_light.bot_on))
dispatcher.add_handler(CommandHandler('light_off', room_light.bot_off))
dispatcher.add_handler(CommandHandler('plant_on', plant_light.bot_on))
dispatcher.add_handler(CommandHandler('plant_off', plant_light.bot_off))

updater.start_polling()
logging.info("start polling...")

threading.Thread(target=motion_thread).start()
threading.Thread(target=display_thread).start()

