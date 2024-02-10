'''
DUT monitoring using serial connection
'''

import pexpect
import sys
import time

# Logging
import logging
logging.basicConfig(
                    format='\n%(asctime)s.%(msecs)03d [%(filename)s line %(lineno)d] %(levelname)-8s %(message)s', 
                    level=logging.INFO,
                    datefmt='%H:%M:%S')

DEV_MACHINE_PROMPT_SYMBOL       = "sharonf@DEV107"
DUT = "3048"
SERIAL_DISCONNECTED_CMD = f'exa-il01-ec-{DUT}-sc'
SERIAL_CONN_CMD         = f'exa-il01-ec-{DUT}-s'
# CMD = 'ssh sharonf@172.30.16.107'

def main() :
    # Configure pexpect object
    pexpect_child = pexpect.spawn(SERIAL_DISCONNECTED_CMD)
    logging.info(f"** Expect prompt **")
    pexpect_child.expect (DEV_MACHINE_PROMPT_SYMBOL)

    # remote_conn = sys.argv[1]
    # if remote_conn == "onl" :
    #     logging.info(f"** Connecting to DEV machine onl **")
    # else :
    logging.info(f"** Connecting to DUT machine screen {remote_conn} **")
    logging.info(f"** Send -d **")
    pexpect_child.sendline(f"screen -d {remote_conn}")    
    logging.info(f"** Expect prompt **")
    pexpect_child.expect (DEV_MACHINE_PROMPT_SYMBOL)
    logging.info(f"** Send -r **")
    pexpect_child.sendline(f"screen -r {remote_conn}")    

    logging.info("** Escape character is '^]' **\n")
    time.sleep(2)
    pexpect_child.interact()
    logging.info("** Left interactive mode **")

if __name__ == "__main__" :
    main()
