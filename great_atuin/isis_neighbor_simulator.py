from scapy.layers.l2 import Ether
from scapy.contrib.isis import ISIS, ISIS_HELLO, ISIS_AreaTlv, ISIS_ProtocolsSupportedTlv, ISIS_IPInterfaceAddressTlv, ISIS_PaddingTlv, CLNP
from scapy.sendrecv import sendp, sniff
from scapy.config import conf
import time

class ISISNeighborSimulator:
    def __init__(self, interface, router_ip, net):
        self.interface = interface
        self.router_ip = router_ip
        self.net = net
        self.system_id = net[3:15]
        conf.load_contrib('isis')

    def craft_hello_packet(self):
        eth = Ether(dst="01:80:c2:00:00:14", type=0x83FE)
        clns = CLNP(pdu_type=0x1F)  # L2 Hello PDU
        isis = ISIS()
        
        hello = ISIS_HELLO(
            circuit_type=2,  # L2 only
            sys_id=self.system_id,
            holding_time=30,
            pdu_type=ISIS_HELLO.ISIS_P2P_HELLO_TYPE  # Changed from ISIS_L2_HELLO
        )

        hello_tlvs = [
            ISIS_AreaTlv(areas=[self.net[:4]]),
            ISIS_ProtocolsSupportedTlv(nlpids=b'\xCC'),  # IPv4
            ISIS_IPInterfaceAddressTlv(addresses=[self.router_ip]),
            ISIS_PaddingTlv(padding=b'\x00' * 255)
        ]

        return eth / clns / isis / hello / hello_tlvs

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
            if ISIS not in received_packet:
                print("Not an ISIS packet")
                return False

            # Verify it's a Hello packet
            if ISIS_HELLO not in received_packet:
                print("Not an ISIS Hello packet")
                return False

            # Verify circuit type (should be L2 or L1L2)
            if received_packet[ISIS_HELLO].circuit_type not in [2, 3]:
                print("Incorrect circuit type")
                return False

            # Verify Area ID
            sent_area = sent_packet[ISIS_AreaTlv].areas[0]
            received_areas = received_packet[ISIS_AreaTlv].areas
            if sent_area not in received_areas:
                print("Area ID mismatch")
                return False

            print("Response verified successfully")
            return True

        except IndexError:
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
    simulator = ISISNeighborSimulator("eth0", "192.168.1.2", "49.0972.0007.0100.0004.00")
    simulator.run()