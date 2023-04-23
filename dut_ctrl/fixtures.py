"""
Fixture functions needed to run the tests
"""

import logging
logging.basicConfig(
                    format='%(asctime)s.%(msecs)03d [%(filename)s line %(lineno)d] %(levelname)-8s %(message)s',                       
                    level=logging.INFO,
                    datefmt='%H:%M:%S')
import pytest
import paramiko
from typing import Tuple

# ***************************************************************************************
# Helper functions
# ***************************************************************************************
def run_remote_shell_cmd(ssh_client: paramiko.SSHClient, cmd_string: str) -> Tuple[int, str] :
    """
    Run remote shell command
    """
    import socket
    import paramiko
    from cli_control import get_time

    exit_status = None
    stdout_str  = None

    try :
        # Execute a command on the remote server and get the output
        logging.info(f"{get_time()} Running remote command: \"{cmd_string}\"")

        ssh_stdin, ssh_stdout, ssh_stderr = ssh_client.exec_command(cmd_string)

        exit_status = ssh_stdout.channel.recv_exit_status()
        if exit_status == 0 :
            logging.info(f"{get_time()} Remote command succeeded")
        else :
            logging.error(f"{get_time()} Command failed with exit status: {exit_status}")

        stdout_str = [line for line in ssh_stdout]

    except paramiko.SSHException as e:
        # Handle SSH exception
        logging.error(f"{get_time()} SSH error: {e}")
    except socket.error as e:
        # Handle socket error
        logging.error(f"{get_time()} Network error: {e}")

    return exit_status, stdout_str

def run_local_shell_cmd(cmd_string) :
    """
    Run local shell command
    """
    import subprocess

    logging.debug(f"Running command: {cmd_string}")
    result = subprocess.run(cmd_string, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    rc = result.returncode
    output = result.stdout.decode()
    logging.debug(f"Return code: {rc}, Output: {output}")

    return rc, output

def wait_for_onl_after_reboot():
    """
    Poll DUT every 5 seconds, and test if SSH is available.
    """
    import time
    import paramiko
    import configparser
    from cli_control import get_time

    # Read globals from ini file
    constants = configparser.ConfigParser()
    constants.read('config.ini')
    host_onl = constants['COMM']['HOST_ONL']

    sleep_counter = 0
    SLEEP_TIME_SECONDS = 5
    BOOT_TIMEOUT_MINUTES = 14

    def _check_ssh_server(address):
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        logging.info(f"{get_time()} Attempting to connect to {address}")
        try:
            ssh.connect(hostname=address, username="root", password="root")
            logging.info(f"{get_time()} Connected to {address}")
            ssh.close()
            return True
        except paramiko.AuthenticationException as e:
            logging.info(f"{get_time()} Authentication failed when connecting to {address}: {e}")
            return False
        except Exception as e:
            logging.info(f"{get_time()} Could not connect to {address}: {e}")
            return False

    while not _check_ssh_server(host_onl):
        logging.info(f"{get_time()} SSH server is still down, waited {sleep_counter * SLEEP_TIME_SECONDS} seconds for it to start...")
        time.sleep(SLEEP_TIME_SECONDS)
        sleep_counter += 1
        if (sleep_counter * SLEEP_TIME_SECONDS) > (BOOT_TIMEOUT_MINUTES*60) :
            raise Exception(f"{get_time()} Timeout expired, exceeded {BOOT_TIMEOUT_MINUTES} minutes")

    logging.info(f"{get_time()} SSH server is up!")
    return True

def _create_ssh_client(is_reset_cpm_connection):
    import configparser
    import paramiko
    import cli_control

    logging.info("_create_ssh_client")

    # Read globals from ini file
    constants = configparser.ConfigParser()
    constants.read('config.ini')
    host_onl = constants['COMM']['HOST_ONL']
    dut_num = constants['GENERAL']['DUT_NUM']
    dut_type = constants['GENERAL']['DUT_TYPE']

    # Reset the Managament interface 10.3.XX.10 (host_onl) by sending "dhclient ma1" in ONL CLI,
    # and CPM interface (10.3.XX.1) by sending ping to vrf management in the DUT CLI, using the serial server 
    cli_control.reset_dut_connections(device_number = dut_num, device_type = dut_type, is_reset_cpm_connection = is_reset_cpm_connection)

    # Connecting over SSH and Managament interface 10.3.XX.10 (host_onl) to the device
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    logging.info(f"Opening connection to host_onl {host_onl}")
    client.connect(hostname=host_onl, username="root", password="root")

    return client
   
def copy_files_from_local_to_dut(dut_num, local_files_list, remote_dut_path):
    """
    Copy files into remote_dut_path in DUT.
    Input : local_files_list - list of Strings
            remote_dut_path  - String
    Hidden assumption : That id_rsa.pub file has been created in DEV machine using ssh-keygen and copied to DUT using ssh-copy-id,
                        so that no password prompt is given 
    """
    from cli_control import get_time
    logging.info(f"{get_time()} copy_files_from_local_to_dut")

    for file in local_files_list :
        command = f"scp {file} root@10.3.{dut_num[-2:]}.10:{remote_dut_path}"
        rc, output = run_local_shell_cmd(command)
        if rc != 0 :
            raise Exception(f"Failed copying {file} to {remote_dut_path}")
        else :
            logging.info((f"Succeeded in copying {file} to {remote_dut_path}"))

def copy_files_from_dut_to_local(dut_num: str, remote_dir: str, remote_files_list, local_path):
    """
    Copy files from remote_files_list in DUT to local_path.
    Input : remote_dir - Remote directory
            remote_files_list - list of Strings
            local_path  - String
    Hidden assumption : That id_rsa.pub file has been created in DEV machine using ssh-keygen and copied to DUT using ssh-copy-id,
                        so that no password prompt is given 
    """
    import os
    from cli_control import get_time
    import time

    logging.debug(f"{get_time()} copy_files_from_local_to_dut")
    
    num_of_retries = 5
    SLEEP_BETWEEN_RETRIES_SECONDS = 60
    full_file_path = None
    is_finished = False

    while num_of_retries > 0 and is_finished == False:
        for index, file in enumerate(remote_files_list) :
            full_file_path = os.path.join (remote_dir, file)
            command = f"scp root@10.3.{dut_num[-2:]}.10:{full_file_path} {local_path}"
            rc, output = run_local_shell_cmd(command)
            if rc != 0 :
                num_of_retries -= 1
                logging.error((f"{get_time()} Error in copying {full_file_path} to {local_path}. RC: {rc}, Output: {output}. Retries left: {num_of_retries}"))
                time.sleep(SLEEP_BETWEEN_RETRIES_SECONDS)
                break    
            else :
                logging.debug((f"{get_time()} Succeeded in copying {full_file_path} to {local_path}"))
            
            if index == len(remote_files_list) - 1 :
                is_finished = True

    if num_of_retries == 0:
        raise Exception(f"{get_time()} Failure copying {remote_files_list} to {local_path}")

# ***************************************************************************************
# Fixtures functions
# ***************************************************************************************
@pytest.fixture(scope="session")
def ssh_client():
    """
    Connect to DUT using SSH client
    """
    from cli_control import get_time

    logging.info(f"{get_time()} ssh_client: Opening connection")
    client = _create_ssh_client(is_reset_cpm_connection = True)
    yield client
    logging.info(f"{get_time()} ssh_client: Closing connection")
    client.close()

@pytest.fixture(scope="session")
def ssh_client__no_cpm_conn_reset():
    """
    Connect to DUT using SSH client, without reseting CPM connection (with ping VRF management DUT CLI command).
    This option is meant for ssh connection to ONL only, where waiting for VRF ping through the CLI would require
    the swapp to initialize, which is no necessary in the test_init modules.
    """
    from cli_control import get_time

    logging.info(f"{get_time()} ssh_client: Opening connection")
    client = _create_ssh_client(is_reset_cpm_connection = False)
    yield client
    logging.info(f"{get_time()} ssh_client: Closing connection")
    client.close()

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
