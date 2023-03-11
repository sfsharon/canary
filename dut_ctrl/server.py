"""
This code is running on the DUT. THerefore, it should support only python 2 code.
"""
import socket

import ConfigParser

config = ConfigParser.RawConfigParser()
config.read('config.ini')

HOST = config.get('COMM', 'HOST')
PORT = config.getint('COMM', 'TCP_PORT')

print('Server started on address ' + HOST + ':' + str(PORT))

# create a socket object
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# bind the socket to a public host, and a port
server_socket.bind((HOST, PORT))

# listen for incoming connections (server mode) with one client allowed to queue
server_socket.listen(1)

print('Server up and running !')

while True:
    # wait for a client connection
    conn, addr = server_socket.accept()
    print('Connected by', addr)

    # receive data from the client
    data = conn.recv(1024)
    
    if data == "test1" :
        print ("Got test1")
    else :
        print ("Not recognizable test")

    # send a response to the client
    conn.sendall('Received: ' + data)

    # close the connection
    conn.close()
