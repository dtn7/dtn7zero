import sys

RUNNING_MICROPYTHON = sys.implementation.name == 'micropython'


class _SubConfigurationIPND:

    def __init__(self):
        self.IDENTIFIER_MTCP = 'mtcp'
        self.IDENTIFIER_REST = 'rest'  # unofficial, to be used to manually add the rest-cla to the router
        self.IDENTIFIER_ESPNOW = 'espnow'  # unofficial, to be used to manually add the espnow-cla to the router
        self.SEND_INTERVAL_MILLISECONDS = 10000

        if RUNNING_MICROPYTHON:
            self.BEACON_MAX_SIZE = 256  # for some reason a bigger datagram receive leads to memory leaks ???
        else:
            self.BEACON_MAX_SIZE = 4096


class _SubConfigurationMTCP:

    def __init__(self):
        if RUNNING_MICROPYTHON:
            self.MAX_CONNECTIONS_STATE_WAITING = 2
            self.MAX_CONNECTIONS_STATE_OPEN_RECEIVE = 3
            self.TIMEOUT_MILLISECONDS_INACTIVE_RECEIVE = 5000
        else:
            self.MAX_CONNECTIONS_STATE_WAITING = 5
            self.MAX_CONNECTIONS_STATE_OPEN_RECEIVE = 10000
            self.TIMEOUT_MILLISECONDS_INACTIVE_RECEIVE = 1000000

        self.TIMEOUT_MILLISECONDS_STALLED_SEND = 2000


class _SubConfigurationPORT:

    def __init__(self):
        self.BEACON_UDP = 7000
        self.REST = 3000
        self.MTCP = 16162
        self.IPND = 3003


class _Configuration:
    RUNNING_MICROPYTHON = sys.implementation.name == 'micropython'

    def __init__(self):
        self.DEBUG = False
        self.WARNING = True

        self.ATTACH_PREVIOUS_NODE_BLOCK = True
        self.SEND_STATUS_REPORTS_ENABLED = False
        self.ENCODING = 'utf-8'
        self.IPND: _SubConfigurationIPND = _SubConfigurationIPND()
        self.MTCP: _SubConfigurationMTCP = _SubConfigurationMTCP()
        self.PORT: _SubConfigurationPORT = _SubConfigurationPORT()

        self.SIMPLE_EPIDEMIC_ROUTER_MIN_NODES_TO_FORWARD_TO = 3
        self.SOCKET_RECEIVE_BUFFER_SIZE = 512

        if RUNNING_MICROPYTHON:
            self.SIMPLE_IN_MEMORY_STORAGE_MAX_STORED_BUNDLES = 7  # experimental setting
            self.SIMPLE_IN_MEMORY_STORAGE_MAX_KNOWN_BUNDLE_IDS = 18  # experimental setting
        else:
            self.SIMPLE_IN_MEMORY_STORAGE_MAX_STORED_BUNDLES = 10000
            self.SIMPLE_IN_MEMORY_STORAGE_MAX_KNOWN_BUNDLE_IDS = 100000


CONFIGURATION = _Configuration()
