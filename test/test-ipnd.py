"""
To be run either on CPython or MicroPython.

If started on two or more different computers in your lokal network,
they should find each other immediately after startup.

To test against the dtn7rs, we can use a generic start command (make sure to set the correct broadcast IP):
dtnd -n node1 -r epidemic -C mtcp -e incoming -E 192.168.2.255:3003

important note: because the beacon-services are not defined clearly and we do not know the expected format of the dtn7rs,
the unicast-beacon will fail to deserialize on the dtn7rs, which is not pretty but cannot be helped at the moment.
"""
from dtn7zero.ipnd import IPND
from dtn7zero.storage.simple_in_memory_storage import SimpleInMemoryStorage
from dtn7zero.utility import get_current_clock_millis, is_timestamp_older_than_timeout


storage = SimpleInMemoryStorage()

discovery = IPND(eid_scheme=1, eid_specific_part='//test-node/', storage=storage)


last_print = get_current_clock_millis()

try:
    while True:
        discovery.update()
        if is_timestamp_older_than_timeout(last_print, 2000):
            print('known nodes: {}'.format(storage.nodes))
            last_print = get_current_clock_millis()
except KeyboardInterrupt:
    pass
