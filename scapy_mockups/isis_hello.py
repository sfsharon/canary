#!/usr/bin/env python3
from scapy.all          import Ether
from scapy.contrib.isis import ISIS_CommonHdr 
from scapy.contrib.isis import _ISIS_LAN_HelloBase 
from scapy.contrib.isis import ISIS_AreaTlv, ISIS_ProtocolsSupportedTlv
from scapy.contrib.isis import ISIS_IpInterfaceAddressTlv, ISIS_PaddingTlv
from scapy.layers.l2    import LLC

def generate_isis_hello():
    # Ethernet layer
    eth = Ether(
        dst='01:80:c2:00:00:15',  # ISIS All L1 ISs MAC address
        src='d0:77:ce:da:71:07',  # Source MAC
        type=0x05d7              # ISIS protocol
    )
    
    # LLC layer
    llc = LLC(
        dsap=0xfe,    # ISO Network Layer
        ssap=0xfe,    # ISO Network Layer
        ctrl=0x03     # Unnumbered Information (UI)
    )
    
    # ISIS layer
    # Creating ISIS Hello packet with specific TLVs
    isis_header = ISIS_CommonHdr(
        pdutype="L2 LAN Hello",
        hdrlen=27
    )
    
    isis_hello = _ISIS_LAN_HelloBase (
        circuittype = 2,
        sourceid='0701.0000.0003',  # System ID
        holdingtime=30,          # Holding timer
        priority=64,
        lanid='0007.0100.0003.06'
    )

    # Combine all layers
    packet = eth/llc/isis_header/isis_hello

    # Add TLVs
    tlvs = [
        ISIS_AreaTlv(
            areas=['01.0000.0003']
        ),
        ISIS_ProtocolsSupportedTlv(
            nlpids=[204, 142]    # Supported protocols
        ),
        # Using raw bytes for IP address to match exact format
        # Raw(b'\x02\x00\x04\x31\x09\x48\x54'),  # IP Interface Address TLV in raw format
        ISIS_IpInterfaceAddressTlv(
            addresses=['49.9.72.84']  # Properly formatted IP address TLV
        ),
        ISIS_PaddingTlv(
            padding=b'\x00' * 240  # Add padding to meet minimum frame size
        )
    ]

    # Add TLVs to the packet
    for tlv in tlvs:
        packet /= tlv
    
    return packet

if __name__ == "__main__":
    # Generate the packet
    packet = generate_isis_hello()
    
    frame_bytes = bytes(packet).hex()
    print (frame_bytes)
    