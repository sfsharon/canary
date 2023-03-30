"""
Parse XML from DUT
"""
import logging
logging.basicConfig(
                    format='%(asctime)s.%(msecs)03d [%(filename)s line %(lineno)d] %(levelname)-8s %(message)s',                       
                    level=logging.INFO,
                    datefmt='%H:%M:%S')
import xml.dom.minidom

# Module Exception class 
class ErrorConf(Exception):
    """
    My exception
    """
    pass

# *************************************
# INTERNAL MODULE FUNCTIONS
# *************************************

def _get_node_text_value (node):
    """
    Parse xml minidom element for text value
    Input  : node - xml minidom element
    Output : String - Node's text 
    """
    rv = None       
    child_node = node.childNodes

    # Assumptions verify
    if   len(child_node) != 1 :
        raise ErrorConf("Error in number of child node. found " + str(len(child_node)) + " instances")
    elif child_node[0].nodeType != child_node[0].TEXT_NODE :
        raise ErrorConf("Error in child node.type. Expecting text type, got instead " + str(child_node[0].nodeType) + " type")
    
    rv = child_node[0].data 

    return rv
 
def _get_node_tag_value (node):
    """
    Parse xml minidom element for node tag value
    Input  : node - xml minidom element
    Output : String - Node's tag 
    """
    rv = None       
    child_node = node.childNodes

    # Assumptions verify
    if   len(child_node) != 1 :
        raise ErrorConf("Error in number of child node. found " + str(len(child_node)) + " instances")
    elif child_node[0].nodeType != child_node[0].TEXT_NODE :
        raise ErrorConf("Error in child node.type. Expecting text type, got instead " + str(child_node[0].nodeType) + " type")
    
    rv = child_node[0].data 

    return rv

def _get_unique_node (xml_tree_dom, tag_name) :
    """
    Get a node that appears only once in the xml_tree_dom object
    Input  : xml_tree_dom
             tag_name - Tag name to search inside the xml_tree_dom xml.minidom object
    Output : xml minidom element if exits single tag_name node, otherwise None 
    """
    rv = None

    instance_nodes = xml_tree_dom.getElementsByTagName(tag_name)
    if len(instance_nodes) != 1 :
        logging.error("Searched for unique xml tag " + tag_name + ", found instead " + str(len(instance_nodes)) + " instances")
    else :
        rv = instance_nodes[0]

    return rv

# *************************************
# EXTERNAL MODULE FUNCTIONS
# *************************************

def get_instance_by_string (xml_tree, filter_name, instance_string_name) :
    """
    Find instance_string_name by parsing XML received xml_tree from DUT, according to the xml_path.
    Input : xml_tree - XML string 
            filter_name - tag name to filter xml tree.
            instance_string_name -  
    Return value : xml node of required instance_string_name under the given xml_path
    """
    
    dom = xml.dom.minidom.parseString(xml_tree)

    ret_node = None

    instance_list = dom.getElementsByTagName(filter_name)

    for dom_elem in instance_list :
        instance_node = _get_unique_node(dom_elem, "instance")
        node_text = _get_node_text_value(instance_node)
        
        if node_text == instance_string_name :
            ret_node = dom_elem
            break

    return ret_node

def get_instance_by_tag (xml_tree, filter_name, instance_tag) :
    """
    Find instance_tag by parsing XML received xml_tree from DUT, according to the xml_path.
    Input : xml_tree - XML string 
            filter_name - tag name to filter xml tree.
            instance_tag -  
    Return value : xml node of required instance_tag under the given xml_path
    """
    
    dom = xml.dom.minidom.parseString(xml_tree)

    ret_node = None

    instance_list = dom.getElementsByTagName(filter_name)

    for dom_elem in instance_list :
        instance_node = _get_unique_node(dom_elem, instance_tag)
        
        if instance_node != None and instance_node.tagName == instance_tag :
            ret_node = instance_tag
            break

    return ret_node


def get_instance_text_attribute (instance_node, xml_path_list) :
    """
    Get an attribute of an object.
    Input : instance_node - xml.minidom.elem object of the required object, found by function _get_unique_node().
            xml_path_list - String list of xml tag names for reaching the required attribute.
                            For example : xml_path_list = ["policy", "acl", "in"] parameter for the following xml tree will 
                                          return the string value "pol_ipv4" :
                                <x-eth>
                                    <instance>0/0/1</instance>
                                    <speed>1000</speed>
                                    <policy>
                                        <acl>
                                            <in>pol_ipv4</in>
                                        </acl>
                                    </policy>
                                </x-eth>
    Return value : String with the required attrbiute, None othewise.
    """

    attr = None
    curr_node = _get_unique_node(instance_node, xml_path_list[0])

    # Edge case - Only one tag name in xml_path_list
    if len(xml_path_list) == 1 :
        attr = _get_node_text_value(curr_node)
        return attr

    for tag_name in xml_path_list[1:] :
        if curr_node == None :
            break
        curr_node = _get_unique_node(curr_node, tag_name)

    if curr_node != None :
        attr = _get_node_text_value(curr_node)
    
    return attr

def get_text_attribute (xml_tree, unique_tag_name) :
    """
    Same as get_instance_text_attribute, but without an instance.
    Input : xml_tree - XML string 
            For example, finding the attribute value of ctrl-plane egress :
            <rpc-reply xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="1">
                <data>
                    <ctrl-plane xmlns="http://compass-eos.com/ns/compass_yang">
                        <policy>
                            <acl>
                                <egress>my</egress>
                            </acl>
                        </policy>
                    </ctrl-plane>
                </data>
            </rpc-reply>
    Return value : String with the required attrbiute, None othewise.
    """
    attr = None 

    dom = xml.dom.minidom.parseString(xml_tree)
    curr_node = _get_unique_node(dom, unique_tag_name)
    if curr_node != None :
        attr = _get_node_text_value(curr_node)
    
    return attr

# ===================================
# UT
# ===================================
if __name__ == "__main__" :

    xml_conf_policy_acl_resp = """<?xml version="1.0" ?>
    <rpc-reply xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="1">
            <data>
                <policy xmlns="http://compass-eos.com/ns/compass_cupl/1.0">                
                    <acl>
                        <name>pol_ipv4</name>
                        <rule>
                            <name>r1</name>
                            <conditional>
                                <if>
                                    <plaincondition>
                                        <source-ip>
                                            <plain>
                                                <eq>
                                                    <value>10.24.0.2</value>
                                                </eq>
                                            </plain>
                                        </source-ip>
                                    </plaincondition>
                                    <then>
                                        <deny/>
                                    </then>
                                </if>
                            </conditional>
                        </rule>
                        <rule>
                            <name>rule-default</name>
                            <unconditional>
                                <permit/>
                            </unconditional>
                        </rule>
                    </acl>
                </policy>
            </data>
    </rpc-reply>"""

    xml_conf_ctrl_plane_resp = """<?xml version="1.0" encoding="UTF-8"?>
    <rpc-reply xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="1">
        <data>
            <ctrl-plane xmlns="http://compass-eos.com/ns/compass_yang">
                <policy>
                    <acl>
                        <egress>my</egress>
                    </acl>
                </policy>
            </ctrl-plane>
        </data>
    </rpc-reply>
    """

    xml_conf_resp = """<?xml version="1.0" ?>
    <rpc-reply xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="1">
        <data>
            <interface xmlns="http://compass-eos.com/ns/compass_yang">
                <x-eth>
                    <instance>0/0/0</instance>
                    <speed>1000</speed>
                    <admin-state>up</admin-state>
                    <ipv4-address>10.1.0.1/24</ipv4-address>
                    <mpls>enable</mpls>
                </x-eth>

                <x-eth>
                    <instance>0/0/1</instance>
                    <speed>1000</speed>
                    <policy>
                        <acl>
                            <in>pol_ipv4</in>
                        </acl>
                    </policy>
                </x-eth>

                <x-eth>
                    <instance>0/0/2</instance>
                    <speed>10000</speed>
                </x-eth>
            </interface>
        </data>
    </rpc-reply>
    """

    x_eth_interface = "0/0/2"
    acl_policy_name = "pol_ipv6"
    xml_filter = f"""
    <interface xmlns="http://compass-eos.com/ns/compass_yang">
        <x-eth>
            <instance>{x_eth_interface}</instance>
            <policy>
                    <acl>
                    <in>{acl_policy_name}</in>
                </acl>
            </policy>
        </x-eth>
    </interface>
    """

    # The response :
    xml_command_resp = """<?xml version="1.0" encoding="UTF-8"?>
                            <rpc-reply xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="1">
                                <ok/>
                            </rpc-reply>
                        """

    # Get policy acl name from XML configuration
    instance_node = get_instance_by_string(xml_conf_resp, "x-eth", "0/0/1")
    acl_policy_name = get_instance_text_attribute (instance_node, ["policy", "acl", "in"])
    logging.info (acl_policy_name)
    
    # Get response (ok / error) from DUT xml
    instance_node = get_instance_by_tag(xml_command_resp, "rpc-reply", "ok") 
    
    # Getting acl ctrl-plane egress
    ctrl_plane_val = get_text_attribute(xml_conf_ctrl_plane_resp, 'egress')

    logging.info("finish")