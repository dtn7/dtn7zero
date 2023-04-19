"""
DTN allows to send bundles anonymously by using 'dtn://none' as the source-address and report-to address.

This framework allows to do so by passing the 'anonymous=True' parameter to the method .send() of any endpoint.
"""
import time

from dtn7zero import setup, register, start_background_update_thread
from py_dtn7.bundle import PrimaryBlock


def callback(payload: bytes, full_source_uri: str, full_destination_uri: str, primary_block: PrimaryBlock):
    print("{} received {} from {}".format(full_destination_uri, payload, full_source_uri))


node_endpoint = setup("dtn://my-node/", callback)

start_background_update_thread()

local_endpoint = register("my/custom/sub/endpoint", callback)


node_endpoint.send(b'mysterious message', "dtn://my-node/my/custom/sub/endpoint", anonymous=True)

local_endpoint.send(b'pure evil', "dtn://my-node/", anonymous=True)

time.sleep(1)
