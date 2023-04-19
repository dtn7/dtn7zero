"""
This example shows how to send a ping and react to the response via callback

It should be used in combination with any echo example (remote_echo_callback.py, remote_echo_poll.py) on another machine.
Both machines must be running in the same local network.
"""
import time

from dtn7zero import setup, register, start_background_update_thread
from py_dtn7.bundle import PrimaryBlock


def callback(payload: bytes, full_source_uri: str, full_destination_uri: str, primary_block: PrimaryBlock):
    print("received echo {}".format(payload))


setup("dtn://node-a/")

start_background_update_thread()

ping = register("ping", callback)


try:
    counter = 1
    while True:
        print("sending ping {}".format(counter))
        ping.send(str(counter).encode(), "dtn://node-b/echo")
        counter += 1
        time.sleep(1)
except KeyboardInterrupt:
    pass
