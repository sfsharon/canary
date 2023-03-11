"""
Client for running tests on DUT. Script runs on dev machine, i.e. python 3
"""

import socket
import configparser

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

    # connect to the server
    client_socket.connect((HOST, PORT))

    # Send data to the server
    client_socket.send(command.encode('utf-8'))

    # receive data from the server
    data = client_socket.recv(1024)

    print('Received:', data)

    # close the connection
    client_socket.close()

if __name__ == "__main__" :
    send_cmd('test1')
