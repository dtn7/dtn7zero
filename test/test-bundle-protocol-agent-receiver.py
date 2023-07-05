"""
To be run either on CPython or MicroPython.

It must be run in combination with test-bundle-protocol-agent-sender.py, which must be started on another computer.
"""
# import gc
# print("init free: {}, used: {}".format(gc.mem_free(), gc.mem_alloc()))
from dtn7zero.bundle_protocol_agent import BundleProtocolAgent
from dtn7zero.endpoints import LocalEndpoint
from dtn7zero.convergence_layer_adapters.mtcp import MTcpCLA
from dtn7zero.storage.simple_in_memory_storage import SimpleInMemoryStorage
from dtn7zero.routers.simple_epidemic_router import SimpleEpidemicRouter
from dtn7zero.configuration import CONFIGURATION
# from dtn7zero.utility import get_current_clock_millis, is_timestamp_older_than_timeout
from py_dtn7 import Bundle
# print("after import free: {}, used: {}".format(gc.mem_free(), gc.mem_alloc()))
# gc.collect()
# print("after import garbage collect free: {}, used: {}".format(gc.mem_free(), gc.mem_alloc()))


def callback(bundle: Bundle):
    print('bundle reached receiver endpoint: {}'.format(bundle.payload_block.data))


storage = SimpleInMemoryStorage()

clas = {CONFIGURATION.IPND.IDENTIFIER_MTCP: MTcpCLA()}
router = SimpleEpidemicRouter(clas, storage)
bpa = BundleProtocolAgent('dtn://nodeRECEIVE/', storage, router)

receiver_endpoint = LocalEndpoint('receiver', receive_callback=callback)

bpa.register_endpoint(receiver_endpoint)

# last_garbage_collect = get_current_clock_millis()
try:
    while True:
        bpa.update()

        # if is_timestamp_older_than_timeout(last_garbage_collect, 2000):
        #     gc.collect()
        #     print('storage: {}, known-bundles: {}'.format(len(storage.bundles), len(storage.bundle_ids)))
        #     print("free: {}, used: {}".format(gc.mem_free(), gc.mem_alloc()))
        #     last_garbage_collect = get_current_clock_millis()
except KeyboardInterrupt:
    pass

bpa.unregister_endpoint(receiver_endpoint)
