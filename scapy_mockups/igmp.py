"""
 IGMPv1 Membership Query

    Transmiting IGMP to x-eth 0/1/4 is BCM port #5, and x-eth 0/1/2 is BCM port #3 : 
    Tx 1 PSRC=5 DATA=14448f047f093448eda0cc7b08004500001c000100000102abd50a0000050102030411000efee0000001

    Transmitting ARP, for sanity check :
    Tx 1 PSRC=7 DATA=ffffffffffff01020304050608060001080006040001cc96e5a9414fc0a81a9700000000000001020304
    Ports #3 and #5 trap an ARP. So I guess x-eth 0/1/2 is #3, and #5 is x-eth 0/1/4

    • With VLAN 400:
    Tx 1 PSRC=5 DATA=14448f047f093448eda0cc7b8100019008004500001c000100000102abd50a0000050102030411000efee0000001

"""
from scapy.all import *
# Create Ethernet header
eth = Ether(dst="14:44:8f:04:7f:09")

# Create IP header
ip = IP(
    dst="1.2.3.4",
    ttl=1,  # IGMP packets typically use TTL=1
    proto=2  # Protocol number 2 is for IGMP
)

# Create IGMP payload with correct checksum
igmp_header = bytes([
    0x11,  # Type
    0x00,  # Max Response Time
    0x0e, 0xfe,  # Checksum (0x0efe)
    0xe0, 0x00, 0x00, 0x01  # Group Address (224.0.0.1)
])

igmp_payload = Raw(load=igmp_header)
# Stack all layers
packet = eth/ip/igmp_payload

# Print packet details
print("=== Packet Details ===")
packet.show()
# Print packet in hexadecimal
frame_bytes = bytes(packet).hex()    
print(frame_bytes)
# Got : 14448f047f093448eda0cc7b08004500001c000100000102abd50a0000050102030411000efee0000001


