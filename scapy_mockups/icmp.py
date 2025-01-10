"""
• Transmit one ICMP packet to  x-eth 0/1/1 (On a EdgeCore Q2A 28XB machine, which fits x-etr29 in the CPM)
• 1.2.3.5 → 1.2.3.4 ICMP Echo (ping) request. 
• The DA of  x-eth 0/1/1 on DUT 3012 is: d0:77:ce:da:71:20

Tx 1 PSRC=30 DATA=d077ceda7120001122334455080045000060ccfd00004001a59301020304010203050800114f2af000055858585858585858585858585858585858585858585858585858585858585858585858585858585858585858585858585858585858585858585858585858585858585858

"""

from scapy.all import Ether, IP, ICMP, Raw

# Create ICMP packet
packet = Ether(
            src="00:11:22:33:44:55",
            dst="d0:77:ce:da:71:20"
        )/IP(
            src="1.2.3.4",
            dst="1.2.3.5",
            tos=0x0,
            ttl=64,
            id=52477,
            flags=0
        )/ICMP(
            type="echo-request",
            id=10992,
            seq=5
        )/Raw(
            load="X"*68)

# Translate frame to bytes
frame_bytes = bytes(packet).hex()    
print(frame_bytes)
