import socket

import sys

#HOST = 'localhost'
HOST = '10.3.10.10'
PORT = 8000

COMMAND = sys.argv[1]

# create a socket object
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# connect to the server
client_socket.connect((HOST, PORT))

# send data to the server
#client_socket.sendall('test1')
client_socket.sendall(COMMAND)

# receive data from the server
data = client_socket.recv(1024)

print('Received:', data)

# close the connection
client_socket.close()

