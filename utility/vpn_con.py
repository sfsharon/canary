'''
Keep VPN connection open using FSM
'''

import sys
import os
from fsm import FSM
import pexpect
import time
import signal
import socket
import logging

# Logging Configuration
logging.basicConfig(
    format='\n%(asctime)s.%(msecs)03d [%(filename)s line %(lineno)d] %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%H:%M:%S')

# Constants
# ==================================================
DEV_MACHINE_IP = "172.30.16.107"
CMD = 'sudo /usr/bin/openfortivpn -c /home/sharonf/my.cfg'
EXPECT_TIMEOUT = 2
PING_TIMEOUT = 1
NOF_RETRY_TIMEOUTS = 100 # Put in a rather large number, because cannot close pexpect process once openfortivpn has connected, so actually no use in trying to reconnect on timeout.
                         # Unless OpenFortiVPN itself gave up with some error string such as "Modem hangup", then it can be closed.

# Setting up GUI
# ==================================================
import multiprocessing
from vpn_gui import StartGui
# Unix domain socket path
SOCKET_PATH = "/tmp/my_unix_socket"

# Create a multiprocessing.Process object for the function
try:
    os.remove(SOCKET_PATH)
except FileNotFoundError:
    pass
gui_process = multiprocessing.Process(target=StartGui, args=(SOCKET_PATH,))
logging.info("** Starting GUI server **")
gui_process.start()
logging.info("** Started GUI server **")
time.sleep(2)

# Signal handler for SIGINT (ctrl-c) so that the GUI gui_process be closed once the main gui_process dies
def SIGINT_function(sig, frame):
    global gui_process
    logging.info(f"** SIGINT_function ** Terminating the GUI gui_process")
    gui_process.terminate()
    logging.info(f"** SIGINT_function ** Waiting for the GUI gui_process to exit")
    gui_process.join()
    logging.info(f"** SIGINT_function ** Exiting program")
    sys.exit(0)

signal.signal(signal.SIGINT, SIGINT_function)


# Action functions for the FSM
# ====================================================
def ErrorFSM (fsm: FSM):
    logging.error(f"** ErrorFSM ** ({fsm.current_state}). Input Symbol : \"{fsm.input_symbol}\", Connection Established : {fsm.memory['is_vpn_tunnel_up']}")
    sys.exit(1)

def EnterPassword (fsm: FSM):
    logging.info(f'** EnterPassword ** Input Symbol: "{fsm.input_symbol}" ({fsm.current_state} -> {fsm.next_state})')
    fsm.memory['response_to_pexpect'] = '123456'

def ConnEstablished (fsm: FSM) :
    logging.info(f'** ConnEstablished ** Input Symbol: "{fsm.input_symbol}" ({fsm.current_state} -> {fsm.next_state})')
    fsm.memory['is_vpn_tunnel_up'] = True

def InitRestartPexpect(fsm: FSM) :
    logging.info(f'** InitRestartPexpect ** Input Symbol: "{fsm.input_symbol}" ({fsm.current_state} -> {fsm.next_state})')
    fsm.memory['is_reset_conn_required'] = True

def RuntimeRestartPexpect(fsm: FSM) :
    logging.info(f'** RuntimeRestartPexpect ** Input Symbol: "{fsm.input_symbol}" ({fsm.current_state} -> {fsm.next_state})')
    fsm.memory['is_reset_conn_required'] = True
    
def TimeoutRestartPexpect (fsm: FSM) :
    logging.info(f'** TimeoutRestartPexpect ** Input Symbol: "{fsm.input_symbol}" ({fsm.current_state} -> {fsm.next_state})')
    fsm.memory['nof_timeouts'] += 1
    logging.info(f"** TimeoutRestartPexpect ** - Number of Timeouts {fsm.memory['nof_timeouts']} ({fsm.current_state})")
    if fsm.memory['nof_timeouts'] % NOF_RETRY_TIMEOUTS == 0 :
        fsm.memory['is_reset_conn_required'] = True

def PingDevMachine (fsm: FSM) :
    logging.debug(f'** PingDevMachine **')
    import subprocess
    ping_command = f"ping -c 1 -w {PING_TIMEOUT} {DEV_MACHINE_IP}"  # Send one ping with a PING_TIMEOUT-second timeout
    response = subprocess.getstatusoutput(ping_command)
    if response[0] == 0:
        fsm.memory['is_ping_successful'] = True
        logging.debug(f"** PingDevMachine ** - {DEV_MACHINE_IP} is up !")
    else:
        fsm.memory['is_ping_successful'] = False
        logging.debug(f"** PingDevMachine ** - {DEV_MACHINE_IP} is down")

# FSM Constants
# ====================================================
TWO_FACTOR_REQUEST_SYMBOL       = "Two-factor authentication token:"
PASSWORD_REQUEST_SYMBOL         = "\[sudo\] password for sharonf:"
SUCCESSFUL_CONNECTION_SYMBOL    = "Tunnel is up and running"
CLOSED_CONNECTION_ERROR_SYMBOL  = "Closed connection to gateway"
MODEM_HANGUP_ERROR_SYMBOL       = "Modem hangup"

EXPECTED_SYMBOLS = [PASSWORD_REQUEST_SYMBOL,
                    TWO_FACTOR_REQUEST_SYMBOL, 
                    CLOSED_CONNECTION_ERROR_SYMBOL,
                    SUCCESSFUL_CONNECTION_SYMBOL,
                    # last two elements are always EOF and TIMEOUT
                    pexpect.EOF, 
                    pexpect.TIMEOUT]
def main():
    logging.info("** Beginning The VPN Connection **")

    # Build the FSM
    fsm = FSM(initial_state='CONNECTING')

    # Default FSM memory values
    fsm.memory = {  'is_reset_conn_required'  : False,    # Used to close pexpect session and open a new one
                    'nof_reset_connection'    : 0,        # If Two-factor request is received, the vpn connection is reset and opened again
                    'is_vpn_tunnel_up'        : False,    # Used to change pexpect timeout if connection established to block indefinitely
                    'response_to_pexpect'     : None,     # Used to send string response back to pexpect
                    'nof_timeouts'            : 0,
                    'is_ping_successful'      : False}    # Is pinging the DEV machine successful 

    # fsm.add_transition_any     (state= 'SETUP', action = CreatePexpectProc, next_state = 'CONNECTING')
    fsm.add_transition         (input_symbol=PASSWORD_REQUEST_SYMBOL,       state='CONNECTING', 
                                action=EnterPassword,                  next_state='CONNECTING')
    
    fsm.add_transition         (input_symbol=TWO_FACTOR_REQUEST_SYMBOL,     state='CONNECTING', 
                                action=InitRestartPexpect,             next_state='CONNECTING')
    
    fsm.add_transition         (input_symbol=pexpect.TIMEOUT,               state='CONNECTING', 
                                action=TimeoutRestartPexpect,          next_state='CONNECTING')    
    
    fsm.add_transition         (input_symbol=SUCCESSFUL_CONNECTION_SYMBOL,  state='CONNECTING', 
                                action=ConnEstablished,                next_state='CONN_ESTABLISHED')

    fsm.add_transition          (input_symbol=pexpect.TIMEOUT,              state='CONN_ESTABLISHED', 
                                action=PingDevMachine,                 next_state='CONN_ESTABLISHED')

    fsm.add_transition_list     (list_input_symbols=[MODEM_HANGUP_ERROR_SYMBOL, CLOSED_CONNECTION_ERROR_SYMBOL] ,  state='CONNECTING', 
                                action=InitRestartPexpect,                                                    next_state='CONNECTING')

    fsm.add_transition_list     (list_input_symbols=[MODEM_HANGUP_ERROR_SYMBOL, CLOSED_CONNECTION_ERROR_SYMBOL],  state='CONN_ESTABLISHED', 
                                action=RuntimeRestartPexpect,                                                next_state='CONNECTING')
    
    fsm.set_default_transition (action=ErrorFSM, next_state='EXIT')
    # Configure pexpect object
    pexpect_child = pexpect.spawn(CMD)
    pexpect_child.logfile = sys.stdout.buffer

    # Connect to the Unix domain socket
    gui_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    gui_socket.connect(SOCKET_PATH)

    # Main Loop - Processing pexpect output
    while True:
        # Create pexpect if FSM decided to reset the connection
        if fsm.memory['is_reset_conn_required']:
            fsm.memory['nof_reset_connection'] += 1
            fsm.memory['is_reset_conn_required'] = False
            logging.info(f"** Main Loop ** : Restarting pexpect. NOF attempts : {fsm.memory['nof_reset_connection']}")
            # logging.info(f"** Main Loop ** : Closing pexpect_child which has status : \n===============\n{pexpect_child}\n===============\n")
            try:
                pexpect_child.close(force=True)
                time.sleep(2)
            except Exception as e:
                logging.info(f"** Main Loop ** : Got exception {str(e)}")
                # logging.info(f"** Main Loop ** : Got exception {str(e)}\npexpect_child status : \n===============\n{pexpect_child}\n===============\n")
                if pexpect_child.isalive():

                    logging.info(f"** Main Loop ** : Using terminate() on pexpect_child\"")
                    pexpect_child.terminate(force=True)
                    # logging.info(f"** Main Loop ** : Using kill 9 on pexpect_child\"")
                    # pexpect_child.kill(9)

                    if pexpect_child.isalive():
                        logging.info(f"** Main Loop ** : Can't kill pexpect_child\"")
                        sys.exit(1)

            # Create a new pexpect child
            pexpect_child = pexpect.spawn(CMD)
            pexpect_child.logfile = sys.stdout.buffer
            logging.info(f"** Main Loop ** : Restarting pexpect. NOF attempts : {fsm.memory['nof_reset_connection']}")

        # Send response if needed
        response = fsm.memory['response_to_pexpect']
        if response is not None:
            pexpect_child.sendline(response)
            fsm.memory['response_to_pexpect'] = None

        # Wait for input
        i = pexpect_child.expect(EXPECTED_SYMBOLS, timeout=EXPECT_TIMEOUT)

        # FSM processing with received input and current state
        fsm.process(EXPECTED_SYMBOLS[i])

        ping_str = ' - No Ping'
        if fsm.memory['is_ping_successful']:
            ping_str = ' - Successful Pinging'

        # Sending status to the PyQt5 server via Unix domain socket
        status_message = fsm.current_state + ping_str
        gui_socket.sendall(status_message.encode('utf-8'))


if __name__ == "__main__":
    main()
