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
    logging.error(f"** ErrorFSM **: Current state:= - {fsm.current_state}")
    logging.error(str(fsm.input_symbol))
    sys.exit(1)

def KillPexpectProc(fsm) :
    logging.info(f'** KillPexpectProc ** : Current state - {fsm.current_state}')
    fsm.memory['reset_connection'] = True

def EnterPassword (fsm):
    logging.info(f'** EnterPassword ** : Current state - {fsm.current_state}')
    fsm.memory['response_to_pexpect'] = '123456'


# FSM Constants
# ====================================================
TWO_FACTOR_REQUEST_SYMBOL = "Two-factor authentication token:"
PASSWORD_REQUEST_SYMBOL   = "\[sudo\] password for sharonf:"
CLOSED_CONNECTION_SYMBOL  = "Closed connection to gateway"
EXPECTED_SYMBOLS = [PASSWORD_REQUEST_SYMBOL,
                    TWO_FACTOR_REQUEST_SYMBOL, 
                    CLOSED_CONNECTION_SYMBOL,
                    # last two elements are always EOF and TIMEOUT
                    pexpect.EOF, 
                    pexpect.TIMEOUT]
CMD = 'sudo /usr/bin/openfortivpn -c /home/sharonf/my.cfg'
EXPECT_TIMEOUT = 3

def main() :

    logging.info("**** Beginning The VPN Connection ****")

    num_connection_attempts = 0

    # Build the FSM 
    default_FSM_memory = {'reset_connection'    : False,
                          'response_to_pexpect' : None}
    fsm = FSM (initial_state = 'CONNECTING', memory = default_FSM_memory)
    # fsm.add_transition_any     (state= 'SETUP', action = CreatePexpectProc, next_state = 'CONNECTING')
    fsm.add_transition         (input_symbol=PASSWORD_REQUEST_SYMBOL,   state='CONNECTING', action=EnterPassword,        next_state='CONNECTING')
    fsm.add_transition         (input_symbol=TWO_FACTOR_REQUEST_SYMBOL, state='CONNECTING', action=KillPexpectProc, next_state='SETUP')
    fsm.set_default_transition (action=ErrorFSM, next_state='EXIT')

    # Configure pexpect object
    pexpect_child = pexpect.spawn(CMD)
    pexpect_child.logfile = sys.stdout.buffer

    # Main Loop - Endless loop to process pexpect output
    while True :
        # Create pexpect if first time or fsm.memory 
        if fsm.memory['reset_connection'] == True :
            num_connection_attempts += 1
            logging.info(f"** Main Loop ** : Restarting pexpect. NOF attempts : {num_connection_attempts}. Exit status: {pexpect_child.exitstatus}, Signal status: {pexpect_child.signalstatus}")
            fsm.memory['reset_connection'] = False
            pexpect_child.close()
            pexpect_child = pexpect.spawn(CMD)
            pexpect_child.logfile = sys.stdout.buffer

        # Send response if needed
        response = fsm.memory['response_to_pexpect']
        if response != None :
            pexpect_child.sendline(response)

        i = pexpect_child.expect (EXPECTED_SYMBOLS, timeout = EXPECT_TIMEOUT)
        fsm.process(EXPECTED_SYMBOLS[i])      

if __name__ == "__main__" :
    main()
