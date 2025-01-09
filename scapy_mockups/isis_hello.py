#!/usr/bin/env python3
from scapy.all          import Ether, wrpcap
from scapy.contrib.isis import ISIS_CommonHdr 
from scapy.contrib.isis import _ISIS_LAN_HelloBase 
from scapy.contrib.isis import ISIS_AreaTlv, ISIS_ProtocolsSupportedTlv
from scapy.contrib.isis import ISIS_IpInterfaceAddressTlv, ISIS_PaddingTlv
from scapy.layers.l2    import LLC

# Adding the missing TLV of Restart Signaling
from scapy.fields       import ByteField, FieldLenField
from scapy.contrib.isis import ISIS_GenericTlv
class ISIS_RestartSignalTlv(ISIS_GenericTlv):
    name = "ISIS Restart Signaling TLV"
    fields_desc = [
        ByteField("type", 211),                                   # TLV type 211 for Restart Signaling
        FieldLenField("len", None, length_of="flags", fmt="B"),
        ByteField("flags", 0)                                     # Flags field (default set to 0)
    ]

# Main function
def generate_isis_hello():
    # Ethernet layer
    eth = Ether(
        dst = '01:80:c2:00:00:15',
        src = 'd0:77:ce:da:71:07',
        type = 0x05d7
    )

    # LLC layer
    llc = LLC(
        dsap = 0xfe,
        ssap = 0xfe,
        ctrl = 0x03
    )

    # ISIS layer
    isis_hello = ISIS_CommonHdr(
        pdutype="L2 LAN Hello",
    ) /          _ISIS_LAN_HelloBase(
        circuittype = 2,
        sourceid    = '0701.0000.0003',
        holdingtime = 30,
        priority    = 64,
        lanid       = '0007.0100.0003.06',
    )
    isis_hello.pdulength = 0 
    isis_hello.hdrlen = len(isis_hello)  # Calculate header length

    # Add TLVs
    tlvs = [
        ISIS_RestartSignalTlv       (flags=0x00),
        ISIS_ProtocolsSupportedTlv  (nlpids=[0xcc, 0x8e]),
        ISIS_AreaTlv                (areas=['01.0000.0003']),
        ISIS_IpInterfaceAddressTlv  (addresses=['49.9.72.84']),
        ISIS_PaddingTlv             (padding=b'\x00' * 240)
    ]

    for tlv in tlvs:
        isis_hello /= tlv

    isis_hello.pdulength = len(isis_hello) - len(eth) - len(llc) # Update PDU Length to account for the TLVs length

    # Combine all layers
    packet = eth / llc / isis_hello

    return packet


if __name__ == "__main__":
    # Generate the packet
    packet = generate_isis_hello()
    
    frame_bytes = bytes(packet).hex()
    print (frame_bytes)
    
    # wrpcap("isis_hello.pcap", packet)