"""
Initialization test.
Installs the required formal build, and makes sure that the device booted in a timely manner 
"""
import logging
logging.basicConfig(
                    format='%(asctime)s.%(msecs)03d [%(filename)s line %(lineno)d] %(levelname)-8s %(message)s',                       
                    level=logging.INFO,
                    datefmt='%H:%M:%S')
import paramiko
from fixtures import run_local_shell_cmd,               \
                     wait_for_onl_after_reboot,         \
                     copy_files_from_local_to_dut,      \
                     ssh_client, run_remote_shell_cmd,  \
                     ssh_client__no_cpm_conn_reset

from common_enums import BcmrmErrors


# ***************************************************************************************
# Helper functions
# ***************************************************************************************
def _get_list_of_files(dir: str) -> str :
    """
    """
    from cli_control import get_time

    command = f'ls -l {dir}'
    rc, output = run_local_shell_cmd(command)
    if rc != 0 :
        raise Exception (f"{get_time()} Error: {rc} from: {command}")
    
    return output

def _link_build_to_onie_installer(device_num, device_type, build_num) :
    """
    Soft link onie-installer for device_num to official build number build_num.
    If build_num == None, use the latest build number from build_path
    """
    import os
    from cli_control import get_time, get_official_install_file_name, get_official_latest_build
    import configparser

    # 1. Get name of build build_num
    constants = configparser.ConfigParser()
    constants.read('config.ini')
    build_path = constants['GENERAL']['BRANCH'] 
    output = _get_list_of_files(build_path)
    
    if build_num == None:
        build_num = get_official_latest_build(output)
        logging.info (f"{get_time()} Using latest build number: {build_num}")
    else :
        logging.info (f"{get_time()} Using user defined build number: {build_num}")

    build_file_name = get_official_install_file_name(output, build_num)
    
    logging.info(f"{get_time()} Build: {build_num}, File name: {build_file_name}")

    # 2. Link formal build to device device_num onie-installer
    device_install_path = f'/home/tftp/onie/exa-il01-{device_type}-30{device_num[-2:]}'
    onie_installer_full_path = os.path.join(device_install_path, 'onie-installer')
    build_file_full_path = os.path.join(build_path, build_file_name)

    command = f'ln -sf {build_file_full_path} {onie_installer_full_path}'
    rc, output = run_local_shell_cmd(command)
    if rc != 0 :
        raise Exception (f"Error: {rc} from: {command}")

def _get_card_state (file_name):
    """
    An example of card card_CPM-0-0.state :
    module:0/CPM0; type:N/A; admin_state:Active; oper_state:Card-Ready; ha_role:A; more_info:
    Function returns the value of oper_state
    """
    import re
    oper_state = None
    pattern = r"oper_state:(.*?);"

    with open(file_name, 'r') as file:
        data = file.readlines()
        for line in data:
            match = re.search(pattern, line)
            if match:
                oper_state = match.group(1)

    return oper_state

def _verify_onl_up(wait_timeout_for_onl_to_boot_minutes) :
    import time 
    from cli_control import get_time, reset_dut_connections
    import configparser

    logging.info (f"{get_time()} _verify_onl_up")

    # Read globals from ini file
    constants = configparser.ConfigParser()
    constants.read('config.ini')
    dut_num = constants['GENERAL']['DUT_NUM']
    dut_type = constants['GENERAL']['DUT_TYPE']

    # Waiting for WAIT_PERIOD_FOR_DUT_START_BOOT_MINUTES minutes for the system to finish initialization
    # WAIT_PERIOD_FOR_DUT_START_BOOT_MINUTES = 11
    minutes_waited = 0
    while minutes_waited < wait_timeout_for_onl_to_boot_minutes :
        time.sleep(60)
        minutes_waited += 1
        logging.info(f"{get_time()} Waited {minutes_waited} minutes for the DUT to boot")

    logging.info(f"{get_time()} Starting to poll ONL IP to test if it is up.")
    reset_dut_connections(device_number = dut_num, device_type = dut_type, is_reset_cpm_connection = False)
    rv = wait_for_onl_after_reboot()

    assert rv == True

def _wait_cpm_and_lc_card_ready() -> bool:
    """
    Return Value : True if both CPM and LC cards reached state CARD_READY within
    timeout WAIT_PERIOD_FOR_DUT_INIT_MINUTES, False otherwise.
    """
    from cli_control import get_time, reset_dut_connections
    from fixtures import copy_files_from_dut_to_local
    import os 
    import time
    import configparser

    logging.info (f"{get_time()} test_init_TC06_verify_cpm_ready")

    # Read globals from ini file
    constants = configparser.ConfigParser()
    constants.read('config.ini')
    dut_num = constants['GENERAL']['DUT_NUM']
    dut_type = constants['GENERAL']['DUT_TYPE']

    reset_dut_connections(device_number = dut_num, device_type = dut_type, is_reset_cpm_connection = False)

    temp_dir               = './temp'
    card_state_remote_dir  = '/vbox/cpm_image/root/var/log'
    card_state_files = ['card_LC-0-0.state', 'card_CPM-0-0.state']

    # Parse card state CPM and LC files, and verify that LC and CPM cards are ready. If not, wait for 1 minute, and try again.
    CARD_READY_STR = "Card-Ready" 
    is_cpm_card_init = False
    is_lc_card_init  = False
    lc_state_full_path  = os.path.join(temp_dir, card_state_files[0])
    cpm_state_full_path = os.path.join(temp_dir, card_state_files[1])
    WAIT_PERIOD_FOR_DUT_INIT_MINUTES = 5
    minutes_waited = 0
    while (minutes_waited < WAIT_PERIOD_FOR_DUT_INIT_MINUTES) :
        # Copy files to locally temp dir
        copy_files_from_dut_to_local(dut_num, card_state_remote_dir,  card_state_files, temp_dir)
        curr_cpm_card_state = _get_card_state(cpm_state_full_path)
        curr_lc_card_state  = _get_card_state(lc_state_full_path)
        is_cpm_card_init =  (curr_cpm_card_state == CARD_READY_STR)
        is_lc_card_init  =  (curr_lc_card_state  == CARD_READY_STR)
        logging.info(f"{get_time()} CPM {curr_cpm_card_state}, LC {curr_lc_card_state}")        
        if is_cpm_card_init == True and is_lc_card_init == True :
            break
        time.sleep(60)
        minutes_waited += 1
        if minutes_waited == 1 :
            logging.info(f"{get_time()} Waited for 1 minute for the DUT to initialize")
        else :
            logging.info(f"{get_time()} Waited for {minutes_waited} minutes for the DUT to initialize")

    rv = None
    if is_cpm_card_init != True or is_lc_card_init != True :
        logging.info(f"{get_time()} DUT did not intialize during {WAIT_PERIOD_FOR_DUT_INIT_MINUTES} minutes.")
        rv = False
    else :
        logging.info(f"{get_time()} DUT intialized successfully")
        rv = True    

    return rv

def _get_bcmrm_error(dut_num: str, temp_dir: str):
    """
    Parse the bcmrm log file /vbox/lc_image/root/var/log/bcmrm_bsl_trace_buffer.trace so that
    application can decide if this an issue that can beresolved by booting, like issue BcmrmErrors.DMA_ERROR 
    Return value : Enumeration class 

    Example of DMA error in bcmrm_bsl log file :
        The file bcmrm_bsl_trace_buffer.trace log error for this case is :
        IRR_MCDB.IRR0 polling timeout
        This DMA failure may be due to wrong PCI configuration.
    """
    from fixtures import copy_files_from_dut_to_local
    import os
    from cli_control import get_time

    rv = None

    DMA_ISSUE_STRING_1 = "IRR_MCDB.IRR0 polling timeout"
    DMA_ISSUE_STRING_2 = "This DMA failure may be due to wrong PCI configuration"

    lc_log_dir = '/vbox/lc_image/root/var/log'
    bcmrm_log_file = ['bcmrm_bsl_trace_buffer.trace']
    bcmrm_log_full_path = os.path.join(temp_dir, bcmrm_log_file[0])
    
    copy_files_from_dut_to_local(dut_num, lc_log_dir, bcmrm_log_file, temp_dir)
    
    with open(bcmrm_log_full_path, 'r') as file:
        contents = file.read()
        if DMA_ISSUE_STRING_1 in contents or DMA_ISSUE_STRING_2 in contents:
            rv = BcmrmErrors.DMA_ERROR
        else:
            rv = BcmrmErrors.OK
    
    return rv

# ***************************************************************************************
# Test Case #01 - Installing formal build
# ***************************************************************************************
def test_init_TC01_installing_build_and_reboot() :
    """
    If attribute 'GENERAL'/'TEST_BUILD_NUMBER' does not exist, will use the latest official build
    """
    from cli_control import get_time, reboot_dut
    logging.info (f"{get_time()} test_init_TC01_installing_build")

    import configparser

    # Read globals from ini file
    constants = configparser.ConfigParser()
    constants.read('config.ini')
    device_type = constants['GENERAL']['DUT_TYPE']
    dut_num = constants['GENERAL']['DUT_NUM']
    dut_type = constants['GENERAL']['DUT_TYPE']

    if constants.has_option('GENERAL', 'TEST_BUILD_NUMBER'):
        build_number = constants['GENERAL']['TEST_BUILD_NUMBER']
    else:
        build_number = None

    logging.info(f"{get_time()} Prepare install soft link to point to the required build file")
    _link_build_to_onie_installer(dut_num, device_type, build_number)

    reboot_dut(device_number = dut_num, device_type = dut_type, is_set_install_mode = True)

# ***************************************************************************************
# Test Case #02 - Wait for DUT to boot, and replace script startagent
# ***************************************************************************************
def test_init_TC02_verify_dut_up() :
    """
    Verify the dut responds to ssh port on onl interface
    """
    from cli_control import get_time

    logging.info (f"{get_time()} test_init_TC02_verify_dut_up")
    _verify_onl_up(wait_timeout_for_onl_to_boot_minutes = 11)

# ***************************************************************************************
# Test Case #03 - 
# ***************************************************************************************
def test_init_TC03_update_build_mode(ssh_client__no_cpm_conn_reset: paramiko.SSHClient) :
    """
    Update build mode from LAB to DEVELOPER. The reason is that in non-DEVELOPER mode, the screen for the bcmrm process is not created, and this disables
        the ability to connect ot the bcm diag shell and send the "Tx" commands that simulate packet ingress 

        
        Neet to patch the script "startagent" in path "./vbox/a/local/bin/startagent", which activates the bcmrm process.
        The reason is that in non-DEVELOPER mode, the screen for the bcmrm process is not created, and this disables
        the ability to connect ot the bcm diag she
    """
    import configparser
    from cli_control import get_time

    logging.info (f"{get_time()} test_init_TC03_update_build_mode")

    # Read globals from ini file
    constants = configparser.ConfigParser()
    constants.read('config.ini')
    dut_num  = constants['GENERAL']['DUT_NUM']
    dut_type = constants['GENERAL']['DUT_TYPE']
    from cli_control import add_dev_machine_ssh_key_to_dut

    # Get build mode
    command = "grep 'Build mode' /vbox/cpm_image/root/opt/compass/build_param.txt | cut -d '=' -f 2 | sed 's#  *##'"
    rv, stdout_str = run_remote_shell_cmd(ssh_client__no_cpm_conn_reset, command)
    if rv != 0 or len(stdout_str) != 1 :
        raise Exception(f"{get_time()} Failed with rv {rv}, when running remote command \"{command}\"")

    # Replace build mode to DEVELOPER
    build_mode = stdout_str[0].strip()
    logging.info (f"{get_time()} Received: {build_mode}. Replacing build mode to DEVELOPER")
    command = f"sed -i 's/{build_mode}/DEVELOPER/g' /vbox/cpm_image/root/opt/compass/build_param.txt"
    rv, stdout_str = run_remote_shell_cmd(ssh_client__no_cpm_conn_reset, command)
    if rv != 0 :
        raise Exception(f"{get_time()} Failed with rv {rv}, when running remote command \"{command}\"")

    # Create ssh key of DEV machine in dut
    add_dev_machine_ssh_key_to_dut(dut_num, dut_type)

# ***************************************************************************************
# Test Case #04 - Rebooting (Duplicate of TC01)
# ***************************************************************************************
def test_init_TC04_reboot() :
    """
    """
    from cli_control import get_time, reboot_dut

    logging.info (f"{get_time()} test_init_TC04_reboot")

    import configparser
    import cli_control
    from cli_control import get_time

    # Read globals from ini file
    constants = configparser.ConfigParser()
    constants.read('config.ini')
    dut_num = constants['GENERAL']['DUT_NUM']
    dut_type = constants['GENERAL']['DUT_TYPE']

    reboot_dut(device_number = dut_num, device_type = dut_type, is_set_install_mode = False)

# ***************************************************************************************
# Test Case #05 - Wait for DUT to boot (duplicate of TC02)
# ***************************************************************************************
def test_init_TC05_verify_dut_up() :
    """
    """
    from cli_control import get_time

    logging.info (f"{get_time()} test_init_TC05_verify_dut_up")
    _verify_onl_up(wait_timeout_for_onl_to_boot_minutes=11)

# ***************************************************************************************
# Test Case #06 - Wait for DUT to boot (duplicate of TC02)
# ***************************************************************************************
def test_init_TC06_verify_cpm_ready() :
    """
    """
    from cli_control import get_time, reset_dut_connections, reboot_dut, get_build_number_from_build_param_file, get_official_latest_build
    from fixtures import copy_files_from_dut_to_local
    import os 
    import shutil 
    import configparser

    logging.info (f"{get_time()} test_init_TC06_verify_cpm_ready")

    # Read globals from ini file
    constants = configparser.ConfigParser()
    constants.read('config.ini')
    dut_num = constants['GENERAL']['DUT_NUM']
    dut_type = constants['GENERAL']['DUT_TYPE']

    if constants.has_option('GENERAL', 'TEST_BUILD_NUMBER'):
        test_build_number = constants['GENERAL']['TEST_BUILD_NUMBER']
        logging.info (f"{get_time()} Using user defined build number: {test_build_number}")
    else:
        build_path = constants['GENERAL']['BRANCH'] 
        output = _get_list_of_files(build_path)
        test_build_number = get_official_latest_build(output)
        logging.info (f"{get_time()} Using latest build number: {test_build_number}")

    reset_dut_connections(device_number = dut_num, device_type = dut_type, is_reset_cpm_connection = False)

    temp_dir               = './temp'
    build_param_remote_dir = '/vbox/cpm_image/root/opt/compass'
    build_param_file = ['build_param.txt']

    # Create temp dir for the card status files from dut
    if os.path.exists(temp_dir):
        logging.info(f'{get_time()} Deleting existing {temp_dir} folder')
        shutil.rmtree(temp_dir)
    
    logging.info(f'{get_time()} Finished Deleting {temp_dir} folder, creating a new one')
    os.makedirs(temp_dir)

    logging.info(f'{get_time()} Copy files to locally temp dir')
    copy_files_from_dut_to_local(dut_num, build_param_remote_dir, build_param_file, temp_dir)

    # Verify that the correct version has been installed
    build_param_full_path = os.path.join(temp_dir, build_param_file[0])
    dut_build_number = get_build_number_from_build_param_file(build_param_full_path) 
    if dut_build_number != test_build_number :
        raise Exception(f'{get_time()} Expected build number: {test_build_number}, instead found {dut_build_number}') 
    else :
        logging.info(f"{get_time()} Found expected build number {dut_build_number}")

    rv = _wait_cpm_and_lc_card_ready()

    if  rv == False :
        logging.error (f"{get_time()} CPM and LC did not reach CARD_READY during timeout. Inspecting bcmrm_bsl log file")
        _verify_onl_up(wait_timeout_for_onl_to_boot_minutes=6)
        bcmrm_error = _get_bcmrm_error(dut_num, temp_dir)

        if bcmrm_error is BcmrmErrors.DMA_ERROR :
            logging.error (f"{get_time()} bcmrm_bsl log file shows there was a DMA error. Rebooting again.")

            reboot_dut(device_number = dut_num, device_type = dut_type, is_set_install_mode = False)
            _verify_onl_up(wait_timeout_for_onl_to_boot_minutes=11)
            rv = _wait_cpm_and_lc_card_ready()
            if rv == False :
                raise Exception ("Device did not reboot correctly after a DMA bcmrm error")
        else :
            raise Exception ("Device did not initialized correctly - Unknown reason")
    assert True


        