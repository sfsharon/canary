"""
Tx 1 PSRC=18 DATA=d077ceda711400000000000008004600002000010000402ee7a87f0000017f000001940400000800f7ff00000000
 
>>> Ether(bytes.fromhex(frame_bytes))
<Ether  dst=d0:77:ce:da:71:14 src=00:00:00:00:00:00 type=IPv4 |
<IP  version=4 ihl=6 tos=0x0 len=32 id=1 flags= frag=0 ttl=64 proto=46 chksum=0xe7a8 src=127.0.0.1 dst=127.0.0.1 options=[<IPOption_Router_Alert  copy_flag=1 optclass=control option=router_alert length=4 alert=router_shall_examine_packet |>] 
|<Raw  load='\x08\x00\\xf7\\xff\x00\x00\x00\x00' |>>>
"""

from scapy.all import Ether, IPOption_Router_Alert, ICMP

# Define the IPv4 packet with IP options set to Router Alert
packet = Ether(dst="d0:77:ce:da:71:14") / IP(options=IPOption_Router_Alert(), proto=46) / ICMP()
# Translate frame to bytes
frame_bytes = bytes(packet).hex()
    
print(frame_bytes)
