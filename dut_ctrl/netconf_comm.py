"""
Implement Netconf communication (get and set configuration) for DUT
"""

import sys

import paramiko

import base64
import socket
from xml.dom import Node

import logging
logging.basicConfig(
                    format='%(asctime)s.%(msecs)03d [%(filename)s line %(lineno)d] %(levelname)-8s %(message)s',                       
                    level=logging.INFO,
                    datefmt='%H:%M:%S')


bufsiz = 16384

nc_ns = 'urn:ietf:params:xml:ns:netconf:base:1.0'

base_1_0 = 'urn:ietf:params:netconf:base:1.0'
base_1_1 = 'urn:ietf:params:netconf:base:1.1'

# RFC 4742
FRAMING_1_0 = 0
# the new framing in 4742bis
FRAMING_1_1 = 1


class MyNetconf(object):
    def __init__(self, hostname, port, username, password,
                 publicKey, publicKeyType,
                 privateKeyFile='', privateKeyType=''):
        self.buf = b""
        self.framing = FRAMING_1_0
        self.eom_found = False
        self.trace = False
        self.hostname = str(hostname)
        self.port = int(port)
        self.privateKeyFile = privateKeyFile
        self.privateKeyType =  privateKeyType
        self.publicKey  = publicKey
        self.publicKeyType =  publicKeyType
        self.password  = password
        self.username = username
        self.saved = ""

    def connect(self):
        logging.info(f"Connecting to {self.hostname}/{self.port}")
        sock = create_connection(self.hostname, self.port)
        
        self.ssh = paramiko.Transport(sock)
                
        if self.publicKeyType == 'rsa':
            agent_public_key = paramiko.RSAKey(
                data=base64.decodestring(self.publicKey))
        elif self.publicKeyType == 'dss':
            agent_public_key = paramiko.DSSKey(
                data=base64.decodestring(self.publicKey))
        else:
            agent_public_key = None
                    
        if not self.privateKeyFile == '':
            if self.privateKeyType == "rsa":
                user_private_key = paramiko.RSAKey.from_private_key_file(self.privateKeyFile)
            #elif self.privateKeyType == "dss":
            else:
                user_private_key = paramiko.DSSKey.from_private_key_file(self.privateKeyFile)

            try:
                self.ssh.connect(hostkey=agent_public_key,
                                 username=self.username,
                                 pkey=user_private_key)
            except paramiko.AuthenticationException:
                print("Authentication failed.")
                sys.exit(1)

        else:
            try:
                self.ssh.connect(hostkey=agent_public_key,
                                 username=self.username,
                                 password=self.password)
            except paramiko.AuthenticationException:
                print("Authentication failed.")
                sys.exit(1)

        self.chan = self.ssh.open_session()
        self.chan.invoke_subsystem("netconf")

    def _send(self, buf):
        try:
            if self.saved:
                buf = self.saved + buf
            # sending too little data in each SSH packet makes the
            # transfer slow.
            # paramiko still has  bug (?) where it doensn't send a full
            # SSH message, but keeps 64 bytes.  so we will send MAX-64, 64,
            # MAX-64, 64, ... instead of MAX all the time.
            if len(buf) < bufsiz:
                self.saved = buf
            else:
                self.chan.sendall(buf[:bufsiz])
                self.saved = buf[bufsiz:]
        except socket.error as x:
            print('socket error:', str(x))

    def _send_eom(self):
        try:
            self.chan.sendall(self.saved + self._get_eom())
            self.saved = ""
        except socket.error as x:
            self.saved = ""
            print('socket error:', str(x))

    def _flush(self):
        try:
            self.chan.sendall(self.saved)
            self.saved = ""
        except socket.error as x:
            self.saved = ""
            print('socket error:', str(x))


    def _set_timeout(self, timeout=None):
        self.chan.settimeout(timeout)
    
    def _recv(self, bufsiz):
        s = self.chan.recv(bufsiz)
        if self.trace:
            sys.stdout.write(s)
            sys.stdout.flush()
        return s

    def send(self, request):
        if self.framing == FRAMING_1_1:
            self._send('\n#%d\n' % len(request) + request)
        else:
            self._send(request)

    def send_msg(self, request):
        self.send(request)
        self._send_eom()

    def send_eom(self):
        self._send_eom()

    def _get_eom(self):
        if self.framing == FRAMING_1_0:
            return ']]>]]>'
        elif self.framing == FRAMING_1_1:
            return '\n##\n'
        else:
            return ''

    def recv_chunk(self, timeout=None):
        """
        ret: (-2, bytes) on framing error
             (-1, bytes) on socket EOF
             (0, "") on EOM
             (1, chunk-data) on data
        """
        self._set_timeout(timeout)
        if self.framing == FRAMING_1_0:
            if self.eom_found:
                self.eom_found = False
                return (0, b"")
            bytes = self.buf
            self.buf = b""
            while len(bytes) < 6:
                x = self._recv(bufsiz)
                if x == b"":
                    return (-1, bytes)
                bytes += x
            idx = bytes.find(b"]]>]]>")
            if idx > -1:
                # eom marker found; store rest in buf
                self.eom_found = True
                self.buf = bytes[idx+6:]
                return (1, bytes[:idx])
            else:
                # no eom marker found, keep the last 5 bytes
                # (might contain parts of the eom marker)
                self.buf = bytes[-5:]
                return (1, bytes[:-5])
        else:
            # new framing
            bytes = self.buf
            self.buf = b""
            # make sure we have at least 4 bytes; LF HASH INT/HASH LF
            while len(bytes) < 4:
                x = self._recv(bufsiz)
                if x == b"":
                    # error, return what we have
                    return (-1, bytes)
                bytes += x
            # check the first two bytes
            if bytes[0:2] != b"\n#":
                # framing error
                return (-2, bytes)
            # read the chunk size
            sz = -1
            while sz == -1:
                # find the terminating LF
                idx = bytes.find(b"\n", 2)
                if idx > 12:
                    # framing error - too large integer or not correct
                    # chunk size specification
                    return (-2, bytes)
                if idx > -1:
                    # newline found, scan for number of bytes to read
                    try:
                        sz = int(bytes[2:idx])
                        if sz < 1 or sz > 4294967295:
                            # framing error - range error
                            return (-2, bytes)
                    except:
                        if bytes[2:idx] == b"#":
                            # EOM
                            self.buf = bytes[idx+1:]
                            return (0, b"")
                        # framing error - not an integer, and not EOM
                        return (-2, bytes)
                    # skip the chunk size.  the while loop is now done
                    bytes = bytes[idx+1:]
                else:
                    # terminating LF not found, read more
                    x = self._recv(bufsiz)
                    if x == b"":
                        # error, return what we have
                        return (-1, bytes)
                    bytes += x
            # read the chunk data
            while len(bytes) < sz:
                x = self._recv(bufsiz)
                if x == b"":
                    return (-1, bytes)
                bytes += x
            # save rest of data
            self.buf = bytes[sz:]
            return (1, bytes[:sz])

    def recv_msg(self, timeout=None):
        msg = b""
        while True:
            (code, bytes) = self.recv_chunk(timeout)
            if code == 1:
                msg += bytes
            elif code == 0:
                return msg
            else:
                # error
                return msg + bytes
    
    def close(self):
        self.ssh.close()
        return True

# ***************************************************************************************
# Netconf Helper functions
# ***************************************************************************************

def create_connection(host, port):
    """
    sort-of socket.create_connection() (new in 2.6)
    """
    sock = None

    for res in socket.getaddrinfo(host, port,
                                  socket.AF_UNSPEC, socket.SOCK_STREAM):
        af, socktype, proto, canonname, sa = res
        try:
            sock = socket.socket(af, socktype, proto)
        except socket.error as xxx_todo_changeme:
            (code, msg) = xxx_todo_changeme.args
            sock = None
            continue
        try:
            sock.connect(sa)
        except socket.error as xxx_todo_changeme1:
            (code, msg) = xxx_todo_changeme1.args
            sock.close()
            sock = None
            continue
        break
    if sock is None:
        print("Failed to connect to %s: %s" % (host, msg))
        sys.exit(1)
    return sock

def write_fd(fd,data):
  try:
    fd.write(data)
  except:
    print("PRINTING DATA")
    print(data)
    sys.stderr.write("1 Problem with xmllint executable. Is it in PATH?\n")
    sys.exit(1)

def hello_msg(versions):
    s = '''<?xml version="1.0" encoding="UTF-8"?>
           <hello xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
           <capabilities>
        '''
    if '1.0' in versions:
        s += '    <capability>%s</capability>\n' % base_1_0
    if '1.1' in versions:
        s += '    <capability>%s</capability>\n' % base_1_1
    s += '''
    </capabilities>
</hello>'''
    return s

def close_msg():
    return '''<?xml version="1.0" encoding="UTF-8"?>
                <rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="0">
                <close-session/>
                </rpc>'''

def get_msg(cmd, db, xpath, with_defaults, with_inactive):
    if xpath == "":
        fstr = ""
    else:
        if "'" in xpath:
            fstr = "<filter type='xpath' select=\"%s\"/>" % xpath
        else:
            fstr = "<filter type='xpath' select='%s'/>" % xpath

    if with_defaults in ("explicit", "trim", "report-all", "report-all-tagged"):
        delem = "<with-defaults xmlns='urn:ietf:params:xml:ns:yang:ietf-netconf-with-defaults'>%s</with-defaults>" % with_defaults
    else:
        delem = ""

    if with_inactive:
        welem = "<with-inactive xmlns='http://tail-f.com/ns/netconf/inactive/1.0'/>"
    else:
        welem = ""

    if cmd == "get-config":
        op = "<get-config><source><%s/></source>%s%s%s</get-config>" % \
             (db, fstr, delem, welem)
    else:
        op = "<get>%s%s%s</get>" % (fstr, delem, welem)

    # deprecated tail-f with-defaults attribute in <rpc>
    if with_defaults in ("true", "false"):
        dattr = " with-defaults=\"%s\"" % with_defaults
    else:
        dattr = ""

    return '''<?xml version="1.0" encoding="UTF-8"?>
                <rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0"%s message-id="1">  
                    %s
                </rpc>''' % (dattr, op)

def get_config_opt(option, opt, value, parser):
    if len(parser.rargs) == 0:
        parser.values.ensure_value("getConfig", "default")
    elif parser.rargs[0].startswith("-"):
        parser.values.ensure_value("getConfig", "default")
    else:
        parser.values.ensure_value("getConfig", parser.rargs[0])
        del parser.rargs[0]

def opt_xpath(option, opt_str, value, parser):
    assert value is None
    done = 0
    value = ""
    rargs = parser.rargs
    while rargs:
        arg = rargs[0]
        # Stop if we hit an arg like "--foo", "-a", "-fx", "--file=f" etc.
        if ((arg[:2] == "--" and len(arg) > 2) or
            (arg[:1] == "-" and len(arg) > 1 and arg[1] != "-")):
            break
        else:
            value = value + " " + arg
            del rargs[0]
    setattr(parser.values, option.dest, value)

def kill_session_msg(id):
    return '''<?xml version="1.0" encoding="UTF-8"?>
                <rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="1">
                    <kill-session><session-id>%s</session-id></kill-session>
                </rpc>''' % id
    
def discard_changes_msg():
    return '''<?xml version="1.0" encoding="UTF-8"?>
                <rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="1">
                    <discard-changes/>
                </rpc>'''

def commit_msg():
    return '''<?xml version="1.0" encoding="UTF-8"?>
                <rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="1">
                    <commit/>
                </rpc>'''

def validate_msg(db):
    return '''<?xml version="1.0" encoding="UTF-8"?>
                <rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="1">
                    <validate><source><%s/></source></validate>
                </rpc>''' % db

def copy_running_to_startup_msg():
    return '''<?xml version="1.0" encoding="UTF-8"?>
                <rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="1">
                    <copy-config>
                    <target>
                        <startup/>
                    </target>
                    <source>
                        <running/>
                    </source>
                    </copy-config>
                </rpc>'''

def get_schema_msg(identifier):
    return '''<?xml version="1.0" encoding="UTF-8"?>
                <rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="1">
                    <get-schema xmlns="urn:ietf:params:xml:ns:yang:ietf-netconf-monitoring">
                    <identifier>%s</identifier>
                    </get-schema>
                </rpc>''' % identifier
    
def create_subscription_msg(stream, xpath):
    if xpath == "":
        fstr = ""
    else:
        if "'" in xpath:
            fstr = "<filter type='xpath' select=\"%s\"/>" % xpath
        else:
            fstr = "<filter type='xpath' select='%s'/>" % xpath
    return '''<?xml version="1.0" encoding="UTF-8"?>
                <rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="1">
                    <create-subscription xmlns="urn:ietf:params:xml:ns:netconf:notification:1.0">
                        <stream>%s</stream>
                        %s
                    </create-subscription>
                </rpc>''' % (stream, fstr)

def read_msg():
    print("\n* Enter a NETCONF operation, end with an empty line")
    msg = '''<?xml version="1.0" encoding="UTF-8"?>
    <rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="2">
    '''
    ln = sys.stdin.readline()
    while ln != "\n":
        msg += ln
        ln = sys.stdin.readline()
    msg += '</rpc>\n'
    return msg

def strip(node):
    """Remove empty text nodes, and non-element nodes.
    The result after strip () is a child list with non-empty text-nodes,
    and element nodes only."""
    c = node.firstChild
    while c != None:
        remove = False
        if c.nodeType == Node.TEXT_NODE:
            if c.nodeValue.strip() == "":
                remove = True
        else:
            if c.nodeType != Node.ELEMENT_NODE:
                remove = True
        if remove:
            tmp = c.nextSibling
            node.removeChild(c)
            c.unlink()
            c = tmp
        else:
            c = c.nextSibling

# ***************************************************************************************
# CONSTANTS
# ***************************************************************************************
# Constants
RPC_REPLY_TAG_NAME = "rpc-reply"
OK_TAG_NAME        = "ok"

XML_REQ_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
            <rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="1">
                <edit-config xmlns:nc='urn:ietf:params:xml:ns:netconf:base:1.0'>
                    <target><candidate/></target>
                    <config>
                        {xml_command}
                    </config>
                </edit-config>
            </rpc>
            """

ACL_IN_XML_CMD = """<interface xmlns="http://compass-eos.com/ns/compass_yang">
                        <x-eth>
                            <instance>{x_eth_interface}</instance>
                            <policy>
                                    <acl>
                                    <in {operation}>{attribute_value}</in>
                                </acl>
                            </policy>
                        </x-eth>
                    </interface>"""

# ***************************************************************************************
# Canary Helper functions
# ***************************************************************************************
def _get_config_by_xpath(connection, xml_path_list) :
    """
    Input : connection  - Netconf connection object 
            xml_path_list - String list of XML path.
    Return value : XML tree Configuration string
    """
    cmd = "get-config"
    db = "running"
    wdefaults = ""
    winactive = False

    xpath = '/' + '/'.join(xml_path_list)

    msg = get_msg(cmd, db, xpath, wdefaults, winactive)
    connection.send_msg(msg)
    dut_reply = connection.recv_msg()
    return dut_reply

def _get_instance_attribute(dut_conn, instance_tag_name, instance_value, instance_path, attribute_path) :
    """
    Input : dut_conn - DUT Connection
            instance_tag_name   - For example, "x-eth"
            instance_value      - For example, "0/0/1" for x-eth 0/0/1
            instance_path       - For example,  ["interface"]
            attribute_path      - For example,  ["policy", "acl", "in"]
    Return value : Attribute of an instance if exists, None otherwise
    """
    import parse_xml
    instance_path.append(instance_tag_name)

    logging.info(f"Get attribute {attribute_path} for instance {instance_path}")
    attr_val = None 

    conf_xml_subtree = _get_config_by_xpath(dut_conn, instance_path)
    if conf_xml_subtree is not None:        
        instance_node = parse_xml.get_instance_by_string(conf_xml_subtree, instance_tag_name, instance_value)
        attr_val = parse_xml.get_instance_text_attribute (instance_node, attribute_path)
        if attr_val != None :
            logging.info(f"Received attribute value: {attr_val}")
        else :
            logging.info("No attribute value found")
    
    return attr_val

# ***************************************************************************************
# Commands functions
# ***************************************************************************************
def cmd_x_eth_configure(dut_conn, x_eth_interface, attribute_value, xml_cmd_template, operation):
    import parse_xml

    logging.info(f"operation: {operation} for {attribute_value} for interface x-eth {x_eth_interface}")

    xml_command = xml_cmd_template.format(x_eth_interface   = x_eth_interface, 
                                          operation         = operation,
                                          attribute_value   = attribute_value)

    logging.info(f"cmd_configure_acl_in xml_command :\n{xml_command}")

    dut_conn.send_msg(XML_REQ_TEMPLATE.format(xml_command = xml_command))
    xml_resp = dut_conn.recv_msg()
    return_val = parse_xml.get_instance_by_tag(xml_resp, RPC_REPLY_TAG_NAME, OK_TAG_NAME)
    if return_val != None :
        logging.info ("Successfull in sending xml command.")
    else :
        raise Exception("Failed in sending xml command !")

    logging.info("Sending commit")
    xml_req = commit_msg()
    dut_conn.send_msg(xml_req)
    xml_resp = dut_conn.recv_msg()
    return_val = parse_xml.get_instance_by_tag(xml_resp, RPC_REPLY_TAG_NAME, OK_TAG_NAME)
    if return_val != None :
        logging.info ("Successfull in sending commit.")
    else :
        raise Exception("Failed in sending commit !")

def cmd_hello(dut_conn):
    """Perform get hello from DUT first"""
    logging.info("Sending Hello message")
    versions = ['1.0']
    dut_conn.send_msg(hello_msg(versions))
    hello_reply = dut_conn.recv_msg()


def cmd_get_policy_acl_in_name(dut_conn, interface) :
    """Get acl in policy of interface
    Input : dut_conn  - DUT connection
            interface - String that holds instace string name. 
                        For example, port #1 will be "0/0/1"
    Return value : Policy ACL in name
    """
    X_ETH_TAG_NAME     = "x-eth"
    X_ETH_XML_PATH     = ["interface"]
    ACL_IN_PATH_LIST   = ["policy", "acl", "in"]

    logging.info("Get policy acl in name for interface x-eth " + interface)
    policy_name = _get_instance_attribute(dut_conn, X_ETH_TAG_NAME, interface, X_ETH_XML_PATH, ACL_IN_PATH_LIST) 
    
    return policy_name

def my_main() :
    """
    My Main - ACL test case example
    """
    import configparser

    # Read globals from ini file
    constants = configparser.ConfigParser()
    constants.read('config.ini')
    HOST_NAME       = constants['COMM']['HOST_CPM']
    NETCONF_PORT    = int(constants['NETCONF']['PORT'])

    X_ETH_VALUE             = "0/0/1"
    NEW_POLICY_ACL_IN_NAME  = "pol_ipv4"
    CPM_USER                = "admin"
    CPM_PASSWORD            = "admin"

    dut_conn = MyNetconf(hostname = HOST_NAME, port = NETCONF_PORT, username = CPM_USER, password = CPM_PASSWORD, 
                         publicKey = "", publicKeyType = "", privateKeyFile = "", privateKeyType = "") 
    dut_conn.connect()

    # Perform get hello from DUT first.
    cmd_hello(dut_conn)

    # Get acl in policy name of X_ETH_VALUE
    acl_in_policy_name = cmd_get_policy_acl_in_name(dut_conn, X_ETH_VALUE)

    if acl_in_policy_name == None :
        # Did not find an acl in policy on X_ETH_VALUE. Configure a new one. 
        cmd_x_eth_configure(dut_conn, X_ETH_VALUE, NEW_POLICY_ACL_IN_NAME, ACL_IN_XML_CMD, operation="")
    else :
        # Found acl in policy name on X_ETH_NAME. Delete it
        cmd_x_eth_configure(dut_conn, X_ETH_VALUE, acl_in_policy_name, ACL_IN_XML_CMD, operation="operation=\"delete\"")

if __name__ == "__main__" :
    my_main()
