"""
To be run either on CPython or MicroPython.

It must be run in combination with test-bundle-protocol-agent-receiver.py, which must be started on another computer.
"""

# import gc
# print("init free: {}, used: {}".format(gc.mem_free(), gc.mem_alloc()))
from dtn7zero.bundle_protocol_agent import BundleProtocolAgent
from dtn7zero.endpoints import LocalEndpoint
from dtn7zero.convergence_layer_adapters.mtcp import MTcpCLA
from dtn7zero.storage.simple_in_memory_storage import SimpleInMemoryStorage
from dtn7zero.routers.simple_epidemic_router import SimpleEpidemicRouter
from dtn7zero.configuration import CONFIGURATION
from dtn7zero.utility import get_current_clock_millis, is_timestamp_older_than_timeout
# print("after import free: {}, used: {}".format(gc.mem_free(), gc.mem_alloc()))
# gc.collect()
# print("after import garbage collect free: {}, used: {}".format(gc.mem_free(), gc.mem_alloc()))
storage = SimpleInMemoryStorage()

clas = {CONFIGURATION.IPND.IDENTIFIER_MTCP: MTcpCLA()}
router = SimpleEpidemicRouter(clas, storage)
bpa = BundleProtocolAgent('dtn://nodeSEND/', storage, router, use_ipnd=True)

sender_endpoint = LocalEndpoint('sender')


bpa.register_endpoint(sender_endpoint)

# print("next free: {}, used: {}".format(gc.mem_free(), gc.mem_alloc()))

message_str = 'hello_world {}'
counter = 1

# print("next free: {}, used: {}".format(gc.mem_free(), gc.mem_alloc()))

last_sending_time = get_current_clock_millis()
try:
    while True:
        bpa.update()

        if is_timestamp_older_than_timeout(last_sending_time, 2000):
            sender_endpoint.start_transmission(message_str.format(counter).encode('utf-8'), 'dtn://nodeRECEIVE/receiver')
            counter += 1

            # gc.collect()
            # print('storage: {}, known-bundles: {}'.format(len(storage.bundles), len(storage.bundle_ids)))
            # print("free: {}, used: {}".format(gc.mem_free(), gc.mem_alloc()))

            last_sending_time = get_current_clock_millis()
except KeyboardInterrupt:
    pass

bpa.unregister_endpoint(sender_endpoint)
