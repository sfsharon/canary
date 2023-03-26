"""
Pytest runner code
"""
import pytest
import configparser

import paramiko
import logging
import snmp_comm

logging.basicConfig(
                    format='%(asctime)s.%(msecs)03d [%(filename)s line %(lineno)d] %(levelname)-8s %(message)s',                       
                    level=logging.INFO,
                    datefmt='%H:%M:%S')

# ***************************************************************************************
# Module Helper functions
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

def _inject_frame_and_verify_counter(ssh_client, phys_port_num, src_ip, dst_ip, dst_mac, num_of_tx) :
    """
    Inject a frame into BCM, and verify that the counter advanced accordingly :
        1. Read ACL counter value 
           (Using SNMP)
        2. Inject packet into bcm's port that will trigger the deny rule in ACL policy 
           (Using BCM Diagnostic shell)
        3. Read ACL counter value again, and assert that it incremented the value of packets injected 
           (Using SNMP)
    """
    import packet_creator

    logging.info("_inject_frame_and_verify_counter")
    
    # Read globals from ini file
    constants = configparser.ConfigParser()
    constants.read('config.ini')
    workdir                  = constants['DUT_ENV']['WORKDIR']
    snmp_counter_update_time = int(constants['SNMP']['COUNTER_UPDATE_TIME'])

    counter_curr = 0
    counter_prev = 0

    # BCM port number is 1 larger then app values (x-eth 0/0/23 is BCM port 24)
    bcm_port_num = str(phys_port_num + 1) 
    
    # Generate the String hex representation of the frame, needed for transmission into the SDK :
    frame = packet_creator.create_frame(src_ip, dst_ip, dst_mac)

    # Read ACL counter value, and save it
    acl_in_counter_prev = int(snmp_comm.acl_in_rule_r1_counter(phys_port_num))
    
    # Run remote command in DUT
    command = f"cd {workdir};python tx_into_bcm.py {frame} {num_of_tx} {bcm_port_num}"
    rv = _run_remote_shell_cmd (ssh_client, command)

    if rv != 0 :
        raise Exception(f"Failed with rv {rv}, when running remote command \"{command}\"")
        
    # Giving the SNMP counters a chance to update. 
    # Probably some periodic thread in DUT that updates counters for SNMP
    for i in range(snmp_counter_update_time) :
        counter_curr = int(snmp_comm.acl_in_rule_r1_counter(phys_port_num))
        
        # If found that counter changed, break
        if counter_curr != counter_prev :
            logging.info(f"Received SNMP results after {i} seconds")
            break
        import time
        if i % 10 == 0 :
            logging.info(f"Waited {i} seconds out of {snmp_counter_update_time} for SNMP to update DUT counters")
        time.sleep(1)

    # Verify counter incremented correctly
    num_of_tx = int(num_of_tx)
    assert  ((counter_curr - counter_prev) == num_of_tx), \
             f"Error: Previous counter: {counter_prev}, Curr counter: {counter_curr}"

# ***************************************************************************************
# Fixtures functions
# ***************************************************************************************
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
    2. Create a new ACL policy named acl_in_policy_name (delete old one, create new one)
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
    canary_acl_in_policy_name  = constants['TEST_SUITE_ACL']['acl_in_policy_name']

    # If there is an acl policy attached to interface, delete it 
    # ----------------------------------------------------------        
    X_ETH_VALUE        = "0/0/" + physical_port_num 
    acl_in_policy_name = netconf_comm.cmd_get_policy_acl_in_name(netconf_client, X_ETH_VALUE)

    if acl_in_policy_name != None :
        logging.info(f"Found policy {acl_in_policy_name} on port {X_ETH_VALUE}. Deleting it")
        netconf_comm.cmd_set_attach_policy_acl_in_x_eth(netconf_client, X_ETH_VALUE, acl_in_policy_name, operation="operation=\"delete\"")

    # Create acl policy canary_acl_in_policy_name
    # ----------------------------------------------------------    
    # Delete operation may return False, if the object did not exist in the first place
    netconf_comm.cmd_set_acl_policy__deny_src_ip(netconf_client, canary_acl_in_policy_name, physical_port_ip, operation = "operation=\"delete\"")
    # Create operation should always succeed.
    rv = netconf_comm.cmd_set_acl_policy__deny_src_ip(netconf_client, canary_acl_in_policy_name, physical_port_ip, operation = "")
    if rv == False :
        raise Exception ("Failed committing cmd_set_acl_policy__deny_src_ip")
    
    # Attach acl in policy canary_acl_in_policy_name to interface X_ETH_VALUE
    # -----------------------------------------------------------------        
    logging.info(f"Attach acl in policy {canary_acl_in_policy_name} to interface {X_ETH_VALUE}")
    rv = netconf_comm.cmd_set_attach_policy_acl_in_x_eth(netconf_client, X_ETH_VALUE, canary_acl_in_policy_name, operation="")
    if rv == False :
        raise Exception ("Failed committing cmd_set_attach_policy_acl_in_x_eth")

    # Initial test TC00 should always succeed
    assert True


# ***************************************************************************************
# Test Case #1 - ACL in
# ***************************************************************************************
def test_TC01_acl_in(ssh_client) :
    """
    Test deny on acl rule R1 :
        1. Read ACL counter value 
           (Using SNMP)
        2. Inject packet into bcm's port that will trigger the deny rule in ACL policy 
           (Using BCM Diagnostic shell)
        3. Read ACL counter value again, and assert that it incremented the value of packets injected 
           (Using SNMP)
    """
    # import packet_creator

    logging.info("test_TC01_acl_in")
    
    # Read globals from ini file
    constants = configparser.ConfigParser()
    constants.read('config.ini')

    phys_port_num = int(constants['TEST_SUITE_ACL']['PHYSICAL_PORT_NUM'])
    src_ip  = constants['TEST_SUITE_ACL']['SRC_IP_RULE_R1']
    dst_ip  = constants['TEST_SUITE_ACL']['DST_IP']
    dst_mac = constants['TEST_SUITE_ACL']['DST_MAC']
    num_of_tx = '5'
    _inject_frame_and_verify_counter(ssh_client, phys_port_num, src_ip, dst_ip, dst_mac, num_of_tx)


def test_TC02_acl_in(ssh_client) :
    """
    Test permit on acl default rule
    """
    logging.info("test_TC02_acl_in")
    
    # Read globals from ini file
    constants = configparser.ConfigParser()
    constants.read('config.ini')

    phys_port_num = int(constants['TEST_SUITE_ACL']['PHYSICAL_PORT_NUM'])
    src_ip  = constants['TEST_SUITE_ACL']['SRC_IP_RULE_DEFAULT']
    dst_ip  = constants['TEST_SUITE_ACL']['DST_IP']
    dst_mac = constants['TEST_SUITE_ACL']['DST_MAC']
    num_of_tx = '10'

    _inject_frame_and_verify_counter(ssh_client, phys_port_num, src_ip, dst_ip, dst_mac, num_of_tx)

