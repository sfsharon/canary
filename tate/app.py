"""
FLask implementation for querying the Tate database. 
Using raw ssh command because paramiko and pymysql cannot support the old ssh authentication on MySql "server cmp-dt-srv2"
"""
from flask import Flask, render_template, request

import logging
logging.basicConfig(
                    format='%(asctime)s.%(msecs)03d [%(filename)s line %(lineno)d] %(levelname)-8s %(message)s',                       
                    level=logging.INFO,
                    datefmt='%H:%M:%S')

# ***************************************************************************************
# Helper functions
# ***************************************************************************************
def _run_local_shell_cmd(cmd_string) :
    """
    Run local shell command
    """
    import subprocess

    logging.debug(f"Running command: {cmd_string}")
    result = subprocess.run(cmd_string, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    rc = result.returncode
    output = result.stdout.decode()
    logging.debug(f"Return code: {rc}, Output:\n------------------------------------------------------------------------------------\n {output}")

    return rc, output

from typing import Dict, List
def _mysql_output_to_map(input : str) -> List[Dict [str, str]] :
    """
    Translate the string received from MySql to a map of {key:value}.
    The keys are the first line received from MySql. each line is separated by '\n',
    and each entry is separatred by '\t'. 
    Hidden assumption is that the number of key values is the same for the number of columns in each entry.

    Output Example :
    data = [{'Name': 'John', 'Age': 30},
            {'Name': 'Jane', 'Age': 25},
            {'Name': 'Bob', 'Age': 40}]
    """
    lines = input.split('\n')
    keys = lines[0].split('\t')
    table_lines = lines[1:]
    output = []
    for line in table_lines :
        entry = {}
        col_values = line.split('\t')
        for index, val in enumerate(col_values):
            # Beautifying values 
            if val == "NULL" : val = " "
            if keys[index] == "suite" :
                val = val.split('/')[-1]
            # Saving values
            entry[keys[index]] = val
        output.append(entry)
    return output

# ***************************************************************************************
# Main Application
# ***************************************************************************************
DEV_MACHINE_IP   = 'localhost'  # '172.30.16.107'
MYSQL_MACHINE_IP = '192.168.20.53'

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index(): 
    data_parsed = []

    if request.method == 'POST' :

        # Build SQL condition string 
        conditions_list = []
        conditions = ""
        # Get input from user
            # job_id
        job_id    = request.form['job_id']
        if len(job_id) > 0 :
            conditions_list.append(f"job_id = {job_id}")
            # submitter
        submitter = request.form['submitter']
        if len(submitter) > 0 :
            conditions_list.append(r"submitter LIKE \"" + f"%{submitter}%" + r"\"")
            # suite
        suite     = request.form['suite']
        if len(suite) > 0 :
            conditions_list.append(r"suite LIKE \"" + f"%{suite}%" + r"\"")

            # sw_ver
        sw_ver     = request.form['sw_ver']
        if len(sw_ver) > 0 :
            conditions_list.append(r"sw_ver LIKE \"" + f"%{sw_ver}%" + r"\"")

            # branch
        # branch     = request.form['branch']
        # if len(branch) > 0 :
        #     conditions_list.append(r"branch LIKE \"" + f"%{branch}%" + r"\"")

            # testbed
        testbed     = request.form['testbed']
        if len(testbed) > 0 and testbed != "any":
            conditions_list.append(r"testbed LIKE \"" + f"%{testbed}%" + r"\"")

            # age
        age     = request.form['age']
        if len(age) > 0 and age != "any":
            conditions_list.append(f"started >= DATE_SUB(CURDATE(), INTERVAL {age})")

        # Combine conditions with AND operator
        if len(conditions_list) > 0 :
            for i, val in enumerate(conditions_list):
                if   i == 0 : conditions = val
                elif i == len(conditions_list) : conditions += val
                else :  conditions += " AND " + val

        if len(conditions) > 0 :
            # Build SQL query
            col_names  = "job_id, suite, tcnum, submitter, sw_ver, branch, started, finished, duration, pass, warning, fail, abort, testbed" 
            # conditions  = "testbed is not null limit 5"
            query      = f"SELECT {col_names} FROM jobs WHERE ({conditions});" 

            # Build and send SSH command
            cmd = f"ssh -o KexAlgorithms=diffie-hellman-group14-sha1 root@{MYSQL_MACHINE_IP} 'mysql -D tate -e \"{query}\"'"
            rc, output_mysql = _run_local_shell_cmd(cmd)

            if rc == 0 :
                logging.info(f"SQL Query '{query}' succeeded")
                # Parse response from MySql server
                data_parsed = _mysql_output_to_map(output_mysql)    
            else :
                logging.error(f"SQL Query '{query}' return error code {rc}")

    # Render HTML
    output = render_template("index.html", data=data_parsed)
    return output

if __name__ == "__main__":
    """
    * For sample query :
        'select  testbed,sw_ver,duration,started,pass,fail from jobs where testbed is not null limit 10;'
    * Sample Output : 
        'testbed\tsw_ver\tduration\tstarted\tpass\tfail\nREG1-pc45\tNULL\t900\t2010-11-20 12:52:07\t2\t0\nREG1-pc45\tNULL\t0\t2010-11-20 13:14:00\t0\t0\nREG1-pc45\tNULL\t608\t2010-11-20 13:27:25\t3\t0\nREG2-pc46\tNULL\t625\t2010-11-20 13:27:26\t3\t0\nREG3-pc47\tNULL\t710\t2010-11-20 13:27:27\t3\t0\nREG4-pc13\tNULL\t615\t2010-11-20 13:27:28\t3\t0\nREG1-pc45\tNULL\t652\t2010-11-20 14:00:13\t3\t0\nREG1-pc45\tNULL\t657\t2010-11-20 14:19:16\t3\t0\nREG2-pc46\tNULL\t642\t2010-11-20 14:19:37\t3\t0\nREG3-pc47\tNULL\t725\t2010-11-20 14:19:48\t3\t0\n'
    * Formatted Sample output :
        testbed     sw_ver  duration started                pass fail
        REG1-pc45	NULL	900	     2010-11-20 12:52:07	2	 0
        REG1-pc45	NULL	0	     2010-11-20 13:14:00	0	 0
        REG1-pc45	NULL	608	     2010-11-20 13:27:25	3	 0
    """
    # Operation program
    app.run(debug=False, host=DEV_MACHINE_IP)
