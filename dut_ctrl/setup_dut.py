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
        stdin, stdout, stderr = ssh_object.exec_command(cmd_string)
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
    # create an SSH client
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

if __name__ == "__main__" :
    # Test constants
    HOST = '10.3.10.10'
    WORKDIR = "/root/workspace"
    COPY_FILE_LIST = ["server.py", "monitor_logfile.py"]

    # Run operation
    create_directory_and_copy_files(HOST, WORKDIR, COPY_FILE_LIST)