"""
An experimental LoRa CLA that broadcasts bundles like the ESPNOW CLA.

It uses a message format compatible to the RH_RF95 library.
    -> fixed header: (TO, FROM, ID, FLAGS) == \xff \xff \x00 \x00

It offers modem configurations compatible to the rf95modem library.
    -> default: Bw125Cr45Sf128

As the message payload contains simply the encoded bundle bytes, messages may be sent and/or received via rf95modem.
"""
from typing import Tuple, Optional
from machine import SoftSPI, Pin

from py_dtn7 import Bundle
from dtn7zero.convergence_layer_adapters import PushBasedCLA
from dtn7zero.data import Node
from dtn7zero.utility import warning, debug
from sx127x import SX127x, DEVICE_CONFIG_ESP32_TTGO, LORA_PARAMETERS_RH_RF95_bw125cr45sf128, \
    LORA_PARAMETERS_RH_RF95_bw125cr45sf2048, LORA_PARAMETERS_RH_RF95_bw125cr48sf4096, \
    LORA_PARAMETERS_RH_RF95_bw31_25cr48sf512, LORA_PARAMETERS_RH_RF95_bw500cr45sf128


BROADCAST_MAC = b'\xff\xff\xff\xff\xff\xff'


class RF95LoRaCLA(PushBasedCLA):

    def __init__(self, device_config=DEVICE_CONFIG_ESP32_TTGO, lora_parameters=LORA_PARAMETERS_RH_RF95_bw125cr45sf128):
        device_spi = SoftSPI(baudrate=10000000,
                             polarity=0, phase=0, bits=8, firstbit=SoftSPI.MSB,
                             sck=Pin(device_config['sck'], Pin.OUT, Pin.PULL_DOWN),
                             mosi=Pin(device_config['mosi'], Pin.OUT, Pin.PULL_UP),
                             miso=Pin(device_config['miso'], Pin.IN, Pin.PULL_UP))

        self.lora = SX127x(device_spi, pins=device_config, parameters=lora_parameters)

    def poll(self, bundle_id: str = None, node: Node = None) -> Tuple[Optional[Bundle], Optional[str]]:
        if bundle_id is not None or node is not None:
            raise Exception('cannot poll specific bundle from specific node with lora cla')

        serialized_message = self.lora.try_receive()

        if serialized_message:
            debug('received LoRa message')
            try:
                # removing rh_rf95 header (TO, FROM, ID, FLAGS)
                serialized_bundle = serialized_message[4:]
                from_node_address = serialized_message[1]
                return Bundle.from_cbor(serialized_bundle), from_node_address
            except Exception as e:
                warning('error during lora bundle deserialization, ignoring bundle. error: {}'.format(e))

        return None, None

    def send_to(self, node: Optional[Node], serialized_bundle: bytes) -> bool:
        if node is not None:
            raise Exception('cannot send bundle to specific node with lora cla')

        # adding default rh_rf95 broadcast header (TO, FROM, ID, FLAGS)
        serialized_message = b'\xff\xff\x00\x00' + serialized_bundle

        debug('started sending bundle via LoRa')
        self.lora.send(serialized_message)
        debug('finished sending bundle via LoRa')
        return True
