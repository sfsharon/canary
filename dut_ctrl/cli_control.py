"""
Controling the DUT CLI using pexpect.
POC - Getting system status
"""

import logging
logging.basicConfig(
                    format='%(asctime)s.%(msecs)03d [%(filename)s line %(lineno)d] %(levelname)-8s %(message)s', 
                    level=logging.INFO,
                    datefmt='%H:%M:%S')

import pexpect

# SSH into the machine
logging.info("1. pexpect.spawn")
child = pexpect.spawn('ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no 10.3.10.1 -l admin')

# Wait for the password prompt and enter the password
logging.info("expect password ")
child.expect('password:')


logging.info("2. sendline admin")
child.sendline('admin')


logging.info("Expect R3010")
child.expect('.*R3010.*')

# Send a command to the machine
logging.info("3. show sys mod")
child.sendline('show sys mod')

logging.info("Expect BOX/SLOT")
child.expect('.*BOX/SLOT.*')

# Wait for the command to complete and print the output
logging.info("END OF SCRIPT")
print(child.after.decode('utf-8'))

