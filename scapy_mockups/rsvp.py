"""
Tx 1 PSRC=18 DATA=d077ceda7114cc483a8d8aad08004500001c00010000402e6c9a0a000014010203040300000000009404
"""

from scapy.all import Ether, IP, BitField, XByteField, XShortField, ByteEnumField, ByteField, Packet

# Define the RSVP PATH message
class RSVP_Path_Message(Packet):
    name = "RSVP_Path_Message"
    fields_desc = [
        BitField("msg_type", 3, 8),
        BitField("msg_flags", 0, 8),
        XByteField("RSVP_checksum", None),
        XByteField("RSVP_ttl", None),
        XShortField("RSVP_reserved", 0)
    ]

# Define the Router Alert option
class Router_Alert_Option(Packet):
    name = "Router_Alert_Option"
    fields_desc = [
        ByteEnumField("option_type", 0x94, {0x94: "Router Alert"}),
        ByteField("option_length", 4)
    ]

# Construct the packet with RSVP PATH message and Router Alert option
packet = Ether(dst="d0:77:ce:da:71:14")/\
         IP(dst="1.2.3.4", proto=46)/\
         RSVP_Path_Message()/\
         Router_Alert_Option()

# Translate frame to bytes
frame_bytes = bytes(packet).hex()
    
print(frame_bytes)
