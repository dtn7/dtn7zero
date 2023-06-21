"""
The espnow support is not yet officially released in MicroPython, but, the changes were recently merged into main.
Therefore, until the next release, we can use the creators pre-builds of MicroPython:
https://github.com/glenn20/micropython-espnow-images/tree/main/20230427-v1.20.0-espnow-2-gcc4c716f6
"""
import espnow
import network

from typing import Tuple, Optional

from py_dtn7 import Bundle
from dtn7zero.convergence_layer_adapters import PushBasedCLA
from dtn7zero.data import Node
from dtn7zero.utility import warning


BROADCAST_MAC = b'\xff\xff\xff\xff\xff\xff'


class EspNowCLA(PushBasedCLA):

    def __init__(self):
        sta = network.WLAN(network.STA_IF)

        # assuming wifi is active through boot.py setup
        assert sta.active()

        # disable wifi power saving mode
        sta.config(pm=sta.PM_NONE)

        self.endpoint = espnow.ESPNow()
        self.endpoint.active(True)
        self.endpoint.add_peer(BROADCAST_MAC)

    def poll(self, bundle_id: str = None, node: Node = None) -> Tuple[Optional[Bundle], Optional[str]]:
        if bundle_id is not None or node is not None:
            raise Exception('cannot poll specific bundle from specific node with espnow cla')

        from_node_address, serialized_bundle = self.endpoint.recv(timeout_ms=0)

        if serialized_bundle:
            try:
                return Bundle.from_cbor(serialized_bundle), from_node_address
            except Exception as e:
                warning('error during mtcp bundle deserialization, ignoring bundle. error: {}'.format(e))

        return None, None

    def send_to(self, node: Optional[Node], serialized_bundle: bytes) -> bool:
        if node is not None:
            raise Exception('cannot send bundle to specific node with espnow cla')

        if len(serialized_bundle) > 250:
            warning('cannot forward bundle through espnow cla because it is longer than 250 bytes: {}'.format(len(serialized_bundle)))
            return False

        self.endpoint.send(BROADCAST_MAC, serialized_bundle)
        return True
