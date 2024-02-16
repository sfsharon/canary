'''
Keep VPN connection open using FSM
'''
from fsm import FSM
import pexpect
import sys
import time

# Logging
import logging
logging.basicConfig(
                    format='\n%(asctime)s.%(msecs)03d [%(filename)s line %(lineno)d] %(levelname)-8s %(message)s', 
                    level=logging.INFO,
                    datefmt='%H:%M:%S')

# Setup GUI
# ==================================================
import multiprocessing
from vpn_gui import StartGui

# Define arguments
GUI_SERVER_HOST = "localhost"
GUI_SERVER_PORT = 1984

# Create a multiprocessing.Process object for the function
process = multiprocessing.Process(target=StartGui, args=(GUI_SERVER_HOST, GUI_SERVER_PORT))
logging.info("** Starting GUI server **")
process.start()
logging.info("** Started GUI server **")
# while (1) :
#     continue
time.sleep(2)

def SendGuiStatus (status: str) :
    import socket
    global GUI_SERVER_HOST, GUI_SERVER_PORT

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        logging.info(f"** SendGuiStatus ** - \"{status}\"")
        s.connect((GUI_SERVER_HOST, GUI_SERVER_PORT))
        s.sendall(status.encode('utf-8'))

# Action functions for the FSM
# ====================================================
def ErrorFSM (fsm: FSM):
    logging.error(f"** ErrorFSM ** ({fsm.current_state}). Input Symbol : \"{fsm.input_symbol}\", Connection Established : {fsm.memory['connection_established']}")
    sys.exit(1)

def EnterPassword (fsm: FSM):
    logging.info(f'** EnterPassword ** Input Symbol: "{fsm.input_symbol}" ({fsm.current_state} -> {fsm.next_state})')
    fsm.memory['response_to_pexpect'] = '123456'

def ConnEstablished (fsm: FSM) :
    logging.info(f'** ConnEstablished ** Input Symbol: "{fsm.input_symbol}" ({fsm.current_state} -> {fsm.next_state})')
    fsm.memory['connection_established'] = True

def InitRestartPexpect(fsm: FSM) :
    logging.info(f'** InitRestartPexpect ** Input Symbol: "{fsm.input_symbol}" ({fsm.current_state} -> {fsm.next_state})')
    fsm.memory['reset_connection'] = True

def RuntimeRestartPexpect(fsm: FSM) :
    logging.info(f'** RuntimeRestartPexpect ** Input Symbol: "{fsm.input_symbol}" ({fsm.current_state} -> {fsm.next_state})')
    fsm.memory['reset_connection'] = True
    
def TimeoutRestartPexpect (fsm: FSM) :
    logging.info(f'** TimeoutRestartPexpect ** Input Symbol: "{fsm.input_symbol}" ({fsm.current_state} -> {fsm.next_state})')
    fsm.memory['nof_timeouts'] += 1
    logging.info(f"** TimeoutRestartPexpect ** - Number of Timeouts {fsm.memory['nof_timeouts']} ({fsm.current_state})")
    if fsm.memory['nof_timeouts'] % 5 == 0 :
        fsm.memory['reset_connection'] = True

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
CMD = 'sudo /usr/bin/openfortivpn -c /home/sharonf/my.cfg'
EXPECT_TIMEOUT = 10

def main() :

    logging.info("** Beginning The VPN Connection **")

    # Build the FSM 
    fsm = FSM (initial_state = 'CONNECTING')

    # Default FSM memory values
    fsm.memory = {  'reset_connection'        : False,    # Used to close pexpect session and open a new one
                    'nof_reset_connection'    : 0,        # If Two-factor request is received, the vpn connection is reset and opened again
                    'connection_established'  : False,    # Used to change pexpect timeout if connection established to block indefinitely
                    'response_to_pexpect'     : None,     # Used to send string response back to pexpect
                    'nof_timeouts'            : 0}

    # fsm.add_transition_any     (state= 'SETUP', action = CreatePexpectProc, next_state = 'CONNECTING')
    fsm.add_transition         (input_symbol=PASSWORD_REQUEST_SYMBOL,       state='CONNECTING', 
                                action=EnterPassword,                  next_state='CONNECTING')
    
    fsm.add_transition         (input_symbol=TWO_FACTOR_REQUEST_SYMBOL,     state='CONNECTING', 
                                action=InitRestartPexpect,             next_state='CONNECTING')
    
    fsm.add_transition         (input_symbol=pexpect.TIMEOUT,               state='CONNECTING', 
                                action=TimeoutRestartPexpect,          next_state='CONNECTING')    
    
    fsm.add_transition         (input_symbol=SUCCESSFUL_CONNECTION_SYMBOL,  state='CONNECTING', 
                                action=ConnEstablished,                next_state='CONN_ESTABLISHED')

    fsm.add_transition_list     (list_input_symbols=[MODEM_HANGUP_ERROR_SYMBOL, CLOSED_CONNECTION_ERROR_SYMBOL] ,  state='CONNECTING', 
                                action=InitRestartPexpect,                                                    next_state='CONNECTING')

    fsm.add_transition_list     (list_input_symbols=[MODEM_HANGUP_ERROR_SYMBOL, CLOSED_CONNECTION_ERROR_SYMBOL],  state='CONN_ESTABLISHED', 
                                action=RuntimeRestartPexpect,                                                next_state='CONNECTING')
    
    fsm.set_default_transition (action=ErrorFSM, next_state='EXIT')

    # Configure pexpect object
    pexpect.DEBUG = True
    pexpect_child = pexpect.spawn(CMD)
    pexpect_child.logfile = sys.stdout.buffer

    # Main Loop - Processing pexpect output
    while True :
        # Create pexpect if FSM decided to reset the connection 
        if fsm.memory['reset_connection'] == True :
            fsm.memory['nof_reset_connection'] += 1
            fsm.memory['reset_connection']      = False
            logging.info(f"** Main Loop ** : Restarting pexpect. NOF attempts : {fsm.memory['nof_reset_connection']}")
            logging.info(f"** Main Loop ** : Closing pexpect_child which has status : {pexpect_child}\"")
            try :
                pexpect_child.close(force=True)
            except Exception as e :
                logging.info(f"** Main Loop ** : Got exception \"{str(e)}\npexpect_child status : {pexpect_child}\"")
                if pexpect_child.isalive():
                    logging.info(f"** Main Loop ** : Using terminate() on pexpect_child\"")
                    pexpect_child.terminate(force = True)                    
                    if pexpect_child.isalive(): 
                        logging.info(f"** Main Loop ** : Can't kill pexpect_child\"")
                        sys.exit(1)

            # Create a new pexpect chile 
            pexpect_child = pexpect.spawn(CMD)
            pexpect_child.logfile = sys.stdout.buffer
            logging.info(f"** Main Loop ** : Restarting pexpect. NOF attempts : {fsm.memory['nof_reset_connection']}")


        # Send response if needed
        response = fsm.memory['response_to_pexpect']
        if response != None :
            pexpect_child.sendline(response)
            fsm.memory['response_to_pexpect'] = None

        # Update timeout. Several seconds during init, infinite if connection established
        pexpect_timeout = EXPECT_TIMEOUT
        if fsm.memory['connection_established'] == True :
            pexpect_timeout = None

        # Wait for input
        i = pexpect_child.expect (EXPECTED_SYMBOLS, timeout = pexpect_timeout)

        # FSM processing with received input and current state
        fsm.process(EXPECTED_SYMBOLS[i]) 
        SendGuiStatus(fsm.current_state)     

if __name__ == "__main__" :
    main()
