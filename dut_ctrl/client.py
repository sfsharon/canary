"""
Client for running tests on DUT. Script runs on dev machine, i.e. python 3
"""

import socket
import configparser

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
    # create a socket object
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Connect to the server
    logging.info(f"Connecting to {HOST}/{PORT}")
    client_socket.connect((HOST, PORT))

    # Send data to the server
    logging.info(f"Sending {command}")
    client_socket.send(command.encode('utf-8'))

    # receive data from the server
    data = client_socket.recv(1024)
    logging.info(f"Received: {data.decode('utf-8')}")

    # close the connection
    client_socket.close()

if __name__ == "__main__" :
    send_cmd('test1')
