import socket
from typing import Tuple, Optional, List, Dict

from dtn7zero.constants import RUNNING_MICROPYTHON, IPND_IDENTIFIER_MTCP, PORT_MTCP, PORT_IPND, IPND_SEND_INTERVAL_MILLISECONDS, IPND_BEACON_MAX_SIZE
from dtn7zero.data import Node
from dtn7zero.storage import Storage
from dtn7zero.utility import is_timestamp_older_than_timeout, get_current_clock_millis, debug, warning, build_broadcast_ipv4_address
from py_dtn7.bundle import Flags

if RUNNING_MICROPYTHON:
    import wlan
else:
    import netifaces

try:
    from cbor2 import dumps, loads
except ImportError:
    from cbor import dumps, loads


class BeaconFlags(Flags):

    @property
    def eid_present(self) -> bool:
        """
        :return: True if the source endpoint identifier is present in this beacon
        """
        return self.get_flag(0)

    @property
    def service_block_present(self) -> bool:
        """
        :return: True if the service block is present in this beacon
        """
        return self.get_flag(1)

    @property
    def beacon_period_present(self) -> bool:
        """
        :return: True if the service block is present in this beacon
        """
        return self.get_flag(2)

    @property
    def reserved_3_to_7(self) -> int:
        """
        :return: shift to zero of bits 3 to 7 that are reserved for future use
        """
        return (self.flags >> 3) & 3


class Beacon:

    def __init__(
            self,
            version: int,
            beacon_flags: BeaconFlags,
            eid_scheme: Optional[int],
            eid_specific_part: Optional[str],
            beacon_sequence_number: int,
            service_block: Tuple[List[Tuple[str, int]], Dict[int, bytes]],
            beacon_period: Optional[int]
    ):
        self.version: int = version
        self.beacon_flags: BeaconFlags = beacon_flags
        self.eid_scheme: Optional[int] = eid_scheme
        self.eid_specific_part: Optional[str] = eid_specific_part
        self.beacon_sequence_number: int = beacon_sequence_number
        self.service_block: Tuple[List[Tuple[str, int]], Dict[int, bytes]] = service_block
        self.beacon_period: Optional[int] = beacon_period

        if version != 7:
            raise NotImplementedError('beacons with other versions than 7 are currently not supported')

        assert not beacon_flags.eid_present or eid_scheme is not None and eid_specific_part is not None
        assert not beacon_flags.service_block_present or service_block is not None
        assert not beacon_flags.beacon_period_present or beacon_period is not None

    def __repr__(self) -> str:
        return '<Beacon: {}]>'.format(self.to_block_data())

    @staticmethod
    def from_block_data(beacon: list):
        version = beacon[0]
        beacon_flags = BeaconFlags(beacon[1])
        beacon_sequence_number = None
        eid_scheme = None
        eid_specific_part = None
        service_block = ([], {})
        beacon_period = None

        expected_length = 3 + int(beacon_flags.eid_present) + int(beacon_flags.service_block_present) + int(beacon_flags.beacon_period_present)
        if len(beacon) != expected_length:
            raise IndexError('cannot decode beacon because actual length {} differs from length, suggested by flags {}. block data: {}'.format(len(beacon), expected_length, beacon))

        # there are some uncertainties I want to circumvent with this approach:
        #  1. the EID and Beacon Sequence Number might be switched in position (indexes 2 and 3)
        #     (ipnd-thesis describes EID at index 3, while dtn7rs places EID at index 2)
        #  2. EID, Service Block, and Beacon Period might be omitted
        #     (ipdn-thesis describes to omit empty fields, which can place later items at earlier indexes)
        for item in beacon[2:]:
            if isinstance(item, int):
                if beacon_sequence_number is None:  # Beacon Sequence Number is set first (in accordance with beacon order)
                    beacon_sequence_number = item
                elif beacon_flags.beacon_period_present:  # Beacon Period is set second (skips unknown integer field if flag is not set)
                    beacon_period = item
            elif isinstance(item, list):
                if eid_scheme is None and beacon_flags.eid_present:  # EID is set first (if flag is set)
                    eid_scheme, eid_specific_part = item
                elif beacon_flags.service_block_present:  # Service Block is set second (if flag is set)
                    service_block = item

        return Beacon(version, beacon_flags, eid_scheme, eid_specific_part, beacon_sequence_number, service_block, beacon_period)

    def to_block_data(self):
        block = [self.version, self.beacon_flags.flags]

        # order is inspired by the dtn7rs implementation and not the ipnd-thesis (EID and Beacon Sequence Number switched)
        if self.beacon_flags.eid_present:
            block.append((self.eid_scheme, self.eid_specific_part))
        block.append(self.beacon_sequence_number)
        if self.beacon_flags.service_block_present:
            block.append(self.service_block)
        if self.beacon_flags.beacon_period_present:
            block.append(self.beacon_period)

        return block

    def to_cbor(self) -> bytes:
        # although bundles must be an infinite array, nothing is specified here, so keep the finite array
        return dumps(self.to_block_data())

    @staticmethod
    def from_objects(
            beacon_sequence_number: int,
            eid_scheme: Optional[int] = None,
            eid_specific_part: Optional[str] = None,
            service_block: Optional[Tuple[List[Tuple[str, int]], Dict[int, bytes]]] = None,
            beacon_period: Optional[int] = None
    ):
        beacon_flags = BeaconFlags()

        if bool(eid_scheme) != bool(eid_specific_part):
            raise IndexError('EID must be complete, got: {}, {}'.format(eid_scheme, eid_specific_part))
        if eid_scheme is not None:
            beacon_flags.set_flag(0)
        if service_block is not None:
            beacon_flags.set_flag(1)
        else:
            service_block = ([], {})
        if beacon_period is not None:
            beacon_flags.set_flag(2)

        return Beacon(7, beacon_flags, eid_scheme, eid_specific_part, beacon_sequence_number, service_block, beacon_period)

    @staticmethod
    def from_cbor(data: bytes):
        return Beacon.from_block_data(loads(data))

    def increment_beacon_sequence_number_by_one(self):
        # ipnd-thesis states to use an unsigned 32bit integer and wrap around on overflow
        self.beacon_sequence_number = (self.beacon_sequence_number + 1) & 0xffffffff

    def is_continuous_with_old_beacon_sequence_number(self, old_beacon_sequence_number: int):
        if old_beacon_sequence_number == 0xffffffff:
            return self.beacon_sequence_number == 0
        return self.beacon_sequence_number == old_beacon_sequence_number


class IPND:

    """
    for now, we only support broadcast on all interfaces and IPv4 only.
    todo: extend functionality to filter network interfaces and support IPv6
    todo: extend functionality to delete nodes after a beacon timeout
    """
    def __init__(self, eid_scheme: int, eid_specific_part: str, storage: Storage):
        self.storage = storage

        # todo: check dynamically for new networks -> also test with changing networks
        if RUNNING_MICROPYTHON:
            self.broadcast_addresses, self.own_addresses = IPND.get_micropython_ipv4_broadcast_addresses()
        else:
            self.broadcast_addresses, self.own_addresses = IPND.get_cpython_ipv4_broadcast_addresses()

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        if not RUNNING_MICROPYTHON:
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.settimeout(0)

        self.sock.bind(('', 3003))

        # self.own_beacon = create_minimal_output_beacon(eid_scheme, eid_specific_part)
        self.own_beacon = Beacon.from_objects(
            beacon_sequence_number=0,
            eid_scheme=eid_scheme,
            eid_specific_part=eid_specific_part,
            service_block=([(IPND_IDENTIFIER_MTCP, PORT_MTCP)], {})  # todo: extend for all and active clas'
        )

        self.last_beacon_broadcast = 0

    def update(self):
        try:
            # todo: for now it seems one full datagram is returned here, as long as the datagram is smaller than bytes-trying-to-receive
            raw_data, (address, port) = self.sock.recvfrom(IPND_BEACON_MAX_SIZE)
        except OSError:
            pass
        except MemoryError:
            warning('MEMORY ERROR DURING BEACON RECEIVE, PASS')
        else:
            try:
                # eid_scheme, eid_specific_part, clas, services = extract_beacon_information_from(raw_data)
                beacon = Beacon.from_cbor(raw_data)
            except Exception as e:
                warning('could not decode beacon. error: {}'.format(e))
            else:
                if address not in self.own_addresses:
                    existing_node = self.storage.get_node(address)

                    if existing_node is None:
                        debug('received beacon from new node: {}, size: {}'.format(address, len(raw_data)))

                        new_node = Node(address, (beacon.eid_scheme, beacon.eid_specific_part), dict(beacon.service_block[0]), beacon.beacon_sequence_number)
                        self.storage.add_node(new_node)

                        sequence_number_matches = False
                    else:
                        debug('received beacon from known node: {}, size: {}'.format(address, len(raw_data)))
                        # existing_node.merge_new_info(eid_scheme, eid_specific_part, dict(clas))
                        existing_node.merge_new_info(beacon.eid_scheme, beacon.eid_specific_part, dict(beacon.service_block[0]))

                        sequence_number_matches = existing_node.advance_sequence_number(beacon.beacon_sequence_number)

                    if not sequence_number_matches:
                        # send back a uni-cast beacon to a previously unknown node for faster knowledge spread
                        # ideal case: it never received a beacon from us -> current state (sequence number) is new to the node
                        # not ideal case: beacons were exchanged concurrently -> state (sequence number) is duplicate, which is unspecified and ideally ignored
                        # dtn7zero specific detail: we add unicast information to the beacon, so there is no second unicast beacon sent back to us

                        if not (42 in beacon.service_block[1] and beacon.service_block[1][42] == b'unicast'):
                            self.own_beacon.service_block[1][42] = b'unicast'
                            self.send_own_beacon_to(address)
                            del self.own_beacon.service_block[1][42]

        if is_timestamp_older_than_timeout(self.last_beacon_broadcast, IPND_SEND_INTERVAL_MILLISECONDS):
            for address in self.broadcast_addresses:
                self.send_own_beacon_to(address)
            # minimal_output_beacon_increase_counter_by_one(self.own_beacon)
            self.own_beacon.increment_beacon_sequence_number_by_one()
            self.last_beacon_broadcast = get_current_clock_millis()

    def send_own_beacon_to(self, address: str):
        message = self.own_beacon.to_cbor()

        while len(message) > 0:
            sent_bytes = self.sock.sendto(message, (address, PORT_IPND))
            message = message[sent_bytes:]

    @staticmethod
    def get_micropython_ipv4_broadcast_addresses() -> (list, list):
        address, subnet, _, _ = wlan.ifconfig()

        if address == '0.0.0.0':
            warning('wlan is not connected, cannot form broadcast address')
            return []

        return [build_broadcast_ipv4_address(address, subnet)], [address]

    @staticmethod
    def get_cpython_ipv4_broadcast_addresses() -> (list, list):
        broadcast_addresses = []
        own_addresses = []

        for interface in netifaces.interfaces():
            interface_information = netifaces.ifaddresses(interface).get(netifaces.AF_INET, [])

            for address_information in interface_information:
                address = address_information['addr']
                netmask = address_information['netmask']

                # in case 'peer' exists => on linux 'lo' interface there is no 'broadcast', only 'peer', but 'netmask' exists
                # in case 'addr' == 'broadcast' => on linux CORE emulator, no correct 'broadcast' address is provided
                if 'peer' in address_information or address_information['broadcast'] == address:
                    broadcast_addresses.append(build_broadcast_ipv4_address(address, netmask))
                else:
                    broadcast_addresses.append(address_information['broadcast'])

                own_addresses.append(address)

        return broadcast_addresses, own_addresses
