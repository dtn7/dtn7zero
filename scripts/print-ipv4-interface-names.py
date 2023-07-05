"""
This script prints all IPv4 interface names in combination with their respective broadcast IP and IP of this device.

It can be used as a utility in combination with the IPND module for the whitelist configuration.

IPND behavior:
- if no whitelist is configured, e.g. the default -> false / empty, then IPND will use ALL IPv4 interfaces
- if a whitelist (with the interface names) is configured -> then IPND will only use those IPv4 interfaces
- an exception is raised on invalid interface names
"""

import netifaces

from dtn7zero.ipnd import IPND

interface_names = [name for name in netifaces.interfaces() if netifaces.ifaddresses(name).get(netifaces.AF_INET, [])]

broadcast_addresses, own_addresses = IPND.get_cpython_ipv4_broadcast_addresses()

print('IPv4 Interfaces: \n(the interface name is everything inside "...")\n\n')

for idx, name in enumerate(interface_names):
    print(f'Interface: "{name}"\nIP: {own_addresses[idx]}, Broadcast IP: {broadcast_addresses[idx]}\n')
