"""
Client for running tests on DUT. Script runs on dev machine, i.e. python 3
"""

import socket
import configparser
import sys

import logging
logging.basicConfig(
                    format='%(asctime)s.%(msecs)03d [%(filename)s line %(lineno)d] %(levelname)-8s %(message)s',                       
                    level=logging.INFO,
                    datefmt='%H:%M:%S')

constants = configparser.ConfigParser()
constants.read('config.ini')

HOST = constants['COMM']['HOST']
PORT = int(constants['COMM']['TCP_PORT'])

def send_cmd(command) :
    """
    Send string command to DUT server for executing related tet operations
    """
    
    # Create a socket object
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Connect to DUT
    # -----------------------------------------------
    import time
    # The number of connection attempts
    attempts = 0

    # The maximum number of attempts
    max_attempts = 10

    # The delay between attempts in seconds
    delay = 0.1

    # A flag to indicate if the connection is successful
    connected = False

    # A while loop that will keep trying to connect
    while not connected and attempts < max_attempts:
        # Increment the number of attempts
        attempts += 1

        # Try to connect to the server
        try:
            logging.info(f"Connecting to {HOST}/{PORT} attempt {attempts}")
            client_socket.connect((HOST, PORT)) 
            connected = True
        except (BlockingIOError, ConnectionRefusedError) as error:
            # The connection was refused or timed out
            logging.info(error)
            logging.info(f"Connection attempt #{attempts} failed. Waiting {delay} seconds,")
            # Wait for some time before retrying
            time.sleep(delay)
    
    if attempts == max_attempts :
        logging.error(f"Could not connect to DUT  {HOST}/{PORT}")
        sys.exit(1)
    else :
        logging.info(f"Connected to DUT  {HOST}/{PORT}")

    # Send data to the server
    logging.info(f"Sending {command}")
    client_socket.send(command.encode('utf-8'))

    # receive data from the server
    data = client_socket.recv(1024)
    logging.info(f"{data.decode('utf-8')}")

    # close the connection
    client_socket.close()

if __name__ == "__main__" :
    send_cmd('test1')
