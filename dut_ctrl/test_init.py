"""
Initialization test.
Installs the required formal build, and makes sure that the device booted in a timely manner 
"""
import logging
logging.basicConfig(
                    format='%(asctime)s.%(msecs)03d [%(filename)s line %(lineno)d] %(levelname)-8s %(message)s',                       
                    level=logging.INFO,
                    datefmt='%H:%M:%S')

from fixtures import run_local_shell_cmd, wait_for_onl_after_reboot, copy_files_from_local_to_dut

# ***************************************************************************************
# Helper functions
# ***************************************************************************************
def _link_build_to_onie_installer(device_num, device_type, build_num) :
    """
    Soft link onie-installer for device_num to official build number build_num
    """
    import os
    import cli_control
    
    # 1. Get name of build build_num
    build_path = '/auto/exaware/build-slave/images/develop'
    command = f'ls -l {build_path}'
    rc, output = run_local_shell_cmd(command)
    if rc != 0 :
        raise Exception (f"Error: {rc} from: {command}")

    build_file_name = cli_control._get_install_file_name(output, build_num)
    logging.info(f"Build: {build_num}, File name: {build_file_name}")

    # 2. Link formal build to device device_num onie-installer
    device_install_path = f'/home/tftp/onie/exa-il01-{device_type}-30{device_num[-2:]}'
    onie_installer_full_path = os.path.join(device_install_path, 'onie-installer')
    build_file_full_path = os.path.join(build_path, build_file_name)

    command = f'ln -sf {build_file_full_path} {onie_installer_full_path}'
    rc, output = run_local_shell_cmd(command)
    if rc != 0 :
        raise Exception (f"Error: {rc} from: {command}")

def _get_build_number(file_name):
    import re
    build_num = None

    build_number_string = 'Build number ='
    with open(file_name, 'r') as file:
        # read a list of lines into data
        data = file.readlines()

        # iterate over each line
        for line in data:
            # check if the line contains the string
            if build_number_string in line:
                build_num = re.findall('\d+', line)
                if len(build_num) != 1 :
                    raise Exception (f"Could not find build number in line {line}")
                build_num = build_num[0]
                break 
    return build_num

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

# ***************************************************************************************
# Test Case #01 - Installing formal build
# ***************************************************************************************
def test_init_TC01_installing_build_and_reboot() :
    """
    """
    logging.info ("{get_time()} test_init_TC01_installing_build")

    import configparser
    import cli_control
    from cli_control import get_time

    # Read globals from ini file
    constants = configparser.ConfigParser()
    constants.read('config.ini')
    device_type = constants['GENERAL']['DUT_TYPE']
    dut_num = constants['GENERAL']['DUT_NUM']
    build_number = constants['GENERAL']['TEST_BUILD_NUMBER']

    logging.info(f"{get_time()} Prepare install soft link to point to the required build file")
    _link_build_to_onie_installer(dut_num, device_type, build_num = build_number)

    cli_control.reboot_dut(device_number = dut_num, is_set_install_mode = True)

# ***************************************************************************************
# Test Case #02 - Wait for DUT to boot, and replace script startagent
# ***************************************************************************************
def test_init_TC02_verify_dut_up() :
    """
    1. Verify the dut responds to ssh port on onl interface
    2. WIP - Verify that for command "show system module" (show sys mod) both lc and cpm are "Card-Ready"
    """
    import time 
    from cli_control import get_time

    logging.info (f"{get_time()} test_init_TC02_verify_dut_up")

    # Waiting for WAIT_PERIOD_FOR_DUT_START_BOOT_MINUTES minutes for the system to finish initialization
    WAIT_PERIOD_FOR_DUT_START_BOOT_MINUTES = 6
    minutes_waited = 0
    while minutes_waited < WAIT_PERIOD_FOR_DUT_START_BOOT_MINUTES :
        time.sleep(60)
        minutes_waited += 1
        logging.info(f"{get_time()} Waited {minutes_waited} minutes for the DUT to boot")

    logging.info(f"{get_time()} Starting to poll ONL IP to test if it is up.")
    rv = wait_for_onl_after_reboot()

    assert rv == True


# ***************************************************************************************
# Test Case #03 - 
# ***************************************************************************************
def test_init_TC03_copy_startagent_to_dut() :
    """
    # - Copy file resources/startagent to DUT in path "./vbox/a/local/bin/startagent"
    # - Do a reboot
        
        Neet to patch the script "startagent" in path "./vbox/a/local/bin/startagent", which activates the bcmrm process.
        The reason is that in non-DEVELOPER mode, the screen for the bcmrm process is not created, and this disables
        the ability to connect ot the bcm diag she
    """
    import configparser
    from cli_control import get_time, add_dev_machine_ssh_key_to_dut

    logging.info (f"{get_time()} test_init_TC03_copy_startagent_to_dut")

    # Read globals from ini file
    constants = configparser.ConfigParser()
    constants.read('config.ini')
    dut_num = constants['GENERAL']['DUT_NUM']

    # Create ssh key of DEV machine in dut
    add_dev_machine_ssh_key_to_dut(dut_num)

    # scp patch file for startagent to dut
    destdir   = '/vbox/a/local/bin'
    copy_file_list = ["./resources/startagent"]
    copy_files_from_local_to_dut(dut_num, copy_file_list, destdir)

# ***************************************************************************************
# Test Case #04 - Rebooting (Duplicate of TC01)
# ***************************************************************************************
def test_init_TC04_reboot() :
    """
    """
    from cli_control import get_time

    logging.info (f"{get_time()} test_init_TC04_reboot")

    import configparser
    import cli_control
    from cli_control import get_time

    # Read globals from ini file
    constants = configparser.ConfigParser()
    constants.read('config.ini')
    dut_num = constants['GENERAL']['DUT_NUM']

    cli_control.reboot_dut(device_number = dut_num, is_set_install_mode = False)

# ***************************************************************************************
# Test Case #05 - Wait for DUT to boot (duplicate of TC02)
# ***************************************************************************************
def test_init_TC05_verify_dut_up() :
    """
    """
    import time 
    from cli_control import get_time, reset_dut_connections
    import configparser

    logging.info (f"{get_time()} test_init_TC05_verify_dut_up")

    # Read globals from ini file
    constants = configparser.ConfigParser()
    constants.read('config.ini')
    dut_num = constants['GENERAL']['DUT_NUM']

    # Waiting for WAIT_PERIOD_FOR_DUT_START_BOOT_MINUTES minutes for the system to finish initialization
    WAIT_PERIOD_FOR_DUT_START_BOOT_MINUTES = 11
    minutes_waited = 0
    while minutes_waited < WAIT_PERIOD_FOR_DUT_START_BOOT_MINUTES :
        time.sleep(60)
        minutes_waited += 1
        logging.info(f"{get_time()} Waited {minutes_waited} minutes for the DUT to boot")

    logging.info(f"{get_time()} Starting to poll ONL IP to test if it is up.")
    reset_dut_connections(device_number = dut_num, is_reset_cpm_connection = False)
    rv = wait_for_onl_after_reboot()

    assert rv == True

# ***************************************************************************************
# Test Case #06 - Wait for DUT to boot (duplicate of TC02)
# ***************************************************************************************
def test_init_TC06_verify_card_ready() :
    """
    """
    from cli_control import get_time, reset_dut_connections
    from fixtures import copy_files_from_dut_to_local
    import os 
    import shutil 
    import time
    import configparser

    logging.info (f"{get_time()} test_init_TC06_verify_card_ready")

    # Read globals from ini file
    constants = configparser.ConfigParser()
    constants.read('config.ini')
    dut_num = constants['GENERAL']['DUT_NUM']
    test_build_number = constants['GENERAL']['TEST_BUILD_NUMBER']

    reset_dut_connections(device_number = dut_num, is_reset_cpm_connection = False)

    temp_dir               = './temp'
    card_state_remote_dir  = '/vbox/cpm_image/root/var/log'
    build_param_remote_dir = '/vbox/cpm_image/root/opt/compass'
    card_state_files = ['card_LC-0-0.state', 'card_CPM-0-0.state']
    build_param_file = ['build_param.txt']

    # Create temp dir for the card status files from dut
    if os.path.exists(temp_dir):
        logging.info(f'{get_time()} Deleting existing {temp_dir} folder')
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir)

    # Copy files to locally temp dir
    copy_files_from_dut_to_local(dut_num, build_param_remote_dir, build_param_file, temp_dir)

    # Verify that the correct version has been installed
    build_param_full_path = os.path.join(temp_dir, build_param_file[0])
    dut_build_number = _get_build_number(build_param_full_path) 
    if dut_build_number != test_build_number :
        raise Exception(f'{get_time()} Expected build number: {test_build_number}, instead found {dut_build_number}') 
    else :
        logging.info(f"{get_time()} Found expected build number {dut_build_number}")

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
        logging.info(f"{get_time()} CPM card state: {curr_cpm_card_state}, LC card state: {curr_lc_card_state}")        
        if is_cpm_card_init == True and is_lc_card_init == True :
            break
        time.sleep(60)
        minutes_waited += 1
        logging.info(f"{get_time()} Waited {minutes_waited} minutes for the DUT to initialize")

    if is_cpm_card_init != True or is_lc_card_init != True :
        logging.info(f"{get_time()} DUT did not intialize during {WAIT_PERIOD_FOR_DUT_INIT_MINUTES} minutes.")
        assert False
    else :
        logging.info(f"{get_time()} DUT intialized successfully")
        assert True
    
