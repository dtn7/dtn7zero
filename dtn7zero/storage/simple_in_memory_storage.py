from typing import Dict, Tuple, List, Optional, Iterable

from dtn7zero.configuration import CONFIGURATION
from dtn7zero.data import BundleInformation, Node
from dtn7zero.storage import Storage
from dtn7zero.utility import get_oldest_bundle, get_oldest_bundle_id


class SimpleInMemoryStorage(Storage):

    def __init__(self):
        self.bundles: Dict[str, BundleInformation] = {}
        self.bundle_ids: Dict[str, Optional[str]] = {}
        self.nodes: Dict[str, Node] = {}

    def add_node(self, node: Node):
        self.nodes[node.address] = node

    def get_node(self, node_address) -> Optional[Node]:
        return self.nodes.get(node_address)

    def get_nodes(self) -> Iterable[Node]:
        return self.nodes.values()

    def get_seen(self, bundle_id: str) -> Optional[str]:
        return self.bundle_ids.get(bundle_id)

    def was_seen(self, bundle_id: str) -> bool:
        return bundle_id in self.bundle_ids

    def store_seen(self, bundle_id: str, node_address):
        if node_address is None and self.bundle_ids.get(bundle_id, None) is not None:
            return  # we do not want to overwrite a valid node with None from an unknown source

        if len(self.bundle_ids) >= CONFIGURATION.SIMPLE_IN_MEMORY_STORAGE_MAX_KNOWN_BUNDLE_IDS:
            del self.bundle_ids[get_oldest_bundle_id(self.bundle_ids)]
        self.bundle_ids[bundle_id] = node_address

    def remove_bundle(self, bundle_id: str) -> bool:
        return self.bundles.pop(bundle_id, False)  # if the bundle exists it is 'truthy'

    def delay_bundle(self, bundle_information: BundleInformation) -> Tuple[bool, List[BundleInformation]]:
        removed_bundles = []

        if bundle_information.bundle.bundle_id in self.bundles:
            return True, removed_bundles

        if len(self.bundles) >= CONFIGURATION.SIMPLE_IN_MEMORY_STORAGE_MAX_STORED_BUNDLES:
            self.garbage_collect()

        if len(self.bundles) >= CONFIGURATION.SIMPLE_IN_MEMORY_STORAGE_MAX_STORED_BUNDLES:
            oldest_bundle = self.bundles.pop(get_oldest_bundle(self.bundles.values()).bundle.bundle_id)
            removed_bundles.append(oldest_bundle)

        self.store_seen(bundle_information.bundle.bundle_id, None)

        self.bundles[bundle_information.bundle.bundle_id] = bundle_information

        return True, removed_bundles

    def garbage_collect(self):
        for bundle_id in list(self.bundles):
            if self.bundles[bundle_id].retention_constraint is None:
                del self.bundles[bundle_id]

    def get_bundles_to_retry(self):
        # simply yield all stored bundles
        # 1. reason: in-memory storage only stores a limited amount of bundles
        # 2. router only forwards bundles where they have not been forwarded yet -> router filters
        return (i for i in tuple(self.bundles.values()))
