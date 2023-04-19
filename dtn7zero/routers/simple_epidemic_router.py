from typing import Dict, Iterable

from dtn7zero.constants import SIMPLE_EPIDEMIC_ROUTER_MIN_NODES_TO_FORWARD_TO, IPND_IDENTIFIER_MTCP, IPND_IDENTIFIER_REST
from dtn7zero.convergence_layer_adapters import CLA
from dtn7zero.data import BundleInformation, Node, BundleStatusReportReasonCodes
from dtn7zero.routers import Router
from dtn7zero.storage import Storage
from dtn7zero.utility import warning


class SimpleEpidemicRouter(Router):

    def __init__(self, convergence_layer_adapters: Dict[str, CLA], storage: Storage):
        self.clas = convergence_layer_adapters
        self.storage = storage

    def generator_poll_bundles(self) -> Iterable[BundleInformation]:
        # Currently there are only two cla types implemented, which are also the only ones supported here.

        for node in self.storage.get_nodes():
            if IPND_IDENTIFIER_REST in node.clas:
                for bundle_information in self._generator_poll_advanced(node, self.clas[IPND_IDENTIFIER_REST]):
                    yield bundle_information

        if IPND_IDENTIFIER_MTCP in self.clas:
            for bundle_information in self._generator_poll_simple(self.clas[IPND_IDENTIFIER_MTCP]):
                yield bundle_information

    def _generator_poll_simple(self, cla: CLA):
        bundle, node_address = cla.poll()
        while bundle is not None:
            if not self.storage.was_seen(bundle.bundle_id):
                self.storage.store_seen(bundle.bundle_id, node_address)

                bundle_information = BundleInformation(bundle)

                node = self.storage.get_node(node_address)
                if node is not None:  # if node is known, prevent the bundle from being sent back to that same node
                    bundle_information.forwarded_to_nodes.append(node)

                yield bundle_information
            bundle, node_address = cla.poll()

    def _generator_poll_advanced(self, node: Node, cla: CLA):
        bundle_ids = cla.poll_ids(node)

        for bundle_id in bundle_ids:
            if not self.storage.was_seen(bundle_id):
                bundle, node_polled_address = cla.poll(bundle_id, node)
                if bundle is not None:
                    self.storage.store_seen(bundle_id, node_polled_address)

                    bundle_information = BundleInformation(bundle)

                    node = self.storage.get_node(node_polled_address)
                    if node is not None:  # if node is known, prevent the bundle from being sent back to that same node
                        bundle_information.forwarded_to_nodes.append(node)

                    yield bundle_information
                    break

    def immediate_forwarding_attempt(self, full_node_uri: str, bundle_information: BundleInformation) -> (bool, int):
        serialized_bundle: bytes = self.prepare_and_serialize_bundle(full_node_uri, bundle_information)

        reason = BundleStatusReportReasonCodes.NO_TIMELY_CONTACT_WITH_NEXT_NODE_ON_ROUTE

        for node in self.storage.get_nodes():
            if node in bundle_information.forwarded_to_nodes:
                continue

            for cla in self.clas.values():
                success = cla.send_to(node, serialized_bundle)
                if success:
                    bundle_information.forwarded_to_nodes.append(node)
                else:
                    reason = BundleStatusReportReasonCodes.TRAFFIC_PARED

        return len(bundle_information.forwarded_to_nodes) >= SIMPLE_EPIDEMIC_ROUTER_MIN_NODES_TO_FORWARD_TO, reason

    def send_to_previous_node(self, full_node_uri: str, bundle_information: BundleInformation) -> bool:
        previous_node_address = self.storage.get_seen(bundle_information.bundle.bundle_id)
        previous_node = self.storage.get_node(previous_node_address)

        if previous_node_address is None or previous_node is None:
            warning('Previous node of bundle-id {} is not known (any more). Ignoring request to send to previous node.'.format(bundle_information.bundle.bundle_id))
            return False

        bundle: bytes = self.prepare_and_serialize_bundle(full_node_uri, bundle_information)

        for cla in self.clas.values():
            if cla.send_to(previous_node, bundle):
                return True
        return False
