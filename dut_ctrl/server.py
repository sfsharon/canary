import socket

#HOST = 'localhost'
HOST = '10.3.10.10'
PORT = 8000

# create a socket object
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# bind the socket to a public host, and a port
server_socket.bind((HOST, PORT))

# listen for incoming connections (server mode) with one client allowed to queue
server_socket.listen(1)

print('Server started!')

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