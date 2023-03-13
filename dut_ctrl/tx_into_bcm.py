"""
Transmit a frame into broadcom using the SDK diag shell
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
        tx_frame(sys.argv[1], sys.argv[2], sys.argv[3])
    else :
        # Send an example frame : "screen -r bcmrm -X   stuff   $' Tx 3 PSRC=24 DATA=0x1e94a004171a00155d6929ba08004500001400010000400066b70a1800020a180001\n'"
        logger.info("Running UT values")
        frame = '0x1e94a004171a00155d6929ba08004500001400010000400066b70a1800020a180001'
        num_of_tx = '3'
        port = '24' # Value 24 referes to physical port x-eth 0/0/23
        tx_frame(frame, num_of_tx, port)