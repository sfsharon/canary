'''
Keep VPN connection open using FSM
'''
from fsm import FSM
import pexpect
import sys

# Logging
import logging
logging.basicConfig(
                    format='%(asctime)s.%(msecs)03d [%(filename)s line %(lineno)d] %(levelname)-8s %(message)s', 
                    level=logging.INFO,
                    datefmt='%H:%M:%S')

# Action functions for the FSM
# ====================================================
def ErrorTransition (fsm):
    logging.error('\nErrorTransition FSM : That does not compute.')
    logging.error(str(fsm.input_symbol))

def ErrorNoInput (fsm):
    print ("\n")
    logging.error('ErrorNoInput : No Recognizable Input.')
    sys.exit(1)

def EnterPassword (fsm):
    # print ("\n")
    logging.error('EnterPassword : Sending password.')
    fsm.memory['pexpect_child'].sendline('123456')
    # sys.exit(2)

# Build the FSM
# ====================================================
TWO_FACTOR_REQUEST_SYMBOL = "Two-factor authentication token:"
# PASSWORD_REQUEST_SYMBOL   = r"[sudo] password for sharonf:"
PASSWORD_REQUEST_SYMBOL   = "\[sudo\] password for sharonf:"
EXPECTED_SYMBOLS = [PASSWORD_REQUEST_SYMBOL,
                    TWO_FACTOR_REQUEST_SYMBOL, 
                    # last two elements are always EOF and TIMEOUT
                    pexpect.EOF, 
                    pexpect.TIMEOUT]

# Application Constants
# ====================================================
CMD = 'sudo /usr/bin/openfortivpn -c /home/sharonf/my.cfg'
EXPECT_TIMEOUT = 3

def main() :

    logging.info("Beginning The VPN Connection !!!\n" + " " * 47  + "-" * 40)

    # Setup the pexpect object
    logging.info(f'Get Input from pexpect')
    pexpect_child = pexpect.spawn(CMD)
    pexpect_child.logfile = sys.stdout.buffer
    fsm_memory = {'pexpect_child' : pexpect_child}

    # Setup the FSM 
    f = FSM (initial_state = 'INIT', memory = fsm_memory)
    f.set_default_transition (ErrorTransition, 'INIT')
    f.add_transition_any     ('INIT', ErrorNoInput, 'INIT')
    f.add_transition         (PASSWORD_REQUEST_SYMBOL, 'INIT', EnterPassword,          'INIT')

    # Main Loop - Endless looping to process pexpect output
    while True :
        i = pexpect_child.expect (EXPECTED_SYMBOLS, timeout = EXPECT_TIMEOUT)
        f.process(EXPECTED_SYMBOLS[i])        

if __name__ == "__main__" :
    main()
