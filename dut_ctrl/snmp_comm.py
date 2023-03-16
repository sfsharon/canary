"""
Trying to imitate :
$ snmpget -v 2c -c testp 10.3.10.1 SNMPv2-SMI::mib-2.2.2.1.2.1074118656
SNMPv2-SMI::mib-2.2.2.1.2.1074118656 = STRING: "x-eth0/0/23"
"""

from pysnmp.hlapi import *

errorIndication, errorStatus, errorIndex, varBinds = next(
    getCmd(SnmpEngine(),
           CommunityData('testp', mpModel=1),
           UdpTransportTarget(('10.3.10.1', 161)),
           ContextData(),
           ObjectType(ObjectIdentity('SNMPv2-SMI', 'mib-2', '2', '2', '1', '2', '1074118656')))
)

if errorIndication:
    print(errorIndication)
else:
    for varBind in varBinds:
        print(varBind)
