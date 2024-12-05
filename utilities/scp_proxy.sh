#!/bin/bash

# Configuration
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PYTHON_SCRIPT="${SCRIPT_DIR}/proxy_scp.py"
CONFIG_FILE="${SCRIPT_DIR}/config.yaml"

# Function to display usage
usage() {
    echo "Usage: scp_proxy <source_file> <destination_path>"
    echo "Transfer files to router through proxy using configuration in ${CONFIG_FILE}"
    echo
    echo "Arguments:"
    echo "  source_file       Path to the local file to transfer"
    echo "  destination_path  Path on the router where the file should be placed"
    echo
    echo "Example:"
    echo "  scp_proxy ~/myfile.txt /tmp/myfile.txt"
    exit 1
}

# Check if python3 is available
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is required but not installed"
    exit 1
fi

# Check if required Python packages are installed
check_python_packages() {
    python3 -c "import paramiko, yaml" 2>/dev/null
    if [ $? -ne 0 ]; then
        echo "Error: Required Python packages (paramiko, pyyaml) are not installed"
        echo "Please install them using: pip3 install paramiko pyyaml"
        exit 1
    fi
}

# Check arguments
if [ "$#" -ne 2 ]; then
    usage
fi

# Verify source file exists
if [ ! -f "$1" ]; then
    echo "Error: Source file '$1' does not exist"
    exit 1
fi

# Check Python packages
check_python_packages

# Execute the Python script
python3 "${PYTHON_SCRIPT}" "$1" "$2" --config "${CONFIG_FILE}"
exit $?
