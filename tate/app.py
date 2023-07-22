"""
FLask implementation for querying the Tate database. 
Using raw ssh command because paramiko and pymysql cannot support the old ssh authentication on MySql "server cmp-dt-srv2"
"""
from flask import Flask

import logging
logging.basicConfig(
                    format='%(asctime)s.%(msecs)03d [%(filename)s line %(lineno)d] %(levelname)-8s %(message)s',                       
                    level=logging.INFO,
                    datefmt='%H:%M:%S')

def run_local_shell_cmd(cmd_string) :
    """
    Run local shell command
    """
    import subprocess

    logging.info(f"Running command: {cmd_string}")
    result = subprocess.run(cmd_string, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    rc = result.returncode
    output = result.stdout.decode()
    logging.info(f"Return code: {rc}, Output:\n------------------------------------------------------------------------------------\n {output}")

    return rc, output

app = Flask(__name__)

DEV_MACHINE_IP   = '172.30.16.107'
MYSQL_MACHINE_IP = '192.168.20.53'

@app.route('/')
def hello_world():
    query = "select  testbed,sw_ver,duration,started,pass,fail from jobs where testbed is not null limit 10;" 
    cmd = f"ssh -o KexAlgorithms=diffie-hellman-group14-sha1 root@{MYSQL_MACHINE_IP} 'mysql -D tate -e \"{query}\"'"
    rc, output = run_local_shell_cmd(cmd)
    return output

if __name__ == '__main__':
    # Run the Flask app
    app.run(host=DEV_MACHINE_IP, port=5000)
