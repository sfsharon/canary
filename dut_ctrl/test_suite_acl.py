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
def ssh_client():
    """
    Connect to DUT using SSH client
    """
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
# Test Case #1
# ***************************************************************************************
def test_TC01_acl_in(ssh_client, setup_dut) :
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
    # Read globals from ini file
    constants = configparser.ConfigParser()
    constants.read('config.ini')
    workdir                  = constants['DUT_ENV']['WORKDIR']
    snmp_counter_update_time = int(constants['SNMP']['COUNTER_UPDATE_TIME'])

    # Test parameters
    port = '24' # Value 24 referes to port x-eth 0/0/23
    num_of_tx = '3'
    frame = '0x1e94a004171a00155d6929ba08004500001400010000400066b70a1800020a180001'

    # Read ACL counter value, and save it
    acl_in_counter_prev = int(snmp_comm.acl_in_rule_r1_counter(int(port) - 1))
    
    # Run remote command in DUT
    command = f"cd {workdir};python tx_into_bcm.py {frame} {num_of_tx} {port}"
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
    acl_in_counter_curr = int(snmp_comm.acl_in_rule_r1_counter(int(port) - 1))

    assert  ((acl_in_counter_curr - acl_in_counter_prev) == num_of_tx), \
             f"Test 1 failed: Prev acl in counter: {acl_in_counter_prev}, Curr acl in counter: {acl_in_counter_curr}"

def test_TC02(setup_logging):
    logging.info("Place holder for ctrl-plane ACL test")