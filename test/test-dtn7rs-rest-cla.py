"""
This can be run on CPython or MicroPython.

It tests the rest-cla against a running dtn7rs on the specified IP with the following generic start command:
dtnd -n node1 -r epidemic -C mtcp -e incoming

Note on MicroPython:
The current configuration of maximum in-memory stored bundles collides with the memory intensive urequests library.
It therefore will likely crash after a few exchanged bundles.
This is an open end topic to investigate.
"""
from dtn7zero.bundle_protocol_agent import BundleProtocolAgent
from dtn7zero.constants import IPND_IDENTIFIER_REST, PORT_REST
from dtn7zero.convergence_layer_adapters.dtn7rs_rest import Dtn7RsRestCLA
from dtn7zero.data import Node
from dtn7zero.endpoints import LocalEndpoint
from dtn7zero.routers.simple_epidemic_router import SimpleEpidemicRouter
from dtn7zero.storage.simple_in_memory_storage import SimpleInMemoryStorage
from dtn7zero.utility import get_current_clock_millis, is_timestamp_older_than_timeout

dtn7rs = Node('192.168.2.163', (1, '//node1/'), {IPND_IDENTIFIER_REST: PORT_REST})

storage = SimpleInMemoryStorage()
storage.add_node(dtn7rs)

clas = {IPND_IDENTIFIER_REST: Dtn7RsRestCLA()}
router = SimpleEpidemicRouter(clas, storage)
bpa = BundleProtocolAgent('dtn://node2/', storage, router, use_ipnd=False)

endpoint = LocalEndpoint('hello')
bpa.register_endpoint(endpoint)

last_send = get_current_clock_millis()
try:
    while True:
        bpa.update()

        if is_timestamp_older_than_timeout(last_send, 2000):
            endpoint.start_transmission(b'world', 'dtn://node1/incoming')

            last_send = get_current_clock_millis()
except KeyboardInterrupt:
    pass
