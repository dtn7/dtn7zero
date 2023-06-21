"""
This test consists of test-espnow-sender.py and test-espnow-receiver.py .

The espnow support is not yet officially released in MicroPython, but, the changes were recently merged into main.
Therefore, until the next release, we can use the creators pre-builds of MicroPython:
https://github.com/glenn20/micropython-espnow-images/tree/main/20230427-v1.20.0-espnow-2-gcc4c716f6

additional notes on the ESP32 sender:

As only one ESP32 can be accessed to start a script on one computer, it may be useful to set the sender-script as main-script on one ESP32:
mpremote fs cp test/test-espnow-sender.py :main.py

The script may be stopped when entering 'mpremote' shell and pressing 'Ctrl + C' as it is an endless loop.
Afterwards, subsequent mpremote calls will not start it again until a soft reset or power reset is performed.
The script may then be removed using:
mpremote fs rm :main.py
"""
from py_dtn7 import Bundle

from dtn7zero.bundle_protocol_agent import BundleProtocolAgent
from dtn7zero.constants import IPND_IDENTIFIER_ESPNOW
from dtn7zero.endpoints import LocalEndpoint
from dtn7zero.convergence_layer_adapters.espnow_cla import EspNowCLA
from dtn7zero.storage.simple_in_memory_storage import SimpleInMemoryStorage
from dtn7zero.routers.simple_epidemic_router import SimpleEpidemicRouter

storage = SimpleInMemoryStorage()

clas = {IPND_IDENTIFIER_ESPNOW: EspNowCLA()}
router = SimpleEpidemicRouter(clas, storage)
bpa = BundleProtocolAgent('dtn://esp-2/', storage, router, use_ipnd=False)


def callback(bundle: Bundle):
    print('received: {}'.format(bundle.payload_block.data))


receiver_endpoint = LocalEndpoint('receiver', receive_callback=callback)
bpa.register_endpoint(receiver_endpoint)


try:
    while True:
        bpa.update()
except KeyboardInterrupt:
    pass

bpa.unregister_endpoint(receiver_endpoint)
