'''
Keep VPN connection open using FSM
'''
from fsm import FSM
import pexpect
import sys

# Logging
import logging
logging.basicConfig(
                    format='\n%(asctime)s.%(msecs)03d [%(filename)s line %(lineno)d] %(levelname)-8s %(message)s', 
                    level=logging.INFO,
                    datefmt='%H:%M:%S')

# Action functions for the FSM
# ====================================================
def ErrorFSM (fsm: FSM):
    logging.error(f"** ErrorFSM ** ({fsm.current_state}). Input Symbol : {fsm.input_symbol}, Connection Established : {fsm.memory['connection_established']}")
    sys.exit(1)

def EnterPassword (fsm: FSM):
    logging.info(f'** EnterPassword ** ({fsm.current_state} -> {fsm.next_state})')
    fsm.memory['response_to_pexpect'] = '123456'

def ConnEstablished (fsm: FSM) :
    logging.info(f'** ConnEstablished ** ({fsm.current_state} -> {fsm.next_state})')
    fsm.memory['connection_established'] = True

def InitRestartPexpect(fsm: FSM) :
    logging.info(f'** InitRestartPexpect ** ({fsm.current_state} -> {fsm.next_state})')
    fsm.memory['reset_connection']    = True

def RuntimeRestartPexpect(fsm: FSM) :
    logging.info(f'** RuntimeRestartPexpect ** ({fsm.current_state} -> {fsm.next_state})')
    fsm.memory['reset_connection']    = True
    # Tell user VPN connection went down
    popup()  
    
def TimeoutRestartPexpect (fsm: FSM) :
    logging.info(f'** TimeoutRestartPexpect ** ({fsm.current_state} -> {fsm.next_state})')
    fsm.memory['nof_timeouts'] += 1
    logging.info(f"** TimeoutRestartPexpect ** - Number of Timeouts {fsm.memory['nof_timeouts']} ({fsm.current_state})")
    if fsm.memory['nof_timeouts'] % 5 == 0 :
        fsm.memory['reset_connection']    = True

def popup():
    """
    Pop up a dialog box to the user informing that the VPN connection has been restarted,
    and need to restart all the sessions to the DEV machine
    """
    from tkinter import Tk, Label, Button
    # Create a new window
    window = Tk()
    window.title("Great Atuin")

    # Add a label with your message
    message = Label(window, text="VPN connection disconnected !")
    message.pack()

    # Add a button to close the window
    close_button = Button(window, text="Close", command=window.destroy)
    close_button.pack()

    # Display the window
    window.mainloop()

# FSM Constants
# ====================================================
TWO_FACTOR_REQUEST_SYMBOL    = "Two-factor authentication token:"
PASSWORD_REQUEST_SYMBOL      = "\[sudo\] password for sharonf:"
CLOSED_CONNECTION_SYMBOL     = "Closed connection to gateway"
SUCCESSFUL_CONNECTION_SYMBOL = "Tunnel is up and running"
MODEM_HANGUP_ERROR_SYMBOL    = "Modem hangup"

EXPECTED_SYMBOLS = [PASSWORD_REQUEST_SYMBOL,
                    TWO_FACTOR_REQUEST_SYMBOL, 
                    CLOSED_CONNECTION_SYMBOL,
                    SUCCESSFUL_CONNECTION_SYMBOL,
                    # last two elements are always EOF and TIMEOUT
                    pexpect.EOF, 
                    pexpect.TIMEOUT]
CMD = 'sudo /usr/bin/openfortivpn -c /home/sharonf/my.cfg'
EXPECT_TIMEOUT = 10

def main() :

    logging.info("** Beginning The VPN Connection **")

    # Build the FSM 
    default_FSM_memory = {'reset_connection'        : False,    # Used to close pexpect session and open a new one
                          'nof_reset_connection'    : 0,        # If Two-factor request is received, the vpn connection is reset and opened again
                          'connection_established'  : False,    # Used to change pexpect timeout if connection established to block indefinitely
                          'response_to_pexpect'     : None,     # Used to send string response back to pexpect
                          'nof_timeouts'            : 0}
    
    fsm = FSM (initial_state = 'CONNECTING', memory = default_FSM_memory)
    # fsm.add_transition_any     (state= 'SETUP', action = CreatePexpectProc, next_state = 'CONNECTING')
    fsm.add_transition         (input_symbol=PASSWORD_REQUEST_SYMBOL,       state='CONNECTING', 
                                action=EnterPassword,           next_state='CONNECTING')
    
    fsm.add_transition         (input_symbol=TWO_FACTOR_REQUEST_SYMBOL,     state='CONNECTING', 
                                action=InitRestartPexpect,     next_state='CONNECTING')
    
    fsm.add_transition         (input_symbol=pexpect.TIMEOUT,               state='CONNECTING', 
                                action=TimeoutRestartPexpect,   next_state='CONNECTING')    
    
    fsm.add_transition         (input_symbol=SUCCESSFUL_CONNECTION_SYMBOL,  state='CONNECTING', 
                                action=ConnEstablished,         next_state='CONN_ESTABLISHED')

    fsm.add_transition         (input_symbol=MODEM_HANGUP_ERROR_SYMBOL,  state='CONNECTING', 
                                action=InitRestartPexpect,     next_state='CONNECTING')

    fsm.add_transition         (input_symbol=MODEM_HANGUP_ERROR_SYMBOL,  state='CONN_ESTABLISHED', 
                                action=RuntimeRestartPexpect,     next_state='CONNECTING')
    
    fsm.set_default_transition (action=ErrorFSM, next_state='EXIT')

    # Configure pexpect object
    pexpect_child = pexpect.spawn(CMD)
    pexpect_child.logfile = sys.stdout.buffer

    # Main Loop - Processing pexpect output
    while True :
        # Create pexpect if first time or fsm.memory 
        if fsm.memory['reset_connection'] == True :
            fsm.memory['nof_reset_connection'] += 1
            logging.info(f"** Main Loop ** : Restarting pexpect. NOF attempts : {fsm.memory['nof_reset_connection']}")
            fsm.memory['reset_connection'] = False
            pexpect_child.close()
            pexpect_child = pexpect.spawn(CMD)
            pexpect_child.logfile = sys.stdout.buffer

        # Send response if needed
        response = fsm.memory['response_to_pexpect']
        if response != None :
            pexpect_child.sendline(response)
            fsm.memory['response_to_pexpect'] = None

        pexpect_timeout = EXPECT_TIMEOUT
        if fsm.memory['connection_established'] == True :
            pexpect_timeout = None
        i = pexpect_child.expect (EXPECTED_SYMBOLS, timeout = pexpect_timeout)
        fsm.process(EXPECTED_SYMBOLS[i])      

if __name__ == "__main__" :
    main()
