"""
Create a packet or a frame using Scapy according to user parameters
"""
from scapy.all import Ether, IP

def create_frame(src_ip, dst_ip, dst_mac) :
    """
    Create a frame
    Return value : String repreentation of the hex frame value
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
    