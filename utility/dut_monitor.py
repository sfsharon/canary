'''
DUT monitoring using serial connection
'''

import pexpect
import sys
# import time
from dev_machine_cli import reset_serial_server_connection

# Logging
import logging
logging.basicConfig(
                    format='%(asctime)s.%(msecs)03d [%(filename)s line %(lineno)d] %(levelname)-8s %(message)s', 
                    level=logging.INFO,
                    datefmt='%H:%M:%S')

# CONSTANTS
# ====================================================
DUT_NUM                     = "3012"
DUT_TYPE                    = "ec"
DEV_MACHINE_PROMPT_SYMBOL   = "sharonf@DEV107"
ONL_PROMPT_SYMBOL           = "root@localhost:~#"


def main() :
    reset_serial_server_connection(DUT_NUM, DUT_TYPE)
    logging.info(f"** running command **")

if __name__ == "__main__" :
    main()
