import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning)

import logging
logging.getLogger("scapy.runtime").setLevel(logging.ERROR)

from scapy.layers.l2 import Ether
from scapy.contrib.isis import ISIS_CommonHdr, ISIS_P2P_Hello, ISIS_AreaEntry, ISIS_ProtocolsSupportedTlv, ISIS_IpInterfaceAddressTlv, ISIS_PaddingTlv
from scapy.sendrecv import sendp, sniff
import time
import binascii

# ISIS PDU types
ISIS_P2P_HELLO_TYPE = 17  # Hardcoded value for P2P Hello

class ISISNeighborSimulator:
    def __init__(self, interface, router_ip, net):
        self.interface = interface
        self.router_ip = router_ip
        self.net = net
        self.system_id = net[3:15]
        self.area_id = self.format_area_id(net[:4])

    def format_area_id(self, area):
        # Ensure area ID is in the correct format (e.g., '49.0001')
        parts = area.split('.')
        return '.'.join([part.zfill(2) for part in parts])

    def craft_hello_packet(self):
        eth = Ether(dst="01:80:c2:00:00:14", type=0x83FE)
        isis_hdr = ISIS_CommonHdr()
        isis_hdr.pdu_type = ISIS_P2P_HELLO_TYPE  # Set PDU type after creation
        
        hello = ISIS_P2P_Hello()
        hello.circuit_type = 2  # L2 only
        hello.sys_id = self.system_id
        hello.hold_time = 30

        hello_tlvs = ISIS_AreaEntry(areaid=self.area_id) / \
                     ISIS_ProtocolsSupportedTlv(nlpids=[0xCC]) / \
                     ISIS_IpInterfaceAddressTlv(addresses=[self.router_ip]) / \
                     ISIS_PaddingTlv(padding=b'\x00' * 255)

        return eth / isis_hdr / hello / hello_tlvs

    def send_hello(self):
        hello_packet = self.craft_hello_packet()
        sendp(hello_packet, iface=self.interface, verbose=False)
        print("Sent ISIS Hello packet")
        return hello_packet

    def receive_hello(self, timeout=5):
        sniffed = sniff(iface=self.interface, filter="isis", timeout=timeout, count=1)
        if sniffed:
            return sniffed[0]
        return None

    def verify_response(self, sent_packet, received_packet):
        if received_packet is None:
            print("No response received")
            return False

        try:
            # Verify it's an ISIS packet
            if ISIS_CommonHdr not in received_packet:
                print("Not an ISIS packet")
                return False

            # Verify it's a Hello packet
            if ISIS_P2P_Hello not in received_packet:
                print("Not an ISIS Hello packet")
                return False

            # Verify circuit type (should be L2 or L1L2)
            if received_packet[ISIS_P2P_Hello].circuit_type not in [2, 3]:
                print("Incorrect circuit type")
                return False

            # Verify Area ID
            sent_area = sent_packet[ISIS_AreaEntry].areaid
            received_areas = [tlv.areaid for tlv in received_packet.getlayer(ISIS_P2P_Hello).tlvs if isinstance(tlv, ISIS_AreaEntry)]
            if sent_area not in received_areas:
                print("Area ID mismatch")
                return False

            print("Response verified successfully")
            return True

        except (IndexError, AttributeError):
            print("Error parsing received packet")
            return False

    def run(self):
        while True:
            sent_packet = self.send_hello()
            received_packet = self.receive_hello()
            if self.verify_response(sent_packet, received_packet):
                print("Valid ISIS neighbor detected")
            else:
                print("Failed to verify ISIS neighbor")
            time.sleep(10)  # Wait before next Hello

# Usage
if __name__ == "__main__":
    simulator = ISISNeighborSimulator("enp4s0f1", "5.6.7.9", "49.0972.0007.0100.0004.00")
    simulator.run()
    