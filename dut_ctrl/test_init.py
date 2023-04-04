"""
Initialization test.
Installs the required formal build, and makes sure that the device booted in a timely manner 
"""
import logging
logging.basicConfig(
                    format='%(asctime)s.%(msecs)03d [%(filename)s line %(lineno)d] %(levelname)-8s %(message)s',                       
                    level=logging.INFO,
                    datefmt='%H:%M:%S')


# ***************************************************************************************
# Helper functions
# ***************************************************************************************
def _run_local_shell_cmd(cmd_string) :
    """
    Run local shell command
    """

    import subprocess

    result = subprocess.run(cmd_string, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    rc = result.returncode
    output = result.stdout.decode()
    logging.debug(f"Return code: {rc}\nOutput:\n{output}")

    return rc, output

def _link_build_to_onie_installer(device_num, device_type, build_num) :
    """
    Soft link onie-installer for device_num to official build number build_num
    """
    import os
    import cli_control
    
    # 1. Get name of build build_num
    build_path = '/auto/exaware/build-slave/images/develop'
    command = 'ls -l ' + build_path
    rc, output = _run_local_shell_cmd(command)
    if rc != 0 :
        raise Exception (f"Error: {rc} from: {command}")

    build_file_name = cli_control._get_install_file_name(output, build_num)
    logging.info(f"Build: {build_num}, File name: {build_file_name}")

    # 2. Link formal build to device device_num onie-installer
    device_install_path = f'/home/tftp/onie/exa-il01-{device_type}-30{device_num[-2:]}'
    onie_installer_full_path = os.path.join(device_install_path, 'onie-installer')
    build_file_full_path = os.path.join(build_path, build_file_name)

    command = f'ln -sf {build_file_full_path} {onie_installer_full_path}'
    rc, output = _run_local_shell_cmd(command)
    if rc != 0 :
        raise Exception (f"Error: {rc} from: {command}")

# ***************************************************************************************
# Fixtures functions
# ***************************************************************************************

# ***************************************************************************************
# Test Case #0 - Installing formal build
# ***************************************************************************************
def test_TC00_installing_build() :
    logging.info ("test_TC99_testing_the_tests")
    _link_build_to_onie_installer('3010', 'dl', '522')
