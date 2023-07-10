"""
This script will send bundles to the "dtn://esp-1/incoming" endpoint
and show the number of sent on the oled display.

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
from dtn7zero.bundle_protocol_agent import BundleProtocolAgent
from dtn7zero.configuration import CONFIGURATION
from dtn7zero.endpoints import LocalEndpoint
from dtn7zero.storage.simple_in_memory_storage import SimpleInMemoryStorage
from dtn7zero.routers.simple_epidemic_router import SimpleEpidemicRouter
from dtn7zero.utility import get_current_clock_millis, is_timestamp_older_than_timeout


CONFIGURATION.IPND.ENABLED = False
CONFIGURATION.MICROPYTHON_CHECK_WIFI = False
CONFIGURATION.SIMPLE_IN_MEMORY_STORAGE_MAX_STORED_BUNDLES = 3
CONFIGURATION.SIMPLE_IN_MEMORY_STORAGE_MAX_KNOWN_BUNDLE_IDS = 8


clas = {CONFIGURATION.IPND.IDENTIFIER_ESPNOW: espnow_cla}
storage = SimpleInMemoryStorage()
router = SimpleEpidemicRouter(clas, storage)
bpa = BundleProtocolAgent('dtn://esp-0/', storage, router)


sender_endpoint = LocalEndpoint('sender')


bpa.register_endpoint(sender_endpoint)

message_str = 'hello_world {}'
bundle_counter = 0
last_transmission = get_current_clock_millis()

display.text('ESPNOW TEST', 20, 0, 1)
display.text('num bundles', 0, 24, 1)
display.text('sent: {}'.format(bundle_counter), 0, 40, 1)
display.show()

print('sender started')
try:
    while True:
        bpa.update()

        if is_timestamp_older_than_timeout(last_transmission, 2000):
            bundle_counter += 1
            sender_endpoint.start_transmission(message_str.format(bundle_counter).encode('utf-8'), 'dtn://esp-1/incoming')

            display.fill_rect(0, 40, 128, 52, 0)
            display.text('sent: {}'.format(bundle_counter), 0, 40, 1)
            display.show()

            last_transmission = get_current_clock_millis()

        time.sleep(0.05)
except KeyboardInterrupt:
    pass

bpa.unregister_endpoint(sender_endpoint)
