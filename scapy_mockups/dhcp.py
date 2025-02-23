"""
Create DORA DHCP frames.
Result :

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

from scapy.layers.l2 import Ether
from scapy.layers.inet import IP, UDP
from scapy.layers.dhcp import DHCP, BOOTP
from scapy.utils import mac2str
from scapy.all import RandInt, sendp

# Define the network interface
interface = "enp3s0f1"

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
print("[*] Sending 10 DHCP Discover packets on", interface)
for i in range(10):
    # dhcp_discover = create_dhcp_discover()
    sendp(dhcp_discover, iface=interface, verbose=True)
    print(f"[*] Packet {i+1} sent.")

print("[*] Finished sending packets.")