"""
This test consists of test-mtcp-intermediate.py, test-mtcp-receiver.py, and test-mtcp-sender.py .

To test the daisy-chain correctly, ipnd is disabled and the nodes are added manually.

--> PLEASE CHECK AND SET THE CORRECT IP ADDRESSES
--> THIS TEST WAS DESIGNED FOR SENDER AND RECEIVER TO BE RUN ON AN ESP32
--> THE INTERMEDIATE NODE SHOULD BE RUNNING ON A COMPUTER
--> THE INTERMEDIATE NODE CAN BE REPLACED BY THE dtn7rs

start-command for the dtn7rs intermediate node:
dtnd -n node1 -r epidemic -C mtcp -e incoming -s mtcp://192.168.2.146:16162/ESP32-6 -s mtcp://192.168.2.177:16162/ESP32-4


additional notes on the ESP32 sender:

As only one ESP32 can be accessed to start a script on one computer, it may be useful to set the sender-script as main-script on one ESP32:
mpremote fs cp test/test-mtcp-sender.py :main.py

The script may be stopped when entering 'mpremote' shell and pressing 'Ctrl + C' as it is an endless loop.
Afterwards, subsequent mpremote calls will not start it again until a soft reset or power reset is performed.
The script may then be removed using:
mpremote fs rm :main.py
"""
from dtn7zero.bundle_protocol_agent import BundleProtocolAgent
from dtn7zero.convergence_layer_adapters.mtcp import MTcpCLA
from dtn7zero.storage.simple_in_memory_storage import SimpleInMemoryStorage
from dtn7zero.routers.simple_epidemic_router import SimpleEpidemicRouter
from dtn7zero.data import Node
from dtn7zero.configuration import CONFIGURATION


CONFIGURATION.IPND.ENABLED = False


esp32_4 = Node('192.168.2.146', (1, '//ESP32-4/'), {CONFIGURATION.IPND.IDENTIFIER_MTCP: CONFIGURATION.PORT.MTCP}, 0)
esp32_6 = Node('192.168.2.177', (1, '//ESP32-6/'), {CONFIGURATION.IPND.IDENTIFIER_MTCP: CONFIGURATION.PORT.MTCP}, 0)

storage = SimpleInMemoryStorage()
storage.add_node(esp32_4)
storage.add_node(esp32_6)

clas = {CONFIGURATION.IPND.IDENTIFIER_MTCP: MTcpCLA()}
router = SimpleEpidemicRouter(clas, storage)
bpa = BundleProtocolAgent('dtn://node1/', storage, router)

try:
    while True:
        bpa.update()
except KeyboardInterrupt:
    pass
