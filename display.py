from epd import epd2in9b
import hum
import time
from PIL import Image, ImageDraw, ImageFont
import traceback
import logging
import datetime

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

font16 = ImageFont.truetype('fonts/wqy-microhei.ttc', 16)
font20 = ImageFont.truetype('fonts/wqy-microhei.ttc', 20)
font24 = ImageFont.truetype('fonts/wqy-microhei.ttc', 24)
font40 = ImageFont.truetype('fonts/wqy-microhei.ttc', 40)

class Display:
    def __init__(self):
        self.epd = epd2in9b.EPD()
        self.epd.init()
        self.red_img = Image.new("1", (epd2in9b.EPD_HEIGHT, epd2in9b.EPD_WIDTH), 255)
        self.black_img = Image.new("1", (epd2in9b.EPD_HEIGHT, epd2in9b.EPD_WIDTH), 255)
        self.clear()

    def reset_img(self):
        self.red_img = Image.new("1", (epd2in9b.EPD_HEIGHT, epd2in9b.EPD_WIDTH), 255)
        self.black_img = Image.new("1", (epd2in9b.EPD_HEIGHT, epd2in9b.EPD_WIDTH), 255)

    def draw(self, light_status, soil_status, sun_set_rise):
        self.epd.init()
        self.reset_img()
        black_draw = ImageDraw.Draw(self.black_img)
        red_draw = ImageDraw.Draw(self.red_img)
        now = datetime.datetime.now()
        humi, temp = hum.read()

        black_draw.text((5, 0), "Patrick's Smart Home", font=font16, fill=0)

        black_draw.text((5, 20), "light:", font=font20, fill=0)
        red_draw.text((55, 20), "on" if light_status else "off", font=font20, fill=0)

        black_draw.text((5, 40), "soil:", font=font20, fill=0)
        red_draw.text((55, 40), "need water" if soil_status else "good", font=font20, fill=0)
        
        black_draw.text((5, 60), "sun:", font=font20, fill=0)
        red_draw.text((55, 60), sun_set_rise, font=font16, fill=0)

        black_draw.text((5, 80), "update:", font=font20, fill=0)
        red_draw.text((5, 100), now.strftime("%b-%d %H:%M"), font=font20, fill=0)

        red_draw.text((170, 20), "{0:0.1f}°C".format(temp), font=font40, fill=0)
        red_draw.text((170, 65), "{0:0.1f}%".format(humi), font=font40, fill=0)

        self.epd.display(self.epd.getbuffer(self.black_img), self.epd.getbuffer(self.red_img))
        self.sleep()

    def clear(self):
        logging.info("Clear all")
        self.epd.Clear(0xFF)

    def sleep(self):
        logging.info("sleep")
        self.epd.sleep()

if __name__ == '__main__':
    dp = Display()
    while True:
        dp.draw_weather()
        time.sleep(10*60)
        logging.info("Refreshing... %s", datetime.datetime.now())

