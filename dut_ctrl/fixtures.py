"""
Fixture functions needed to run the tests
"""

import logging
logging.basicConfig(
                    format='%(asctime)s.%(msecs)03d [%(filename)s line %(lineno)d] %(levelname)-8s %(message)s',                       
                    level=logging.INFO,
                    datefmt='%H:%M:%S')
import pytest

# ***************************************************************************************
# Helper functions
# ***************************************************************************************
def run_remote_shell_cmd(ssh_client, cmd_string) :
    """
    Run remote shell command
    """
    import socket
    import paramiko

    exit_status = None

    try :
        # Execute a command on the remote server and get the output
        logging.info(f"Running remote command: \"{cmd_string}\"")

        ssh_stdin, ssh_stdout, ssh_stderr = ssh_client.exec_command(cmd_string)

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

def run_local_shell_cmd(cmd_string) :
    """
    Run local shell command
    """

    import subprocess

    logging.info(f"Running command: {cmd_string}")
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
        logging.info(f"Attempting to connect to {address}")
        try:
            ssh.connect(hostname=address, username="root", password="root")
            logging.info(f"Connected to {address}")
            ssh.close()
            return True
        except paramiko.AuthenticationException as e:
            logging.info(f"Authentication failed when connecting to {address}: {e}")
            return False
        except Exception as e:
            logging.info(f"Could not connect to {address}: {e}")
            return False

    while not _check_ssh_server(host_onl):
        logging.info(f"SSH server is still down, waited {sleep_counter * SLEEP_TIME_SECONDS} seconds for it to start...")
        time.sleep(SLEEP_TIME_SECONDS)
        sleep_counter += 1
        if (sleep_counter * SLEEP_TIME_SECONDS) > (BOOT_TIMEOUT_MINUTES*60) :
            raise Exception(f"Timeout expired, exceeded {BOOT_TIMEOUT_MINUTES} minutes")

    logging.info("SSH server is up!")
    return True

def _create_ssh_client():
    import configparser
    import paramiko
    import cli_control

    logging.info("_create_ssh_client")

    # Read globals from ini file
    constants = configparser.ConfigParser()
    constants.read('config.ini')
    host_onl = constants['COMM']['HOST_ONL']
    dut_num = constants['GENERAL']['DUT_NUM']

    # Reset the Managament interface 10.3.XX.10 (host_onl) by sending "dhclient ma1" in ONL CLI,
    # and CPM interface (10.3.XX.1) by sending ping to vrf management in the DUT CLI, using the serial server 
    cli_control.reset_mng_and_cpm_connections(dut_num)

    # Connecting over SSH and Managament interface 10.3.XX.10 (host_onl) to the device
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    logging.info(f"Opening connection to host_onl {host_onl}")
    client.connect(hostname=host_onl, username="root", password="root")

    return client
   
def copy_files_from_local_to_dut(dut_num, local_files_list, remote_dut_path):
    """
    Copy files into workdir in DUT.
    If workdir already exists, first delete it completly.
    Input : local_files_list - list of Strings
            remote_dut_path  - String
    Hidden assumption : That id_rsa.pub file has been created in DEV machine using ssh-keygen and copied to DUT using ssh-copy-id,
                        so that no password prompt is given 
    """
    logging.info(f"copy_files_from_local_to_dut")

    for file in local_files_list :
        command = f"scp {file} root@10.3.{dut_num[-2:]}.10:/vbox/a/local/bin"
        rc, output = run_local_shell_cmd(command)
        if rc != 0 :
            raise Exception(f"Failed copying modified startagent")
        else :
            logging.info((f"Succeeded in copying modified startagent"))

# ***************************************************************************************
# Fixtures functions
# ***************************************************************************************
@pytest.fixture(scope="module")
def ssh_client_scope_module():
    """
    Connect to DUT using SSH client with module fixture scope
    """
    logging.info("ssh_client_scope_module: Opening connection")
    client = _create_ssh_client()
    yield client
    logging.info(f"ssh_client_scope_module: Closing connection")
    client.close()

@pytest.fixture(scope="function")
def ssh_client_scope_function():
    """
    Connect to DUT using SSH client with function fixture scope
    """
    logging.info("ssh_client_scope_function: Opening connection")
    client = _create_ssh_client()
    yield client
    logging.info(f"ssh_client_scope_function: Closing connection")
    client.close()