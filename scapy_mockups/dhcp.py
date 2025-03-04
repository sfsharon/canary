"""
Create DORA DHCP frames.
Result :

[*] DHCP6 SOLICIT Packet:
33330001000200155d3e96cd86dd60000000002e1140fe80000000000000020c29fffeabcdefff02000000000000000000000001000202220223002e5e19011234560001000e00010001293d5099000c29abcdef0003000c000000010000000000000000

sharonf@DESKTOP-NJLVCVF:~/workspace/canary/scapy_mockups(main)$ python3 dhcp.py
[*] DHCP DISCOVER Packet:
Tx 10 PSRC=31 DATA=ffffffffffff00112233445508004500011000010000401179dd00000000ffffffff0044004300fc117c0101060051653f0e00000000000000000000000000000000000000000011223344550000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000063825363350101ff
- From Hex packet Decoder : 0.0.0.0 → 255.255.255.255 DHCP DHCP Discover - Transaction ID 0x51653f0e

[*] DHCP OFFER Packet:
WARNING: Unknown field option yiaddr
Tx 10 PSRC=31 DATA=001122334455aabbccddeeff080045000116000100004011b82dc0a80101ffffffff0043004401022b70020106002f11520a0000000000000000c0a80164c0a801010000000000112233445500000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000638253633501023604c0a80101ff
- From Hex packet Decoder : 192.168.1.1 → 255.255.255.255 DHCP DHCP Offer - Transaction ID 0x2f11520a

[*] DHCP REQUEST Packet:
Tx 10 PSRC=2 DATA=ffffffffffff00112233445508004500011c00010000401179d100000000ffffffff0044004301080b13010106004bc48a14000000000000000000000000000000000000000000112233445500000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000638253633501033204c0a801643604c0a80101ff
- From Hex packet Decoder : 0.0.0.0 → 255.255.255.255 DHCP DHCP Request - Transaction ID 0x4bc48a14

[*] DHCP ACK Packet:
WARNING: Unknown field option yiaddr
Tx 1 PSRC=5 DATA=001122334455aabbccddeeff080045000116000100004011b82dc0a80101ffffffff00430044010233f902010600ea518b400000000000000000c0a80164c0a801010000000000112233445500000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000638253633501053604c0a80101ff
- From Hex packet Decoder : 192.168.1.1 → 255.255.255.255 DHCP DHCP ACK - Transaction ID 0xea518b40

"""
# General Imports
from scapy.layers.l2 import Ether
from scapy.layers.inet import IP, UDP
from scapy.utils import mac2str
# from scapy.all import RandMAC
from scapy.all import RandInt, sendp

# DHCP IPv4
from scapy.layers.dhcp import DHCP, BOOTP

# DHCP IPv6
from scapy.layers.inet6 import IPv6
from scapy.layers.dhcp6 import DHCP6_Solicit, DHCP6OptClientId, DHCP6OptIA_NA


# Define the network interface
interface = "enp3s0f1"


# =============================================
# DHCPIPv4
# =============================================

# Define the client MAC address (random or real)
client_mac = "00:11:22:33:44:55"

# Define transaction ID (same for all packets in the DORA process)
transaction_id = RandInt()

# Define IP addresses (Example values)
offered_ip = "192.168.1.100"   # IP offered by the DHCP server
server_ip = "192.168.1.1"      # DHCP server IP


# DHCP DISCOVER
dhcp_discover = Ether(dst="ff:ff:ff:ff:ff:ff", src=client_mac) / \
                IP(src="0.0.0.0", dst="255.255.255.255") / \
                UDP(sport=68, dport=67) / \
                BOOTP(chaddr=[mac2str(client_mac)], xid=transaction_id) / \
                DHCP(options=[("message-type", "discover"), "end"])


# DHCP OFFER (typically sent by the server, but here we prepare it)
dhcp_offer = Ether(dst=client_mac, src="aa:bb:cc:dd:ee:ff") / \
             IP(src=server_ip, dst="255.255.255.255") / \
             UDP(sport=67, dport=68) / \
             BOOTP(op=2, yiaddr=offered_ip, siaddr=server_ip, xid=transaction_id, chaddr=[mac2str(client_mac)]) / \
             DHCP(options=[("message-type", "offer"), ("server_id", server_ip), ("yiaddr", offered_ip), "end"])


# DHCP REQUEST
dhcp_request = Ether(dst="ff:ff:ff:ff:ff:ff", src=client_mac) / \
               IP(src="0.0.0.0", dst="255.255.255.255") / \
               UDP(sport=68, dport=67) / \
               BOOTP(chaddr=[mac2str(client_mac)], xid=transaction_id) / \
               DHCP(options=[("message-type", "request"),
                             ("requested_addr", offered_ip),
                             ("server_id", server_ip),
                             "end"])


# DHCP ACK (typically sent by the server, but here we prepare it)
dhcp_ack = Ether(dst=client_mac, src="aa:bb:cc:dd:ee:ff") / \
           IP(src=server_ip, dst="255.255.255.255") / \
           UDP(sport=67, dport=68) / \
           BOOTP(op=2, yiaddr=offered_ip, siaddr=server_ip, xid=transaction_id, chaddr=[mac2str(client_mac)]) / \
           DHCP(options=[("message-type", "ack"), ("server_id", server_ip), ("yiaddr", offered_ip), "end"])



# =============================================
# DHCPIPv6
# =============================================
# Define the destination multicast address for DHCPv6 agents
DHCPV6_MULTICAST = "ff02::1:2"

DHCPV6_MULTICAST = "ff02::1:2"                  # DHCPv6 All Servers multicast address
CLIENT_MAC       = "00:0c:29:ab:cd:ef"          # Hardcoded MAC address
CLIENT_IPV6      = "fe80::20c:29ff:feab:cdef"   # Link-local address derived from MAC
CLIENT_DUID      = b"\x00\x01\x00\x01\x29\x3D\x50\x99\x00\x0C\x29\xAB\xCD\xEF"  # Example DUID

# Create the DHCPv6 Solicit packet
dhcp6_solicit = (
    Ether(dst="33:33:00:01:00:02")          # Multicast MAC for ff02::1:2
    / IPv6(dst=DHCPV6_MULTICAST, src=CLIENT_IPV6)
    / UDP(sport=546, dport=547)
    / DHCP6_Solicit(trid=0x123456)          # Hardcoded Transaction ID
    / DHCP6OptClientId(duid=CLIENT_DUID)    # Hardcoded Client Identifier (DUID)
    / DHCP6OptIA_NA(iaid=1, T1=0, T2=0)     # Request IPv6 address
)

# =============================================
# Operate frames
# =============================================
# Print packets for verification
print("[*] DHCP6 SOLICIT Packet:")
# Translate frame to bytes
frame_bytes = bytes(dhcp6_solicit).hex()
print(frame_bytes)

# # Print packets for verification
# print("[*] DHCP DISCOVER Packet:")
# # Translate frame to bytes
# frame_bytes = bytes(dhcp_discover).hex()
# print(frame_bytes)

# print("\n[*] DHCP OFFER Packet:")
# frame_bytes = bytes(dhcp_offer).hex()
# print(frame_bytes)

# print("\n[*] DHCP REQUEST Packet:")
# frame_bytes = bytes(dhcp_request).hex()
# print(frame_bytes)

# print("\n[*] DHCP ACK Packet:")
# frame_bytes = bytes(dhcp_ack).hex()
# print(frame_bytes)

# Send 10 DHCP Discover packets
# print("[*] Sending 10 DHCP Discover packets on", interface)
# for i in range(10):
#     # dhcp_discover = create_dhcp_discover()
#     sendp(dhcp_discover, iface=interface, verbose=True)
#     print(f"[*] Packet {i+1} sent.")
# print("[*] Finished sending packets.")