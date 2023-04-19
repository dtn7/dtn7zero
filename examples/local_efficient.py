"""
The framework allows to save power by limiting the number of updates in the update-loop.

For this, run_forever, start_background_update_thread have the '_sleep_time_seconds' parameter.

first example: usage of the background thread in combination with '_sleep_time_seconds'
second example: usage of the single-threaded run_forever() in combination with '_sleep_time_seconds'
"""
import time

from dtn7zero import setup, start_background_update_thread, run_forever
from py_dtn7.bundle import PrimaryBlock


def callback(payload: bytes, full_source_uri: str, full_destination_uri: str, primary_block: PrimaryBlock):
    print("received message: {}".format(payload.decode()))


node_endpoint = setup("dtn://node1/", callback)

FIRST_EXAMPLE = True

if FIRST_EXAMPLE:
    start_background_update_thread(_sleep_time_seconds=0.1)

    try:
        while True:
            node_endpoint.send("hello world".encode(), "dtn://node1/")
            time.sleep(1)
    except KeyboardInterrupt:
        pass
else:
    def main():
        node_endpoint.send("hello world".encode(), "dtn://node1/")

    run_forever(main, loop_callback_interval_milliseconds=1000, _sleep_time_seconds=0.1)
