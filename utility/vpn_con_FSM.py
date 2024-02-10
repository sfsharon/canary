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
def ErrorFSM (fsm):
    logging.error(f"** ErrorFSM ** ({fsm.current_state}). Input Symbol : {fsm.input_symbol}, Connection Established : {fsm.memory['connection_established']}")
    sys.exit(1)

def KillPexpectProc(fsm) :
    logging.info(f'** KillPexpectProc ** ({fsm.current_state})')
    fsm.memory['reset_connection']    = True

def EnterPassword (fsm):
    logging.info(f'** EnterPassword ** ({fsm.current_state})')
    fsm.memory['response_to_pexpect'] = '123456'

def ConnEstablished (fsm) :
    logging.info(f'** ConnEstablished ** ({fsm.current_state})')
    fsm.memory['connection_established'] = True

# FSM Constants
# ====================================================
TWO_FACTOR_REQUEST_SYMBOL    = "Two-factor authentication token:"
PASSWORD_REQUEST_SYMBOL      = "\[sudo\] password for sharonf:"
CLOSED_CONNECTION_SYMBOL     = "Closed connection to gateway"
SUCCESSFUL_CONNECTION_SYMBOL = "Tunnel is up and running"
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

    num_connection_attempts = 0

    # Build the FSM 
    default_FSM_memory = {'reset_connection'        : False,    # Used to close pexpect session and open a new one
                          'connection_established'  : False,    # Used to change pexpect timeout if connection established to block indefinitely
                          'response_to_pexpect'     : None}     # Used to send string response back to pexpect
    
    fsm = FSM (initial_state = 'CONNECTING', memory = default_FSM_memory)
    # fsm.add_transition_any     (state= 'SETUP', action = CreatePexpectProc, next_state = 'CONNECTING')
    fsm.add_transition         (input_symbol=PASSWORD_REQUEST_SYMBOL,      state='CONNECTING', action=EnterPassword,   next_state='CONNECTING')
    fsm.add_transition         (input_symbol=TWO_FACTOR_REQUEST_SYMBOL,    state='CONNECTING', action=KillPexpectProc, next_state='CONNECTING')
    fsm.add_transition         (input_symbol=SUCCESSFUL_CONNECTION_SYMBOL, state='CONNECTING', action=ConnEstablished, next_state='CONN_ESTABLISHED')
    fsm.set_default_transition (action=ErrorFSM, next_state='EXIT')

    # Configure pexpect object
    pexpect_child = pexpect.spawn(CMD)
    pexpect_child.logfile = sys.stdout.buffer

    # Main Loop - Endless loop to process pexpect output
    while True :
        # Create pexpect if first time or fsm.memory 
        if fsm.memory['reset_connection'] == True :
            num_connection_attempts += 1
            logging.info(f"** Main Loop ** : Restarting pexpect. NOF attempts : {num_connection_attempts}")
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
