from abc import ABC
from typing import List, Tuple, Optional, Iterable

from dtn7zero.data import BundleInformation, Node


class Storage(ABC):

    def add_node(self, node: Node):
        raise NotImplementedError('do not instantiate Storage class directly')

    def get_node(self, node_address: str) -> Optional[Node]:
        raise NotImplementedError('do not instantiate Storage class directly')

    def get_nodes(self) -> Iterable[Node]:
        raise NotImplementedError('do not instantiate Storage class directly')

    def was_seen(self, bundle_id: str) -> bool:
        raise NotImplementedError('do not instantiate Storage class directly')

    def get_seen(self, bundle_id: str) -> Optional[str]:
        raise NotImplementedError('do not instantiate Storage class directly')

    def store_seen(self, bundle_id: str, node: Optional[str]):
        raise NotImplementedError('do not instantiate Storage class directly')

    def remove_bundle(self, bundle_id: str) -> bool:
        raise NotImplementedError('do not instantiate Storage class directly')

    def delay_bundle(self, bundle_information: BundleInformation) -> Tuple[bool, List[BundleInformation]]:
        raise NotImplementedError('do not instantiate Storage class directly')

    def get_bundles_to_retry(self):
        raise NotImplementedError('do not instantiate Storage class directly')
