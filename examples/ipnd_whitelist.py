"""
The framework allows certain configurations to be taken before any objects are created.

For a complete look at all advanced option take a look at the 'dtn7zero/configuration.py' module.

The framework allows to filter which interfaces IPND should use via a whitelist.
The utility script 'scripts/print-ipv4-interface-names.py' can be used to get an overview on available interfaces and addresses.

Start this script on two different machines to observe the IPND discovery via the debug messages.
"""
import time

from dtn7zero import setup, start_background_update_thread
from dtn7zero.configuration import CONFIGURATION

# this enables debug messages, with which we can track the nodes IPND found and also over which interface
CONFIGURATION.DEBUG = True

# an empty list enables all interfaces
# a filled list behaves like a whitelist where only the interfaces contained in the list are enabled
#
# windows-like example:
# CONFIGURATION.IPND.INTERFACE_WHITELIST = ["{30F834AD-888A-45A4-9D7D-5DFA63E42548}", "{734D491D-5F2C-11EA-B3E3-806E6F6E6963}"]
# linux-like example:
# CONFIGURATION.IPND.INTERFACE_WHITELIST = ["eth0", "lo"]


node_endpoint = setup("dtn://node1/")


start_background_update_thread(sleep_time_milliseconds=50)

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    pass
