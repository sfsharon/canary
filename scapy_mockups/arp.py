"""
>>> print(frame_bytes)
ffffffffffff3c219c714891080600010800060400013c219c714891c0a8534300000000000001020304

• Reverse engineer what Scapy produced :
    >>> Ether(bytes.fromhex(frame_bytes))
    <Ether  dst=ff:ff:ff:ff:ff:ff src=3c:21:9c:71:48:91 type=ARP |<ARP  hwtype=Ethernet (10Mb) ptype=IPv4 hwlen=6 plen=4 op=who-has hwsrc=3c:21:9c:71:48:91 psrc=192.168.83.67 hwdst=00:00:00:00:00:00 pdst=1.2.3.4 |>>
    
• Transmit one ARP packet to x-eth 0/0/10:
Tx 1 PSRC=11 DATA=ffffffffffff00155d2881020806000108000604000100155d288102ac1a9fe800000000000001020304

• Transmit one ARP packet to  x-eth 0/1/1 (On a EdgeCore Q2A 28XB machine, which fits x-etr29 in the CPM) - ARP, Request who-has 1.2.3.4 tell 1.2.3.5, length 28:
Tx 1 PSRC=30 DATA=ffffffffffff00155d2881020806000108000604000100155d28810201020305ffffffffffff01020304

"""

from scapy.all import Ether, ARP

# Craft Ethernet frame
ether = Ether(dst = "ff:ff:ff:ff:ff:ff")  # Destination MAC is broadcast

# Craft ARP request
arp = ARP(
            op=1,                     # ARP Request
            psrc="1.2.3.5",            # Sender IP address
            hwdst="ff:ff:ff:ff:ff:ff", # Target MAC (broadcast)
            pdst="1.2.3.4")            # Target IP address

# Stack the Ethernet frame and ARP request
packet = ether / arp

# Translate frame to bytes
frame_bytes = bytes(packet).hex()

print(frame_bytes)
