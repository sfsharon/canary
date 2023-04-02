"""
Pytest runner code
"""
import pytest
import configparser

import paramiko
import logging
import snmp_comm
from common_enums import InterfaceOp, AclCtrlPlaneType, FrameType, InterfaceType

logging.basicConfig(
                    format='%(asctime)s.%(msecs)03d [%(filename)s line %(lineno)d] %(levelname)-8s %(message)s',                       
                    level=logging.INFO,
                    datefmt='%H:%M:%S')


# ***************************************************************************************
# Helper functions
# ***************************************************************************************
def _remote_exists(sftp, path):
    """ 
    Check if a remote path exists
    """
    try:
        sftp.stat(path)
        return True
    except IOError:
        return False

def _run_remote_shell_cmd(ssh_object, cmd_string) :
    """
    Run remote shell command
    """
    import socket

    exit_status = None

    try :
        # Execute a command on the remote server and get the output
        logging.info(f"Running remote command:\n\"{cmd_string}\"")

        ssh_stdin, ssh_stdout, ssh_stderr = ssh_object.exec_command(cmd_string)

        exit_status = ssh_stdout.channel.recv_exit_status()
        if exit_status == 0 :
            logging.info(f"Remote command succeeded")
        else :
            logging.info(f"Command failed with exit status: {exit_status}")

    except paramiko.SSHException as e:
        # Handle SSH exception
        logging.error(f'SSH error: {e}')
    except socket.error as e:
        # Handle socket error
        logging.error(f'Network error: {e}')

    return exit_status

def _inject_frame_and_verify_counter(ssh_client, 
                                     cli_client,
                                     src_ip, dst_ip, dst_mac, 
                                     num_of_tx, 
                                     frame_type,
                                     interface_type,
                                     workdir, 
                                     physical_port_num,
                                     policy_name,
                                     rule_name) :
    """
    Inject a frame into BCM, and verify that the counter advanced accordingly :
        1. Create packet
        2. Read ACL counter value 
           (Using CLI)
        3. Inject packet into bcm's port that will trigger the deny rule in ACL policy 
           (Using BCM Diagnostic shell "TX" command)
        4. Read ACL counter value again, and assert that it incremented the value of packets injected 
           (Using CLI)

        Input : ssh_client      - 
                cli_client      - 
                src_ip, dst_ip, dst_mac - 
                num_of_tx       - 
                frame_type  - Enumeration for different frames to be transmitted. L2_L3 or ICMP frames
                interface_type - Enumeration InterfaceType, values "CTRL_PLANE", "X_ETH"
        Return value : None
    """
    import packet_creator
    import cli_control

    logging.info("_inject_frame_and_verify_counter")
    

    # BCM port number is 1 larger then app values (x-eth 0/0/23 is BCM port 24)
    bcm_port_num = str(int(physical_port_num) + 1) 
    
    # 1. Generate the Byte hex representation of the frame, needed for transmission into the SDK :
    if frame_type is FrameType.L2_L3_FRAME :
        frame = packet_creator.create_l2_l3_frame(src_ip, dst_ip, dst_mac)
    elif frame_type is FrameType.ICMP_FRAME :
        frame = packet_creator.create_icmp_frame(src_ip, dst_ip, dst_mac)
    else :
        raise Exception (f"Unrecognized frame type {frame_type}")

    # 2. Read ACL counter value
    counter_prev = int(cli_control.get_show_counter(cli_client, physical_port_num, interface_type, policy_name, rule_name))
                                                                                        

    # 3. Inject frame into BCM - Run remote command in DUT
    command = f"cd {workdir};python tx_into_bcm.py {frame} {num_of_tx} {bcm_port_num}"
    rv = _run_remote_shell_cmd (ssh_client, command)

    if rv != 0 :
        raise Exception(f"Failed with rv {rv}, when running remote command \"{command}\"")
        
    # 4. Reading updated ACL counter
    counter_curr = int(cli_control.get_show_counter(cli_client, physical_port_num, interface_type, policy_name, rule_name))


    # Verify counter incremented correctly
    delta_counter = counter_curr - counter_prev
    num_of_tx = int(num_of_tx)
    logging.info(f"Previous counter: {counter_prev}, Curr counter: {counter_curr}, delta : {delta_counter}, expected delta: {num_of_tx}")
    
    assert  (delta_counter == num_of_tx), \
             f"Error: Previous counter: {counter_prev}, Curr counter: {counter_curr}"

def _acl_in_policy_Operation_on_interface (netconf_client, physical_port_num, acl_policy_name, interface_op) :
    """
    Perform attach / detach operation of an ACL in policy on interface physical_port_num.
    Input:  netconf_client
            physical_port_num - Integer
            acl_policy_name - String
            interface_op - Enumeration of type InterfaceOp. Activating either attach or detach from interface.
    Return : True on success, False otherwise
    """
    import netconf_comm

    rv = None
    x_eth_name        = "0/0/" + str(physical_port_num )
    logging.info(f"Operation: {interface_op.name} for policy name:{acl_policy_name} on port {x_eth_name}")

    if interface_op is InterfaceOp.ATTACH :
        rv = netconf_comm.cmd_set_attach_policy_acl_in_x_eth(netconf_client, x_eth_name, acl_policy_name, operation="")
    elif interface_op is InterfaceOp.DETACH :
        rv = netconf_comm.cmd_set_attach_policy_acl_in_x_eth(netconf_client, x_eth_name, acl_policy_name, operation="operation=\"delete\"")
    else :
        raise Exception(f"Received unfamiliar operation {interface_op}")
    return rv

def _acl_ctrl_plane_policy_Operation (netconf_client, ctrl_plane_type, acl_policy_name, interface_op) :
    """
    Perform attach / detach operation of an ACL in policy on acl ctrl-plane.
    Input:  netconf_client
            ctrl_plane_type - String. Possible values: EGRESS or NNI_INGRESS
            acl_policy_name - String
            interface_op    - Enumeration of type InterfaceOp. Activating either attach or detach from interface.    
    Return : True on success, False otherwise
    """
    import netconf_comm

    rv = None
    logging.info(f"Operation: {interface_op.name}, acl policy name:{acl_policy_name}, ctrl-plane {ctrl_plane_type}")

    if interface_op is InterfaceOp.ATTACH :
        rv = netconf_comm.cmd_set_ctrl_plane_acl(dut_conn            = netconf_client, 
                                                 acl_ctrl_plane_type = ctrl_plane_type, 
                                                 operation           = "", 
                                                 attribute_value     = acl_policy_name)
    elif interface_op is InterfaceOp.DETACH :
        rv = netconf_comm.cmd_set_ctrl_plane_acl(dut_conn            = netconf_client, 
                                                 acl_ctrl_plane_type = ctrl_plane_type, 
                                                 operation           = " operation=\"delete\"", 
                                                 attribute_value     = acl_policy_name)
    else :
        raise Exception(f"Received unfamiliar operation: {interface_op.name}")
    return rv


# ***************************************************************************************
# Fixtures functions
# ***************************************************************************************
@pytest.fixture(scope="session")
def cli_client():
    """
    Connect to DUT using pyexpect
    """
    logging.info("Fixture: cli_client")

    import cli_control
    import configparser

    # Read globals from ini file
    constants = configparser.ConfigParser()
    constants.read('config.ini')
    DUT_NUMBER = constants['GENERAL']['DUT']

    cli_comm = cli_control.open_cli_session(DUT_NUMBER)
    yield cli_comm
    cli_control.close_cli_session(cli_comm)

@pytest.fixture(scope="session")
def netconf_client():
    """
    Connect to DUT using Netconf protocol
    """
    logging.info("Fixture: netconf_client")

    import netconf_comm
    import configparser

    # Read globals from ini file
    constants = configparser.ConfigParser()
    constants.read('config.ini')
    HOST_NAME       = constants['COMM']['HOST_CPM']
    NETCONF_PORT    = int(constants['NETCONF']['PORT'])

    CPM_USER                = "admin"
    CPM_PASSWORD            = "admin"

    dut_conn = netconf_comm.MyNetconf(hostname = HOST_NAME, port = NETCONF_PORT, username = CPM_USER, password = CPM_PASSWORD, 
                                      publicKey = "", publicKeyType = "", privateKeyFile = "", privateKeyType = "") 
    dut_conn.connect()

    # Perform get hello from DUT first.
    netconf_comm._cmd_hello(dut_conn)

    yield dut_conn
    dut_conn.close()

@pytest.fixture(scope="session")
def ssh_client():
    """
    Connect to DUT using SSH client
    """
    logging.info("Fixture: ssh_client")
    
    # Read globals from ini file
    constants = configparser.ConfigParser()
    constants.read('config.ini')
    host = constants['COMM']['HOST_ONL']

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=host, username="root", password="root")

    logging.info(f"Connecting to host {host}")
    client.connect(hostname=host, username="root", password="root")
    yield client
    client.close()

@pytest.fixture(scope="session")
def setup_dut(ssh_client):
    """
    Move testing files into workdir in DUT.
    If workdir already exists, first delete it completly.
    """
    logging.info("Fixture: setup_dut")

    # Read globals from ini file
    constants = configparser.ConfigParser()
    constants.read('config.ini')
    workdir     = constants['DUT_ENV']['WORKDIR']

    copy_file_list = ["tx_into_bcm.py", "monitor_logfile.py", "config.ini"]

    # Create an SFTP client
    with ssh_client.open_sftp() as sftp:   
        if _remote_exists(sftp, workdir) :
            logging.info(f"Removing working directory {workdir}")
            _run_remote_shell_cmd(ssh_client, f'rm -rf {workdir}')

        logging.info(f"create a new folder for workspace {workdir}")           
        sftp.mkdir(workdir)

        for file in copy_file_list :
            logging.info(f"Copying {file} to the {workdir}")
            sftp.put(file, workdir + "/" + file)

# ***************************************************************************************
# Test Case #0 - Setup Environment
# ***************************************************************************************
def test_TC00_Setup_Environment(setup_dut, netconf_client):
    """
    Setup configured policy :
    1. Read global variables from config.ini file
    2. if interface physical_port_num contains acl in policy, delete it
       (Using Netconf)
    2. Create a new ACL policy named acl_policy_name (delete old one, create new one)
       (Using Netconf)
    3. Attach new policy to interface physical_port_num
       (Using Netconf)
    """
    import netconf_comm

    logging.info("test_TC00_Setup_Environment")

    # Read globals from ini file
    # ----------------------------------------------------------
    constants = configparser.ConfigParser()
    constants.read('config.ini')
    physical_port_ip    = constants['TEST_SUITE_ACL']['SRC_IP_RULE_R1']
    physical_port_num   = constants['TEST_SUITE_ACL']['PHYSICAL_PORT_NUM']
    canary_acl_policy_name  = constants['TEST_SUITE_ACL']['ACL_POLICY_NAME']

    # If there is an acl in policy attached to interface, delete it 
    # ---------------------------------------------------------------        
    x_eth_name        = "0/0/" + physical_port_num 
    acl_policy_name = netconf_comm.cmd_get_policy_acl_in_name(netconf_client, x_eth_name)

    if acl_policy_name != None :
        _acl_in_policy_Operation_on_interface (netconf_client, physical_port_num, acl_policy_name, InterfaceOp.DETACH) 

    # Create acl policy canary_acl_policy_name
    # ----------------------------------------------------------    
    # Delete operation may return False, if the object did not exist in the first place
    netconf_comm.cmd_set_acl_policy__deny_src_ip(netconf_client, canary_acl_policy_name, physical_port_ip, operation = "operation=\"delete\"")
    # Create operation should always succeed.
    rv = netconf_comm.cmd_set_acl_policy__deny_src_ip(netconf_client, canary_acl_policy_name, physical_port_ip, operation = "")
    if rv == False :
        raise Exception ("Failed committing cmd_set_acl_policy__deny_src_ip")
    
    # Initial test TC00 should always succeed
    assert True

# ***************************************************************************************
# Test Case #1 - ACL in
# ***************************************************************************************
def test_TC01_rule_r1_acl_in(ssh_client, netconf_client, cli_client) :
    """
    Test deny on acl rule R1 :
        1. Attach policy to interface
           (Using Netconf)
        2. Inject frame and verify counters increase
        3. Detach policy to interface
           (Using Netconf)
    """
    logging.info("test_TC01_rule_r1_acl_in")
    
    # Read globals from ini file
    constants = configparser.ConfigParser()
    constants.read('config.ini')

    physical_port_num = int(constants['TEST_SUITE_ACL']['PHYSICAL_PORT_NUM'])
    src_ip  = constants['TEST_SUITE_ACL']['SRC_IP_RULE_R1']
    dst_ip  = constants['TEST_SUITE_ACL']['DST_IP']
    dst_mac = constants['TEST_SUITE_ACL']['DST_MAC']
    canary_acl_policy_name  = constants['TEST_SUITE_ACL']['ACL_POLICY_NAME']
    rule_name = "r1"
    workdir = constants['DUT_ENV']['WORKDIR']
    num_of_tx = '142'

    # Attach acl in policy to interface
    # ---------------------------------------------------------------------------        
    rv = _acl_in_policy_Operation_on_interface (netconf_client, physical_port_num, canary_acl_policy_name, InterfaceOp.ATTACH) 
    if rv == False :
        raise Exception (f"Failed attaching {canary_acl_policy_name} from interface {physical_port_num}")

    # Perform test
    # ---------------------------------------------------------------------------        
    _inject_frame_and_verify_counter(ssh_client, 
                                     cli_client,                                     
                                     src_ip, dst_ip, dst_mac, 
                                     num_of_tx,
                                     FrameType.L2_L3_FRAME,
                                     InterfaceType.X_ETH,
                                     workdir,
                                     physical_port_num,  
                                     canary_acl_policy_name,
                                     rule_name)

    # Detach acl in policy from interface
    # ---------------------------------------------------------------------------        
    rv = _acl_in_policy_Operation_on_interface (netconf_client, physical_port_num, canary_acl_policy_name, InterfaceOp.DETACH) 
    if rv == False :
        raise Exception (f"Failed detaching {canary_acl_policy_name} from interface {physical_port_num}")

def test_TC02_default_rule_acl_in(ssh_client, netconf_client, cli_client) :
    """
    Test permit on acl default rule
    """
    logging.info("test_TC02_default_rule_acl_in")
    
    # Read globals from ini file
    constants = configparser.ConfigParser()
    constants.read('config.ini')

    physical_port_num = int(constants['TEST_SUITE_ACL']['PHYSICAL_PORT_NUM'])
    src_ip  = constants['TEST_SUITE_ACL']['SRC_IP_RULE_DEFAULT']
    dst_ip  = constants['TEST_SUITE_ACL']['DST_IP']
    dst_mac = constants['TEST_SUITE_ACL']['DST_MAC']
    canary_acl_policy_name  = constants['TEST_SUITE_ACL']['ACL_POLICY_NAME']
    rule_name = "rule-default"
    workdir = constants['DUT_ENV']['WORKDIR']
    num_of_tx = '143'

    # Attach acl in policy to interface
    # ---------------------------------------------------------------------------        
    rv = _acl_in_policy_Operation_on_interface (netconf_client, physical_port_num, canary_acl_policy_name, InterfaceOp.ATTACH) 
    if rv == False :
        raise Exception (f"Failed attaching {canary_acl_policy_name} from interface {physical_port_num}")

    # Perform test
    # ---------------------------------------------------------------------------        
    _inject_frame_and_verify_counter(ssh_client, 
                                     cli_client,                                     
                                     src_ip, dst_ip, dst_mac, 
                                     num_of_tx,
                                     FrameType.L2_L3_FRAME,
                                     InterfaceType.X_ETH,
                                     workdir,
                                     physical_port_num,  
                                     canary_acl_policy_name,
                                     rule_name)

    # Detach acl in policy from interface
    # ---------------------------------------------------------------------------        
    rv = _acl_in_policy_Operation_on_interface (netconf_client, physical_port_num, canary_acl_policy_name, InterfaceOp.DETACH) 
    if rv == False :
        raise Exception (f"Failed detaching {canary_acl_policy_name} from interface {physical_port_num}")

def test_TC03_acl_rule_r1_ctrl_plane_egress(ssh_client, netconf_client, cli_client) :
    """
    Test deny rule r1 on acl ctrl-plane egress
    """
    logging.info("test_TC03_acl_rule_r1_ctrl_plane_egress")
    
    # Read globals from ini file
    constants = configparser.ConfigParser()
    constants.read('config.ini')

    physical_port_num = int(constants['TEST_SUITE_ACL']['PHYSICAL_PORT_NUM'])
    
    rule_name = "r1"
    src_ip  = constants['TEST_SUITE_ACL']['SRC_IP_RULE_R1']
    
    dst_ip  = constants['TEST_SUITE_ACL']['DST_IP']
    dst_mac = constants['TEST_SUITE_ACL']['DST_MAC']
    canary_acl_policy_name  = constants['TEST_SUITE_ACL']['ACL_POLICY_NAME']
    workdir = constants['DUT_ENV']['WORKDIR']    
    num_of_tx = '87'

    ctrl_plane_type = AclCtrlPlaneType.EGRESS.name.lower()

    # Attach acl policy to acl egress ctrl-plane
    # ---------------------------------------------------------------------------        
    rv = _acl_ctrl_plane_policy_Operation (netconf_client, ctrl_plane_type, canary_acl_policy_name, InterfaceOp.ATTACH) 
    if rv == False :
        raise Exception (f"Failed attaching {canary_acl_policy_name} to ctrl-plane {ctrl_plane_type}")

    # Perform test
    # ---------------------------------------------------------------------------        
    _inject_frame_and_verify_counter(ssh_client, 
                                     cli_client,                                     
                                     src_ip, dst_ip, dst_mac, 
                                     num_of_tx,
                                     FrameType.ICMP_FRAME,
                                     InterfaceType.CTRL_PLANE,
                                     workdir,
                                     physical_port_num,  
                                     canary_acl_policy_name,
                                     rule_name)

    # Detach acl in policy from interface
    # ---------------------------------------------------------------------------        
    rv = _acl_ctrl_plane_policy_Operation (netconf_client, ctrl_plane_type, canary_acl_policy_name, InterfaceOp.DETACH) 
    if rv == False :
        raise Exception (f"Failed detaching {canary_acl_policy_name} from interface {physical_port_num}")
