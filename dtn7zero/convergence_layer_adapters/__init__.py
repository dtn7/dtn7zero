from abc import ABC
from typing import Optional, List, Tuple

from dtn7zero.data import Node
from py_dtn7 import Bundle


class PullBasedCLA(ABC):

    def poll(self, bundle_id: str, node: Node) -> Tuple[Optional[Bundle], Optional[str]]:
        raise NotImplementedError('do not instantiate CLA class directly')

    def poll_ids(self, node: Node) -> Optional[List[str]]:
        raise NotImplementedError('do not instantiate CLA class directly')

    def send_to(self, node: Node, serialized_bundle: bytes) -> bool:
        raise NotImplementedError('do not instantiate CLA class directly')


class PushBasedCLA(ABC):
    def poll(self) -> Tuple[Optional[Bundle], Optional[str]]:
        raise NotImplementedError('do not instantiate CLA class directly')

    def send_to(self, node: Optional[Node], serialized_bundle: bytes) -> bool:
        raise NotImplementedError('do not instantiate CLA class directly')

