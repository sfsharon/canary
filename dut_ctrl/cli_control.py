"""
Controling the DUT CLI using pexpect.
"""

import logging
logging.basicConfig(
                    format='%(asctime)s.%(msecs)03d [%(filename)s line %(lineno)d] %(levelname)-8s %(message)s', 
                    level=logging.INFO,
                    datefmt='%H:%M:%S')

import pexpect


def open_session(device_number):
    """
    Open a pexpect session to a DUT CLI shell
    Input : Device number, such as 3010
    Return value : pexpect child
    """
    
    CPM_ADDRESS = f"10.3.{device_number[2:4]}.1"
    PROMPT      = f"R{device_number}"
    TIMEOUT     = 10
    child = None

    try :
        # SSH into the machine
        logging.info(f"Connecting to device {device_number}")
        child = pexpect.spawn(f'ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no {CPM_ADDRESS} -l admin', 
                              encoding='utf-8',
                              timeout=TIMEOUT)

        # Wait for the password prompt and enter the password
        logging.info("Wait for password prompt")
        child.expect('password:')

        logging.info("send password")
        child.sendline('admin')

        logging.info(f"Expecting prompt {PROMPT}")
        child.expect(f'.*{PROMPT}.*')
    except pexpect.exceptions.TIMEOUT :
        logging.error(f"Cannot connect to device {device_number}")

    return child

def print_system_mod (child) :
    logging.info("Send command \"show sys mod\"")
    child.sendline('show sys mod')

    logging.info("Expecting: \"BOX/SLOT\"")
    child.expect('.*BOX/SLOT.*')

    logging.info("Received results")
    print(child.after)

def print_acl_interface_details(child, interface_number) :
    """show acl interface detail x-eth0/0/1"""
    command = f'show acl interface detail x-eth0/0/{str(interface_number)}'
    logging.info(f"Send command: \"{command}\"")
    child.sendline(command)

    logging.info("Expecting: \"INTERFACE\"")
    child.expect('.*INTERFACE.*')

    logging.info("Received results")
    print(child.after)
   
def parse_acl_show_detail(return_value) :
    # ------------------------
    # IMPLEMENT
    # ------------------------
    pass

if __name__ == "__main__" :
    DEVICE_NUMBER = '3010'

    child = open_session(DEVICE_NUMBER)

    # print_system_mod(child)

    print_acl_interface_details(child, 1)
    print_acl_interface_details(child, 1)

    logging.info("Finished")
