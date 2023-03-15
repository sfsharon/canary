"""
Parse CLI strings received from the 
"""

def get_show_acl_in_detail (input_str) :
    """
    Parse the output of 'show acl interface detail x-eth0/0/XX' for the first rule name, and
    its deny and permit counter value.
    Input : CLI output of show acl
    Return value : Tuple of (policy_name, deny_counter, permit_counter)
    """
    
    # Returns (policy_name, first_rule_name, deny_counter, second_rule_name, permit_counter)
    regular_exp = "x-eth0\/0\/\d{1,2}\s*in\s+(\S+)\s+(\S+)\s+deny\s+(\d+)\s+(\S+)\s+permit\s+(\d+)"
    
    #WIP
    # Validate : first_rule_name == r1
    # 			 second_rule_name == default_rule

if __name__ == "__main__": 
    show_acl_detail = """	                                                 HIT
    	INTERFACE   DIR  POL       RULE          ACTION  COUNT
    	--------------------------------------------------------
    	x-eth0/0/1  in   pol_ipv4  r1            deny    0
    	                           rule-default  permit  0
    """    

    policy_name, deny_counter, permit_counter = get_show_acl_in_detail(show_acl_detail)