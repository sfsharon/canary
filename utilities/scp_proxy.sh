#!/bin/bash

# Configuration
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PYTHON_SCRIPT="${SCRIPT_DIR}/proxy_scp.py"
CONFIG_FILE="${SCRIPT_DIR}/config.yaml"

# Function to display usage
usage() {
    echo "Usage: scp_proxy <operation> <source_path> <destination_path>"
    echo "Transfer files to/from router through proxy using configuration in ${CONFIG_FILE}"
    echo
    echo "Operations:"
    echo "  upload    Transfer file from local machine to router"
    echo "  download  Transfer file from router to local machine"
    echo
    echo "Arguments:"
    echo "  source_path       Path to the source file"
    echo "  destination_path  Path where the file should be placed"
    echo
    echo "Examples:"
    echo "  scp_proxy upload ~/myfile.txt /tmp/myfile.txt     # Local to router"
    echo "  scp_proxy download /tmp/myfile.txt ~/myfile.txt   # Router to local"
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
if [ "$#" -ne 3 ]; then
    usage
fi

# Verify operation is valid
if [[ ! "$1" =~ ^(upload|download)$ ]]; then
    echo "Error: Invalid operation '$1'. Must be 'upload' or 'download'"
    usage
fi

# For upload, verify source file exists locally
if [ "$1" = "upload" ] && [ ! -f "$2" ]; then
    echo "Error: Source file '$2' does not exist"
    exit 1
fi

# For download, verify destination directory exists or can be created
if [ "$1" = "download" ]; then
    dest_dir=$(dirname "$3")
    if [ ! -d "$dest_dir" ]; then
        mkdir -p "$dest_dir" || {
            echo "Error: Cannot create destination directory '$dest_dir'"
            exit 1
        }
    fi
fi

# Check Python packages
check_python_packages

# Execute the Python script
python3 "${PYTHON_SCRIPT}" "$1" "$2" "$3" --config "${CONFIG_FILE}"
exit $?