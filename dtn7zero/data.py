from typing import List, Tuple, Dict

from dtn7zero.utility import get_current_clock_millis
from py_dtn7 import Bundle


class BundleStatusReportReasonCodes:
    """
    RFC 9171, 9.5 Bundle Status Report Reason Codes
    """
    NO_ADDITIONAL_INFORMATION = 0
    LIFETIME_EXPIRED = 1
    FORWARDED_OVER_UNIDIRECTIONAL_LINK = 2
    TRANSMISSION_CANCELED = 3
    DEPLETED_STORAGE = 4
    DESTINATION_ENDPOINT_ID_UNAVAILABLE = 5
    NO_KNOWN_ROUTE_TO_DESTINATION_FROM_HERE = 6
    NO_TIMELY_CONTACT_WITH_NEXT_NODE_ON_ROUTE = 7
    BLOCK_UNINTELLIGIBLE = 8
    HOP_LIMIT_EXCEEDED = 9
    TRAFFIC_PARED = 10
    BLOCK_UNSUPPORTED = 11


class Node:

    def __init__(self, address: str, eid: Tuple[int, str], clas: Dict[str, int], sequence_number: int):
        self.address = address  # the IP address of the node
        # todo: currently a node is identified by its IP address, maybe this requires changes sometime in the future.
        # storage also depends on the address field as the unique identifier of a node

        self.eid = eid  # DTN node id, a tuple of "address-type" (1 or 2) and "the node-id" in the correct format -> for type 1 (DTN) -> example: "//node1/"
        self.clas = clas  # a list of tuples, consisting of the ipnd-cla-identifier + application port
        self.sequence_number = sequence_number

        self.latest_discovery = get_current_clock_millis()

    def merge_new_info(self, eid_scheme: int, eid_specific_part: str, clas: Dict[str, int]):
        if eid_specific_part is not None:
            self.eid = (eid_scheme, eid_specific_part)
        self.clas = clas  # replace with new information -> clas might have gotten deactivated

        self.latest_discovery = get_current_clock_millis()

    def advance_sequence_number(self, new_sequence_number: int) -> bool:
        old_sequence_number = self.sequence_number
        self.sequence_number = new_sequence_number
        return old_sequence_number + 1 == new_sequence_number


class BundleInformation:
    RETENTION_CONSTRAINT_DISPATCH_PENDING = 'Dispatch pending'
    RETENTION_CONSTRAINT_FORWARD_PENDING = 'Forward pending'

    def __init__(self, bundle: Bundle):
        self.bundle = bundle
        self.retention_constraint = None
        self.locally_delivered = False
        self.received_at_ms = get_current_clock_millis()
        self.forwarded_to_nodes: List[Node] = []
