"""
DTN7-Zero API

Inspired by the networkzero library.

Provides a simple NDN (named data network) interface on top of DTN7.
"""
import time

from typing import Optional, List, Tuple, Callable

from dtn7zero.bundle_protocol_agent import BundleProtocolAgent
from dtn7zero.configuration import CONFIGURATION, RUNNING_MICROPYTHON
from dtn7zero.convergence_layer_adapters.mtcp import MTcpCLA
from dtn7zero.data import Node
from dtn7zero.endpoints import LocalEndpoint, LocalGroupEndpoint
from dtn7zero.routers.simple_epidemic_router import SimpleEpidemicRouter
from dtn7zero.storage.simple_in_memory_storage import SimpleInMemoryStorage
from dtn7zero.utility import get_current_clock_millis, is_timestamp_older_than_timeout
from py_dtn7.bundle import Bundle, PrimaryBlock

if RUNNING_MICROPYTHON:
    import _thread
else:
    import threading


BPA: Optional[BundleProtocolAgent] = None
BPA_THREAD = None


class SimpleEndpoint:

    def __init__(self, service_name, callback=None):
        self._callback = callback
        self._endpoint = LocalEndpoint(service_name, self._simplifying_callback if callback is not None else None)

    def _simplifying_callback(self, bundle: Bundle):
        self._callback(bundle.payload_block.data, bundle.primary_block.full_source_uri, bundle.primary_block.full_destination_uri, bundle.primary_block)

    def send(self, payload: bytes, full_destination_address: str, anonymous: bool = False):
        """ sends a payload(message) to the specified node_id and service_name
        """
        self._endpoint.start_transmission(payload, full_destination_address, anonymous=anonymous)

    def poll(self) -> Tuple[Optional[bytes], Optional[str], Optional[str], Optional[PrimaryBlock]]:
        """ polls a passive endpoint (without callback) for a new payload(message)

        use pythons value unpacking feature with the methods' signature like so:

        payload, full_source_uri, full_destination_uri, primary_block = my_endpoint.poll()

        the primary block is provided for direct access to additional information
        """
        bundle = self._endpoint.poll()

        if bundle is not None:
            return bundle.payload_block.data, bundle.primary_block.full_source_uri, bundle.primary_block.full_destination_uri, bundle.primary_block
        return None, None, None, None


class SimpleGroupEndpoint:

    def __init__(self, full_group_uri, callback=None):
        self._callback = callback
        self._endpoint = LocalGroupEndpoint(full_group_uri, self._simplifying_callback if callback is not None else None)

    def _simplifying_callback(self, bundle: Bundle):
        self._callback(bundle.payload_block.data, bundle.primary_block.full_source_uri, bundle.primary_block.full_destination_uri, bundle.primary_block)

    def poll(self) -> Tuple[Optional[bytes], Optional[str], Optional[str], Optional[PrimaryBlock]]:
        """ polls a passive endpoint (without callback) for a new payload(message)

        use pythons value unpacking feature with the methods' signature like so:

        payload, full_source_uri, full_destination_uri, primary_block = my_endpoint.poll()

        the primary block is provided for direct access to additional information
        """
        bundle = self._endpoint.poll()

        if bundle is not None:
            return bundle.payload_block.data, bundle.primary_block.full_source_uri, bundle.primary_block.full_destination_uri, bundle.primary_block
        return None, None, None, None


def setup(full_node_uri: str, node_receive_callback: Callable[[bytes, str, str, PrimaryBlock], None] = None) -> SimpleEndpoint:
    """ initializes the bundle protocol agent with the provided full-node-id and returns the node-central endpoint

    full_node_uri examples:
            dtn addressing scheme -> "dtn://node1/", "dtn://cool-node/"  # '/' at the end is mandatory
            ipn addressing scheme -> "ipn://12", "ipn://24.25"  # will be joined with the endpoints via '.'

    node_receive_callback -> may be None, but then you need to manually poll the endpoint

    node_receive_callback signature/example:

    callback(payload: bytes, full_source_uri: str, full_destination_uri: str, primary_block: PrimaryBlock) -> None:
        pass

    the primary block is provided for direct access to additional information

    call only once!
    """
    global BPA

    if BPA is not None:
        raise Exception('setup(node_id) was called twice!')

    storage = SimpleInMemoryStorage()
    router = SimpleEpidemicRouter({CONFIGURATION.IPND.IDENTIFIER_MTCP: MTcpCLA()}, storage)
    BPA = BundleProtocolAgent(full_node_uri, storage, router, use_ipnd=True)

    # node specific endpoint works like a normal endpoint (only receives exactly matched bundles), but for the node itself
    endpoint = SimpleEndpoint('', node_receive_callback)
    BPA.register_endpoint(endpoint._endpoint)

    return endpoint


def register(endpoint_identifier: str, receive_callback: Callable[[bytes, str, str, PrimaryBlock], None] = None) -> SimpleEndpoint:
    """ registers an endpoint at the bundle protocol agent over which you can send/receive bundles(messages)

    endpoint_identifier examples:
        dtn addressing scheme -> "echo", "echo/subecho"
        ipn addressing scheme -> "12", "24.15.16"

    receive_callback -> may be None, but then you need to manually poll the endpoint

    receive_callback signature/example:

    callback(payload: bytes, full_source_uri: str, full_destination_uri: str, primary_block: PrimaryBlock) -> None:
        pass

    the primary block is provided for direct access to additional information
    """
    global BPA

    if BPA is None:
        raise Exception('setup(node_id) was not called!')

    endpoint = SimpleEndpoint(endpoint_identifier, receive_callback)
    BPA.register_endpoint(endpoint._endpoint)

    return endpoint


def register_group(full_group_uri: str, receive_callback: Callable[[bytes, str, str, PrimaryBlock], None] = None) -> SimpleGroupEndpoint:
    """ registers a group-endpoint at the bundle protocol agent over which you can receive group-addressed bundles

    full_group_uri examples:
        "dtn://news/~sport", "dtn://my-group/interesting/new/~topics"

    receive_callback -> may be None, but then you need to manually poll the endpoint

    receive_callback signature/example:

    callback(payload: bytes, full_source_uri: str, full_destination_uri: str, primary_block: PrimaryBlock) -> None:
        pass

    the primary block is provided for direct access to additional information
    """
    global BPA

    if BPA is None:
        raise Exception('setup(node_id) was not called!')

    endpoint = SimpleGroupEndpoint(full_group_uri, receive_callback)
    BPA.register_group_endpoint(endpoint._endpoint)

    return endpoint


def discover() -> List[Node]:
    """ returns a list of all currently known other nodes in the local network
    """
    global BPA

    if BPA is None:
        raise Exception('setup(node_id) was not called!')

    return list(BPA.storage.get_nodes())


def update():
    """ explicitly updates the bundle protocol agent

    to be called in an endless loop if you want to write the loop yourself

    the alternative solution (or inspiration) is: run_forever()
    """
    global BPA

    if BPA is None:
        raise Exception('setup(node_id was not called!')

    BPA.update()


def run_forever(loop_callback=None, loop_callback_interval_milliseconds=1000, _sleep_time_seconds=0):
    """ update loop to run the bundle protocol agent until KeyboardInterrupt

    custom_logic_callback can be used for application specific logic after the bundle protocol agent was started

    custom_logic_callback signature:

    callback() -> None:
        pass
    """
    global BPA

    if BPA is None:
        raise Exception('setup(node_id was not called!')

    last_callback_execution = get_current_clock_millis()

    try:
        while True:
            BPA.update()

            if loop_callback is not None and is_timestamp_older_than_timeout(last_callback_execution, loop_callback_interval_milliseconds):
                last_callback_execution = get_current_clock_millis()
                loop_callback()

            time.sleep(_sleep_time_seconds)
    except KeyboardInterrupt:
        pass


def start_background_update_thread(_sleep_time_seconds=0):
    """ (experimental) background update thread

    On MicroPython the limited RAM can lead to crashes (most prominently a maximum-recursion-depth RuntimeError).
    The _thread.stack_size(...) can be adjusted for compensation if needed and possible.
    """
    global BPA
    global BPA_THREAD

    if BPA is None:
        raise Exception('setup(node_id was not called!')

    if BPA_THREAD is not None:
        raise Exception('start_background_update_thread() should only be called once!')

    if RUNNING_MICROPYTHON:
        _thread.stack_size(11500)  # experimental setting: 7000 does not run, 8000 does run, 11500 picked for leeway

        def update_runner():
            while True:
                BPA.update()
                time.sleep(_sleep_time_seconds)

        BPA_THREAD = _thread.start_new_thread(update_runner, ())
    else:
        def self_stopping_update_runner():
            while threading.main_thread().is_alive():
                BPA.update()
                time.sleep(_sleep_time_seconds)

        BPA_THREAD = threading.Thread(target=self_stopping_update_runner)
        BPA_THREAD.start()
