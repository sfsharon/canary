"""
Setup environment in DUT for starting the testing
"""

import paramiko

HOST = '10.3.10.10'
WORKDIR = "/root/workspace"
COPY_FILE_LIST = ["server.py", "monitor_logfile.py"]

# create an SSH client
with paramiko.SSHClient() as ssh:
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=HOST, username="root", password="root")

    # create an SFTP client
    with ssh.open_sftp() as sftp:

        # create a remote folder for workspace
        sftp.mkdir(WORKDIR)

        for file in COPY_FILE_LIST :
            # copy a local file to the remote folder
            sftp.put(file, WORKDIR + "/" + file)
