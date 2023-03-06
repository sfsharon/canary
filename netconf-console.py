#!/usr/bin/python3
#
# Trivial Netconf Console
#

import sys
import os
# import re

import paramiko

# if sys.hexversion < 0x02030000:
#     print("This script needs python version >= 2.3")
#     sys.exit(1)

from optparse import OptionParser
import base64
import socket
from xml.dom import Node
import xml.dom.minidom

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
#            self.chan.sendall(buf)
#            return
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
# sort-of socket.create_connection() (new in 2.6)
def create_connection(host, port):
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
# qos-v Helper functions
# ***************************************************************************************
def get_config_by_xpath(connection, xpath) :
    """
    Input : xpath input with type string.
            connection object
    Return value : XML Configuration 
    """
    cmd = "get-config"
    db = "running"
    wdefaults = ""
    winactive = False
    msg = get_msg(cmd, db, xpath, wdefaults, winactive)
    connection.send_msg(msg)
    dut_reply = connection.recv_msg()
    return dut_reply

def get_policy_acl_in (xml_resp, interface_name) :
    """
    Parse XML received from DUT for the ACL ingress policy name attached to interface_name.
    Input : xml_rest - XML string for query the "x-eth" tag name
            interface_name - String for searching the acl ingress policy .
                             Values can be "x-eth", "ctrl-plane", "agg-eth", etc. 
    Return value : Policy acl in if exists, empty string otherwise
    """
    x_eth_dom = xml.dom.minidom.parseString(xml_resp)

    policy_acl_in = ''

    x_eth_list = x_eth_dom.getElementsByTagName(interface_name)
    for x_eth in x_eth_list :
        acl_node_list = x_eth.getElementsByTagName("acl")
        for acl_node in acl_node_list :
            dir_node = acl_node.getElementsByTagName("in")
            if len(dir_node) == 1 :
                policy_acl_in = ((dir_node[0].childNodes)[0].data)
                break    

    return policy_acl_in

def my_main() :
    """
    My Main
    """
    dut_conn = MyNetconf(hostname = "10.3.10.1", port = 2022, username = "admin", password = "admin", 
                  publicKey = "", publicKeyType = "", privateKeyFile = "", privateKeyType = "") 


    # connect to the NETCONF server
    dut_conn.connect()

    # First get the hello message
    versions = ['1.0']
    dut_conn.send_msg(hello_msg(versions))
    hello_reply = dut_conn.recv_msg()

    print ("GET FIRST ACL IN CONFIGURATION FROM X-ETH : \n------------------------------")
    conf_xml_subtree = get_config_by_xpath(dut_conn, "/interface/x-eth")
    
    if conf_xml_subtree is not None:
        # print(conf_xml_subtree.toprettyxml())
        acl_in_policy = get_policy_acl_in(conf_xml_subtree, "x-eth")
        print ("Policy in : " + acl_in_policy)

def original_main() :
    # main
    usage = """%prog [-h | --help] [options] [cmdoptions | <filename> | -]
        
    Where <filename> is a file containing a NETCONF XML command session.
    If <filename> is not given, one of the Command Options must be given.
    Filename - means standard input.
    """

    parser = OptionParser(usage)
    parser.add_option("-v", "--version", dest="version",
                    help="force NETCONF version 1.0 or 1.1")
    parser.add_option("-u", "--user", dest="username", default="admin",
            help="username")
    parser.add_option("-p", "--password", dest="password", default="admin",
            help="password")
    parser.add_option("--proto", dest="proto", default="ssh",
            help="Which transport protocol to use, one of ssh or tcp")
    parser.add_option("--host", dest="host", default="localhost",
                    help="NETCONF agent hostname")
    parser.add_option("--port", dest="port", default=2022, type="int",
                    help="NETCONF agent SSH port")
    parser.add_option("-s", "--outputStyle", dest="style", default="default",
                    help="Display output in: raw, plain, pretty, all, " \
                        "or noaaa format")
    parser.add_option("--iter", dest="iter", default=1, type="int",
                    help="Sends the same request ITER times.  Useful only in" \
                    "test scripts")
    parser.add_option("-i", "--interactive", dest="interactive", action="store_true")

    sshopts = parser.add_option_group("SSH Options")
    sshopts.add_option("--privKeyType", dest="privKeyType", default="",
                    help="type of private key, rsa or dss")
    sshopts.add_option("--privKeyFile", dest="privKeyFile", default="",
                    help="file which contains the private key")

    tcpopts = parser.add_option_group("TCP Options")
    tcpopts.add_option("-g", "--groups", dest="groups", default="", 
                    help="Set group membership for user - comma separated string")
    tcpopts.add_option("-G", "--sup-groups", dest="supgroups", default="", 
                    help="Set supplementary UNIX group ids for user - comma " \
                    "separated string of integers")


    cmdopts = parser.add_option_group("NETCONF Command Options")
    cmdopts.add_option("--hello", dest="hello", action="store_true",
                    help="Connect to the server and print its capabilities")
    cmdopts.add_option("--get", dest="get", action="store_true",
                    help="Takes an optional -x argument for XPath filtering")
    cmdopts.add_option("--get-config", action="callback", callback=get_config_opt,
                    help="Takes an optional --db argument, default is 'running'"\
                    ", and an optional -x argument for XPath filtering")
    cmdopts.add_option("--db", dest="db", default="running",
                    help="Database for commands that operate on a database."),
    cmdopts.add_option("--with-defaults", dest="wdefaults", default="",
                    help="One of 'explicit', 'trim', 'report-all' or "\
                    "'report-all-tagged'.  Use with --get, --get-config, or "\
                    "--copy-config.")
    cmdopts.add_option("--with-inactive", dest="winactive", action="store_true",
                    help="Send with-inactive parameter.  Use with --get, "\
                    "--get-config, --copy-config, or --edit-cinfig.")
    cmdopts.add_option("-x", "--xpath", dest="xpath", default="",
                    action="callback", callback=opt_xpath,
                    help="XPath filter to be used with --get, --get-config, " \
                    "and --create-subscription")
    cmdopts.add_option("--kill-session", dest="kill_session", default="",
                    help="Takes a session-id as argument.")
    cmdopts.add_option("--discard-changes", dest="discard_changes",
                    action="store_true")
    cmdopts.add_option("--commit", dest="commit",
                    action="store_true")
    cmdopts.add_option("--validate", dest="validate",
                    action="store_true",
                    help="Takes an optional --db argument, default is 'running'.")
    cmdopts.add_option("--copy-running-to-startup", dest="copy_running_to_startup",
                    action="store_true")
    cmdopts.add_option("--copy-config", dest="copy", default="",
                    help="Takes a filename as argument. The contents of the file"\
                    " is data for a single NETCONF copy-config operation"\
                    " (put into the <config> XML element)."\
                    " Takes an optional --db argument, default is 'running'.")
    cmdopts.add_option("--edit-config", dest="edit", default="",
                    help="Takes a filename as argument. The contents of the file"\
                    " is data for a single NETCONF edit-config operation"\
                    " (put into the <config> XML element)."\
                    " Takes an optional --db argument, default is 'running'.")
    cmdopts.add_option("--get-schema", dest="get_schema",
                    help="Takes an identifier (typically YANG module name) "\
                    "as parameter")
    cmdopts.add_option("--create-subscription", dest="create_subscription",
                    help="Takes a stream name as parameter, and an optional " \
                    "-x for XPath filtering")
    cmdopts.add_option("--rpc", dest="rpc", default="",
                    help="Takes a filename as argument. The contents of the file"\
                    " is a single NETCONF rpc operation (w/o the surrounding"\
                    " <rpc>).")


    (o, args) = parser.parse_args()

    if (o.wdefaults != "" and
        o.wdefaults not in ("trim", "explicit", "report-all", "report-all-tagged",
                            "true", "false")):
        print("Bad --with-defaults value: ", o.wdefaults)
        sys.exit(1)

    if len(args) == 1:
        filename = args[0]
    else:
        filename = None

    cmdf = None
    dataf = None
    # Read the command file
    if filename:
        if filename == '-':
            cmdf = sys.stdin
        else:
            cmdf = open(filename, "r")
        msg = None
    elif o.get:
        msg = get_msg("get", None, o.xpath, o.wdefaults, o.winactive)
    elif hasattr(o, "getConfig"):
        cmd = "get-config"
        if o.getConfig == "default":
            db = o.db
        else:
            db = o.getConfig
        msg = get_msg(cmd, db, o.xpath, o.wdefaults, o.winactive)
    elif o.rpc != "":
        dataf = open(o.rpc, "r")
        msg = None
    elif o.edit != "":
        dataf = open(o.edit, "r")
        msg = None
    elif o.copy != "":
        dataf = open(o.copy, "r")
        msg = None
    elif o.kill_session != "":
        msg = kill_session_msg(o.kill_session)
    elif o.discard_changes:
        msg = discard_changes_msg()
    elif o.commit:
        msg = commit_msg()
    elif o.validate:
        msg = validate_msg(o.db)
    elif o.copy_running_to_startup:
        msg = copy_running_to_startup_msg()
    elif o.get_schema is not None:
        msg = get_schema_msg(o.get_schema)
    elif o.create_subscription is not None:
        msg = create_subscription_msg(o.create_subscription, o.xpath)
    elif o.hello:
        msg = None
    elif o.interactive:
        pass
    else:
        parser.error("a filename or a command option is required")

    # create the transport object
    if o.proto == "ssh":
        try:
            import paramiko
        except:
            print("You must install the python ssh implementation paramiko")
            print("in order to use ssh.")
            sys.exit(1)

        c = NetconfSSH(o.host, o.port, o.username, o.password, "", "", 
                    o.privKeyFile, o.privKeyType)
    else:
        c = NetconfTCP(o.host, o.port, o.username, o.groups, o.supgroups)

    if o.style == "raw":
        c.trace = True

    # connect to the NETCONF server
    c.connect()

    # figure out which versions to advertise
    versions = []
    if cmdf is not None and o.version is None:
        # backwards compat - no version specified, and everything is
        # done from file.  assume this is 1.0.
        versions.append('1.0')
    else:    
        if o.version == '1.0' or o.version is None:
            versions.append('1.0')
        if o.version == '1.1' or o.version is None:
            versions.append('1.1')

    # send our hello unless we do everything from the file
    if cmdf is None:
        c.send_msg(hello_msg(versions))

    # read the server's hello
    hello_reply = c.recv_msg()

    # parse the hello message to figure out which framing
    # protocol to use
    d = xml.dom.minidom.parseString(hello_reply)

    if d is not None:
        print(d.toprettyxml())
    sys.exit(0)

if __name__ == "__main__" :
    # original_main()
    my_main()
