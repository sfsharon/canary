"""
Python implementation of bash command :
    $ snmpget -v 2c -c testp 10.3.10.1 SNMPv2-SMI::mib-2.2.2.1.2.1074118656
    SNMPv2-SMI::mib-2.2.2.1.2.1074118656 = STRING: "x-eth0/0/23"

DUT configuration :
    snmp
        status enable
        agent
        network
            ip-address 0.0.0.0
            vrf        management
                version v2c
                    community-name testp
                !
            !
        platform
            ip-address 0.0.0.0
            vrf        management
                version v2c
                    community-name testp
                !
            !
        !
    !

"""
import logging
import configparser
from pysnmp.hlapi import *


logging.basicConfig(
                    format='%(asctime)s.%(msecs)03d [%(filename)s line %(lineno)d] %(levelname)-8s %(message)s', 
                    level=logging.INFO,
                    datefmt='%H:%M:%S')

# ------------------------------------------------
# EXCEPTIONS
# ------------------------------------------------
class TimeoutCommunicationToDut(Exception) :
    pass

# ------------------------------------------------
# GLOBALS
# ------------------------------------------------
# Read globals from ini file
constants = configparser.ConfigParser()
constants.read('config.ini')
COMMUNITY_NAME  = constants['SNMP']['COMMUNITY_NAME']
HOST            = constants['COMM']['HOST_CPM']


# ------------------------------------------------
# SNMP OID CONSTANS
# ------------------------------------------------
PORT_TO_OID_MAP = { 0:1073741824, 
                    1:1073758208, 
                    2:1073774592, 
                    3:1073790976, 
                    4:1073807360, 
                    5:1073823744, 
                    6:1073840128, 
                    7:1073856512, 
                    8:1073872896, 
                    9:1073889280, 
                    10:1073905664,
                    11:1073922048,
                    12:1073938432,
                    13:1073954816,
                    14:1073971200,
                    15:1073987584,
                    16:1074003968,
                    17:1074020352,
                    18:1074036736,
                    19:1074053120,
                    20:1074069504,
                    21:1074085888,
                    22:1074102272,
                    23:1074118656,
                    24:1074135040,
                    25:1074151424,
                    26:1074167808,
                    27:1074184192,
                    28:1074200576,
                    29:1074216960,
                    30:1074233344,
                    31:1074249728,
                    32:1074266112,
                    33:1074282496,
                    34:1074298880,
                    35:1074315264,
                    36:1074331648,
                    37:1074348032,
                    38:1074364416,
                    39:1074380800,
                    40:1074397184,
                    41:1074413568,
                    42:1074429952,
                    43:1074446336,
                    44:1074462720,
                    45:1074479104,
                    46:1074495488,
                    47:1074511872,
                    48:1074532352,
                    49:1074548736,
                    50:1074565120,
                    51:1074581504,
                    52:1074597888,
                    53:1074614272}

# ------------------------------------------------
# MODULE INTERNAL FUNCTIONS
# ------------------------------------------------
def _get_snmp_val (community_name, host, oid) :    

    logging.info(f"Getting SNMP information from Host: {host}, OID: {oid}")

    oid = ObjectIdentity(*oid)
    errorIndication, errorStatus, errorIndex, varBinds = next(
        getCmd(SnmpEngine(),
            CommunityData(community_name, mpModel=1),
            UdpTransportTarget((host, 161)),
            ContextData(),
            ObjectType(oid)))

    if errorIndication:
        logging.error(f"Error indication: {errorIndication}")
        raise TimeoutCommunicationToDut()
    else:
        results = [(oid, val)  for oid, val in varBinds]
        if len(results) != 1 :
            raise Exception (f"\nReceived wrong results length {len(results)}")
        
        # Return val value from the tuple (oid, val) of the first and only tuple results
        rv = results[0][1].prettyPrint()
        return rv

# ------------------------------------------------
# MODULE API FUNCTIONS
# ------------------------------------------------
def acl_in_rule_r1_counter(port) :
    acl_in_rule_r1_counter_oid = ['SNMPv2-SMI', 'enterprises', '36348', '1', '1', '2', '3', '2', '2', '1', '1', '5', str(PORT_TO_OID_MAP[port]), '1', '2']
    val = _get_snmp_val(COMMUNITY_NAME, HOST, acl_in_rule_r1_counter_oid)
    logging.info(f"Got value for {port}: {val}")
    return val

# ------------------------------------------------
# UT
# ------------------------------------------------
if __name__ == "__main__" :
    acl_in_rule_r1_counter(port = 23)

    
    