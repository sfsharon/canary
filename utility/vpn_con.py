'''
Keep VPN connection open
'''
import pexpect
import sys

CMD = 'sudo /usr/bin/openfortivpn -c /home/sharonf/my.cfg'
EXPECT_TIMEOUT = 2

child = pexpect.spawn(CMD)
child.logfile = sys.stdout.buffer

i = child.expect (["Two-factor authentication token: ", 
                   "\[sudo\] password for sharonf: ",
                   pexpect.EOF, 
                   pexpect.TIMEOUT], timeout = EXPECT_TIMEOUT)
if i == 0:
    print("Two factor")
elif i == 1 :
    child.sendline("123456")    
    print ("Sent password")
    i = child.expect(["Two-factor authentication token: ", 
                      pexpect.EOF, 
                      pexpect.TIMEOUT], timeout = EXPECT_TIMEOUT)
    if i == 0 :
        print ("Need to send ctrl-c")
    elif i == 1:
        print ("EOF")
    elif i ==2 :
        print ("Timeout 2")
elif i == 2:
    print ("EOF")
elif i == 3:
    print ("TIMEOUT 1")
else:
    print ("Unrecognized")
