"""
Controling the DUT CLI using pexpect.
"""

import logging
logging.basicConfig(
                    format='%(asctime)s.%(msecs)03d [%(filename)s line %(lineno)d] %(levelname)-8s %(message)s', 
                    level=logging.INFO,
                    datefmt='%H:%M:%S')

from common_enums import InterfaceOp, AclCtrlPlaneType, FrameType, InterfaceType

import pexpect

# ***************************************************************************************
# Module helper functions
# ***************************************************************************************
def _print_system_mod (cli_comm) :
    logging.info("Send command \"show sys mod\"")
    cli_comm.sendline('show sys mod')

    logging.info("Expecting: \"BOX/SLOT\"")
    cli_comm.expect('.*BOX/SLOT.*')

    logging.info("Received results")
    print(cli_comm.after)

def _parse_show_counter(cli_response, policy_name, rule_name) :
    """
        Parse input from DUT for acl show command, and return the counter value
        Input : cli_response - String multi line of the DUT response
                policy_name  - String 
                rule_name    - String
        Return value : Integer counter of the rule_name acl counter

        Hidden assumption : There are only two rules in the acl policy : 
                            Regular rule (such as "r1"), and a default rule (name always "rule-default")
    """
    normalised_input = [line.lstrip() for line in cli_response.lower().splitlines()]
    for i, line in enumerate(normalised_input) :
        if policy_name in line :
            # The Rule name is the third word from the end of the line
            first_rule  = (normalised_input[i].split())[-3]
            second_rule = (normalised_input[i+1].split())[-3]
            if rule_name == first_rule :
                return int((normalised_input[i].split())[-1])
            if rule_name == second_rule :
                return int((normalised_input[i+1].split())[-1])
            else :
                raise Exception (f"Unrecognized Rule name: {rule_name}")

def _reset_serial_server_connection(device_number) :
    """
    Issue from Dev machine command "exa-il01-dl-3010-sc"
    exa-il01-dl-3010-sc is aliased to `ts-cl 10.1.10.253 hw-lab-gw-1 lab lab 91'
        Output :
            sharonf@DEV107:~$ exa-il01-dl-3010-sc
            spawn telnet 10.1.10.253
            Trying 10.1.10.253...
            Connected to 10.1.10.253.
            Escape character is '^]'.

            hw-lab-gw-1#c
            Done
    """    
    logging.info("Disconnect the serial server from the DUT")
    import subprocess
    command = f'ts-cl 10.1.{device_number[-2:]}.253 hw-lab-gw-1 lab lab 91' 
    logging.info(f"Command: {command}")

    process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
    output, error = process.communicate()
    logging.info(f"_disconnect_dut_serial_connection output:\n{output.decode()}")


# ***************************************************************************************
# External API functions
# ***************************************************************************************

def reset_mng_and_cpm_connections(device_number):
    """
    1. Reset serial server connection, so that if another client is connected, it would be kicked out.
    2. Send "dhclient ma1" on ONL CLI for fixing management communication to IP 10.3.XX.10 (needed for DUT CLI commands),
    3. Send "ping vrf management 10.3.XX.254" in the DUT CLI for fixing CPM communication to IP 10.3.XX.1 (needed for Netconf),
       using the serial server connection
    Input : Device number, such as 3010
    Return value : None

    exa-il01-dl-3010-s  is aliased to `telnet 10.1.10.253 2091'
        Output :
            sharonf@DEV107:~$ exa-il01-dl-3010-s
                Trying 10.1.10.253...
                Connected to 10.1.10.253.
                Escape character is '^]'.

                root@localhost:~#
    """
    SERIAL_SERVER_ADDRESS = f"10.1.{device_number[-2:]}.253"
    CPM_PROMPT  = f"R{device_number}"
    ONL_PROMPT  = f"root@localhost:~#"
    TIMEOUT     = 20
    cli_comm    = None

    logging.info("*** Begin reset_mng_and_cpm_connections")

    # 1. Disconnect other client if connected to serial server 
    _reset_serial_server_connection(device_number)

    try :
        # 2. Telnet into the machine using the serial server and send "dhclient ma1"
        logging.info(f"Opening ONL CLI connection to device {device_number}")
        cli_comm = pexpect.spawn(f'telnet {SERIAL_SERVER_ADDRESS} 2091', 
                                   encoding='utf-8',
                                   timeout=TIMEOUT)

        # Wait for the password prompt and enter the password
        logging.info("Waiting for Serial server prompt")
        cli_comm.expect('.*Escape character.*')

        logging.info("send \\n")
        cli_comm.sendline('')

        logging.info(f"Expecting connection with DUT")
        i = cli_comm.expect([f'.*{ONL_PROMPT}.*', f'.*{CPM_PROMPT}.*'])
        if i == 1:
            logging.info("Exiting ssc")
            cli_comm.sendline('exit')
            cli_comm.expect(f'.*{ONL_PROMPT}.*')

        logging.info("Sending \"dhclient ma1\"")
        cli_comm.sendline('dhclient ma1')
        logging.info(f"Expecting prompt ONL prompt: {ONL_PROMPT}")
        cli_comm.expect(f'.*{ONL_PROMPT}.*')

        # 3. Send ping to vrf management
        logging.info("Connect to DUT CLI (ssc)")
        cli_comm.sendline('ssc')
        cli_comm.expect('.*password:.*')
        logging.info("send password")
        cli_comm.sendline('admin')
        logging.info(f"Expecting CPM prompt: {CPM_PROMPT}")
        cli_comm.expect(f'.*{CPM_PROMPT}.*')

        ping_command = f'ping vrf management 10.3.{device_number[-2:]}.254'
        logging.info(f"Sending ping command: \"{ping_command}\"")
        cli_comm.sendline(f'ping vrf management 10.3.{device_number[-2:]}.254')
        logging.info(f"Expecting end of ping")
        cli_comm.expect([f'.*rtt min/avg/max/mdev.*', f'.*{CPM_PROMPT}.*'])
    except pexpect.exceptions.TIMEOUT :
        logging.error(f"Waiting for CLI response exceeded {TIMEOUT} seconds")
    finally:
        logging.info("Closing ONL CLI connection")
        cli_comm.close()

    logging.info("*** End reset_mng_and_cpm_connections")

def open_cpm_session(device_number):
    """
    Open a pexpect session to a DUT CLI shell (in the cpm)
    Input : Device number, such as 3010
    Return value : Spawned pexpect process (cli_comm)
    """
    
    CPM_ADDRESS = f"10.3.{device_number[-2:]}.1"
    CPM_PROMPT  = f"R{device_number}"
    TIMEOUT     = 10
    cli_comm    = None

    try :
        # SSH into the machine
        logging.info(f"Opening CPM CLI connection to device {device_number}")
        cli_comm = pexpect.spawn(f'ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no {CPM_ADDRESS} -l admin', 
                              encoding='utf-8',
                              timeout=TIMEOUT)

        # Wait for the password prompt and enter the password
        logging.info("Waiting for password prompt")
        cli_comm.expect('password:')

        logging.info("send password")
        cli_comm.sendline('admin')

        logging.info(f"Expecting CPM prompt: {CPM_PROMPT}")
        cli_comm.expect(f'.*{CPM_PROMPT}.*')
    except pexpect.exceptions.TIMEOUT :
        logging.error(f"Cannot connect to device {device_number}")

    return cli_comm   

def close_cpm_session(cli_comm):
    """
    Close cleanly a pexpect session to a DUT CLI shell (in the cpm)
    Input : Spawned pexpect process (cli_comm)
    Return value : None
    """
    logging.info(f"Closing CLI connection")
    cli_comm.close()

def get_show_counter (cli_comm, interface, interface_type, policy_name, rule_name) :
    """
    Reading ACL counter according to interface, policy name and action
    Input : cli_comm - 
            interface - Physical interface such as "4"
            interface_type - Enumeration InterfaceType, values "CTRL_PLANE", "X_ETH"
            policy_name - String
            rule_name : String
    Caveat :Sending each command twice due to bug in acl show function
    """
    logging.info(f"Policy : {policy_name}, Rule name: {rule_name} on type: {interface_type}, interface {interface}")
    if interface_type is InterfaceType.CTRL_PLANE :
        command = f'show ctrl-plane acl detail'
        expect_string = '.*MODE.*'
    elif interface_type is InterfaceType.X_ETH:
        command = f'show acl interface detail x-eth0/0/{interface}'
        expect_string = '.*INTERFACE.*'
    else :
        raise Exception (f"Unrecognized interface type: {interface_type}")

    # First counter read. Disregard results
    logging.info(f"Send command 1st: \"{command}\"")
    cli_comm.sendline(command)
    logging.info(f"Expecting: {expect_string}")
    cli_comm.expect(expect_string)
    response = cli_comm.after

    # Second counter read. This is the actual value. Need to read twice due to bug
    logging.info(f"Send command 2nd: \"{command}\"")
    cli_comm.sendline(command)
    logging.info(f"Expecting: {expect_string}")
    cli_comm.expect(expect_string)
    response = cli_comm.after

    counter = _parse_show_counter(response, policy_name, rule_name)
    logging.info(f"counter value: {counter}")

    return counter

# ***************************************************************************************
# UT
# ***************************************************************************************
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
    counter = _parse_show_counter(show_acl_ifc_detail, "canary_pol_deny_src_ip", "r1")
    print (counter)
    counter = _parse_show_counter(show_acl_ifc_detail, "canary_pol_deny_src_ip", "rule-default")
    print (counter)
    counter = _parse_show_counter(show_acl_ctrl_plane_detail, "canary_pol_deny_src_ip", "r1")
    print (counter)
    counter = _parse_show_counter(show_acl_ctrl_plane_detail, "canary_pol_deny_src_ip", "rule-default")
    print (counter)

def _test_basic() :
    DEVICE_NUMBER = '3010'
    cli_comm = open_cpm_session(DEVICE_NUMBER)

    # SYSTEM SHOW
    # -------------------
    _print_system_mod(cli_comm)

    # ACL SHOW
    # --------------------
    _print_acl_interface_details(cli_comm, 23)
    _print_acl_interface_details(cli_comm, 23)

def _test_get_counters() :
    # Read globals from ini file
    import configparser
    constants = configparser.ConfigParser()
    constants.read('config.ini')
    dut_number = constants['GENERAL']['DUT_NUM']
    physical_port_num = int(constants['TEST_SUITE_ACL']['PHYSICAL_PORT_NUM'])
    canary_acl_policy_name  = constants['TEST_SUITE_ACL']['ACL_POLICY_NAME']

    # Open CLI connection
    cli_comm = open_cpm_session(dut_number)

    # Read counters
    counter = get_show_counter (cli_comm, physical_port_num, InterfaceType.CTRL_PLANE, canary_acl_policy_name, "r1")
    print (f"Rule: r1, GOT : {counter}")

    counter = get_show_counter (cli_comm, physical_port_num, InterfaceType.CTRL_PLANE, canary_acl_policy_name, "rule-default")
    print (f"Rule: default, GOT : {counter}")

if __name__ == "__main__" :
    # _test_get_counters()
    # _test_basic()
    # _test_acl_show_counter()

    reset_mng_and_cpm_connections('3010')

    logging.info("Finished")
