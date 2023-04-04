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

# ***************************************************************************************
# Helper functions
# ***************************************************************************************
def _run_remote_shell_cmd(ssh_client, cmd_string) :
    """
    Run remote shell command
    """
    import socket

    exit_status = None

    try :
        # Execute a command on the remote server and get the output
        logging.info(f"Running remote command:\n\"{cmd_string}\"")

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

def _run_local_shell_cmd(cmd_string) :
    """
    Run local shell command
    """

    import subprocess

    result = subprocess.run(cmd_string, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    rc = result.returncode
    output = result.stdout.decode()
    logging.debug(f"Return code: {rc}\nOutput:\n{output}")

    return rc, output

# ***************************************************************************************
# Fixtures functions
# ***************************************************************************************
@pytest.fixture(scope="module")
def ssh_client():
    """
    Connect to DUT using SSH client
    """
    logging.info("Fixture: ssh_client")
    import configparser
    import paramiko
    import cli_control

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
    client.connect(hostname=host_onl, username="root", password="root")

    logging.info(f"Opening connection to host_onl {host_onl}")
    client.connect(hostname=host_onl, username="root", password="root")
    yield client
    logging.info(f"Closing connection to host_onl {host_onl}")
    client.close()