"""
This example shows how to register two endpoints and locally send messages between them.

The framework treats/delivery bundles from any source (local, remote, local-self) the same way, although local bundles
are, of course, delivered directly without any network involvement.
"""
import time

from dtn7zero import setup, register, start_background_update_thread
from py_dtn7.bundle import PrimaryBlock


def ping_callback(payload: bytes, full_source_uri: str, full_destination_uri: str, primary_block: PrimaryBlock):
    print("received integer echo data: {}".format(int(payload.decode())))


def echo_callback(payload: bytes, full_source_uri: str, full_destination_uri: str, primary_block: PrimaryBlock):
    print("sending back raw ping data: {}".format(payload))
    echo_endpoint.send(payload, full_source_uri)


setup("dtn://node1/")

ping_endpoint = register("ping", ping_callback)

echo_endpoint = register("echo", echo_callback)

start_background_update_thread()


try:
    counter = 1
    while True:
        print("sending ping: {}".format(counter))
        ping_endpoint.send(str(counter).encode(), "dtn://node1/echo")
        counter += 1
        time.sleep(2)
except KeyboardInterrupt:
    pass
