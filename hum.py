import Adafruit_DHT

sensor = Adafruit_DHT.AM2302
pin = 4

def read():
    return Adafruit_DHT.read_retry(sensor, pin)
