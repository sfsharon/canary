
"""
Results :
>>> print (frame_bytes)
d077ceda71143c219c714891810000640800450000140001000040005bfdc0a854430a00000158585858585858585858585858585858585858585858585858585858585858585858585858585858585858585858585858585858585858585858585858585858585858585858585858585858585858585858585858585858585858585858585858585858

>>> # Reverse engineer raw packet to make sure everything is fine
>>> Ether(bytes.fromhex(frame_bytes))
<Ether  dst=d0:77:ce:da:71:14 src=3c:21:9c:71:48:91 type=VLAN |<Dot1Q  prio=0 id=0 vlan=100 type=IPv4 |<IP  version=4 ihl=5 tos=0x0 len=20 id=1 flags= frag=0 ttl=64 proto=ip chksum=0x5bfd src=192.168.84.67 dst=10.0.0.1 |<Padding  load='XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX' |>>>>

>>> len(Ether(bytes.fromhex(frame_bytes)))
138

"""

from scapy.all import Ether, Dot1Q, IP, Padding

# Define target details
dst_mac = "d0:77:ce:da:71:14"
vlan_value = 100

# Create a VLAN header with VLAN ID 100
vlan = Dot1Q(vlan=100)

# Create an Ether packet with the target MAC address
ether = Ether(dst=dst_mac)

# Combine the layers (VLAN -> Ethernet -> IP -> TCP)
packet = ether / vlan / IP(dst="10.0.0.1") / Padding(load="X"*100)

# Getting raw packet
frame_bytes = bytes(packet).hex()
print (frame_bytes)

# Reverse engineer raw packet to make sure everything is fine
Ether(bytes.fromhex(frame_bytes))
