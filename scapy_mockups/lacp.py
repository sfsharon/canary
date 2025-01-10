"""
TX 1 PSRC=28 DATA=0180c20000023c219c7148918809010114ffff001122334455000100ff00013d00000002140000000000000000000000000000000000000310000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000
"""

from scapy.all import Ether
from scapy.contrib.lacp import LACP
LACP_DEST_MAC = "01:80:c2:00:00:02"
SLOW_PROTOCOL_ETH_TYPE = 0x8809
# Ethernet frame
eth = Ether(dst = LACP_DEST_MAC, type = SLOW_PROTOCOL_ETH_TYPE)
# LACP packet
lacp = LACP(
    actor_system_priority=65535,
    actor_system='00:11:22:33:44:55',
    actor_key=1,
    actor_port_priority=255,
    actor_port_number=1,
    actor_state=0x3d,  # Activity=1, Timeout=0, Aggregation=1, Synchronization=1, Collecting=1, Distributing=1, Defaulted=0, Expired=0
    partner_system_priority=0,
    partner_system='00:00:00:00:00:00',
    partner_key=0,
    partner_port_priority=0,
    partner_port_number=0,
    partner_state=0x00,
    collector_max_delay=0
)
# Combine Ethernet frame and LACP packet
packet = eth / lacp
# Getting raw packet
frame_bytes = bytes(packet).hex()
print (frame_bytes)
# Reverse engineer raw packet to make sure everything is fine
Ether(bytes.fromhex(frame_bytes))

