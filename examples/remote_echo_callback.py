"""
This example shows how to react to incoming messages via callback.

It should be used in combination with any ping example (remote_ping_callback.py, remote_ping_poll.py) on another machine.
Both machines must be running in the same local network.
"""
import time

from dtn7zero import setup, register, start_background_update_thread
from py_dtn7.bundle import PrimaryBlock


def callback(payload: bytes, full_source_uri: str, full_destination_uri: str, primary_block: PrimaryBlock):
    print("received ping {}, sending back echo".format(payload))
    echo.send(payload, full_source_uri)


setup("dtn://node-b/")

echo = register("echo", callback)

start_background_update_thread()


try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    pass
