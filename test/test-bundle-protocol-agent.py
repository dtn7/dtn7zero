"""
To be run either on CPython or MicroPython.

Registers two local endpoints and sends from one to the other.
"""
import time

from dtn7zero.constants import IPND_IDENTIFIER_MTCP
from dtn7zero.convergence_layer_adapters.mtcp import MTcpCLA
from dtn7zero.bundle_protocol_agent import BundleProtocolAgent
from dtn7zero.endpoints import LocalEndpoint
from dtn7zero.storage.simple_in_memory_storage import SimpleInMemoryStorage
from dtn7zero.routers.simple_epidemic_router import SimpleEpidemicRouter
from py_dtn7 import Bundle


def callback(bundle: Bundle):
    print('bundle reached receiver endpoint: {}'.format(bundle))


storage = SimpleInMemoryStorage()

clas = {IPND_IDENTIFIER_MTCP: MTcpCLA()}

router = SimpleEpidemicRouter(clas, storage)
bpa = BundleProtocolAgent('dtn://node2/', storage, router)

sender_endpoint = LocalEndpoint('sender')
receiver_endpoint = LocalEndpoint('receiver', receive_callback=callback)


bpa.register_endpoint(sender_endpoint)
bpa.register_endpoint(receiver_endpoint)

message_str = 'hello_world {}'
counter = 1

try:
    while True:
        bpa.update()
        time.sleep(1)
        sender_endpoint.start_transmission(message_str.format(counter).encode('utf-8'), 'dtn://node2/receiver')
        time.sleep(1)
        counter += 1
except KeyboardInterrupt:
    pass

bpa.unregister_endpoint(sender_endpoint)
bpa.unregister_endpoint(receiver_endpoint)



