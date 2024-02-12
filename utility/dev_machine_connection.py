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
    # Configure pexpect object
    pexpect_child = pexpect.spawn(CMD)
    logging.info(f"** Expect prompt **")
    pexpect_child.expect (DEV_MACHINE_PROMPT_SYMBOL)

    remote_conn = sys.argv[1]
    if remote_conn == "onl" :
        logging.info(f"** Connecting to DEV machine onl **")
    else :
        logging.info(f"** Connecting to DEV machine screen {remote_conn} **")
        logging.info(f"** Send -d **")
        pexpect_child.sendline(f"screen -d {remote_conn}")    
        logging.info(f"** Expect prompt **")
        pexpect_child.expect (DEV_MACHINE_PROMPT_SYMBOL)
        logging.info(f"** Send -r **")
        pexpect_child.sendline(f"screen -r {remote_conn}")    

    logging.info("** Escape character is '^]'**\n")
    
    def get_terminal_size():
        import struct, fcntl, termios
        s = struct.pack("HHHH", 0, 0, 0, 0)
        a = struct.unpack('hhhh', fcntl.ioctl(sys.stdout.fileno(), termios.TIOCGWINSZ, s))
        return a[0], a[1]

    terminal_size = get_terminal_size()
    logging.info(f"** Setting terminal size to {terminal_size} **\n")
    pexpect_child.setwinsize(*terminal_size)

    # Before handing back control to the user, few seconds to read logs
    time.sleep(2)

    pexpect_child.interact()
    logging.info("** Left interactive mode **")

if __name__ == "__main__" :
    main()
