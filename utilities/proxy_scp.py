"""
SCP a file from local machine to remote router through a proxy machine, using credentials in the config.yaml file
"""
import paramiko
import yaml
import os
import logging
import argparse
from pathlib import Path

class ProxySCP:
    def __init__(self, config_path):
        """Initialize with path to YAML config file."""
        # Load configuration
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
                
        # Setup logging
        # -------------

        # Lower Paramiko's log verbosity, so that info logs from sftp.py or transport.py will be suppressed
        logging.getLogger("paramiko").setLevel(logging.WARNING)

        log_config = self.config['logging']
        log_dir = os.path.dirname(log_config['file'])
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
            
        logging.basicConfig(
            level=log_config['level'],
            format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
            handlers=[
                logging.FileHandler(log_config['file']),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Set default timeouts if not in config
        if 'timeouts' not in self.config:
            self.config['timeouts'] = {
                'connection': 30,  # Default 30 seconds for connection
                'command': 180,    # Default 180 seconds for commands
                'commit': 600      # Default 600 seconds for commits
            }
            self.logger.info("Using default timeout values: %s", self.config['timeouts'])

        # Initialize SSH clients
        self.proxy_client = paramiko.SSHClient()
        self.router_client = paramiko.SSHClient()
        
        # Auto-add host keys
        self.proxy_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.router_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    def connect(self):
        """Establish connections to proxy and router."""
        try:
            self.logger.info("Connecting to proxy %s", self.config['proxy']['host'])
            # Connect to proxy
            self.proxy_client.connect(
                hostname=self.config['proxy']['host'],
                username=self.config['proxy']['username'],
                password=self.config['proxy']['password'],
                port=self.config['proxy']['port'],
                timeout=self.config['timeouts']['connection']
            )
            
            # Create proxy channel
            self.logger.info("Creating tunnel to router %s", self.config['router']['host'])
            proxy_channel = self.proxy_client.get_transport().open_channel(
                'direct-tcpip',
                (self.config['router']['host'], self.config['router']['port']),
                ('', 0)
            )
            
            # Connect to router through proxy
            self.logger.info("Connecting to router through proxy")
            self.router_client.connect(
                hostname=self.config['router']['host'],
                username=self.config['router']['username'],
                password=self.config['router']['password'],
                port=self.config['router']['port'],
                sock=proxy_channel,
                timeout=self.config['timeouts']['connection']
            )
            
            self.logger.info("Successfully connected to proxy and router")
            return True
            
        except Exception as e:
            self.logger.error("Connection failed: %s", str(e))
            self.close()
            return False

    def transfer_file(self, local_path, remote_path):
        """Transfer file from local machine to router through proxy."""
        try:
            if not os.path.exists(local_path):
                self.logger.error("Local file does not exist: %s", local_path)
                return False
                
            self.logger.info("Opening SFTP, and starting file transfer: %s -> %s", local_path, remote_path)
            
            # Create SFTP session through the proxy connection
            sftp = self.router_client.open_sftp()
            
            self.logger.info("Put file")

            # Transfer the file
            sftp.put(local_path, remote_path)
            
            self.logger.info("Successfully transferred file")
            sftp.close()
            return True
            
        except Exception as e:
            self.logger.error("File transfer failed: %s", str(e))
            return False

    def close(self):
        """Close all connections."""
        self.logger.info("Closing connections")
        self.router_client.close()
        self.proxy_client.close()

def main():
    parser = argparse.ArgumentParser(description='Transfer files through proxy to router')
    parser.add_argument('source', help='Source file path on local machine')
    parser.add_argument('destination', help='Destination file path on router')
    parser.add_argument('--config', default='config.yaml', 
                      help='Path to YAML config file (default: config.yaml)')
    
    args = parser.parse_args()
    
    # Resolve paths
    source_path = os.path.abspath(args.source)
    config_path = os.path.abspath(args.config)
    
    # Create ProxySCP instance
    proxy_scp = ProxySCP(config_path)
    
    # Attempt connection and file transfer
    success = False
    if proxy_scp.connect():
        success = proxy_scp.transfer_file(source_path, args.destination)
    
    # Clean up
    proxy_scp.close()
    
    # Exit with appropriate status
    exit(0 if success else 1)

if __name__ == '__main__':
    main()
    