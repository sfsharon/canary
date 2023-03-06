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

# x_eth_dom = xml.dom.minidom.parseString(resp)

# policy_acl_in = ''

# x_eth_list = x_eth_dom.getElementsByTagName("x-eth")
# for x_eth in x_eth_list :
#     acl_node_list = x_eth.getElementsByTagName("acl")
#     for acl_node in acl_node_list :
#         dir_node = acl_node.getElementsByTagName("in")
#         if len(dir_node) == 1 :
#             policy_acl_in = ((dir_node[0].childNodes)[0].data)
#             break


def get_object_instance (xml_tree, filter_name, instance_name) :
    """
    Find instance_name by parsing XML received xml_tree from DUT, according to the xml_path.
    Input : xml_tree - XML string for query the "x-eth" tag name
    		filter_name - tag name to filter accordingly.
            instance_name - String 
    Return value : xml node of requred instance_name under the given xml_path
    """
    class ErrorXmlPath(Exception):
         pass
    
    dom = xml.dom.minidom.parseString(xml_tree)

    ret_node = None

    instance_list = dom.getElementsByTagName(filter_name)
    for dom_elem in instance_list :
        instance_node = dom_elem.getElementsByTagName("instance")
        if len(instance_node) != 1 :
            raise ErrorXmlPath("Error in number of xml tag " + instance_name + ", found " + str(len(instance)) + " instances")
        
        child_node = instance_node[0].childNodes

        if len(child_node) != 1 :
            raise ErrorXmlPath("Error in number of child node. found " + str(len(child_node)) + " instances")
        
        if child_node[0].nodeType != child_node[0].TEXT_NODE :
            raise ErrorXmlPath("Error in child node.type. Expecting text type, got " + str(child_node[0].nodeType) + " type")
        
        if child_node[0].data == instance_name :
            ret_node = dom_elem
            break

    return ret_node

def get_object_attribute (instance_node, xml_path_list) :
    """
    Get an attribute of an object.
    Input : instance_node - xml.minidom.elem object of the required object, found by function get_object_instance().
            xml_path_list - String list of the xml tag names for finding the required attribute.
                            For example : ["policy", "acl", "in"]
    Return value : String with the required attrbiute, None othewise.
    """

    attr = None



    # curr_node = None

    # for i, curr_path in enumerate(xml_path[:-1]) :
    #     curr_node = dom.getElementsByTagName(curr_path)

    #     if len(curr_node) != 1 :
    #         raise ErrorXmlPath("Error in number of xml tags " + curr_path + ", found " + len(curr_node))
    
        
    # x_eth_list = x_eth_dom.getElementsByTagName(interface_name)
    # for x_eth in x_eth_list :
    #     acl_node_list = x_eth.getElementsByTagName("acl")
    #     for acl_node in acl_node_list :
    #         dir_node = acl_node.getElementsByTagName("in")
    #         if len(dir_node) == 1 :
    #             policy_acl_in = ((dir_node[0].childNodes)[0].data)
    #             break    

    # return policy_acl_in

# val = get_object_instance(xml_resp, ["data", "interface", "x-eth"], "0/0/1")
instance_node = get_object_instance(xml_resp, "x-eth", "0/0/1")
acl_in_policy_name = get_object_attribute (instance_node, ["policy", "acl", "in"])
print(acl_in_policy_name)

print("finish")