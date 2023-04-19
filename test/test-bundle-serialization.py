"""
To be run on CPython or MicroPython.

Tests the correct (de)-serialization of a bundle.
"""
from py_dtn7 import Bundle

raw_bundle = b'\x9f\x88\x07\x1a\x00\x02\x00\x04\x00\x82\x01l//node1/ping\x82\x01h//node1/\x82\x01h//node1/\x82\x1b\x00\x00\x00\xa8\xb0R\x18\xb8\x00\x1a\x006\xee\x80\x85\n\x02\x00\x00D\x82\x18 \x00\x85\x01\x01\x00\x00X@LwL2KMBGNgy11Y8Ofa4EYfDultcE7Ulq7b3veSMSKgzvSjDbO0aRVxQYwMInIR4g\xff'

bundle = Bundle.from_cbor(raw_bundle)

print(bundle)

assert raw_bundle == bundle.to_cbor()

flags = bundle.primary_block.bundle_processing_control_flags

print(flags)

assert (flags.is_fragment |
        flags.payload_is_admin_record << 1 |
        flags.do_not_fragment << 2 |
        flags.reserved_3_to_4 << 3 |
        flags.acknowledgement_is_requested << 5 |
        flags.status_time_is_requested << 6 |
        flags.reserved_7_to_13 << 7 |
        flags.status_of_report_reception_is_requested << 14 |
        flags.reserved_15 << 15 |
        flags.status_of_report_forwarding_is_requested << 16 |
        flags.status_of_report_delivery_is_requested << 17 |
        flags.status_of_report_deletion_is_requested << 18 |
        flags.reserved_19_to_20 << 19 |
        flags.unassigned_21_to_63 << 21 == flags.flags)

flags = bundle.payload_block.block_processing_control_flags

print(flags)

assert (flags.block_must_be_replicated |
        flags.report_status_if_block_cant_be_processed << 1 |
        flags.delete_bundle_if_block_cant_be_processed << 2 |
        flags.reserved_3 << 3 |
        flags.discard_block_if_block_cant_be_processed << 4 |
        flags.reserved_5_to_6 << 5 |
        flags.unassigned_7_to_63 << 7 == flags.flags)
