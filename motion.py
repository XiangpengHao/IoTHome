import RPi.GPIO as GPIO
import time
import datetime
import logging
import threading
from aiohttp import web
import aiohttp
import asyncio
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

TIME_LIMIT = 10 * 60
DND = range(0, 8)

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


room_light = Light("light_on", "light_off")
plant_light = Light("plant_on", "plant_off")


async def motion_task():
    logging.info("begin to detect motion...")
    counter = 0
    while True:
        now = datetime.datetime.now()
        if GPIO.input(23):
            logging.info("Motion detected: %s", now)
            if now.hour not in DND:
                await room_light.on()
                await plant_light.off()
            await asyncio.sleep(5)
            counter = 0
        await asyncio.sleep(1)
        counter += 1
        if counter >= TIME_LIMIT:
            await room_light.off()
            if now.hour not in DND:
                await plant_light.on()
            else:
                await plant_light.off()
            counter = 0


async def display_task():
    dp = Display()
    while True:
        dp.draw(room_light.light_status, GPIO.input(5))
        await asyncio.sleep(10 * 60)
        logging.info("Refreshing... %s", datetime.datetime.now())


async def web_task():
    app = web.Application()
    app.add_routes([web.get('/room_on', room_light.web_on)])
    app.add_routes([web.get('/room_off', room_light.web_off)])
    app.add_routes([web.get('/plant_on', plant_light.web_on)])
    app.add_routes([web.get('/plant_off', plant_light.web_off)])

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 12306)
    logging.info("Starting the webserver at 0.0.0.0:12306")
    await site.start()


def bot_setup(loop):
    dp.register_message_handler(room_light.bot_on, commands=['light_on'])
    dp.register_message_handler(room_light.bot_off, commands=['light_off'])
    dp.register_message_handler(plant_light.bot_on, commands=['plant_on'])
    dp.register_message_handler(plant_light.bot_off, commands=['plant_off'])
    logging.info("start polling...")
    bot_exec = executor.Executor(dp, skip_updates=True)
    bot_exec._prepare_polling()
    loop.run_until_complete(bot_exec._startup_polling())
    loop.create_task(bot_exec.dispatcher.start_polling(
        reset_webhook=False, timeout=20, relax=0.1, fast=True))


def main():
    loop = asyncio.get_event_loop()
    loop.create_task(motion_task())
    loop.create_task(web_task())
    loop.create_task(display_task())
    bot_setup(loop)
    loop.run_forever()


if __name__ == '__main__':
    main()
