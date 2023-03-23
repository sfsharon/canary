"""
Create a packet or a frame using Scapy according to user parameters
"""
from scapy.all import Ether, IP

def create_frame(src_ip, dst_ip) :
    """
    Create a frame
    Return value : String repreentation of the hex frame value
    For example :
        >>> frame =  Ether() / IP(src='1.2.3.4', dst = '5.5.5.5')
        >>> frame_bytes = bytes(frame).hex()
        >>> frame_bytes
        'ffffffffffff00155d5e082b0800450000140001000040006cda0102030405050505'
        >>> Ether(bytes.fromhex(frame_bytes))
        <Ether  dst=ff:ff:ff:ff:ff:ff src=00:15:5d:5e:08:2b type=IPv4 |<IP  version=4 ihl=5 tos=0x0 len=20 id=1 flags= frag=0 
                                                                            ttl=64 proto=hopopt chksum=0x6cda 
                                                                            src=1.2.3.4 dst=5.5.5.5 |>>
    """
    frame = Ether() / IP(src = src_ip, dst = dst_ip)
    return bytes(frame).hex()
    