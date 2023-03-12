"""
Setup environment in DUT for starting the testing
"""
import paramiko

import logging
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
    Run remote sheel command
    """
    import socket
    try :
        # Execute a command on the remote server and get the output
        logging.info(f"Running \"{cmd_string}\" :")
        stdin, stdout, stderr = ssh_object.exec_command(cmd_string)
        logging.info(f"Output of \"{cmd_string}\" :")

    except paramiko.SSHException as e:
        # Handle SSH exception
        logging.error(f'SSH error: {e}')
    except socket.error as e:
        # Handle socket error
        logging.error(f'Network error: {e}')

# ***************************************************************************************
# Main function
# ***************************************************************************************
def create_directory_and_copy_files (host, workdir, copy_file_list):
    """
    Move testing files into directory in DUT.
    If already exists, first delete workdir directory.
    """
    # Connect to DUT using SSH client
    with paramiko.SSHClient() as ssh:
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        logging.info(f"Connecting to host {host}")
        ssh.connect(hostname=host, username="root", password="root")

        # Create an SFTP client
        with ssh.open_sftp() as sftp:   
            if _remote_exists(sftp, workdir) :
                logging.info(f"Removing working directory {workdir}")
                _run_remote_shell_cmd(ssh, f'rm -rf {workdir}')

            logging.info(f"create a new folder for workspace {workdir}")           
            sftp.mkdir(workdir)

            for file in copy_file_list :
                logging.info(f"Copying {file} to the {workdir}")
                sftp.put(file, workdir + "/" + file)

def activate_dut_test(host, server_cmd, client_path) :
    """
    Activate DUT test server by running script file uploaded by create_directory_and_copy_files()
    """
    # Connect to DUT using SSH client
    with paramiko.SSHClient() as ssh:
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        logging.info(f"Connecting to host {host}")
        ssh.connect(hostname=host, username="root", password="root")

        logging.info(f"Run server command in DUT: {server_cmd}")
        _run_remote_shell_cmd (ssh, server_cmd)

    logging.info(f"Run client command locally: {client_path}")
    import client
    logging.info("Waiting for 3 seconds for the server to come alive")
    import time
    time.sleep(3)
    client.send_cmd("test1")


if __name__ == "__main__" :
    # Test constants

    import configparser
    import os

    # Read globals from ini file
    constants = configparser.ConfigParser()
    constants.read('config.ini')
    HOST        = constants['COMM']['HOST']
    PORT        = int(constants['COMM']['TCP_PORT'])
    WORKDIR     = constants['DUT_ENV']['WORKDIR']
    LOG_FILE    = constants['DUT_ENV']['LOG_FILE']

    COPY_FILE_LIST = ["server.py", "monitor_logfile.py", "config.ini"]
    CLIENT_PATH = "./client.py"

    # Create test environment on DUT 
    create_directory_and_copy_files(HOST, WORKDIR, COPY_FILE_LIST)

    # Run operation
    server_cmd = f"cd {WORKDIR};python server.py &"
    activate_dut_test(HOST, server_cmd, CLIENT_PATH)