"""
DEV_MACHINE_CLI.py
- Controling the DUT CLI using pexpect.
- This is a fork from the cli_control.py file that was originally written for the Canary app, in the folder dut_ctrl.
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
def _get_dut_alias_to_cmd (device_num: str, device_type: str, command: str) -> str:
    """
    Search the alias_sw_lab_new file for the requested command
    device_num  : e.g., '3010'
    device_type : Applicable values : 'dl', 'ec', 'al', 'uf'
    command     : Applicable values : 'm', 'o', 'off', 'on', 'reset', 's', 'sc' 
    """
    import re

    alias_file = '/home/exaware/alias_sw_lab_new'
    dev_specific_num = device_num[-2:]
    
    with open(alias_file, 'r') as f:
        text = f.read()

    full_command = f"alias exa-il01-{device_type}-30{dev_specific_num}-{command}"
    pattern = f"{full_command}='(.*)'"

    matches = re.findall(pattern, text)

    if len(matches) != 1 :
        raise Exception (f"Could not find command {full_command} in alias file {alias_file}")
    
    print(f"Command {full_command} in aliased to {matches[0]}")
    return matches[0]

def reset_serial_server_connection(device_number: str, device_type: str) -> None :
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
    logging.info(f"{get_time()} Disconnect the serial server from the DUT")
    import subprocess

    dut_cmd = "sc"
    command = _get_dut_alias_to_cmd(device_number, device_type, dut_cmd)

    logging.info(f"{get_time()} Reset serial server connection for device number: {device_number}, type: {device_type}")

    process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
    output, error = process.communicate()

    logging.info(f"{get_time()} output : {output}, error: {error}")

# ---------------------------------------------------------------------
# OLD STUFF FROM DUT_CTRL !!!
# ---------------------------------------------------------------------

def _print_system_mod (cli_comm) :
    logging.info("Send command \"show sys mod\"")
    cli_comm.sendline('show sys mod')

    logging.info("Expecting: \"BOX/SLOT\"")
    cli_comm.expect('.*BOX/SLOT.*')

    logging.info("Received results")
    print(cli_comm.after)


def get_official_install_file_name(cli_response, build_number) :
    """
    Input: cli_response - Output from command "ls" for build files 
           build_number -
    Return value : String, file name of build build_number
    """
    required_file_name = None

    normalised_input = [line.lstrip() for line in cli_response.splitlines()]
    for i, line in enumerate(normalised_input) :
        build_name = (line.split())[-1]
        if build_name.endswith(f"b{build_number}") :
            required_file_name = build_name            
            break

    return required_file_name

def get_official_latest_build(cli_response: str) -> str :
    """
    Input: cli_response - Output from command "ls" for build files 
    Return value : String, Latest build_number
    """
    import re
    install_file_name_pattern   = r"onie-installer-.*b\d+$"
    get_build_num_pattern       = r"\d+$"
    max_build_num = 0

    normalised_input = [line.lstrip() for line in cli_response.splitlines()]
    for i, line in enumerate(normalised_input) :
        file_name = (line.split())[-1]
        if re.search(install_file_name_pattern, file_name) :
            match = re.search(get_build_num_pattern, file_name)
            build_num = int(match.group())
            if build_num > max_build_num : max_build_num = build_num
            logging.debug(f"Found build number {build_num}")
    logging.debug(f"Latest build number {max_build_num}")
    return str(max_build_num)
    
def get_build_number_from_build_param_file(file_name):
    import re
    build_num = None

    build_number_string = 'Build number ='
    with open(file_name, 'r') as file:
        # read a list of lines into data
        data = file.readlines()

        # iterate over each line
        for line in data:
            # check if the line contains the string
            if build_number_string in line:
                build_num = re.findall('\d+', line)
                if len(build_num) != 1 :
                    raise Exception (f"Could not find build number in line {line}")
                build_num = build_num[0]
                break 
    return build_num

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


# ***************************************************************************************
# External API functions
# ***************************************************************************************
def get_time() :
    """
    Returns elapsed time string from a given time in seconds
    """
    import time
    current_time = time.strftime("%H:%M:%S", time.localtime())
    return current_time

def reset_dut_connections(device_number: str, device_type: str, is_reset_cpm_connection: bool) -> None :
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
    CPM_PROMPT  = f"R{device_number}"
    ONL_PROMPT  = f"root@localhost:~#"
    TIMEOUT     = 20
    cli_comm    = None


    logging.info(f"{get_time()} Begin reset_dut_connections")

    # 1. Disconnect other client if connected to serial server 
    _reset_serial_server_connection(device_number, device_type)

    try :
        # 2. Telnet into the machine using the serial server and send "dhclient ma1"
        logging.info(f"{get_time()} Opening ONL CLI connection to device number: {device_number}, device type: {device_type}")
        dut_cmd = "s"
        command = _get_dut_alias_to_cmd(device_number, device_type, dut_cmd)
        cli_comm = pexpect.spawn(command, encoding='utf-8', timeout=TIMEOUT, codec_errors='ignore')

        # Wait for the password prompt and enter the password
        logging.info(f"{get_time()} Waiting for Serial server prompt")
        cli_comm.expect('.*Escape character.*')

        logging.info(f"{get_time()}  send \\n")
        cli_comm.sendline('')

        logging.info(f"{get_time()} Expecting connection with DUT")
        i = cli_comm.expect([f'.*{ONL_PROMPT}.*', f'.*{CPM_PROMPT}.*', '.*localhost login:.*'])
        if i == 0:
            logging.info(f"{get_time()}  ONL CLI Shell. Doing nothing")
        elif i == 1:
            logging.info(f"{get_time()}  DUT CLI Shell. Exiting")
            cli_comm.sendline('exit')
            cli_comm.expect(f'.*{ONL_PROMPT}.*')
        elif i == 2:
            logging.info(f"{get_time()} New CLI shell. Performing logging")
            cli_comm.sendline('root')
            cli_comm.expect(f'.*Password:.*')
            cli_comm.sendline('root')
            cli_comm.expect(f'.*{ONL_PROMPT}.*')            
        logging.info(f"{get_time()} Sending \"dhclient ma1\"")
        cli_comm.sendline('dhclient ma1')
        logging.info(f"{get_time()} Expecting ONL prompt: {ONL_PROMPT}")
        i = cli_comm.expect([f'.*{ONL_PROMPT}.*', pexpect.TIMEOUT, pexpect.EOF], timeout=300)
        if i == 0 :
            logging.info(f"{get_time()} Got: {ONL_PROMPT}. Continuing")
        elif i == 1 :
            logging.info(f"{get_time()} Got: Timeout. Bailing out")
            raise Exception ("Timeout")
        elif i == 2 :
            logging.info(f"{get_time()} Got: EOF. Bailing out")
            raise Exception ("EOF")
        else :
            logging.info(f"{get_time()} Got unidentified index {i}.")
            raise Exception ("Unidentified index")
        
        # 3. Send ping to vrf management, to "shake" the CPM 10.3.XX.1 connection into life
        if is_reset_cpm_connection == True:
            logging.info(f"{get_time()} Resetting CPM connection (to IP 10.3.XX.1)")
            logging.info(f"{get_time()} Connecting to DUT CLI (using command \"ssc\")")
            cli_comm.sendline('ssc')
            cli_comm.expect(['.*Are you sure you want to continue connecting (yes/no)?.*', '.*password:.*'])
            if i == 0:
                logging.info(f"{get_time()} First time connection to DUT.")
                cli_comm.sendline('yes')
                cli_comm.expect('.*password:.*')
            logging.info(f"{get_time()} Sending password")
            cli_comm.sendline('admin')
            logging.info(f"{get_time()} Expecting CPM prompt: {CPM_PROMPT} with timeout=30")
            cli_comm.expect([f'.*{CPM_PROMPT}.*'], timeout= 300)

            ping_command = f'ping vrf management 10.3.{device_number[-2:]}.254'
            logging.info(f"{get_time()} Sending ping command: \"{ping_command}\"")
            cli_comm.sendline(f'ping vrf management 10.3.{device_number[-2:]}.254')
            logging.info(f"{get_time()} Expecting end of ping")
            cli_comm.expect([f'.*rtt min/avg/max/mdev.*', f'.*{CPM_PROMPT}.*'])

            # Exiting DUT CLI back to ONL, in preparation for the tests 
            logging.info(f"{get_time()} Sending \\n")
            cli_comm.sendline('')
            logging.info(f"{get_time()} Expecting CPM prompt: {CPM_PROMPT}")
            cli_comm.expect(f'.*{CPM_PROMPT}.*')
            logging.info(f"{get_time()} Sending exit command")
            cli_comm.sendline('exit')
            logging.info(f"{get_time()} Expecting ONL prompt: {ONL_PROMPT}")
            cli_comm.expect(f'.*{ONL_PROMPT}.*')

    except pexpect.exceptions.TIMEOUT :
        raise Exception(f"{get_time()} Waiting for CLI response exceeded {TIMEOUT} seconds")
    except pexpect.exceptions.EOF :
        raise Exception(f"{get_time()} pexpect EOF exception")    
    finally:
        logging.info(f"{get_time()} Closing ONL CLI connection")
        cli_comm.close()
    
    logging.info(f"{get_time()} End reset_dut_connections")

def reboot_dut(device_number, device_type, is_set_install_mode = False):
    """
    """
    CPM_PROMPT  = f"R{device_number}"
    ONL_PROMPT  = f"root@localhost:~#"
    TIMEOUT     = 5
    cli_comm    = None

    logging.info(f"{get_time()} Begin set_install_mode_and_reboot_dut")

    # 1. Disconnect other client if connected to serial server 
    _reset_serial_server_connection(device_number, device_type)

    try :
        # 2. Telnet into the machine using the serial server
        logging.info(f"{get_time()} Opening ONL CLI connection to device number: {device_number}, device type: {device_type}")
        dut_cmd = "s"
        command = _get_dut_alias_to_cmd(device_number, device_type, dut_cmd)                                 
        cli_comm = pexpect.spawn(command, encoding='utf-8', timeout=TIMEOUT, codec_errors='ignore')

        # Wait for the password prompt and enter the password
        logging.info(f"{get_time()} Waiting for Serial server prompt")
        cli_comm.expect('.*Escape character.*')

        logging.info(f"{get_time()} send \\n")
        cli_comm.sendline('')

        logging.info(f"{get_time()} Expecting connection with DUT")
        i = cli_comm.expect([f'.*{ONL_PROMPT}.*', f'.*{CPM_PROMPT}.*', '.*localhost login:.*'])
        if i == 0:
            logging.info(f"{get_time()} ONL CLI Shell. Doing nothing")
        elif i == 1:
            logging.info(f"{get_time()} DUT CLI Shell. Exiting")
            cli_comm.sendline('exit')
            cli_comm.expect(f'.*{ONL_PROMPT}.*')
        elif i == 2:
            logging.info(f"{get_time()} New CLI shell. Performing logging")
            cli_comm.sendline('root')
            cli_comm.expect(f'.*Password:.*')
            cli_comm.sendline('root')
            cli_comm.expect(f'.*{ONL_PROMPT}.*')       

        if is_set_install_mode == True :
            # Setting boot mode to install
            command = "onl-onie-boot-mode install"
            expected_response = "The system will boot into ONIE install mode at the next restart."
            logging.info(f"{get_time()} Sending \"{command}\"")
            cli_comm.sendline(command)
            logging.info(f"{get_time()} Expecting: \"{expected_response}\"")
            cli_comm.expect(f'.*{expected_response}.*')
            
        # Rebooting
        command = "/sbin/reboot"
        logging.info(f"{get_time()} Sending \"{command}\"")
        cli_comm.sendline(command)
    except pexpect.exceptions.TIMEOUT :
        raise Exception(f"{get_time()} Waiting for CLI response exceeded {TIMEOUT} seconds")
    finally:
        logging.info(f"{get_time()} Closing ONL CLI connection")
        cli_comm.close()

    logging.info(f"{get_time()} End reset_dut_connections")

def add_dev_machine_ssh_key_to_dut(device_number, device_type):
    """
    """
    CPM_PROMPT  = f"R{device_number}"
    ONL_PROMPT  = f"root@localhost:~#"
    TIMEOUT     = 5
    cli_comm    = None

    logging.info(f"{get_time()} add_dev_machine_ssh_key_to_dut")

    # 1. Disconnect other client if connected to serial server 
    _reset_serial_server_connection(device_number, device_type)

    try :
        # 2. Telnet into the machine using the serial server
        logging.info(f"{get_time()} Opening ONL CLI connection to device number: {device_number}, device type: {device_type}")
        dut_cmd = "s"
        command = _get_dut_alias_to_cmd(device_number, device_type, dut_cmd) 
        cli_comm = pexpect.spawn(command, encoding='utf-8', timeout=TIMEOUT, codec_errors='ignore')

        # Wait for the password prompt and enter the password
        logging.info(f"{get_time()} Waiting for Serial server prompt")
        cli_comm.expect('.*Escape character.*')

        logging.info(f"{get_time()} send \\n")
        cli_comm.sendline('')

        logging.info(f"{get_time()} Expecting connection with DUT")
        i = cli_comm.expect([f'.*{ONL_PROMPT}.*', f'.*{CPM_PROMPT}.*', '.*localhost login:.*'])
        if i == 0:
            logging.info(f"{get_time()} ONL CLI Shell. Doing nothing")
        elif i == 1:
            logging.info(f"{get_time()} DUT CLI Shell. Exiting")
            cli_comm.sendline('exit')
            cli_comm.expect(f'.*{ONL_PROMPT}.*')
        elif i == 2:
            logging.info(f"{get_time()} New CLI shell. Performing logging")
            cli_comm.sendline('root')
            cli_comm.expect(f'.*Password:.*')
            cli_comm.sendline('root')
            cli_comm.expect(f'.*{ONL_PROMPT}.*')       

        # Creating ~/.ssh directory
        command = "mkdir ~/.ssh"
        expected_response = ONL_PROMPT
        logging.info(f"{get_time()} Sending \"{command}\"")
        cli_comm.sendline(command)
        logging.info(f"{get_time()} Expecting: \"{expected_response}\"")
        cli_comm.expect(f'.*{expected_response}.*')

        # Creating ~/.ssh/authorized_keys file
        command = 'echo "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQDEX/adijlM2zGZpqeJ9mz5J4RYW0k3LQWISW/lN31NVfZEY8LxghsiGWnsJfFMWRUP/n1NE72mfSZOozFv/WmLtSaRLdzBlpK1cg7nMuQvE7zL9/Y9WdzgSKEs6Khx/8tFPbjr0VyEmM+aSFGuc8xSyaTYCcNcfvN/rbmVFWaS379FQRFXyFrlZZ5ynrP1gCKblLK3m1cNUq/B7NXWyuoQHDLvGHe+B5UnviUQRl8xmTUuq/VVccwGvNNcuvXYxnE8GE5zM/mKhPDChgusy5Km3W33nK2jGTleaZWAIVPk4FSJyCTI/2F/4AOGbjp4b5iBkRtesQFAQtDN6hkV9iAtLVpydx3rMUArgFcuwo06VK7BN3lOfXy7h+0E1f/q/7rRHVSD2O0jCk/36LmMbllqqbsScAHuUZfxX1fJnd7gCC2XedMU/3WUJ62O3L8LiPQP9XhBUpSUgKoBeXxIHgg4QRiqm/I+gXCsUVSVf9nN+DfKuvZcRzMSbK3ZDByUjZs= sharonf@DEV107" > ~/.ssh/authorized_keys'
        expected_response = ONL_PROMPT
        logging.info(f"{get_time()} Sending \"{command}\"")
        cli_comm.sendline(command)
        logging.info(f"{get_time()} Expecting: \"{expected_response}\"")
        cli_comm.expect(f'.*{expected_response}.*')
    except pexpect.exceptions.TIMEOUT :
        raise Exception(f"{get_time()} Waiting for CLI response exceeded {TIMEOUT} seconds")
    finally:
        logging.info(f"{get_time()} Closing ONL CLI connection")
        cli_comm.close()

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
        logging.info(f"{get_time()} Opening CPM CLI connection to device {device_number}")
        cli_comm = pexpect.spawn(f'ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no {CPM_ADDRESS} -l admin', 
                                  encoding='utf-8',
                                  timeout=TIMEOUT,
                                  codec_errors='ignore')

        # Wait for the password prompt and enter the password
        logging.info(f"{get_time()} Waiting for password prompt")
        cli_comm.expect('password:')

        logging.info(f"{get_time()} send password")
        cli_comm.sendline('admin')

        logging.info(f"{get_time()} Expecting CPM prompt: {CPM_PROMPT}")
        cli_comm.expect(f'.*{CPM_PROMPT}.*')
    except pexpect.exceptions.TIMEOUT :
        logging.error(f"{get_time()} Cannot connect to device {device_number}")

    return cli_comm   

def close_cpm_session(cli_comm):
    """
    Close cleanly a pexpect session to a DUT CLI shell (in the cpm)
    Input : Spawned pexpect process (cli_comm)
    Return value : None
    """
    logging.info(f"{get_time()} Closing CLI connection")
    cli_comm.close()

# def get_show_counter (cli_comm, interface, interface_type, policy_name, rule_name) :
#     """
#     Reading ACL counter according to interface, policy name and action
#     Input : cli_comm - 
#             interface - Physical interface such as "4"
#             interface_type - Enumeration InterfaceType, values "CTRL_PLANE", "X_ETH"
#             policy_name - String
#             rule_name : String
#     Caveat :Sending each command twice due to bug in acl show function
#     """
#     logging.info(f"{get_time()} Policy : {policy_name}, Rule name: {rule_name} on type: {interface_type}, interface {interface}")
#     if interface_type is InterfaceType.CTRL_PLANE :
#         command = f'show ctrl-plane acl detail'
#         expect_string = '.*MODE.*'
#     elif interface_type is InterfaceType.X_ETH:
#         command = f'show acl interface detail x-eth0/0/{interface}'
#         expect_string = '.*INTERFACE.*'
#     else :
#         raise Exception (f"Unrecognized interface type: {interface_type}")

#     # First counter read. Disregard results
#     logging.info(f"{get_time()} Send command 1st: \"{command}\"")
#     cli_comm.sendline(command)
#     logging.info(f"{get_time()} Expecting: {expect_string}")
#     cli_comm.expect(expect_string)
#     response = cli_comm.after

#     # Second counter read. This is the actual value. Need to read twice due to bug
#     logging.info(f"{get_time()} Send command 2nd: \"{command}\"")
#     cli_comm.sendline(command)
#     logging.info(f"{get_time()} Expecting: {expect_string}")
#     cli_comm.expect(expect_string)
#     response = cli_comm.after

#     counter = _parse_show_counter(response, policy_name, rule_name)
#     logging.info(f"{get_time()} Counter value: {counter}")

#     return counter

# ***************************************************************************************
# UT
# ***************************************************************************************
def _print_acl_interface_details(cli_comm, interface_number) :
    """show acl interface detail x-eth0/0/1"""
    command = f'show acl interface detail x-eth0/0/{str(interface_number)}'
    logging.info(f"{get_time()} Send command: \"{command}\"")
    cli_comm.sendline(command)

    logging.info("{get_time()} Expecting: \"INTERFACE\"")
    cli_comm.expect('.*INTERFACE.*')

    logging.info("{get_time()} Received results")
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

# def _test_get_counters() :
#     # Read globals from ini file
#     import configparser
#     constants = configparser.ConfigParser()
#     constants.read('config.ini')
#     dut_number = constants['GENERAL']['DUT_NUM']
#     physical_port_num = int(constants['TEST_SUITE_ACL']['PHYSICAL_PORT_NUM'])
#     canary_acl_policy_name__r1_deny_default_permit  = constants['TEST_SUITE_ACL']['ACL_POLICY_NAME_R1_DENY_DEFAULT_PERMIT']

#     # Open CLI connection
#     cli_comm = open_cpm_session(dut_number)

#     # Read counters
#     counter = get_show_counter (cli_comm, physical_port_num, InterfaceType.CTRL_PLANE, canary_acl_policy_name__r1_deny_default_permit, "r1")
#     print (f"Rule: r1, GOT : {counter}")

#     counter = get_show_counter (cli_comm, physical_port_num, InterfaceType.CTRL_PLANE, canary_acl_policy_name__r1_deny_default_permit, "rule-default")
#     print (f"Rule: default, GOT : {counter}")

def _test_official_builds_manipulation():
    input = """-rw-r--r-- 1 buildslave sw-all        33 Mar 30 00:19 onie-installer-vdevelop.8.0.0-2023-03-29-21-18-14-l-nl-g03b2807b-b536.bsc
-rw-r--r-- 1 buildslave sw-all 734982823 Apr  2 00:19 onie-installer-vdevelop.8.0.0-2023-04-01-21-18-06-l-nl-g03b2807b-b537
-rw-r--r-- 1 buildslave sw-all        33 Apr  2 00:19 onie-installer-vdevelop.8.0.0-2023-04-01-21-18-06-l-nl-g03b2807b-b537.bsc
-rw-r--r-- 1 buildslave sw-all 734982823 Apr  3 00:19 onie-installer-vdevelop.8.0.0-2023-04-02-21-18-22-l-nl-g03b2807b-b538
-rw-r--r-- 1 buildslave sw-all        33 Apr  3 00:19 onie-installer-vdevelop.8.0.0-2023-04-02-21-18-22-l-nl-g03b2807b-b538.bsc
-rw-r--r-- 1 buildslave sw-all 734982823 Apr  4 00:19 onie-installer-vdevelop.8.0.0-2023-04-03-21-18-19-l-nl-g03b2807b-b539
-rw-r--r-- 1 buildslave sw-all        33 Apr  4 00:19 onie-installer-vdevelop.8.0.0-2023-04-03-21-18-19-l-nl-g03b2807b-b539.bsc
-rwxrwxrwx 1 buildslave sw-all 700854925 Jan  5 00:17 vbox-vdevelop.8.0.0-2023-01-04-22-15-24-l-nl-g9c0dd54c-b480.tar.gz
-rwxrwxrwx 1 buildslave sw-all        33 Jan  5 00:17 vbox-vdevelop.8.0.0-2023-01-04-22-15-24-l-nl-g9c0dd54c-b480.tar.gz.bsc
-rwxrwxrwx 1 buildslave sw-all 700857989 Jan  8 00:18 vbox-vdevelop.8.0.0-2023-01-07-22-15-27-l-nl-g9c0dd54c-b481.tar.gz
-rwxrwxrwx 1 buildslave sw-all        33 Jan  8 00:18 vbox-vdevelop.8.0.0-2023-01-07-22-15-27-l-nl-g9c0dd54c-b481.tar.gz.bsc"""

    # get_official_install_file_name(input, '538')
    get_official_latest_build(input)

if __name__ == "__main__" :
    logging.info(f"{get_time()} Started")
    # _test_get_counters()
    # _test_basic()
    # _test_acl_show_counter()
    # reset_dut_connections(device_number = '3010', is_reset_cpm_connection = True)

    # _test_official_builds_manipulation()

    DEVICE_NUMBER = "3054"
    DEVICE_TYPE = "ec"
    # add_dev_machine_ssh_key_to_dut(DEVICE_NUMBER, DEVICE_TYPE)
    _get_dut_alias_to_cmd (device_num = "3088", device_type = "ec", command = "sc")

    logging.info(f"{get_time()} Finished")
