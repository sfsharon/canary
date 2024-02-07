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

# Application Constants
CMD = 'sudo /usr/bin/openfortivpn -c /home/sharonf/my.cfg'
EXPECT_TIMEOUT = 2

# Action functions for the FSM
# ====================================================
def Error (fsm):
    logging.error('Error FSM : That does not compute.')
    logging.error(str(fsm.input_symbol))


# Build the FSM
# ====================================================
TWO_FACTOR_REQUEST_SYMBOL = r"Two-factor authentication token:"
PASSWORD_REQUEST_SYMBOL   = r"[sudo] password for sharonf: "
EXPECTED_SYMBOLS = [TWO_FACTOR_REQUEST_SYMBOL, 
                    PASSWORD_REQUEST_SYMBOL,
                    # last two elements are always EOF and TIMEOUT
                    pexpect.EOF, 
                    pexpect.TIMEOUT]

def main() :

    logging.info("Beginning The VPN Connection !!!\n" + "=" * 20)


    f = FSM (initial_state = 'INIT', memory = None)

    # Build FSM Nodes and Edges
    f.set_default_transition (Error, 'INIT')
    f.add_transition_any  ('INIT', GetInitialInput, 'INIT')

    logging.info(f'Get Input from pexpect')
    # Setup the pexpect object
    pexpect_child = pexpect.spawn(CMD)
    pexpect_child.logfile = sys.stdout.buffer
    i = pexpect_child.expect (EXPECTED_SYMBOLS, timeout = EXPECT_TIMEOUT)

    # if i == 0:
    #     print("Two factor")
    # elif i == 1 :
    #     pexpect_child.sendline("123456")    
    #     print ("Sent password")
    #     i = pexpect_child.expect(["Two-factor authentication token: ", 
    #                     pexpect.EOF, 
    #                     pexpect.TIMEOUT], timeout = EXPECT_TIMEOUT)
    #     if i == 0 :
    #         print ("Need to send ctrl-c")
    #     elif i == 1:
    #         print ("EOF")
    #     elif i ==2 :
    #         print ("Timeout 2")
    # elif i == 2:
    #     print ("EOF")
    # elif i == 3:
    #     print ("TIMEOUT 1")
    # else:
    #     print ("Unrecognized")

    # Endless loop to process pexpect output
    while True :
        f.process(EXPECTED_SYMBOLS[i])

if __name__ == "__main__" :
    main()
