""" SSH Connection handling """

# connection.py

import paramiko
import time
import logging
import unittest
from typing import Optional, Tuple, Dict, List
from dataclasses import dataclass

@dataclass
class ProxyConfig:
    """Configuration for proxy (jump) host"""
    host: str
    username: str
    password: str
    port: int = 22
    host_key_algorithms: Optional[List[str]] = None

@dataclass
class SSHConfig:
    """Configuration for SSH connection"""
    host: str
    username: str
    password: str
    port: int = 22
    timeout: int = 30
    enable_password: Optional[str] = None
    proxy: Optional[ProxyConfig] = None
    host_key_algorithms: Optional[List[str]] = None

class SSHConnectionError(Exception):
    """Custom exception for SSH connection issues"""
    pass

class SSHConnection:
    def __init__(self, config: SSHConfig):
        self.config = config
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.proxy_client = None
        self.shell = None
        self.logger = logging.getLogger(__name__)

    def _create_proxy_channel(self) -> paramiko.Channel:
        """Creates SSH channel through proxy"""
        try:
            # Connect to proxy host
            self.proxy_client = paramiko.SSHClient()
            self.proxy_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Connect to proxy
            transport = paramiko.Transport((self.config.proxy.host, self.config.proxy.port))
            
            # Set host key algorithms if specified
            if self.config.proxy.host_key_algorithms:
                transport.get_security_options().key_types = tuple(self.config.proxy.host_key_algorithms)
            
            transport.connect(
                username=self.config.proxy.username,
                password=self.config.proxy.password
            )
            
            # Create channel to target through proxy
            dest_addr = (self.config.host, self.config.port)
            local_addr = (self.config.proxy.host, self.config.proxy.port)
            channel = transport.open_channel("direct-tcpip", dest_addr, local_addr)
            
            return channel
            
        except Exception as e:
            if self.proxy_client:
                self.proxy_client.close()
            raise SSHConnectionError(f"Proxy connection failed: {str(e)}")
            
    def connect(self) -> None:
        """Establishes SSH connection (direct or through proxy) and opens shell"""
        try:
            # Set up the transport
            if self.config.proxy:
                sock = self._create_proxy_channel()
                transport = paramiko.Transport(sock)
            else:
                transport = paramiko.Transport((self.config.host, self.config.port))
            
            # Set host key algorithms if specified
            if self.config.host_key_algorithms:
                transport.get_security_options().key_types = tuple(self.config.host_key_algorithms)
            
            # Connect transport
            transport.connect(
                username=self.config.username,
                password=self.config.password
            )
            
            # Create client using transport
            self.client._transport = transport
            
            # Create shell
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
        """Closes SSH connection and proxy if used"""
        if self.shell:
            self.shell.close()
        if self.client:
            self.client.close()
        if self.proxy_client:
            self.proxy_client.close()

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
                    if '#' in chunk or 'exaware' in chunk:
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
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Example usage with proxy jump
    config = SSHConfig(
        host="10.3.12.1",
        username="admin",
        password="admin",
        proxy=ProxyConfig(
            host="172.30.16.107",
            username="my_dev_user",
            password="my_dev_password",
            host_key_algorithms=['ssh-rsa', 'ssh-dss']
        ),
        host_key_algorithms=['ssh-rsa', 'ssh-dss']
    )
    
    ssh = SSHConnection(config)
    try:
        ssh.connect()
        logging.info("Connection successful")
        response, success = ssh.execute_command("show sys mod")
        logging.info(f"\nSuccess: {success}\nResponse:\n{response}")

    except SSHConnectionError as e:
        logging.error(f"Connection failed: {e}")
    finally:
        ssh.disconnect()
    