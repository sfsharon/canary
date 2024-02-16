"""
VPN GUI - Displaying the VPN connection status
"""

import sys
from PyQt5.QtWidgets import QApplication, QDialog, QLabel, QVBoxLayout
import socket
import threading

# Logging
import logging
logging.basicConfig(format='\n%(asctime)s.%(msecs)03d [%(filename)s line %(lineno)d] %(levelname)-8s %(message)s', 
                    level=logging.INFO,
                    datefmt='%H:%M:%S')

class MyDialog(QDialog):
    def __init__(self, host : str, port : int):
        super().__init__()
        
        self.host = host
        self.port = port
        
        self.setWindowTitle("VPN Status")
        self.label = QLabel()
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        self.setLayout(layout)
        self.start_server()

    def start_server(self):
        server_thread = threading.Thread(target=self.server_thread)
        server_thread.daemon = True
        server_thread.start()

    def server_thread(self):      
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(1)
        logging.info(f"** MyDialog.start_server - Server listening on {self.host}:{self.port}")

        while True:
            conn, addr = self.server_socket.accept()
            with conn:
                logging.info(f"** MyDialog.start_server - Connected by {addr}")
                data = conn.recv(1024)
                text = data.decode()
                logging.info(f"** MyDialog.start_server - Received data: \"{text}\"")
                self.update_label(text)

    def update_label(self, text):
        self.label.setText(text)
        self.label.adjustSize()

def StartGui(host : str, port : int):
    logging.info("*** Start GUI ***")
    app = QApplication(sys.argv)
    dialog = MyDialog(host, port)
    dialog.show()
    sys.exit(app.exec_())
    

if __name__ == "__main__":
    StartGui("localhost", 12345)
