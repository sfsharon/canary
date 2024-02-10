'''
DEV machine connection - Connect to a screen session on my DEV machine
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

DEV_MACHINE_PROMPT_SYMBOL = "sharonf@DEV107"
CMD = 'ssh sharonf@172.30.16.107'

def main() :

    screen_session = sys.argv[1]
    logging.info(f"** Connecting to DEV machine screen {screen_session} **")

    # Configure pexpect object
    pexpect_child = pexpect.spawn(CMD)

    logging.info(f"** Expect prompt **")
    pexpect_child.expect (DEV_MACHINE_PROMPT_SYMBOL)
    logging.info(f"** Send -d **")
    pexpect_child.sendline(f"screen -d {screen_session}")    
    logging.info(f"** Expect prompt **")
    pexpect_child.expect (DEV_MACHINE_PROMPT_SYMBOL)
    logging.info(f"** Send -r **")
    pexpect_child.sendline(f"screen -r {screen_session}")    
    logging.info("** Escape character is '^]' **\n")
    time.sleep(2)
    pexpect_child.interact()
    logging.info("** Left interactive mode **")

if __name__ == "__main__" :
    main()
