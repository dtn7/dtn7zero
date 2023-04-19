"""
This is a single-threaded example.

run_forever is blocking and calls the provided 'main' method every 1000 milliseconds.
"""
from dtn7zero import setup, run_forever
from py_dtn7.bundle import PrimaryBlock


def callback(payload: bytes, full_source_uri: str, full_destination_uri: str, primary_block: PrimaryBlock):
    print("received message: {}".format(payload.decode()))


node_endpoint = setup("dtn://node1/", callback)


def main():
    node_endpoint.send("hello world".encode(), "dtn://node1/")


run_forever(main, loop_callback_interval_milliseconds=1000)
