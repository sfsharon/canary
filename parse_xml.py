"""
Parse XML from DUT
"""

xml_resp = """<?xml version="1.0" ?>
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

import xml.dom.minidom

class ErrorConf(Exception):
    """
    My exception
    """
    pass

# *************************************
# INTERNAL MODULE FUNCTIONS
# *************************************

def _get_node_text (node):
    """
    Parse xml minidom element for text value
    Input : node - xml minidom element
    Output : String
    """
    rv = None       
    child_node = node.childNodes

    # Sanity checking
    if len(child_node) != 1 :
        raise ErrorConf("Error in number of child node. found " + str(len(child_node)) + " instances")
    elif child_node[0].nodeType != child_node[0].TEXT_NODE :
        raise ErrorConf("Error in child node.type. Expecting text type, got " + str(child_node[0].nodeType) + " type")
    
    rv = child_node[0].data 

    return rv
 
def _get_unique_node (xml_tree_dom, tag_name) :
    """
    Get a node that appears only once in the xml_tree_dom
    Input : xml_tree_dom
            tag_name
    output : xml minidom element if exits single tag_name node, None otherwise
    """
    rv = None

    instance_nodes = xml_tree_dom.getElementsByTagName(tag_name)
    if len(instance_nodes) != 1 :
        raise ErrorConf("Error - Searched for unique xml tag " + tag_name + ", found instead " + str(len(instance_nodes)) + " instances")
    rv = instance_nodes[0]

    return rv

def _get_object_attribute (instance_node, xml_path_list) :
    """
    Get an attribute of an object.
    Input : instance_node - xml.minidom.elem object of the required object, found by function get_object_instance().
            xml_path_list - String list of the xml tag names for finding the required attribute.
                            For example : ["policy", "acl", "in"]
    Return value : String with the required attrbiute, None othewise.
    """

    attr = None
    currNode = None

    if len(xml_path_list) == 1 :
        

    for path in xml_path_list :
        instance_nodes = dom_elem.getElementsByTagName("instance")
                if len(instance_nodes) != 1 :
                    raise ErrorConf("Error in number of xml tag " + instance_name + ", found " + str(len(instance)) + " instances")
                instance_node = instance_nodes[0]


# *************************************
# EXTERNAL MODULE FUNCTIONS
# *************************************

def get_object_instance (xml_tree, filter_name, instance_name) :
    """
    Find instance_name by parsing XML received xml_tree from DUT, according to the xml_path.
    Input : xml_tree - XML string for query the "x-eth" tag name
    		filter_name - tag name to filter accordingly.
            instance_name - String 
    Return value : xml node of requred instance_name under the given xml_path
    """
    
    dom = xml.dom.minidom.parseString(xml_tree)

    ret_node = None

    instance_list = dom.getElementsByTagName(filter_name)
    for dom_elem in instance_list :
        instance_node = _get_unique_node(dom_elem, "instance")
        node_text = _get_node_text(instance_node)
        
        if node_text == instance_name :
            ret_node = dom_elem
            break

    return ret_node



if __name__ == "__main__" :
    instance_node = get_object_instance(xml_resp, "x-eth", "0/0/1")
    acl_in_policy_name = _get_object_attribute (instance_node, ["policy", "acl", "in"])
    print(acl_in_policy_name)

    print("finish")