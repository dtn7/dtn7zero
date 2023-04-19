"""
This test consists of test-mtcp-intermediate.py, test-mtcp-receiver.py, and test-mtcp-sender.py .

To test the daisy-chain correctly, ipnd is disabled and the nodes are added manually.

--> PLEASE CHECK AND SET THE CORRECT IP ADDRESSES
--> THIS TEST WAS DESIGNED FOR SENDER AND RECEIVER TO BE RUN ON AN ESP32
--> THE INTERMEDIATE NODE SHOULD BE RUNNING ON A COMPUTER
--> THE INTERMEDIATE NODE CAN BE REPLACED BY THE dtn7rs

start-command for the dtn7rs intermediate node:
dtnd -n node1 -r epidemic -C mtcp -e incoming -s mtcp://192.168.2.182:16162/ESP32-6 -s mtcp://192.168.2.162:16162/ESP32-4


additional notes on the ESP32 sender:

As only one ESP32 can be accessed to start a script on one computer, it may be useful to set the sender-script as main-script on one ESP32:
mpremote fs cp test/test-mtcp-sender.py :main.py

The script may be stopped when entering 'mpremote' shell and pressing 'Ctrl + C' as it is an endless loop.
Afterwards, subsequent mpremote calls will not start it again until a soft reset or power reset is performed.
The script may then be removed using:
mpremote fs rm :main.py
"""
from dtn7zero.bundle_protocol_agent import BundleProtocolAgent
from dtn7zero.endpoints import LocalEndpoint
from dtn7zero.convergence_layer_adapters.mtcp import MTcpCLA
from dtn7zero.storage.simple_in_memory_storage import SimpleInMemoryStorage
from dtn7zero.routers.simple_epidemic_router import SimpleEpidemicRouter
from dtn7zero.data import Node
from dtn7zero.constants import IPND_IDENTIFIER_MTCP, PORT_MTCP
from py_dtn7 import Bundle


dtn7rs_node = Node('192.168.2.163', (1, '//node1/'), {IPND_IDENTIFIER_MTCP: PORT_MTCP})

storage = SimpleInMemoryStorage()
storage.add_node(dtn7rs_node)

clas = {IPND_IDENTIFIER_MTCP: MTcpCLA()}
router = SimpleEpidemicRouter(clas, storage)
bpa = BundleProtocolAgent('dtn://ESP32-4/', storage, router, use_ipnd=False)


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
