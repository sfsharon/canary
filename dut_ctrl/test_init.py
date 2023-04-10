"""
Initialization test.
Installs the required formal build, and makes sure that the device booted in a timely manner 
"""
import logging
logging.basicConfig(
                    format='%(asctime)s.%(msecs)03d [%(filename)s line %(lineno)d] %(levelname)-8s %(message)s',                       
                    level=logging.INFO,
                    datefmt='%H:%M:%S')

from fixtures import ssh_client_scope_function,                     \
                    run_local_shell_cmd, run_remote_shell_cmd,      \
                    wait_for_onl_after_reboot,                      \
                    copy_files_from_local_to_dut

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

    logging.info(f"{get_time()} Prepare install soft link to point to the required build file")
    _link_build_to_onie_installer(dut_num, device_type, build_num = '536')

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
def test_init_TC04_verify_dut_up() :
    """
    """
    import time 
    from cli_control import get_time

    logging.info (f"{get_time()} test_init_TC04_verify_dut_up")

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
