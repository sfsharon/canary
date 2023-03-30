"""
Controling the DUT CLI using pexpect.
"""

import logging
logging.basicConfig(
                    format='%(asctime)s.%(msecs)03d [%(filename)s line %(lineno)d] %(levelname)-8s %(message)s', 
                    level=logging.INFO,
                    datefmt='%H:%M:%S')

import pexpect

# ***************************************************************************************
# Module helper functions
# ***************************************************************************************
def _parse_show_counter(cli_response, policy_name, action) :
    """
        Parse input from DUT for acl show command, and return the counter value
        Input : cli_response - String multi line of the DUT response
                policy_name  - String 
                action       - String, Values can be "deny" or "permit"
        Return value : Integer of the ACTION acl counter

        Hidden assumption : The rules have only two lines at most.
    """
    normalised_input = [line.lstrip() for line in cli_response.lower().splitlines()]
    for i, line in enumerate(normalised_input) :
        if policy_name in line :
            # The action is the second word from the end of the line
            first_action  = (normalised_input[i].split())[-2]
            second_action = (normalised_input[i+1].split())[-2]
            if action == first_action :
                return int((normalised_input[i].split())[-1])
            if action == second_action :
                return int((normalised_input[i+1].split())[-1])
            else :
                raise Exception (f"Unrecognized action: {action}")

# ***************************************************************************************
# External API functions
# ***************************************************************************************
def open_cli_session(device_number):
    """
    Open a pexpect session to a DUT CLI shell (in the cpm)
    Input : Device number, such as 3010
    Return value : pexpect cli_comm
    """
    
    CPM_ADDRESS = f"10.3.{device_number[2:4]}.1"
    PROMPT      = f"R{device_number}"
    TIMEOUT     = 10
    cli_comm    = None

    try :
        # SSH into the machine
        logging.info(f"Connecting to device {device_number}")
        cli_comm = pexpect.spawn(f'ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no {CPM_ADDRESS} -l admin', 
                              encoding='utf-8',
                              timeout=TIMEOUT)

        # Wait for the password prompt and enter the password
        logging.info("Wait for password prompt")
        cli_comm.expect('password:')

        logging.info("send password")
        cli_comm.sendline('admin')

        logging.info(f"Expecting prompt {PROMPT}")
        cli_comm.expect(f'.*{PROMPT}.*')
    except pexpect.exceptions.TIMEOUT :
        logging.error(f"Cannot connect to device {device_number}")

    return cli_comm   
            
def get_show_counter (cli_comm, interface, policy_name, action) :
    """
    Sending each command twice due to bug in acl show function
    """
    logging.info(f"Policy : {policy_name}, action: {action}")
    if interface == "ctrl-plane" :
        command = f'show ctrl-plane acl detail'
        expect_string = '.*MODE.*'
    else :
        command = f'show acl interface detail x-eth0/0/{interface}'
        expect_string = '.*INTERFACE.*'

    logging.info(f"Send command 1st: \"{command}\"")
    cli_comm.sendline(command)
    logging.info(f"Expecting: {expect_string}")
    cli_comm.expect(expect_string)
    response = cli_comm.after
    
    logging.info(f"Send command 2nd: \"{command}\"")
    cli_comm.sendline(command)
    logging.info(f"Expecting: {expect_string}")
    cli_comm.expect(expect_string)
    response = cli_comm.after

    counter = _parse_show_counter(response, policy_name, action)
    logging.info(f"counter value: {counter}")

    return counter

# ***************************************************************************************
# UT
# ***************************************************************************************
def _print_system_mod (cli_comm) :
    logging.info("Send command \"show sys mod\"")
    cli_comm.sendline('show sys mod')

    logging.info("Expecting: \"BOX/SLOT\"")
    cli_comm.expect('.*BOX/SLOT.*')

    logging.info("Received results")
    print(cli_comm.after)

def _print_acl_interface_details(cli_comm, interface_number) :
    """show acl interface detail x-eth0/0/1"""
    command = f'show acl interface detail x-eth0/0/{str(interface_number)}'
    logging.info(f"Send command: \"{command}\"")
    cli_comm.sendline(command)

    logging.info("Expecting: \"INTERFACE\"")
    cli_comm.expect('.*INTERFACE.*')

    logging.info("Received results")
    print(cli_comm.after)

def _test_acl_show_counter() :
   # Command :
    # R3010[2023-03-30-18:02:14]# show acl interface detail x-eth0/0/1
    show_acl_ifc_detail = """
                                                                    HIT
        INTERFACE   DIR  POL                     RULE          ACTION  COUNT
        ----------------------------------------------------------------------
        x-eth0/0/1  in   canary_pol_deny_src_ip  r1            deny    20
                                                rule-default  permit  30    
    """

    # Command :
    # R3010[2023-03-30-17:56:48]# show ctrl-plane acl detail
    show_acl_ctrl_plane_detail = """
                                                            HIT
        MODE    POL                     RULE          ACTION  COUNT
        -------------------------------------------------------------
        egress  canary_pol_deny_src_ip  r1            deny    40
                                        rule-default  permit  317
    """
    counter = _parse_show_counter(show_acl_ifc_detail, "canary_pol_deny_src_ip", "deny")
    print (counter)
    counter = _parse_show_counter(show_acl_ifc_detail, "canary_pol_deny_src_ip", "permit")
    print (counter)
    counter = _parse_show_counter(show_acl_ctrl_plane_detail, "canary_pol_deny_src_ip", "deny")
    print (counter)
    counter = _parse_show_counter(show_acl_ctrl_plane_detail, "canary_pol_deny_src_ip", "permit")
    print (counter)

def _test_basic() :
    DEVICE_NUMBER = '3010'
    cli_comm = open_cli_session(DEVICE_NUMBER)

    # SYSTEM SHOW
    # -------------------
    _print_system_mod(cli_comm)

    # ACL SHOW
    # --------------------
    _print_acl_interface_details(cli_comm, 23)
    _print_acl_interface_details(cli_comm, 23)

if __name__ == "__main__" :
    DEVICE_NUMBER = '3010'
    cli_comm = open_cli_session(DEVICE_NUMBER)

    # _test_basic()
    # _test_acl_show_counter()

    counter = get_show_counter (cli_comm, "ctrl-plane", "canary_pol_deny_src_ip", "permit")
    print (f"GOT : {counter}")

    logging.info("Finished")
