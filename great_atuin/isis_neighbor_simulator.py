import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning)

import logging
# logging.getLogger("scapy.runtime").setLevel(logging.ERROR)

logging.basicConfig(
    format='\n%(asctime)s.%(msecs)03d [%(filename)s line %(lineno)d] %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%H:%M:%S')

from scapy.layers.l2 import Ether, Dot3, LLC
from scapy.packet import Raw
from scapy.contrib.isis import (
    ISIS_CommonHdr, ISIS_P2P_Hello, ISIS_L1_LAN_Hello, ISIS_L2_LAN_Hello, ISIS_AreaTlv,
    ISIS_AreaEntry, ISIS_ProtocolsSupportedTlv, ISIS_IpInterfaceAddressTlv, ISIS_PaddingTlv    
)
from scapy.sendrecv import sendp, sniff
import time
# import binascii

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
        isis_hdr.pdutype = ISIS_P2P_HELLO_TYPE  # Set PDU type after creation
        
        hello = ISIS_P2P_Hello()
        hello.circuittype = 2  # L2 only
        hello.sys_id = self.system_id
        hello.hold_time = 30

        hello_tlvs = ISIS_AreaTlv(areas=self.area_id) / \
                     ISIS_ProtocolsSupportedTlv(nlpids=[0xCC]) / \
                     ISIS_IpInterfaceAddressTlv(addresses=[self.router_ip]) / \
                     ISIS_PaddingTlv(padding=b'\x00' * 255)

        return eth / isis_hdr / hello / hello_tlvs

    def send_hello(self):
        hello_packet = self.craft_hello_packet()
        sendp(hello_packet, iface=self.interface, verbose=False)
        logging.info("Sent ISIS Hello packet")
        return hello_packet

    def receive_hello(self, timeout=5):
        sniffed = sniff(iface=self.interface, filter="isis", timeout=timeout, count=1)
        if sniffed:
            return sniffed[0]
        return None

    def verify_response(self, sent_packet, received_packet):

        try:
            logging.debug(f"Received packet summary: {received_packet.summary()}")

            # Extract the ISIS layer
            if Dot3 in received_packet:
                logging.debug("Packet identified as Dot3")
                if LLC in received_packet:
                    logging.debug("LLC layer found")
                    isis_layer = received_packet[LLC].payload
                else:
                    logging.error("No LLC layer found in Dot3 frame")
                    return False
            elif Ether in received_packet:
                logging.info("Packet identified as Ether")
                isis_layer = received_packet[Ether].payload
            else:
                logging.error("Not an Ethernet or Dot3 frame")
                return False

            # Ensure we're working with an ISIS packet
            if not isinstance(isis_layer, ISIS_CommonHdr):
                # If it's not already parsed as ISIS, try to force parse it
                try:
                    isis_layer = ISIS_CommonHdr(bytes(isis_layer))
                except:
                    logging.error("Failed to parse as ISIS packet")
                    return False

            logging.debug(f"ISIS PDU Type: {isis_layer.pdutype}")

            # Check if it's a Hello packet (LAN or P2P)
            if isis_layer.pdutype not in [15, 16, 17]:
                logging.error("Not an ISIS Hello packet")
                return False

            # Extract the appropriate Hello layer
            if isis_layer.pdutype == 15:
                hello_layer = isis_layer.getlayer(ISIS_L1_LAN_Hello)
                logging.info("### Received L1 LAN Hello")
            elif isis_layer.pdutype == 16:
                hello_layer = isis_layer.getlayer(ISIS_L2_LAN_Hello)
                logging.info("### Received L2 LAN Hello")
            else:  # pdutype == 17
                hello_layer = isis_layer.getlayer(ISIS_P2P_Hello)
                logging.info("### Received P2P Hello")

            if not hello_layer:
                logging.error("Failed to extract Hello layer")
                return False

            logging.debug(f"Circuit Type: {hello_layer.circuittype}")

            # Verify circuit type
            if hello_layer.circuittype not in [1, 2, 3]:  # L1, L2, or L1L2
                logging.error("Incorrect circuit type")
                return False

            # Verify Area ID
            sent_area = sent_packet[ISIS_AreaTlv].areas[0]
            received_areas = []
            for tlv in hello_layer.tlvs:
                if isinstance(tlv, ISIS_AreaTlv):
                    received_areas.extend(tlv.areas)
            
            if not received_areas:
                logging.error("No Area ID found in received packet")
                return False

            logging.debug(f"Sent Area: {sent_area}")
            logging.debug(f"Received Areas: {received_areas}")

            if sent_area not in received_areas:
                logging.debug("Area ID mismatch")
                # return False

            logging.debug("Response verified successfully")
            return True

        except Exception as e:
            logging.info(f"Error parsing received packet: {e}")
            return False

        return True

    def run(self):
        while True:
            sent_packet = self.send_hello()
            received_packet = self.receive_hello()

            if received_packet is not None :
                logging.debug (f"### Received: {bytes(received_packet).hex()}")
            else:
                logging.info("### No response received")
                continue

            if self.verify_response(sent_packet, received_packet):
                logging.info("Valid ISIS neighbor detected")
            else:
                logging.info("Failed to verify ISIS neighbor")
            time.sleep(3)  # Wait before next Hello

# ====================================================================================
# Unit Testing
# ====================================================================================
def run_ut(simlator : ISISNeighborSimulator) -> None :
    """
    Send an Hello ISIS packet received from the DUT into the packet verification
    """

    received_ISIS_Hello_pkt_str = "0180c2000015d077ceda710705d7fefe03831b01001001000002000701000003001e05d44000070100000306d301008102cc8e01040349097284040506070908ff00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000008ff00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000008ff00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000008ff00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000008ff000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000089f000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
    received_ISIS_Hello_pkt     = Ether(bytes.fromhex(received_ISIS_Hello_pkt_str))
    sent_ISIS_Hello_pkt         = simlator.craft_hello_packet()
    simulator.verify_response(sent_ISIS_Hello_pkt, received_ISIS_Hello_pkt)

# ====================================================================================
# Main
# ====================================================================================
if __name__ == "__main__":
    MODE_UT          = 1
    MODE_OPERATIONAL = 2
    # sim_mode = MODE_UT
    sim_mode = MODE_OPERATIONAL

    # Main simulator object
    simulator = ISISNeighborSimulator("enp4s0f1", "5.6.7.9", "49.0972.0007.0100.0004.00")
    
    if sim_mode == MODE_OPERATIONAL :
        simulator.run()
    if sim_mode == MODE_UT :
        run_ut(simulator)
    logging.info("End of ISIS Neighbor Simulator Run")
    