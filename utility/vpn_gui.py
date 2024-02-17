"""
VPN GUI - Displaying the VPN connection status
"""
import sys
import os
from PyQt5.QtWidgets import QApplication, QDialog, QLabel, QVBoxLayout
from PyQt5.QtNetwork import QLocalServer
from PyQt5.QtCore import QIODevice, pyqtSignal

# Logging
import logging
logging.basicConfig(format='%(asctime)s.%(msecs)03d [%(filename)s line %(lineno)d] %(levelname)-8s %(message)s',
                    level=logging.INFO,
                    datefmt='%H:%M:%S')


class MyDialog(QDialog):
    closed = pyqtSignal()

    def __init__(self, socket_path: str):
        super().__init__()

        self.socket_path = socket_path

        self.setWindowTitle("VPN Status")
        self.label = QLabel()
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        self.setLayout(layout)

        # Create and start the local server
        self.local_server = QLocalServer(self)
        self.local_server.newConnection.connect(self.handle_new_connection)
        self.local_server.listen(self.socket_path)

    def handle_new_connection(self):
        client_connection = self.local_server.nextPendingConnection()
        client_connection.readyRead.connect(lambda: self.handle_client_data(client_connection))

    def handle_client_data(self, client_connection):
        data = client_connection.readAll().data().decode()
        logging.info(f"Received data from client: {data}")
        self.update_label(data)

    def update_label(self, text):
        self.label.setText(text)
        self.label.setStyleSheet("QLabel { font-size: 14px; font-weight: bold; color: #333; }")
        self.label.adjustSize()

        # Adjust minimum size of dialog based on label size
        self.setMinimumWidth(max(self.label.sizeHint().width() + 20, 300))
        self.setMinimumHeight(max(self.label.sizeHint().height() + 20, 100))

    def closeEvent(self, event):
        self.closed.emit()

    def showEvent(self, event):
        super().showEvent(event)
        # Move dialog to top-left corner of screen
        self.move(0, 0)


def StartGui(socket_path: str):
    logging.info("--- Start GUI ---")
    app = QApplication(sys.argv)
    dialog = MyDialog(socket_path)
    dialog.show()

    dialog.update_label("Initializing")

    sys.exit(app.exec_())


if __name__ == "__main__":
    socket_path = "/tmp/my_unix_socket"
    # Remove existing socket file if it exists
    try:
        os.remove(socket_path)
    except FileNotFoundError:
        pass

    gui_closed = False

    def handle_gui_closed():
        global gui_closed
        gui_closed = True

    gui_closed_signal = StartGui(socket_path)
    gui_closed_signal.connect(handle_gui_closed)
