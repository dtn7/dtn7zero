import time
from abc import ABC
from typing import Iterable

from dtn7zero.configuration import CONFIGURATION
from dtn7zero.data import BundleInformation
from py_dtn7 import Bundle
from py_dtn7.bundle import PreviousNodeBlock, BlockProcessingControlFlags


class Router(ABC):

    def prepare_and_serialize_bundle(self, full_node_uri: str, bundle_information: BundleInformation) -> bytes:
        """ RFC 9171, 5.4 Bundle Forwarding
        […]
        Step 4: For each node selected for forwarding, the BPA MUST invoke the services of the selected CLA(s) in order
        to effect the sending of the bundle to that node. […] Note that:

        * If the bundle has a Previous Node Block, as defined in Section 4.4.1, then that block MUST be removed from
        the bundle before the bundle is forwarded.

        * If the BPA is configured to attach Previous Node Blocks to forwarded bundles, then a Previous Node Block
        containing the node ID of the forwarding node MUST be inserted into the bundle before the bundle is forwarded.

        * If the bundle has a Bundle Age Block, as defined in Section 4.4.2, then at the last possible moment before
        the CLA initiates conveyance of the bundle via the CL protocol the bundle age value MUST be increased by the
        difference between the current time and the time at which the bundle was received (or, if the local node is
        the source of the bundle, created).
        """

        # copy bundle to not alter the storage instance
        bundle = Bundle.from_cbor(bundle_information.bundle.to_cbor())

        if bundle.previous_node_block:
            bundle.remove_block(bundle.previous_node_block)

        if CONFIGURATION.ATTACH_PREVIOUS_NODE_BLOCK:
            flags = BlockProcessingControlFlags(0)
            flags.set_flag(4)  # discard block if block cant be processed

            previous_node_block = PreviousNodeBlock.from_objects(full_node_uri, flags)

            bundle.insert_canonical_block(previous_node_block)

        if bundle.bundle_age_block:
            # todo: assuming no wrap-around on micropython here -> test after which time this happens
            bundle.bundle_age_block.age_milliseconds += (time.time_ns() // 1000000) - bundle_information.received_at_ms

        """ RFC 9171, 4.4.3 Hop Count
        […] the hop count value SHOULD initially be zero and SHOULD be increased by 1 on each hop.
        """
        if bundle.hop_count_block:
            bundle.hop_count_block.hop_count += 1

        return bundle.to_cbor()

    def generator_poll_bundles(self) -> Iterable[BundleInformation]:
        raise NotImplementedError('do not instantiate Router class directly')

    def immediate_forwarding_attempt(self, full_node_uri: str, bundle_information: BundleInformation) -> (bool, int):
        raise NotImplementedError('do not instantiate Router class directly')

    def send_to_previous_node(self, full_node_uri: str, bundle_information: BundleInformation) -> bool:
        raise NotImplementedError('do not instantiate Router class directly')
