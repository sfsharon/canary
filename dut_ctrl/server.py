"""
This code is running on the DUT. THerefore, it should support only python 2 code.
"""
import socket
import ConfigParser
import logging
import sys 
from os import system

# Monitoring bcmrm_bsl file 
import monitor_logfile
#import threading

# Configuration configuration
# ---------------------------------------------------
config = ConfigParser.RawConfigParser()
config.read('config.ini')
HOST = config.get('COMM', 'HOST')
PORT = config.getint('COMM', 'TCP_PORT')
LOG_FILE = config.get('DUT_ENV', 'LOG_FILE')

# Log configuration
# ---------------------------------------------------
logger = logging.getLogger('my_logger')
logger.setLevel(logging.INFO)
# create file handler
fh = logging.FileHandler(LOG_FILE)
fh.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s.%(msecs)03d [%(filename)s line %(lineno)d] %(levelname)-8s %(message)s')
# set formatter for handlers
fh.setFormatter(formatter)
# add handlers to logger
logger.addHandler(fh)

# Start server script
# ---------------------------------------------------
logger.info('Server started on address ' + HOST + ':' + str(PORT))

# Create a socket object with socket reuse option SO_REUSEADDR, 
# so to avoid  "[Errno 98] Address already in use" when socket is held in WAIT_TIME state by the kernel,
# when running several client instances one after the other
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

try :
    # Bind the socket to a public host, and a port
    server_socket.bind((HOST, PORT))

    # Listen for incoming connections (server mode) with one client allowed to queue
    server_socket.listen(1)

    logger.info('Server up and running !')
    while True:
        # Wait for a client connection
        # -----------------------------------------------------------------        
        conn, addr = server_socket.accept()
        logger.info('Connected from client: ' + str(addr))

#        # Attach log to bcmrm_bsl_trace_buffer.trace
#        # -----------------------------------------------------------------
#        input_file = '/vbox/lc_image/root/var/log/bcmrm_bsl_trace_buffer.trace'
#        output_file = '/root/workspace/bcmrm_bsl_trace_buffer.trace'
#        monitor_bcmrm_log_thread = threading.Thread(target=monitor_logfile.monitor_file, args=(input_file, output_file))
#        monitor_bcmrm_log_thread.start()

        # Receive data from the client
        # ------------------------------------------------------------------
        data = conn.recv(1024)
        
        if data == "test1" :
            logger.info ("Got test1")
            command = r"screen -r bcmrm -X   stuff   $' Tx 3 PSRC=24 DATA=0x1e94a004171a00155d6929ba08004500001400010000400066b70a1800020a180001\n'"
            result = system(command)
            logger.info ("Run command " + command)
            logger.info("Return value: " + str(result))
        else :
            logger.info ("Not recognizable test")

        response = 'Received: ' + data
        logger.info ("Sending response: \"" + response + "\"")
        # Send a response to the client
        conn.sendall('Received: ' + data)

        # Close the client connection
        logger.info("Closing client connection")
        conn.close()

        # Exit after first connectin. Work Around, instead of killing process
        logger.info("Exiting")
        sys.exit(0)
except Exception as e:
    logger.exception(e)
    # Close the client connection
    logger.info("Got exception - Closing client connection")
    conn.close()
    sys.exit(1)


