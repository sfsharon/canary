r"""
Outputs:

    ###[ Ethernet ]###
    dst       = 01:00:5e:00:00:02
    src       = 00:15:5d:5d:33:a4
    type      = IPv4
    ###[ IP ]###
        version   = 4
        ihl       = None
        tos       = 0x0
        len       = None
        id        = 1
        flags     =
        frag      = 0
        ttl       = 64
        proto     = udp
        chksum    = None
        src       = 172.26.144.1
        dst       = 224.0.0.2
        \options   \
    ###[ UDP ]###
            sport     = 646
            dport     = 646
            len       = None
            chksum    = None
    ###[ LDP ]###
            version   = 1
            len       = None
            id        = 10.0.0.1
            space     = 0

    0000  01 00 5E 00 00 02 00 15 5D 5D 33 A4 08 00 45 00  ..^.....]]3...E.
    0010  00 26 00 01 00 00 40 11 5E A8 AC 1A 90 01 E0 00  .&....@.^.......
    0020  00 02 02 86 02 86 00 12 D4 97 00 01 00 06 0A 00  ................
    0030  00 01 00 00                                      ....

    C:\Users\sharonf\workspace\ldp_scapy> python3 .\main.py
    01005e00000200155d5d33a40800450000260001000040115ea8ac1a9001e0000002028602860012d497000100060a0000010000
    
    x-eth 0/1/2 is BCM port #3 =>
    
    Tx 1 PSRC=3 DATA=01005e00000200155d5d33a40800450000260001000040115ea8ac1a9001e0000002028602860012d497000100060a0000010000
"""


from scapy.all import Ether, IP, UDP, load_contrib
from scapy.contrib.ldp import LDP
load_contrib('ldp')

def create_ldp_frame():
    # Create an LDP PDU
    ldp_pdu = LDP(
        version=1,                    # LDP Version 1
        space=0,                  # Label Space ID
        id='10.0.0.1'           # LSR ID (Router ID)
    )

    # Stack the layers
    frame = (
        Ether(dst="01:00:5e:00:00:02")/          # Multicast Ethernet
        IP(dst="224.0.0.2")/                      # All Routers Multicast
        UDP(sport=646, dport=646)/                # LDP Port
        ldp_pdu
    )

    return frame

if __name__ == "__main__":
    # Generate the frame
    ldp_frame = create_ldp_frame()
    
    frame_bytes = bytes(ldp_frame).hex()
    print (frame_bytes)


    # # Show frame details
    # ldp_frame.show()
    
    # # Optionally write to pcap file
    # wrpcap("ldp_hello.pcap", ldp_frame)
    
    # # Print hexdump
    # hexdump(ldp_frame)




