from typing import Dict, List, Optional, Tuple

from dtn7zero.convergence_layer_adapters import PullBasedCLA
from dtn7zero.data import Node
from dtn7zero.utility import debug, warning

try:
    import requests
except ImportError:
    import urequests as requests

from py_dtn7 import DTNRESTClient, Bundle

from dtn7zero.constants import IPND_IDENTIFIER_REST


class Dtn7RsRestCLA(PullBasedCLA):

    def __init__(self):
        self.connections: Dict[Node, DTNRESTClient] = {}

    def add_connection(self, node: Node):
        http_address = 'http://{}'.format(node.address)
        port = node.clas[IPND_IDENTIFIER_REST]
        try:
            # we assume if there is a dtn7rs-like HTTP-API present, then we can proceed
            dtn7rs_rest_client = DTNRESTClient(host=http_address, port=port)
        except OSError as e:  # urequests only uses default exceptions
            warning('could not add node: {}:{} error: {}'.format(http_address, port, e))
            return

        self.connections[node] = dtn7rs_rest_client
        node.eid = (1, self.connections[node].node_id)  # todo: remove hardcoded dtn uri scheme assignment
        debug('added new rest cla connection: {} {}'.format(node.eid, http_address))

    def poll(self, bundle_id: str, node: Node) -> Tuple[Optional[Bundle], Optional[str]]:
        if bundle_id is None or node is None:
            return None, None

        if node not in self.connections:
            return None, None

        try:
            raw_bundle = self.connections[node].download(bundle_id=bundle_id)
        except OSError:  # urequests only uses default exceptions
            del self.connections[node]
            return None, None

        if raw_bundle == b'Bundle not found':
            return None, None

        return Bundle.from_cbor(raw_bundle), node.address

    def poll_ids(self, node: Node) -> Optional[List[str]]:
        if node not in self.connections:
            # try to establish a new node connection, todo: what to do on repeated failures (slowing the framework down)?
            self.add_connection(node)

        try:
            return self.connections[node].bundles
        except (OSError, ValueError):  # urequests only uses default exceptions
            del self.connections[node]
        return None

    def send_to(self, node: Node, serialized_bundle: bytes) -> bool:
        if IPND_IDENTIFIER_REST not in node.clas:
            return False

        if node not in self.connections:
            # try to establish a new node connection, todo: what to do on repeated failures (slowing the framework down)?
            self.add_connection(node)

        try:
            response = self.connections[node].push(serialized_bundle)
            if response.status_code != 200:
                warning('connection {} did not accept our bundle: {} {}'.format(node.address, response.status_code, response.content))
                return False
            return True
        except OSError:  # urequests only uses default exceptions
            warning('removing bad connection {}'.format(node.address))
            del self.connections[node]
        except KeyError:
            return False
        return False
