"""
This code is running on the DUT. THerefore, it should support only python 2 code.
"""
import socket
import ConfigParser
import logging

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

# Create a socket object
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

try :
    # Bind the socket to a public host, and a port
    server_socket.bind((HOST, PORT))

    # Listen for incoming connections (server mode) with one client allowed to queue
    server_socket.listen(1)

    logger.info('Server up and running !')

    while True:
        # Wait for a client connection
        conn, addr = server_socket.accept()
        logger.info('Connected from client: ' + str(addr))

        # Receive data from the client
        data = conn.recv(1024)
        
        if data == "test1" :
            logger.info ("Got test1")
        else :
            logger.info ("Not recognizable test")

        response = 'Received: ' + data
        logger.info ("Sending response: \"" + response + "\"")
        # Send a response to the client
        conn.sendall('Received: ' + data)

        logger.info("Closing connection")
        # Close the connection
        conn.close()
except Exception as e:
    logger.exception(e)
