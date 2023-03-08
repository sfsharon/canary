"""
Setup environment in DUT for starting the testing
"""
import paramiko

import logging
logging.basicConfig(
                    format='%(asctime)s.%(msecs)03d [%(filename)s line %(lineno)d] %(levelname)-8s %(message)s',                       
                    level=logging.INFO,
                    datefmt='%H:%M:%S')



def create_directory_and_copy_files (host, workdir, copy_file_list):
    """
    Move testing files into directory in DUT.
    If already exists, first delete directory.
    """
    # create an SSH client
    with paramiko.SSHClient() as ssh:
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        logging.info(f"Connecting to host {host}")
        ssh.connect(hostname=host, username="root", password="root")

        # create an SFTP client
        with ssh.open_sftp() as sftp:

            # define a function to check if a remote path exists
            def rexists(sftp, path):
                try:
                    sftp.stat(path)
                    return True
                except IOError:
                    return False

            if rexists(sftp, workdir) :
                logging.warning(f"Removing working directory {workdir}")
                sftp.remove(workdir)

            logging.info(f"create a new folder for workspace {workdir}")           
            sftp.mkdir(workdir)

            for file in copy_file_list :
                logging.info(f"Copying {file} to the {workdir}")
                sftp.put(file, workdir + "/" + file)

if __name__ == "__main__" :
    HOST = '10.3.10.10'
    WORKDIR = "/root/workspace"
    COPY_FILE_LIST = ["server.py", "monitor_logfile.py"]

    create_directory_and_copy_files(HOST, WORKDIR, COPY_FILE_LIST)