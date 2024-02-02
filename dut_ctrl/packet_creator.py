"""
Create a packet or a frame using Scapy according to user parameters
"""
from scapy.all import Ether, IP, ICMP

def create_l2_l3_frame(src_ip, dst_ip, dst_mac) :
    """
    Create a frame
    Return value : String representation of the hex frame value
    For example :
        >>> frame =  Ether(dst='1e:94:a0:04:17:06') / IP(src='1.2.3.4', dst = '1.2.3.3')
        >>> frame_bytes = bytes(frame).hex()
        >>> frame_bytes
        '1e94a004170600155d941aa608004500001400010000400072df0102030401020303'
        >>> Ether(bytes.fromhex(frame_bytes))
        <Ether  dst=31:65:3a:39:34:3a src=61:30:3a:30:34:3a type=0x3137 |
        <Raw  load=':06E\x00\x00\x14\x00\x01\x00\x00@\x00r\\xdf\x01\x02\x03\x04\x01\x02\x03\x03' |>>
    """
    frame = Ether(dst = dst_mac) / IP(src = src_ip, dst = dst_ip)
    return bytes(frame).hex()
    
def create_icmp_frame(src_ip, dst_ip, dst_mac) :
    """
    Create an icmp frame
    Return value : String representation of the hex frame value
    For example :
        >>> frame =  Ether(dst='1e:94:a0:04:17:06') / IP(src='1.2.3.4', dst = '1.2.3.3')/ICMP()
        >>> frame_bytes = bytes(frame).hex()
        >>> frame_bytes
        '1e94a004170600155dcdff0708004500001c00010000400172d601020304010203030800f7ff00000000'
        >>> Ether(bytes.fromhex(frame_bytes))
        <Ether  dst=31:65:3a:39:34:3a src=61:30:3a:30:34:3a type=0x3137 |
        <Raw  load=':06E\x00\x00\x14\x00\x01\x00\x00@\x00r\\xdf\x01\x02\x03\x04\x01\x02\x03\x03' |>>
    """
    frame = Ether(dst = dst_mac) / IP(src = src_ip, dst = dst_ip) / ICMP()
    return bytes(frame).hex()

def create_l3_dscp_frame(src_ip: str, dst_ip: str, dst_mac: str , tos: int) -> bytes :
    """
    Create a frame
    Return value : String representation of the hex frame value
    For example :
        >>> frame =  Ether(dst='90:3c:b3:04:60:31') / IP(src='54.46.1.2', dst = '54.47.1.2', tos = 0x88)
        >>> frame_bytes = bytes(frame).hex()
        >>> frame_bytes
        '903cb304603100155de27a690800458800140001000040000c01362e0102362f0102'
        >>> Ether(bytes.fromhex(frame_bytes))
        <Ether  dst=90:3c:b3:04:60:31 src=00:15:5d:e2:7a:69 type=IPv4 |
             <IP  version=4 ihl=5 tos=0x88 len=20 id=1 flags= frag=0 ttl=64 proto=hopopt chksum=0xc01 
                  src=54.46.1.2 dst=54.47.1.2 |>>
    """

    # x-eth 0/0/46 MAC value : 90:3c:b3:04:60:31
    #              IP        : 54.46.1.1/24

    # x-eth 0/0/47 IP        : 54.47.1.1/24
    # a = IP(dst="172.31.0.1", tos=184) # 184 is the decimal equivalent of 0xB8 which is the hex 
    #                                    af41 is TOS 0x88 goes to queue af3
    # TX from BCMRM : tx 10 PSRC=47 DATA=903cb304603100155de27a690800458800140001000040000c01362e0102362f0102
    
    frame = Ether(dst = dst_mac) / IP(src = src_ip, dst = dst_ip, tos = tos)
    return bytes(frame).hex()


from scapy.all import *

def create_dhcp_discover_packet(vlan_id):
    """Creates a DHCP discover packet with the specified VLAN ID."""

    ethernet_frame = Ether(dst="ff:ff:ff:ff:ff:ff") / Dot1Q(vlan=vlan_id) / Ether()
    ip_packet = IP(src="0.0.0.0", dst="255.255.255.255")
    udp_packet = UDP(sport=68, dport=67)
    dhcp_packet = DHCP(options=[("message-type", "discover"), ("requested_option", 53)])

    packet = ethernet_frame/ip_packet/udp_packet/dhcp_packet

    return packet

if __name__ == "__main__":
    packet = create_dhcp_discover_packet(1)
    print(packet.summary())
    frame_bytes = bytes(packet).hex()
    print(frame_bytes)
    print(Ether(bytes.fromhex(frame_bytes)))