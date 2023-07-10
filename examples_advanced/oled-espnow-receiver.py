"""
This script will receive bundles on the "dtn://esp-1/incoming" endpoint
and show the number of received on the oled display.

To be run on a LILYGO-TTGO-LORA32 ESP32.

information about the oled taken from: https://docs.micropython.org/en/latest/esp8266/tutorial/ssd1306.html


IMPORT AND SETUP ORDER IS IMPORTANT

oled and espnow setup must be done first,
because the garbage collector can recover most of the RAM after those two are imported and initiated.


DEPLOYMENT INFORMATION

this example currently relies on the inofficial espnow builds: https://github.com/glenn20/micropython-espnow-images/tree/main/20230427-v1.20.0-espnow-2-gcc4c716f6
"""
import time

# DISPLAY SETUP
from machine import Pin, SoftI2C
from ssd1306 import SSD1306_I2C

WIDTH = 128
HEIGHT = 64

rst = Pin(16, Pin.OUT)
rst.value(1)

i2c = SoftI2C(sda=Pin(4), scl=Pin(15))

display = SSD1306_I2C(WIDTH, HEIGHT, i2c)


# ESPNOW CLA SETUP
from dtn7zero.convergence_layer_adapters.espnow_cla import EspNowCLA

espnow_cla = EspNowCLA()


# dtn7zero SETUP
from py_dtn7 import Bundle

from dtn7zero.bundle_protocol_agent import BundleProtocolAgent
from dtn7zero.configuration import CONFIGURATION
from dtn7zero.endpoints import LocalEndpoint
from dtn7zero.storage.simple_in_memory_storage import SimpleInMemoryStorage
from dtn7zero.routers.simple_epidemic_router import SimpleEpidemicRouter


CONFIGURATION.IPND.ENABLED = False
CONFIGURATION.MICROPYTHON_CHECK_WIFI = False
CONFIGURATION.SIMPLE_IN_MEMORY_STORAGE_MAX_STORED_BUNDLES = 3
CONFIGURATION.SIMPLE_IN_MEMORY_STORAGE_MAX_KNOWN_BUNDLE_IDS = 8


clas = {CONFIGURATION.IPND.IDENTIFIER_ESPNOW: espnow_cla}
storage = SimpleInMemoryStorage()
router = SimpleEpidemicRouter(clas, storage)
bpa = BundleProtocolAgent('dtn://esp-1/', storage, router)


bundle_counter = 0


def callback(bundle: Bundle):
    global bundle_counter

    bundle_counter += 1
    display.fill_rect(0, 40, 128, 52, 0)
    display.text('recv: {}'.format(bundle_counter), 0, 40, 1)
    display.show()


receiver_endpoint = LocalEndpoint('incoming', receive_callback=callback)
bpa.register_endpoint(receiver_endpoint)

display.text('ESPNOW TEST', 20, 0, 1)
display.text('num bundles', 0, 24, 1)
display.text('recv: {}'.format(bundle_counter), 0, 40, 1)
display.show()

print('receiver started')
try:
    while True:
        bpa.update()
        time.sleep(0.05)
except KeyboardInterrupt:
    pass

bpa.unregister_endpoint(receiver_endpoint)
