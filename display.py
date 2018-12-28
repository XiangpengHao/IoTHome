from epd import epd2in9b
import time
from PIL import Image, ImageDraw, ImageFont
import traceback
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

font16 = ImageFont.truetype('fonts/wqy-microhei.ttc', 16)
font20 = ImageFont.truetype('fonts/wqy-microhei.ttc', 20)
font24 = ImageFont.truetype('fonts/wqy-microhei.ttc', 24)

class Display:
    def __init__(self):
        self.epd = epd2in9b.EPD()
        self.epd.init()
        self.red_img = Image.new("1", (epd2in9b.EPD_HEIGHT, epd2in9b.EPD_WIDTH), 255)
        self.black_img = Image.new("1", (epd2in9b.EPD_HEIGHT, epd2in9b.EPD_WIDTH), 255)
        self.clear()

    def draw_dummy(self):
        black_draw = ImageDraw.Draw(self.black_img)
        red_draw = ImageDraw.Draw(self.red_img)
        black_draw.text((5, 0), "Patrick's Smart Home", font=font16, fill=0)
        self.epd.display(self.epd.getbuffer(self.black_img), self.epd.getbuffer(self.red_img))


    def clear(self):
        logging.info("Clear all")
        self.epd.Clear(0xFF)

    def sleep(self):
        logging.info("sleep")
        self.epd.sleep()

if __name__ == '__main__':
    dp = Display()
    dp.draw_dummy()
    dp.sleep()

