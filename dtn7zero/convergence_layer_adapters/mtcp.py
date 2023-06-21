import socket
import struct
from typing import Optional, Dict, Tuple

try:
    from cbor2 import dumps
except ImportError:
    from cbor import dumps

from dtn7zero.constants import PORT_MTCP, MTCP_MAX_CONNECTIONS_STATE_WAITING, SOCKET_RECEIVE_BUFFER_SIZE, \
    MTCP_MAX_CONNECTIONS_STATE_OPEN_RECEIVE, MTCP_TIMEOUT_MILLISECONDS_INACTIVE_RECEIVE, \
    MTCP_TIMEOUT_MILLISECONDS_STALLED_SEND, RUNNING_MICROPYTHON, IPND_IDENTIFIER_MTCP
from dtn7zero.convergence_layer_adapters import PushBasedCLA
from dtn7zero.data import Node
from dtn7zero.utility import get_current_clock_millis, is_timestamp_older_than_timeout, debug, warning
from py_dtn7 import Bundle


TYPE_BYTES = 0x40

_CBOR_TYPE_MASK = 0xE0
_CBOR_INFO_BITS = 0x1F

_CBOR_UINT8_FOLLOWS = 24  # 0x18
_CBOR_UINT16_FOLLOWS = 25  # 0x19
_CBOR_UINT32_FOLLOWS = 26  # 0x1a
_CBOR_UINT64_FOLLOWS = 27  # 0x1b


class RemoteClosedConnectionException(Exception):
    pass


class RemoteStalledConnectionException(Exception):
    pass


class ReceivedInvalidDataOnSocketException(Exception):
    pass


def _poll_one_byte(connection):
    try:
        buf = connection.recv(1)
    # if a non-blocking read fails we have read everything there is to read at the moment
    # ,but we need to read exactly n bytes
    except OSError:
        return None
    else:
        # on 0 bytes received the socket connection is closed
        # the desired 1 byte could not be received -> incomplete data -> discard
        if len(buf) == 0:
            raise RemoteClosedConnectionException()

        return buf


def _receive_exactly_n_bytes(connection, num_bytes):
    result = b''

    while True:
        try:
            buf = connection.recv(min(num_bytes, SOCKET_RECEIVE_BUFFER_SIZE))
        # if a non-blocking read fails we have read everything there is to read at the moment
        # ,but we need to read exactly n bytes
        except OSError:
            pass
        else:
            # on 0 bytes received the socket connection is closed
            # the desired num_bytes could not be received in total -> incomplete data -> discard
            if len(buf) == 0:
                raise RemoteClosedConnectionException()

            result += buf
            num_bytes -= len(buf)

            if num_bytes == 0:
                return result


def _read_full_message_or_none(connection):
    header = _poll_one_byte(connection)

    if header is None:
        return None

    header = struct.unpack_from('!B', header, 0)[0]

    tag = header & _CBOR_TYPE_MASK
    tag_aux = header & _CBOR_INFO_BITS

    if tag != TYPE_BYTES:
        raise ReceivedInvalidDataOnSocketException('mtcp cla received invalid header: only accepting type byte-string')

    if tag_aux <= 23:
        aux = tag_aux
    elif tag_aux == _CBOR_UINT8_FOLLOWS:
        data = _receive_exactly_n_bytes(connection, 1)
        aux = struct.unpack_from('!B', data, 0)[0]
    elif tag_aux == _CBOR_UINT16_FOLLOWS:
        data = _receive_exactly_n_bytes(connection, 2)
        aux = struct.unpack_from('!H', data, 0)[0]
    elif tag_aux == _CBOR_UINT32_FOLLOWS:
        data = _receive_exactly_n_bytes(connection, 4)
        aux = struct.unpack_from('!I', data, 0)[0]
    elif tag_aux == _CBOR_UINT64_FOLLOWS:
        data = _receive_exactly_n_bytes(connection, 8)
        aux = struct.unpack_from('!Q', data, 0)[0]
    else:
        raise ReceivedInvalidDataOnSocketException('mtcp cla received invalid header: only accepting definite length byte-strings')

    return _receive_exactly_n_bytes(connection, aux)


def _send_message(address, port, message):
    # create a standard ipv4 stream socket
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.settimeout(0)

    '''
    Connection Establishment Analysis

    Problem
    socket.settimeout(1) -> does not set the desired timeout on MicroPython (ESP32-GENERIC), 
    but instead keeps the default timeout of about 12 seconds.

    Analysis
    The following OSError numbers (e.errno) are thrown on MicroPython on connecting with a non-blocking socket:
    119 EINPROGRESS  -> thrown by the connect request on a non-blocking socket
     11 EAGAIN       -> thrown if no data could be sent (also thrown on sending b'')

    Solution
    As we cannot be sure when the socket is connected we just skip the connect timeout and go straight to the deadlock timeout.
    To be consistent on MicroPython and CPython we do this on both.
    '''

    try:
        client_socket.connect((address, port))
    except OSError:
        # this will raise an exception on non-blocking sockets
        pass

    deadlock_check = get_current_clock_millis()
    while len(message) > 0 and not is_timestamp_older_than_timeout(deadlock_check, MTCP_TIMEOUT_MILLISECONDS_STALLED_SEND):
        try:
            bytes_sent = client_socket.send(message)
        # Windows behaviour??? If other end is forcibly closed it raises an ConnectionResetError -> OSError
        except OSError:
            # We ignore all OSErrors.
            # The correct way would be to check the errno for "busy" (MicroPython -> 11, CPython+Windows -> 10035)
            # but, because it is implementation dependent, and we do not expect the receiver to immediately close the
            # connection, we accept the rare case of a deadlock-timeout because of an early-closed socket.
            pass
        else:
            # on 0 bytes sent the socket connection is closed
            if bytes_sent == 0:
                client_socket.close()
                raise RemoteClosedConnectionException("0 bytes")
            # update the message and length to send
            message = message[bytes_sent:]
            # update our deadlock-check as we managed to send some data
            deadlock_check = get_current_clock_millis()

    if len(message) > 0:
        client_socket.close()
        raise RemoteStalledConnectionException()

    client_socket.close()


class MTcpCLA(PushBasedCLA):

    def __init__(self):
        # a standard ipv4 stream socket
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # allow immediate rebind to a floating socket (last app crashed or otherwise non fully closed server socket)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # bind to all interfaces available
        self.socket.bind(('0.0.0.0', PORT_MTCP))
        # We will accept a maximum of x connect requests into our connect queue before we are busy
        # A connection gets out of this queue on socket creation
        self.socket.listen(MTCP_MAX_CONNECTIONS_STATE_WAITING)
        # change to non-blocking mode
        # MicroPython supports only one thread/process, and therefore we need to implement everything synchronous
        self.socket.settimeout(0)

        self.open_receive_connections: Dict[str, (socket.socket, int)] = {}
        self.gracefully_shutdown_connections: Dict[str, socket.socket] = {}

    def poll(self, bundle_id: str = None, node: Node = None) -> Tuple[Optional[Bundle], Optional[str]]:
        if bundle_id is not None or node is not None:
            raise Exception('cannot poll specific bundle from specific node with mtcp cla')

        # check for new incoming connections
        self._check_for_new_connections()

        # try to receive one bundle
        serialized_bundle, from_node_address = self._poll_from_open_receive_connections()

        if serialized_bundle is None:
            serialized_bundle, from_node_address = self._poll_from_gracefully_shutdown_connections()

        if serialized_bundle is None:
            return None, None

        try:
            return Bundle.from_cbor(serialized_bundle), from_node_address
        except Exception as e:
            warning('error during mtcp bundle deserialization, ignoring bundle. error: {}'.format(e))
        return None, None

    def _poll_from_open_receive_connections(self):
        serialized_bundle, from_node_address = None, None

        for address_tuple, (connection, last_received) in tuple(self.open_receive_connections.items()):
            try:
                serialized_bundle = _read_full_message_or_none(connection)
            except RemoteClosedConnectionException:
                debug('remote closed down incoming mtcp connection {}'.format(address_tuple))
                if not RUNNING_MICROPYTHON:
                    connection.shutdown(socket.SHUT_RDWR)
                connection.close()
                del self.open_receive_connections[address_tuple]
            except ReceivedInvalidDataOnSocketException as e:
                warning('incoming mtcp connection {} sent invalid data, discarding connection, error: {}'.format(address_tuple, e))
                if not RUNNING_MICROPYTHON:
                    connection.shutdown(socket.SHUT_RDWR)
                connection.close()
                del self.open_receive_connections[address_tuple]
            else:
                if serialized_bundle is not None:
                    from_node_address = address_tuple[0]
                    self.open_receive_connections[address_tuple] = (connection, get_current_clock_millis())
                    break
                elif is_timestamp_older_than_timeout(last_received, MTCP_TIMEOUT_MILLISECONDS_INACTIVE_RECEIVE):
                    if not RUNNING_MICROPYTHON:
                        debug('gracefully closing incoming mtcp connection {} due to inactivity timeout'.format(address_tuple))
                        connection.shutdown(socket.SHUT_WR)
                        self.gracefully_shutdown_connections[address_tuple] = connection
                    else:
                        debug('forcefully closing incoming mtcp connection {} due to inactivity timeout (no shutdown support on micropython)'.format(address_tuple))
                        connection.close()
                    del self.open_receive_connections[address_tuple]

        return serialized_bundle, from_node_address

    def _poll_from_gracefully_shutdown_connections(self):
        serialized_bundle, from_node_address = None, None

        for address_tuple, connection in tuple(self.gracefully_shutdown_connections.items()):
            try:
                serialized_bundle = _read_full_message_or_none(connection)
            except RemoteClosedConnectionException:
                debug('gracefully shutdown mtcp connection closed by remote {}'.format(address_tuple))
                connection.close()
                del self.gracefully_shutdown_connections[address_tuple]
            except ReceivedInvalidDataOnSocketException as e:
                debug('gracefully shutdown mtcp connection {} sent invalid data, discarding connection, error: {}'.format(address_tuple, e))
                connection.close()
                del self.gracefully_shutdown_connections[address_tuple]
            else:
                if serialized_bundle is not None:
                    from_node_address = address_tuple[0]
                    break

        return serialized_bundle, from_node_address

    def _check_for_new_connections(self):
        if len(self.open_receive_connections) < MTCP_MAX_CONNECTIONS_STATE_OPEN_RECEIVE:
            try:
                client_socket, address_tuple = self.socket.accept()
            except OSError:
                # no new connect request waiting
                pass
            else:
                # change to non-blocking mode to be able to poll without blocking
                client_socket.settimeout(0)

                # we allow multiple connections from one IP address, because if we accept the connection, the whole bundle
                #  could be already transmitted before we can close the connection from our checks
                #  -> would lead to false positive on the sender side
                # next best thing: limit number of open-receive-connections
                # print('new mtcp receive connection opened from address {}'.format(address_tuple))
                self.open_receive_connections[address_tuple] = (client_socket, get_current_clock_millis())

    def send_to(self, node: Optional[Node], serialized_bundle: bytes) -> bool:
        if node is None:
            raise Exception('cannot send bundle to unspecified node with mtcp cla')

        message = dumps(serialized_bundle)

        if IPND_IDENTIFIER_MTCP in node.clas:
            try:
                port = node.clas[IPND_IDENTIFIER_MTCP]
                _send_message(node.address, port, message)
            except (RemoteClosedConnectionException, RemoteStalledConnectionException):
                del node.clas[IPND_IDENTIFIER_MTCP]  # the node can re-announce it, but currently we cannot connect
                return False
            return True
        return False
