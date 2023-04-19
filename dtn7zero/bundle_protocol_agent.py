from datetime import datetime, timezone, timedelta
from typing import Dict, List

from dtn7zero.data import BundleInformation, BundleStatusReportReasonCodes
from dtn7zero.constants import SEND_STATUS_REPORTS_ENABLED, RUNNING_MICROPYTHON
from dtn7zero.endpoints import LocalEndpoint, LocalGroupEndpoint, _LocalEndpoint
from dtn7zero.ipnd import IPND
from dtn7zero.routers import Router
from dtn7zero.storage import Storage
from dtn7zero.utility import debug, is_correct_node_uri, is_correct_endpoint_uri, is_correct_group_uri
from py_dtn7.bundle import PrimaryBlock

if RUNNING_MICROPYTHON:
    from wlan import connect, isconnected


class BundleProtocolAgent:

    def __init__(self, full_node_uri: str, storage: Storage, router: Router, use_ipnd=True):
        """ The main RFC 9171 compliant bpa component.

        full_node_uri examples:
            dtn addressing scheme -> "dtn://node1/", "dtn://cool-node/"  # '/' at the end is mandatory
            ipn addressing scheme -> "ipn://12", "ipn://24.25"  # will be joined with the endpoints via '.'
        """
        assert is_correct_node_uri(full_node_uri)

        self.full_node_uri = full_node_uri
        self.storage = storage
        self.router = router
        self.local_registered_endpoints: Dict[str, List[_LocalEndpoint]] = {}

        self.local_bundle_dispatch_queue: List[BundleInformation] = []  # this pipeline-stage is needed to prevent infinite-recursion if two local endpoints answer each other on every reception-callback
        self.storage_retry_generator = None
        self.router_poll_generator = None

        self.use_ipnd = use_ipnd
        if self.use_ipnd:
            # on micropython we need to handle wireless connections manually
            if RUNNING_MICROPYTHON and not isconnected():
                connect()  # the microcontroller may be moved around, so connect to any available network instead of reconnect

            scheme_encoded, node_encoded = PrimaryBlock.from_full_uri(full_node_uri)
            self.ipnd = IPND(scheme_encoded, node_encoded, storage)

    def update(self):
        # on micropython we need to handle wireless connections manually
        if RUNNING_MICROPYTHON and not isconnected():
            connect()  # the microcontroller may be moved around, so connect to any available network instead of reconnect

        # update discovery
        if self.use_ipnd:
            self.ipnd.update()

        # process stored/delayed bundle
        if self.storage_retry_generator is None:
            self.storage_retry_generator = self.storage.get_bundles_to_retry()

        try:
            self.bundle_dispatching(next(self.storage_retry_generator))
        except StopIteration:
            self.storage_retry_generator = None

        # process one new local bundle
        if self.local_bundle_dispatch_queue:
            self.bundle_reception(self.local_bundle_dispatch_queue.pop(0))

        # process new remote bundle
        if self.router_poll_generator is None:
            self.router_poll_generator = self.router.generator_poll_bundles()

        try:
            self.bundle_reception(next(self.router_poll_generator))
        except StopIteration:
            self.router_poll_generator = None

    def register_endpoint(self, endpoint: LocalEndpoint) -> LocalEndpoint:
        """ RFC 9171, 3.3 Services Offered by Bundle Protocol Agents
        […] * commencing a registration (registering the node in an endpoint).
        """
        endpoint.bpa_register(self)

        assert is_correct_endpoint_uri(endpoint.full_endpoint_uri)

        if endpoint.full_endpoint_uri in self.local_registered_endpoints:
            endpoint.bpa_unregister()
            raise Exception('tried to register local endpoint {}, which is already registered as a local endpoint'.format(endpoint.endpoint_identifier))

        self.local_registered_endpoints[endpoint.full_endpoint_uri] = (endpoint,)

        return endpoint

    def register_group_endpoint(self, endpoint: LocalGroupEndpoint) -> LocalGroupEndpoint:
        """ RFC 9171, 3.3 Services Offered by Bundle Protocol Agents
        […] * commencing a registration (registering the node in an endpoint).
        """
        assert is_correct_group_uri(endpoint.full_endpoint_uri)

        endpoint.bpa_register(self)

        if endpoint.full_endpoint_uri in self.local_registered_endpoints:
            self.local_registered_endpoints[endpoint.full_endpoint_uri].append(endpoint)
        else:
            self.local_registered_endpoints[endpoint.full_endpoint_uri] = [endpoint]

        return endpoint

    def unregister_endpoint(self, endpoint: LocalEndpoint):
        """ RFC 9171, 3.3 Services Offered by Bundle Protocol Agents
        […] * terminating a registration.
        """
        if endpoint.full_endpoint_uri not in self.local_registered_endpoints:
            raise Exception('tried to unregister non-existent local endpoint {}'.format(endpoint.endpoint_identifier))

        full_endpoint_uri = endpoint.full_endpoint_uri
        self.local_registered_endpoints[full_endpoint_uri][0].bpa_unregister()
        del self.local_registered_endpoints[full_endpoint_uri]

    def unregister_group_endpoint(self, endpoint: LocalGroupEndpoint):
        """ RFC 9171, 3.3 Services Offered by Bundle Protocol Agents
        […] * terminating a registration.
        """
        if endpoint.full_endpoint_uri not in self.local_registered_endpoints:
            raise Exception('tried to unregister non-existent local group endpoint {}'.format(endpoint.full_endpoint_uri))

        try:
            self.local_registered_endpoints[endpoint.full_endpoint_uri].remove(endpoint)
        except ValueError:
            raise Exception('tried to unregister non-existent local group endpoint {}'.format(endpoint.full_endpoint_uri))

        if not self.local_registered_endpoints[endpoint.full_endpoint_uri]:
            del self.local_registered_endpoints[endpoint.full_endpoint_uri]

    def cancel_transmission(self, bundle_id: str) -> bool:
        """ RFC 9171, 3.3 Services Offered by Bundle Protocol Agents
        […] * canceling a transmission.
        """
        # should only be called by a local endpoint
        # returns True if the bundle was still in local storage to delete, False otherwise
        return self.storage.remove_bundle(bundle_id)

    def bundle_reception(self, bundle_information: BundleInformation):
        # bundles with the same ID should never land here -> either they are filtered by the router or uniquely created from an endpoint

        bundle = bundle_information.bundle

        """ RFC 9171, 5.6 Bundle Reception
        […] Step 1: The retention constraint "Dispatch pending" MUST be added to the bundle. […]
        """
        bundle_information.retention_constraint = BundleInformation.RETENTION_CONSTRAINT_DISPATCH_PENDING

        """ RFC 9171, 5.6 Bundle Reception
        […] Step 2: If the "request reporting of bundle reception" flag in the bundle's status report request field 
        is set to 1 and status reporting is enabled, then a bundle reception status report with reason code 
        "No additional information" SHOULD be generated, destined for the bundle's report-to endpoint ID. […]
        """
        if bundle.primary_block.bundle_processing_control_flags.status_of_report_reception_is_requested:
            # todo: create a status report
            pass

        """ RFC 9171, 5.6 Bundle Reception
        […] Step 3: CRCs SHOULD be computed for every block of the bundle that has an attached CRC. 
        If any block of the bundle is malformed according to this specification (including syntactically invalid CBOR), 
        or if any block has an attached CRC and the CRC computed for this block upon reception differs from that 
        attached CRC, then the BPA MUST delete the bundle for the reason "Block unintelligible". The Bundle Deletion 
        procedure defined in Section 5.10 MUST be followed, and all remaining steps of the Bundle Reception procedure 
        MUST be skipped. […]
        """
        # currently there is no CRC implemented and bundles with CRC are rejected at bundle deserialization
        # todo: implement CRC support

        """ RFC 9171, 5.6 Bundle Reception
        […] Step 4: For each block in the bundle that is an extension block that the BPA cannot process:
        
        * If the block processing control flags in that block indicate that a status report is requested in this event 
        and if status reporting is enabled, then a bundle reception status report with reason code "Block unsupported" 
        SHOULD be generated, destined for the bundle's report-to endpoint ID.
        
        * If the block processing control flags in that block indicate that the bundle must be deleted in this event, 
        then the BPA MUST delete the bundle for the reason "Block unsupported"; the Bundle Deletion procedure defined 
        in Section 5.10 MUST be followed, and all remaining steps of the Bundle Reception procedure MUST be skipped.
        
        * If the block processing control flags in that block do NOT indicate that the bundle must be deleted in this 
        event but do indicate that the block must be discarded, then the BPA MUST remove this block from the bundle.
        
        * If the block processing control flags in that block neither indicate that the bundle must be deleted nor 
        indicate that the block must be discarded, then processing continues with the next extension block that the 
        BPA cannot process, if any; otherwise, processing proceeds from Step 5. […]
        """
        for block in bundle.other_blocks[:]:
            flags = block.block_processing_control_flags

            if flags.report_status_if_block_cant_be_processed and SEND_STATUS_REPORTS_ENABLED:
                # todo: generate a status report
                pass

            if flags.delete_bundle_if_block_cant_be_processed:
                self.bundle_deletion(bundle_information, BundleStatusReportReasonCodes.BLOCK_UNSUPPORTED)
                return
            elif flags.discard_block_if_block_cant_be_processed:
                bundle.other_blocks.remove(block)

        """ 4.4.3 Hop Count
        […] When a bundle's hop count exceeds its hop limit, the bundle SHOULD be deleted for the reason "Hop limit 
        exceeded", following the Bundle Deletion procedure defined in Section 5.10.
        """
        if bundle.hop_count_block and bundle.hop_count_block.hop_count >= bundle.hop_count_block.hop_limit:
            self.bundle_deletion(bundle_information, BundleStatusReportReasonCodes.HOP_LIMIT_EXCEEDED)
            return
        if bundle.bundle_age_block and bundle.bundle_age_block.age_milliseconds >= bundle.primary_block.lifetime:
            self.bundle_deletion(bundle_information, BundleStatusReportReasonCodes.LIFETIME_EXPIRED)
            return
        if not RUNNING_MICROPYTHON and bundle.primary_block.bundle_creation_time != 0:
            expiration_time = bundle.primary_block.bundle_creation_time_datetime + timedelta(milliseconds=bundle.primary_block.lifetime)
            if expiration_time < datetime.now(timezone.utc):
                self.bundle_deletion(bundle_information, BundleStatusReportReasonCodes.LIFETIME_EXPIRED)
                return

        """ RFC 9171, 5.6 Bundle Reception
        […] Step 5: Processing proceeds from Step 1 of Section 5.3.
        """
        self.bundle_dispatching(bundle_information)

    def bundle_dispatching(self, bundle_information: BundleInformation):
        """ RFC 9171, 5.3 Bundle Dispatching
        […] Step 1: If the bundle's destination endpoint is an endpoint of which the node is a member, 
        the Bundle Delivery procedure defined in Section 5.7 MUST be followed and, […] the node SHALL NOT undertake to 
        forward the bundle to itself in the course of performing the procedure described in Section 5.4. […]
        """
        if not bundle_information.locally_delivered and bundle_information.bundle.primary_block.full_destination_uri in self.local_registered_endpoints:
            self.local_bundle_delivery(bundle_information)

        """ RFC 9171, 5.3 Bundle Dispatching
        […] Step 2: Processing proceeds from Step 1 of Section 5.4.
        """
        self.bundle_forwarding(bundle_information)

    def local_bundle_delivery(self, bundle_information: BundleInformation):

        """ RFC 9171, 5.7 Local Bundle Delivery
        […] Step 1: If the received bundle is a fragment, the ADU Reassembly procedure described in Section 5.9 
        MUST be followed. If this procedure results in reassembly of the entire original ADU, processing of the 
        fragmentary bundle whose payload has been replaced by the reassembled ADU (whether this bundle or a previously 
        received fragment) proceeds from Step 2; otherwise, the retention constraint "Reassembly pending" MUST be added 
        to the bundle, and all remaining steps of this procedure MUST be skipped. […]
        """
        # there is currently no fragment support implemented and fragmented bundles are rejected at deserialization
        # todo: implement fragment support

        """ RFC 9171, 5.7 Local Bundle Delivery
        […] Step 2: Delivery depends on the state of the registration whose endpoint ID matches that of the destination 
        of the bundle:
        
        * An additional implementation-specific delivery deferral procedure MAY optionally be associated with the 
        registration. […]
        """
        bundle_information.locally_delivered = True

        # on group-endpoints there can be multiple registrations, on unicast-endpoints this is a 1-tuple
        for endpoint in self.local_registered_endpoints[bundle_information.bundle.primary_block.full_destination_uri]:
            endpoint.bpa_local_bundle_delivery(bundle_information.bundle)

    def bundle_forwarding(self, bundle_information: BundleInformation):

        """ RFC 9171, 5.4 Bundle Forwarding
        […] Step 1: The retention constraint "Forward pending" MUST be added to the bundle, and the bundle's 
        "Dispatch pending" retention constraint MUST be removed. […]
        """
        bundle_information.retention_constraint = BundleInformation.RETENTION_CONSTRAINT_FORWARD_PENDING

        """ RFC 9171, 5.4 Bundle Forwarding
        […] Step 2: The BPA MUST determine whether or not forwarding is contraindicated (that is, rendered inadvisable)
        […] * […] If the BPA elects to forward the bundle to some other node(s) for further forwarding but finds it 
        impossible to select any node(s) to forward the bundle to, then forwarding is contraindicated. […]
        """
        success, reason = self.router.immediate_forwarding_attempt(self.full_node_uri, bundle_information)

        """ RFC 9171, 5.4 Bundle Forwarding
        […] Step 3: If forwarding of the bundle is determined to be contraindicated for any of the reasons listed in 
        the IANA "Bundle Status Report Reason Codes" registry (see Section 9.5), then the Forwarding Contraindicated 
        procedure defined in Section 5.4.1 MUST be followed; the remaining steps of this Bundle Forwarding procedure 
        are skipped at this time. […]
        """
        if not success:
            """ RFC 9171, 5.4.1 Forwarding Contraindicated
            […] Step 1: The BPA MUST determine whether or not to declare failure in forwarding the bundle. 
            Note: This decision is likely to be influenced by the reason for which forwarding is contraindicated. […]
            """
            no_failure_codes = (
                BundleStatusReportReasonCodes.NO_KNOWN_ROUTE_TO_DESTINATION_FROM_HERE,
                BundleStatusReportReasonCodes.NO_TIMELY_CONTACT_WITH_NEXT_NODE_ON_ROUTE,
                BundleStatusReportReasonCodes.TRAFFIC_PARED
            )

            if reason in no_failure_codes:
                """ RFC 9171, 5.4.1 Forwarding Contraindicated
                […] when -- at some future time -- the forwarding of this bundle ceases to be contraindicated, 
                processing proceeds from Step 4 of Section 5.4. […]
                """
                storage_success, removed_bundle_informations = self.storage.delay_bundle(bundle_information)

                if not storage_success:
                    reason = BundleStatusReportReasonCodes.DEPLETED_STORAGE

                for removed_bundle_information in removed_bundle_informations:
                    if len(removed_bundle_information.forwarded_to_nodes) > 0:
                        removed_bundle_reason = BundleStatusReportReasonCodes.NO_ADDITIONAL_INFORMATION
                    else:
                        removed_bundle_reason = BundleStatusReportReasonCodes.DEPLETED_STORAGE

                    self.bundle_deletion(removed_bundle_information, removed_bundle_reason)

            if reason not in no_failure_codes:
                """ RFC 9171, 5.4.1 Forwarding Contraindicated
                […] Step 2: If forwarding failure is declared, then the Forwarding Failed procedure defined in 
                Section 5.4.2 MUST be followed. […]
                """
                """ RFC 9171, 5.4.2 Forwarding Failed
                […] Step 1: The BPA MAY forward the bundle back to the node that sent it, as identified by the Previous 
                Node Block, if present. This forwarding, if performed, SHALL be accomplished by performing Step 4 and 
                Step 5 of Section 5.4 where the sole node selected for forwarding SHALL be the node that sent the 
                bundle. […]
                """
                if bundle_information.bundle.previous_node_block:
                    self.router.send_to_previous_node(self.full_node_uri, bundle_information)

                """ RFC 9171, 5.4.2 Forwarding Failed
                […] Step 2: If the bundle's destination endpoint is an endpoint of which the node is a member, 
                then the bundle's "Forward pending" retention constraint MUST be removed. Otherwise, the bundle MUST be 
                deleted: the Bundle Deletion procedure defined in Section 5.10 MUST be followed, citing the reason for 
                which forwarding was determined to be contraindicated.
                """
                if bundle_information.bundle.primary_block.destination_specific_part in self.local_registered_endpoints:
                    bundle_information.retention_constraint = None
                else:
                    self.bundle_deletion(bundle_information, reason)
        else:
            """ RFC 9171, 5.4 Bundle Forwarding
            […] If completion of the data-sending procedures by all selected CLAs HAS resulted in successful forwarding 
            of the bundle, or if it has not but the BPA does not choose to initiate another attempt to forward the 
            bundle, then:
            
            * If the "request reporting of bundle forwarding" flag in the bundle's status report request field is set 
            to 1 and status reporting is enabled, then a bundle forwarding status report SHOULD be generated, destined 
            for the bundle's report-to endpoint ID. The reason code on this bundle forwarding status report MUST 
            be "no additional information". […]
            """
            if bundle_information.bundle.primary_block.bundle_processing_control_flags.status_of_report_forwarding_is_requested:
                # todo: generate a status report
                pass

            """ RFC 9171, 5.4 Bundle Forwarding
            […] * The bundle's "Forward pending" retention constraint MUST be removed.
            """
            bundle_information.retention_constraint = None

    def bundle_deletion(self, bundle_information: BundleInformation, reason: int):
        """ RFC 9171, 5.10 Bundle Deletion
        […] Step 1: If the "request reporting of bundle deletion" flag in the bundle's status report request field is
        set to 1 and if status reporting is enabled, then a bundle deletion status report citing the reason for
        deletion SHOULD be generated, destined for the bundle's report-to endpoint ID. […]
        """
        flags = bundle_information.bundle.primary_block.bundle_processing_control_flags
        if flags.status_of_report_deletion_is_requested and SEND_STATUS_REPORTS_ENABLED:
            # todo: generate a status report
            pass

        """ RFC 9171, 5.10 Bundle Deletion
        […] Step 2: All of the bundle's retention constraints MUST be removed.
        """
        bundle_information.retention_constraint = None

        debug('bundle scheduled for deletion, reason: {}, bundle: {}'.format(reason, bundle_information.bundle.bundle_id))
