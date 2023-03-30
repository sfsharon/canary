"""
Transmit a frame into broadcom using the SDK diag shell.
To inject 32 frames into BCM, port 4 :
Scapy :
    Eth(Vlan 12) -> IPv4(SIP=10.0.0.1 DIP=20.0.0.1 Prot=17) -> UDP(SP=1000 DP=2000)
BCM Diag shell :
    tx 32 PSRC=4 DATA=0x00E01C3C17C2001F33D981608100000C080045B800800000400040111BB40A0000011400000103E807D0006CF527795681800001000200020000046D61696C0870617472696F747302696E0000010001C00C0005000100002A4B0002C011C0110001000100002A4C00044A358C99C011000200010001438C0006036E7332C011C011000200010001438C0006036E7331C011

"""
import logging
from os import system
import sys 

# Log configuration
# ---------------------------------------------------
logger = logging.getLogger('my_logger')
logger.setLevel(logging.INFO)
# create file handler
fh = logging.FileHandler("tx_into_bcm.log")
fh.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s.%(msecs)03d [%(filename)s line %(lineno)d] %(levelname)-8s %(message)s')
# set formatter for handlers
fh.setFormatter(formatter)
# add handlers to logger
logger.addHandler(fh)

def tx_frame(frame, num_of_tx, port) :
    """
    Transmit a frame into bcm
    Input: frame: Byte array of the frame to transmit
           num_of_tx : Number of times to transmit
           port : Physical port of the machine. e.g, 23 will transmit into port x-eth 0/0/23.
    Return value : 0 on success, otherwise non-zero
    """
    try: 
        command = r"screen -r bcmrm -X   stuff   $' Tx " + num_of_tx + \
                  " PSRC=" + port  + \
                  " DATA=" + frame + "\n'"
        logger.info('Running command: ' + command)
        rv = system(command)
        logger.info("Return value: " + str(rv))
        sys.exit(rv)
    except Exception as e:
        logger.exception(e)
        # Close the client connection
        logger.info("Got exception - Exiting")
        sys.exit(1)    

if __name__ == "__main__" :
    if len(sys.argv) == 4 :
        tx_frame(frame = sys.argv[1], num_of_tx = sys.argv[2], port = sys.argv[3])
    else :
        # Send an example frame : "screen -r bcmrm -X   stuff   $' Tx 3 PSRC=24 DATA=0x1e94a004171a00155d6929ba08004500001400010000400066b70a1800020a180001\n'"
        logger.info("Running UT values- Sending an ICMP frame (ping)")
        frame = '1e94a004170600155dcdff0708004500001c00010000400172d601020304010203030800f7ff00000000'
        num_of_tx = '42'
        port = '5' # Value 24 referes to physical port x-eth 0/0/23
        tx_frame(frame, num_of_tx, port)