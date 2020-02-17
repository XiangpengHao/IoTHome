import RPi.GPIO as GPIO
import time
import datetime
import logging
import threading
from aiohttp import web
import aiohttp
import asyncio
import json
import dateparser 
from aiogram import Bot, Dispatcher, executor, types

from config import TOKEN, IFTTT, WEB_TOKEN
from display import Display

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

GPIO.setmode(GPIO.BCM)
GPIO.setup(23, GPIO.IN)
GPIO.setup(5, GPIO.IN)

IFTTT_URL = 'https://maker.ifttt.com/trigger/{event}/with/key/{key}'

# Vancouver
SUNSET_URL = 'https://api.sunrise-sunset.org/json?lat=49.2827&lng=-123.1207&formatted=0'

TIME_LIMIT = 10 * 60

ifttt_session = None


class Light:
    def __init__(self, on_event, off_event):
        self.light_status = False
        self.on_event = on_event
        self.off_event = off_event
        self.light_lock = asyncio.Lock()

    async def on(self):
        if self.light_status:
            return
        self.light_status = True
        async with self.light_lock:
            async with aiohttp.ClientSession() as session:
                async with session.get(IFTTT_URL.format(event=self.on_event, key=IFTTT)) as response:
                    await response.text()
                    logging.warning("%s triggered", self.on_event)

    async def off(self):
        if not self.light_status:
            return
        self.light_status = False

        async with self.light_lock:
            async with aiohttp.ClientSession() as session:
                async with session.get(IFTTT_URL.format(event=self.off_event, key=IFTTT)) as response:
                    await response.text()
                    logging.warning("%s triggered", self.off_event)

    async def bot_on(self, message: types.Message):
        await self.on()
        await message.reply("%s triggered" % (self.on_event), reply=False)

    async def bot_off(self, message: types.Message):
        await self.off()
        await message.reply("%s triggered" % (self.off_event), reply=False)

    async def web_on(self, request):
        token = request.rel_url.query.get('token')
        if token != WEB_TOKEN:
            return web.Response(text='invalid token')

        await self.on()
        return web.Response(text=f"{self.on_event} triggered")

    async def web_off(self, request):
        token = request.rel_url.query.get('token')
        if token != WEB_TOKEN:
            return web.Response(text='invalid token')

        await self.off()
        return web.Response(text=f"{self.off_event} triggered")


class Room:
    def __init__(self):
        self.room_light = Light("light_on", "light_off")
        self.plant_light = Light("plant_on", "plant_off")
        self.sun_rise = None
        self.sun_set = None

    async def motion_detected(self):
        await self.plant_light.off()
        await self.room_light.on()

    async def motion_timeout(self):
        now = datetime.datetime.now()
        await self.room_light.off()
        if self.sun_rise < now < self.sun_set:
            await self.plant_light.on()
        else:
            await self.plant_light.off()

    async def update_sun_time(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(SUNSET_URL) as response:
                json_obj = await response.text()
                json_obj = json.loads(json_obj)
                if json_obj['status'] != 'OK':
                    logging.warning("sunset time update failed!")
                results = json_obj['results']
                self.sun_rise = dateparser.parse(results['sunrise'])
                self.sun_set = dateparser.parse(results['sunset'])
                logging.warning("sunrise %s, runset %s", self.sun_rise, self.sun_set)
        await asyncio.sleep(60 * 60 * 6)
        return self.update_sun_time()
    
    def get_sun_rise_set(self):
        if not self.sun_rise or not self.sun_set:
            return 'unknown'
        rise = self.sun_rise
        return f'{rise.month}-{rise.day} {rise.hour}-{self.sun_set.hour}'

room = Room()


async def motion_task():
    logging.info("begin to detect motion...")
    counter = 0
    while True:
        now = datetime.datetime.now()
        if GPIO.input(23):
            logging.info("Motion detected: %s", now)
            await room.motion_detected()
            await asyncio.sleep(5)
            counter = 0

        await asyncio.sleep(1)
        counter += 1
        if counter >= TIME_LIMIT:
            await room.motion_timeout()
            counter = 0


async def display_task():
    dp = Display()
    while True:
        dp.draw(room.room_light.light_status, GPIO.input(5), room.get_sun_rise_set())
        await asyncio.sleep(10 * 60)
        logging.info("Refreshing... %s", datetime.datetime.now())


async def web_task():
    app = web.Application()
    app.add_routes([web.get('/room_on', room.room_light.web_on)])
    app.add_routes([web.get('/room_off', room.room_light.web_off)])
    app.add_routes([web.get('/plant_on', room.plant_light.web_on)])
    app.add_routes([web.get('/plant_off', room.plant_light.web_off)])

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 12306)
    logging.info("Starting the webserver at 0.0.0.0:12306")
    await site.start()


def bot_setup(loop):
    dp.register_message_handler(room.room_light.bot_on, commands=['light_on'])
    dp.register_message_handler(
        room.room_light.bot_off, commands=['light_off'])
    dp.register_message_handler(room.plant_light.bot_on, commands=['plant_on'])
    dp.register_message_handler(
        room.plant_light.bot_off, commands=['plant_off'])
    logging.info("start polling...")
    bot_exec = executor.Executor(dp, skip_updates=True)
    bot_exec._prepare_polling()
    loop.run_until_complete(bot_exec._startup_polling())
    loop.create_task(bot_exec.dispatcher.start_polling(
        reset_webhook=False, timeout=20, relax=0.1, fast=True))


def main():
    loop = asyncio.get_event_loop()
    loop.create_task(room.update_sun_time())
    loop.create_task(motion_task())
    loop.create_task(web_task())
    loop.create_task(display_task())
    bot_setup(loop)
    loop.run_forever()


if __name__ == '__main__':
    main()
