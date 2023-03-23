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
        logging.info(f"Running remote command\n\"{cmd_string}\" :")

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
def test_TC00_Setup_Environment(netconf_client):
    """
    Setup configured policy  
    """
    import netconf_comm

    logging.info("test_TC00_Setup_Environment")

   # Read globals from ini file
    constants = configparser.ConfigParser()
    constants.read('config.ini')
    phys_port_ip = constants['TEST_SUITE_ACL']['SRC_IP']
 
    # Remove Policy if exists, and then configure a new one 
    netconf_comm.cmd_set_acl_policy__deny_src_ip(netconf_client, phys_port_ip, operation = "operation=\"delete\"")
    netconf_comm.cmd_set_acl_policy__deny_src_ip(netconf_client, phys_port_ip, operation = "")
    assert 1==1


# ***************************************************************************************
# Test Case #1 - ACL in
# ***************************************************************************************
def test_TC01_acl_in(ssh_client) :
    """
    Run test #1 on DUT :
        1. Configure ACL policy on port 23 
           (Using Netconf)
        2. Read ACL counter value 
           (Using SNMP)
        3. Inject packet into bcm's port that will trigger the deny rule in ACL policy 
           (Using BCM Diagnostic shell)
        4. Read ACL counter value, and assert that it incremented the value of packets injected 
           (Using SNMP)
    """
    import packet_creator

    logging.info("test_TC01_acl_in")
    
    # Read globals from ini file
    constants = configparser.ConfigParser()
    constants.read('config.ini')
    workdir                  = constants['DUT_ENV']['WORKDIR']
    snmp_counter_update_time = int(constants['SNMP']['COUNTER_UPDATE_TIME'])
    phys_port_num = int(constants['TEST_SUITE_ACL']['PHYSICAL_PORT_NUM'])
    src_ip  = constants['TEST_SUITE_ACL']['SRC_IP']
    dst_ip  = constants['TEST_SUITE_ACL']['DST_IP']

    # Test parameters
    bcm_port_num = str(phys_port_num + 1) # BCM port number is 1 larger then app values (x-eth 0/0/23 is BCM port 24)
    num_of_tx = '3'
    
    # Generate the String hex representation of the frame, needed for transmission into the SDK :
    frame = packet_creator.create_frame(src_ip = '1.2.3.4', dst_ip = '5.5.5.5')
    # frame = '0x1e94a004171a00155d6929ba08004500001400010000400066b70a1800020a180001'
    # frame translates to :
    # >>> Ether(frame_byte)
    # <Ether  dst=1e:94:a0:04:17:1a src=00:15:5d:69:29:ba type=IPv4 |
    # <IP  version=4 ihl=5 tos=0x0 len=20 id=1 flags= frag=0 ttl=64 proto=hopopt chksum=0x66b7 src=10.24.0.2 dst=10.24.0.1 |>>

    # Read ACL counter value, and save it
    acl_in_counter_prev = int(snmp_comm.acl_in_rule_r1_counter(phys_port_num))
    
    # Run remote command in DUT
    command = f"cd {workdir};python tx_into_bcm.py {frame} {num_of_tx} {bcm_port_num}"
    rv = _run_remote_shell_cmd (ssh_client, command)

    if rv != 0 :
        raise Exception(f"Test #1 failed with rv {rv}, when running remote command \"{command}\"")
        
    # Giving the SNMP counters a chance to update. 
    # Probably some periodic thread in DUT that updates counters for SNMP
    for i in range(snmp_counter_update_time) :
        import time
        if i % 10 == 0 :
            logging.info(f"Waited {i} seconds out of {snmp_counter_update_time} for SNMP to update DUT counters")
        time.sleep(1)

    # Verify counters incremented correctly
    num_of_tx = int(num_of_tx)
    acl_in_counter_curr = int(snmp_comm.acl_in_rule_r1_counter(phys_port_num))

    assert  ((acl_in_counter_curr - acl_in_counter_prev) == num_of_tx), \
             f"Test 1 failed: Prev acl in counter: {acl_in_counter_prev}, Curr acl in counter: {acl_in_counter_curr}"

def test_TC02(setup_logging):
    logging.info("Place holder for ctrl-plane ACL test")