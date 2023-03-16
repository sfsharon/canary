"""
Setup environment in DUT for starting the testing
"""
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
# Main function
# ***************************************************************************************
def create_workdir_and_copy_files (host, workdir, copy_file_list):
    """
    Move testing files into workdir in DUT.
    If workdir already exists, first delete it completly.
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

def activate_dut_test_1(host, workdir) :
    """
    Run test 1 on DUT :
        1. Configure ACL policy on port 23 
           (Using Netconf)
        2. Read ACL counter value 
           (Using SNMP)
        3. Inject packet into bcm's port that will trigger the deny rule in ACL policy 
           (Using BCM Diagnostic shell)
        4. Read ACL counter value, and assert that it incremented the value of packets injected 
           (Using SNMP)
    """
    port = '24' # Value 24 referes to port x-eth 0/0/23

    rv = None

    acl_in_counter_prev = snmp_comm.acl_in_rule_r1_counter(int(port) - 1)

    # Connect to DUT using SSH client
    with paramiko.SSHClient() as ssh:
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        logging.info(f"Connecting to host {host}")
        ssh.connect(hostname=host, username="root", password="root")

        frame = '0x1e94a004171a00155d6929ba08004500001400010000400066b70a1800020a180001'
        num_of_tx = '3'
        command = f"cd {workdir};python tx_into_bcm.py {frame} {num_of_tx} {port}"

        # Run remote command in DUT
        rv = _run_remote_shell_cmd (ssh, command)

    # Giving the counters a chance to update. 
    # Probably some periodic thread in DUT that updates counters for SNMP
    for i in range(30) :
        import time
        logging.info(f"Waiting {i} seconds out of 30")
        time.sleep(1)

    acl_in_counter_curr = snmp_comm.acl_in_rule_r1_counter(int(port) - 1)
    logging.info(f"Prev acl in counter: {acl_in_counter_prev}\nCurr acl in counter: {acl_in_counter_curr}")

    if rv == 0:
        logging.info("Test 1 finished successfully")
    else :
        logging.info(f"Test 1 failed with return value {rv}")

if __name__ == "__main__" :
    import configparser

    # Read globals from ini file
    constants = configparser.ConfigParser()
    constants.read('config.ini')
    HOST        = constants['COMM']['HOST_ONL']
    WORKDIR     = constants['DUT_ENV']['WORKDIR']
    LOG_FILE    = constants['DUT_ENV']['LOG_FILE']

    COPY_FILE_LIST = ["tx_into_bcm.py", "monitor_logfile.py", "config.ini"]

    # Create test environment on DUT 
    create_workdir_and_copy_files(HOST, WORKDIR, COPY_FILE_LIST)

    # Run operation
    activate_dut_test_1(HOST, WORKDIR)