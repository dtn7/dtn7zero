import time
import re
from typing import Iterable

from dtn7zero.constants import DEBUG, WARNING

NODE_URI_REGEX = re.compile(r'(^dtn://[^~/]+/$)|(^ipn://\d+(\.\d+)*$)')
ENDPOINT_URI_REGEX = re.compile(r'(^dtn://none$)|(^dtn://[^~/]+/([^~/]+/)*[^~/]+$)|(^ipn://\d+(\.\d+)+$)')
GROUP_URI_REGEX = re.compile(r'^dtn://[^~/]+/([^~]+/)*~[^/]+$')


def get_oldest_bundle_id(bundle_ids: Iterable[str]):
    """
    returns the oldest bundle, based on the creation timestamp and sequence number, with inaccurate packages being newer
    """

    def is_x_older(x_time, x_num, y_time, y_num):
        if x_time == 0:
            if y_time == 0:
                return x_num < y_num
            else:
                return False  # prefer packages with no accurate clock -> newer
        elif y_time == 0:
            return True  # prefer packages with no accurate clock -> newer
        elif x_time == y_time:
            return x_num < y_num
        else:
            return x_time < y_time

    oldest, oldest_time, oldest_num = None, None, None

    for bundle_id in bundle_ids:
        if oldest is None:
            oldest = bundle_id
            _, oldest_time, oldest_num = oldest.rsplit('-', 2)  # source-uri might contain unforeseen character
            oldest_time, oldest_num = int(oldest_time), int(oldest_num)
        else:
            _, bundle_time, bundle_num = bundle_id.rsplit('-', 2)  # source-uri might contain unforeseen character
            bundle_time, bundle_num = int(bundle_time), int(bundle_num)

            if is_x_older(bundle_time, bundle_num, oldest_time, oldest_num):
                oldest, oldest_time, oldest_num = bundle_id, bundle_time, bundle_num

    return oldest


def get_oldest_bundle(bundle_informations):
    """
    simplicity -> returns the oldest bundle based on reception time

    This eliminates bundles with extremely long lifetime blocking storage,
    but it also discriminates packages with low hop count.
    """
    oldest = None

    for bundle_information in bundle_informations:
        if oldest is None:
            oldest = bundle_information
        elif bundle_information.received_at_ms < oldest.received_at_ms:
            oldest = bundle_information

    return oldest


def get_current_clock_millis():
    return time.time_ns() // 1000000


def is_timestamp_older_than_timeout(clock_timestamp_millis: int, timeout_millis: int):
    return time.time_ns() // 1000000 - clock_timestamp_millis >= timeout_millis


def debug(*args):
    if DEBUG:
        print(*args)


def warning(*args):
    if WARNING:
        print(*args)


def is_correct_node_uri(node_uri: str) -> bool:
    """ match description:
    dtn -> starts with "dtn://", then one or more characters (except "~" or "/"), ends with "/"
    ipn -> starts with "ipn://", then one or more digits, then zero or more "." + one or more digits

    Currently used only on bpa creation to check the supplied node string.
    """
    return bool(NODE_URI_REGEX.match(node_uri))


def is_correct_endpoint_uri(endpoint_uri: str) -> bool:
    """ match description:
    dtn -> one or more characters (except "~" or "/"), then zero or more "/"+one or more characters (except "~" or "/")
    ipn -> one or more digits
    special -> "dtn://none" for the anonymous none-endpoint is also supported
    special -> a correct node uri (example: "dtn://node/") is also a correct endpoint uri

    Currently used only on endpoint registration by the bpa to check the validity of a full-endpoint-uri.
    As the LocalEndpoint is composed of bpa-node-uri + endpoint-id it is (and should never) be possible to register "dtn://none".
    """
    return bool(ENDPOINT_URI_REGEX.match(endpoint_uri)) or is_correct_node_uri(endpoint_uri)


def is_correct_group_uri(group_uri: str) -> bool:
    """match description:
    dtn -> one or more characters (except "~" or "/"), then zero or more "/"+one or more characters (except "~" or "/"), ending with "/~"+one or more characters (except "~" or "/")
    ipn -> no group registration

    Currently used only on group-endpoint registration by the bpa to check the validity of a full-group-uri.
    """
    return bool(GROUP_URI_REGEX.match(group_uri))
