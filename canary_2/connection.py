""" SSH Connection handling """

# connection.py

import paramiko
import time
import logging
import unittest
from typing import Optional, Tuple
from dataclasses import dataclass

@dataclass
class SSHConfig:
    """Configuration for SSH connection"""
    host: str
    username: str
    password: str
    port: int = 22
    timeout: int = 30
    enable_password: Optional[str] = None

class SSHConnectionError(Exception):
    """Custom exception for SSH connection issues"""
    pass

class SSHConnection:
    def __init__(self, config: SSHConfig):
        self.config = config
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.shell = None
        self.logger = logging.getLogger(__name__)
        
    def connect(self) -> None:
        """Establishes SSH connection and opens shell"""
        try:
            self.client.connect(
                hostname=self.config.host,
                username=self.config.username,
                password=self.config.password,
                port=self.config.port,
                timeout=self.config.timeout,
                allow_agent=False,
                look_for_keys=False
            )
            self.shell = self.client.invoke_shell()
            self.shell.settimeout(self.config.timeout)
            
            # Clear initial buffer
            time.sleep(1)
            self.shell.recv(10000)
            
            # Enter enable mode if password provided
            if self.config.enable_password:
                self._enter_enable_mode()
                
        except paramiko.SSHException as e:
            raise SSHConnectionError(f"SSH connection failed: {str(e)}")
        except Exception as e:
            raise SSHConnectionError(f"Unexpected error: {str(e)}")

    def _enter_enable_mode(self) -> None:
        """Enters enable mode using provided enable password"""
        self.shell.send('enable\n')
        time.sleep(1)
        self.shell.recv(1000)  # Clear buffer
        self.shell.send(f'{self.config.enable_password}\n')
        time.sleep(1)
        response = self.shell.recv(1000).decode('utf-8')
        if '#' not in response:
            raise SSHConnectionError("Failed to enter enable mode")

    def disconnect(self) -> None:
        """Closes SSH connection"""
        if self.shell:
            self.shell.close()
        self.client.close()

    def execute_command(self, command: str, timeout: int = 10) -> Tuple[str, bool]:
        """
        Executes command and returns response
        
        Args:
            command: Command to execute
            timeout: Command timeout in seconds
            
        Returns:
            Tuple of (response_text, success_flag)
        """
        if not self.shell:
            raise SSHConnectionError("Not connected")

        try:
            # Send command
            self.shell.send(command + '\n')
            
            # Wait for response
            response = ''
            end_time = time.time() + timeout
            
            while time.time() < end_time:
                if self.shell.recv_ready():
                    chunk = self.shell.recv(4096).decode('utf-8')
                    response += chunk
                    
                    # Check if response is complete
                    if '#' in chunk or '>' in chunk:
                        return response.strip(), True
                        
                time.sleep(0.1)
                
            return response.strip(), False  # Timeout occurred
            
        except Exception as e:
            self.logger.error(f"Command execution failed: {str(e)}")
            return str(e), False

if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    # Manual testing
    config = SSHConfig("10.3.12.1", "admin", "admin")
    ssh = SSHConnection(config)
    
    # Manual setup
    logging.info("Testing connection...")
    try:
        ssh.connect()
        logging.info("Connection successful")
    except Exception as e:
        logging.error(f"Connection failed: {e}")
        exit(1)    