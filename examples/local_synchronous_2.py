"""
This is another single-threaded example.

For simplicity, we use the node-endpoint directly.

This time we build our own update-loop.
The framework profits from repeated network polls, which is why the main-loop does not wait extensively and calls update() often.
"""
import time

from dtn7zero import setup, update
from dtn7zero.utility import get_current_clock_millis, is_timestamp_older_than_timeout
from py_dtn7.bundle import PrimaryBlock


def callback(payload: bytes, full_source_uri: str, full_destination_uri: str, primary_block: PrimaryBlock):
    print("received message: {}".format(payload.decode()))


node_endpoint = setup("dtn://node1/", callback)


last_send = get_current_clock_millis()
try:
    while True:
        update()

        if is_timestamp_older_than_timeout(last_send, 1000):
            node_endpoint.send("hello world".encode(), "dtn://node1/")
            last_send = get_current_clock_millis()

        time.sleep(0.01)
except KeyboardInterrupt:
    pass
