#!/usr/bin/env python3

# tests and documents the (http-)functionality of the py_dtn7 library against a dtn-rs server
import time
import json
import sys

from py_dtn7 import DTNRESTClient, Bundle

# connection to the dtn-rs client is made and the node_id gets fetched
dtn = DTNRESTClient(host='http://192.168.2.163', port=3000)
# dtn = DTNRESTClient(host='http://localhost', port=3000)

# the 'name' of the server. A registered service gets a subname in the servers namespace
print('connected to dtn node: {}\n'.format(dtn.node_id))

# I do not know if there is a better way to get this.
# But, the node_id includes the naming identifier, which is left out in bundles, but needs to be included when sending through the send endpoint
USING_IPN_NAMING = dtn.node_id.startswith('ipn')

# echo service definition
# there are two naming schemes: dtn and ipn
service = 'echo'
if USING_IPN_NAMING:
    service = 7

# fetches all bundles via the public status/bundles and download endpoint
# deserializes them into the bundle class
pretty_bundles = '\n'.join(str(bundle) for bundle in dtn.get_all_bundles())
print('all bundles currently stored on the server: \n{}\n'.format(pretty_bundles))

# fetches a raw bundle from the public download endpoint
# bundle_id or time and seq must be provided
# bundle can be deserialized through Bundle.from_cbor(...)
bundle_id = 'dtn://node1/-724512676024-0'
raw_bundle_bytes = dtn.download(bundle_id=bundle_id)
if raw_bundle_bytes == b'Bundle not found':
    deserialized_bundle = raw_bundle_bytes.decode()
else:
    deserialized_bundle = Bundle.from_cbor(raw_bundle_bytes)
print('this a download response for bundle-id "{}": \nraw: {}\ndeserialized: {}\n'.format(bundle_id, raw_bundle_bytes, deserialized_bundle))

# fetches a list of all endpoints(str) currently registered at this server
pretty_endpoints = '\n'.join(dtn.endpoints)
print('all endpoints currently registered at this endpoint: \n{}\n'.format(pretty_endpoints))

# fetches a list of all bundle-ids(str) of the bundles currently stored on the server
pretty_bundle_ids = '\n'.join(dtn.bundles)
print('all bundle-ids of the bundles currently on the server: \n{}\n'.format(pretty_bundle_ids))

# fetches a list of all bundle-ids(str) of the bundles currently stored on the server matching the filter.
# no wildcards possible, but generalizations or parts, examples: dtn://node1/ping, node1/ping, node1, ping
address_part_criteria = 'ping'
pretty_filtered_bundle_ids = '\n'.join(dtn.get_filtered_bundles(address_part_criteria))
print('all bundle-ids of the bundles currently on the server matching the filter "{}": \n{}\n'.format(address_part_criteria, pretty_filtered_bundle_ids))

# fetches a list of all bundle-ids with the current status (concatenated string)
pretty_stored_bundles = '\n'.join(dtn.store)
print('all bundle-ids of the bundles currently on the server and their constraints: \n{}\n'.format(pretty_stored_bundles))

# fetches a list of all known peers -> dictionary structure
pretty_peers = '\n'.join(json.dumps(peer, indent=4) for peer in dtn.peers)
print('all peers known by the server: \n{}\n'.format(pretty_peers))

# fetches general info about the server instance
if sys.implementation.name == 'micropython':
    pretty_info = json.dumps(dtn.info)
else:
    pretty_info = json.dumps(dtn.info, indent=4)
print('info about the server instance: \n{}\n'.format(pretty_info))

# the following public endpoints are not supported by this library:
# /download.hex
# /push
# /status/bundles/digest
# /status/bundles/verbose
# /status/bundles/filtered/digest?addr=<address_part_criteria>

"""
LOCAL ONLY API
This is only available via localhost, or, on other network interfaces with the -U option
"""

# registers a service for message reception
# this may be a singleton endpoint: mailbox or echo
# this may be a group endpoint: dtn://global/~news
# So, this can either be in the server-namespace, or, you define your own (global) one
print(dtn.register(service).content)

try:
    while True:
        # fetches from the internal 'endpoint' endpoint a single bundle
        # if not bundle is available the string 'Nothing to receive' is returned
        raw_bundle = dtn.fetch_endpoint(service)
        if b'Nothing to receive' in raw_bundle:
            print('no bundle was available at endpoint "{}", returned: {}'.format(service, raw_bundle))
        else:
            deserialized_bundle = Bundle.from_cbor(raw_bundle)
            print('a bundle fetched from the endpoint "{}":\n  raw: {}\n  deserialized: {}'.format(service, raw_bundle, deserialized_bundle))

            # sends an echo-reply back to the origin via the send endpoint
            response = dtn.send(
                payload=deserialized_bundle.payload_block.data,
                destination=deserialized_bundle.primary_block.full_source_uri,
                lifetime=3600*24*1000
            )
            print('  echo reply was sent back to server, response was: {}, {}, {}'.format(response.status_code, response.content, response.headers))

        time.sleep(1)
except KeyboardInterrupt:
    pass

# unregisters a previously registered service
print(dtn.unregister(service).content)
