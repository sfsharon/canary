'''
DUT monitoring using serial connection
'''

import pexpect
import sys
# import time

# Logging
import logging
logging.basicConfig(
                    format='%(asctime)s.%(msecs)03d [%(filename)s line %(lineno)d] %(levelname)-8s %(message)s', 
                    level=logging.INFO,
                    datefmt='%H:%M:%S')

# CONSTANTS
# ====================================================
DUT                         = "3062"
# DEV_MACHINE_CONN_CMD        = 'ssh sharonf@172.30.16.107'
DEV_MACHINE_PROMPT_SYMBOL   = "sharonf@DEV107"
ONL_PROMPT_SYMBOL           = "root@localhost:~#"
SERIAL_DISCONNECT_CMD       = f'exa-il01-ec-{DUT}-sc'
SERIAL_CONNECT_CMD          = f'exa-il01-ec-{DUT}-s'


def main() :
    # pexpect_child = pexpect.spawn(DEV_MACHINE_CONN_CMD)
    # logging.info(f"** Expect DEV Machine prompt **")
    # pexpect_child.expect (DEV_MACHINE_PROMPT_SYMBOL)
    # pexpect_child.sendline(SERIAL_DISCONNECT_CMD)
    
    logging.info(f"** Disconnecting DUT serial **")
    pexpect_child = pexpect.spawn(SERIAL_DISCONNECT_CMD)
    pexpect_child.logfile = sys.stdout.buffer
    pexpect_child.expect (DEV_MACHINE_PROMPT_SYMBOL)

    logging.info(f"** Connecting to DUT serial **")
    pexpect_child.sendline("ls -l")
    pexpect_child.expect (ONL_PROMPT_SYMBOL)

    logging.info(f"** running command **")

if __name__ == "__main__" :
    main()
