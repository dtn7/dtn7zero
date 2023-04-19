"""
A simple demo for the standalone ExternalEndpoint.

It connects to a running dtn7-rs via the HTTP client interface, which can be started like so:
dtnd -n node1 -r epidemic -C mtcp -e incoming -U

Important is the -U flag to allow "local HTTP API access" on non-localhost network interfaces.
"""
import time

from dtn7zero.endpoints import ExternalEndpoint
from py_dtn7 import Bundle

dtn7rs_endpoint = ExternalEndpoint("192.168.2.163", "my-endpoint")

dtn7rs_endpoint.start_transmission(b'hello_world', "dtn://node1/my-endpoint")

try:
    while True:
        bundle: Bundle = dtn7rs_endpoint.poll()

        if bundle is not None:
            print("received: {}".format(bundle.payload_block.data))
            break

        time.sleep(.1)
except KeyboardInterrupt:
    pass
