"""
This example shows how to receive group-addressed messages.

It should be used in combination with the first remote example (remote_group_a.py) on another machine.
Both machines must be running in the same local network.
"""
import time

from dtn7zero import setup, register_group, start_background_update_thread
from py_dtn7.bundle import PrimaryBlock


def callback(payload: bytes, full_source_uri: str, full_destination_uri: str, primary_block: PrimaryBlock):
    print("received group-message {}, from {}".format(payload, full_source_uri))


node = setup("dtn://node-b/")

group = register_group("dtn://global/~news", callback)

start_background_update_thread()

node.send(b'hi from node b', "dtn://global/~news")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    pass
