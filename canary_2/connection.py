""" SSH Connection handling 
SSH-ing through proxy (dev machine) :
ssh -o HostKeyAlgorithms=+ssh-rsa,ssh-dss -J sharonf@172.30.16.107 admin@10.3.12.1
"""

# connection.py
import paramiko
import time
import logging
import yaml
import os
from typing import Optional, Tuple, List
from dataclasses import dataclass
from tqdm import tqdm
import sys
from datetime import datetime, timedelta

@dataclass
class ProxyConfig:
    """Configuration for proxy (jump) host"""
    host: str
    username: str
    password: str
    port: int
    host_key_algorithms: Optional[List[str]] = None

@dataclass
class SSHConfig:
    """Configuration for SSH connection"""

    # Class defaults
    DEFAULT_PORT = 22
    DEFAULT_CONNECTION_TIMEOUT  = 30
    DEFAULT_COMMAND_TIMEOUT     = 100
    DEFAULT_COMMIT_TIMEOUT      = 600

    host: str
    username: str
    password: str
    port: int = DEFAULT_PORT
    connection_timeout: int = DEFAULT_CONNECTION_TIMEOUT
    command_timeout: int    = DEFAULT_COMMAND_TIMEOUT
    commit_timeout: int     = DEFAULT_COMMIT_TIMEOUT
    proxy: Optional[ProxyConfig] = None
    host_key_algorithms: Optional[List[str]] = None

    @classmethod
    def from_yaml(cls):
        """Load configuration from YAML file in the same directory"""
        config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Create proxy config if specified
        proxy = None
        if 'proxy' in config:
            proxy = ProxyConfig(
                host                = config['proxy']['host'],
                username            = config['proxy']['username'],
                password            = config['proxy']['password'],
                port                = config['proxy'].get('port', cls.DEFAULT_PORT),
                host_key_algorithms = config['proxy'].get('host_key_algorithms')
            )

        return cls(
            host                = config['router']['host'],
            username            = config['router']['username'],
            password            = config['router']['password'],
            port                = config['router'].get('port', cls.DEFAULT_PORT),
            connection_timeout  = config.get('timeouts', {}).get('connection',  cls.DEFAULT_CONNECTION_TIMEOUT),
            command_timeout     = config.get('timeouts', {}).get('command',     cls.DEFAULT_COMMAND_TIMEOUT),
            commit_timeout      = config.get('timeouts', {}).get('commit',      cls.DEFAULT_COMMIT_TIMEOUT),
            proxy               = proxy,
            host_key_algorithms = config['router'].get('host_key_algorithms')
        )

class SSHConnectionError(Exception):
    """Custom exception for SSH connection issues"""
    pass

class PromptTimeoutError(SSHConnectionError):
    """Custom exception for prompt timeout"""
    pass

class SSHConnection:
    EXPECTED_OPER_PROMPT     = "exaware#"
    EXPECTED_CONF_PROMPT     = "exaware(config)#"
    PROMPT_CHECK_INTERVAL    = 0.1  # seconds
    PROGRESS_UPDATE_INTERVAL = 0.5  # seconds
    
    def __init__(self, config: Optional[SSHConfig] = None):
        self.config = config or SSHConfig.from_yaml()

        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.proxy_client = None
        self.shell = None
        self.logger = logging.getLogger(__name__)
        self.expected_prompt = self.EXPECTED_OPER_PROMPT

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
        """
        Establishes SSH connection (direct or through proxy) and opens shell
        Ensures connection is only established after seeing the expected prompt
        """
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
            self.shell.settimeout(self.config.connection_timeout)
            
            # Wait for initial prompt
            if not self._wait_for_prompt():
                raise SSHConnectionError("Failed to get initial prompt")
           
        except PromptTimeoutError as e:
            raise SSHConnectionError(f"Failed to get expected prompt: {str(e)}")
        except paramiko.SSHException as e:
            raise SSHConnectionError(f"SSH connection failed: {str(e)}")
        except Exception as e:
            raise SSHConnectionError(f"Unexpected error: {str(e)}")

    def _wait_for_prompt(self) -> bool:
        """
        Wait for the expected prompt to appear
                  
        Returns:
            True if prompt found, False if timeout
            
        Raises:
            PromptTimeoutError: If prompt not found within timeout
        """
        self.logger.debug(f"Waiting for prompt '{self.expected_prompt}'")
        end_time = time.time() + self.config.command_timeout
        buffer = ""
        
        while time.time() < end_time:
            if self.shell.recv_ready():
                chunk = self.shell.recv(4096).decode('utf-8')
                buffer += chunk
                
                if self.expected_prompt in buffer:
                    self.logger.debug("Expected prompt found")
                    return True
                    
            time.sleep(self.PROMPT_CHECK_INTERVAL)
            
        raise PromptTimeoutError(
            f"Timed out waiting for prompt '{self.expected_prompt}'. "
            f"Last received buffer: {buffer}"
        )

    def enter_configure_mode(self) -> None:
        """Enters configuration mode"""
        self.expected_prompt = self.EXPECTED_CONF_PROMPT
        self.shell.send('configure\n')
       
        # Wait for prompt after configure command
        if not self._wait_for_prompt():
            raise SSHConnectionError("Failed to get prompt after enable command")

    @staticmethod
    def _format_remaining_time(seconds: float) -> str:
        """Format remaining time as MM:SS"""
        return str(timedelta(seconds=int(seconds))).split('.')[0]

    def execute_command(self, command: str) -> Tuple[str, bool]:
        """
        Executes command and returns response with progress bar
        
        Args:
            command: Command to execute
            
        Returns:
            Tuple of (response_text, success_flag)
        """
        if not self.shell:
            raise SSHConnectionError("Not connected")

        try:
            # Send command
            logging.info(f"Sending command \"{command}\"")
            self.shell.send(command + '\n')
            
            # Initialize progress tracking
            response = ''
            start_time = time.time()
            end_time = start_time + self.config.commit_timeout
            total_timeout = self.config.commit_timeout

            # Create progress bar
            with tqdm(
                total=total_timeout,
                desc=f"Executing: {command}",
                bar_format='{desc}: {percentage:3.0f}%|{bar}| {n:.1f}/{total:.1f}s [ETA: {remaining}]',
                unit='s',
                file=sys.stdout
            ) as pbar:
                
                last_update = start_time
                completion_time = None
                
                while time.time() < end_time:
                    current_time = time.time()
                    elapsed = current_time - start_time
                    
                    # Only update if we haven't completed the command
                    if completion_time is None:                    
                        # Update progress bar at specified interval
                        if current_time - last_update >= self.PROGRESS_UPDATE_INTERVAL:
                            pbar.n = elapsed
                            remaining_time = self._format_remaining_time(total_timeout - elapsed)
                            pbar.set_postfix({'Remaining': remaining_time}, refresh=True)
                            last_update = current_time
                    
                    # Check for response
                    if self.shell.recv_ready():
                        chunk = self.shell.recv(4096).decode('utf-8')
                        response += chunk
                        
                        # Check if response is complete (includes prompt)
                        if self.expected_prompt in chunk and completion_time is None:
                            completion_time = elapsed
                            # Set the final progress bar position
                            pbar.n = completion_time
                            pbar.refresh()
                            # Update description to show completion
                            pbar.set_description(f"Completed: {command}")
                            pbar.set_postfix({'Time': f'{completion_time:.1f}s'}, refresh=True)
                            return response.strip(), True
                    
                    time.sleep(self.PROMPT_CHECK_INTERVAL)

            # If we get here, timeout occurred
            logging.error(f"Command {command} - Timeout {self.config.commit_timeout} seconds exceeded waiting for prompt {self.expected_prompt}")    
            return response.strip(), False
                    
        except Exception as e:
            self.logger.error(f"Command execution failed: {str(e)}")
            return str(e), False

    def disconnect(self) -> None:
        """Closes SSH connection and proxy if used"""
        if self.shell:
            self.shell.close()
        if self.client:
            self.client.close()
        if self.proxy_client:
            self.proxy_client.close()

if __name__ == "__main__":
    NUM_OF_ITERATIONS = 7

    # Setup logging   
    logging.basicConfig(
        format='\n%(asctime)s.%(msecs)03d [%(filename)s line %(lineno)d] %(levelname)-8s %(message)s',
        level=logging.INFO,
        datefmt='%H:%M:%S')

    # Create SSH connection using config from YAML
    ssh = SSHConnection()
    try:
        ssh.connect()
        logging.info("Connection successful")

        # Show system module
        response, success = ssh.execute_command("show sys mod")
        logging.info(f"\nSuccess: {success}\nResponse:\n{response}")

        # Change to Configuration mode
        ssh.enter_configure_mode()

        # Run testing iterations
        for i in range(NUM_OF_ITERATIONS) :
            logging.info(f"Iteration {i + 1}\n" + "-" * 80)
            # Clean previous configuration
            response, success = ssh.execute_command("load override exaSystemConf_pc3012.cfg ; commit")
            logging.info(f"\nSuccess: {success}\nResponse:\n{response}")
            if success == False :
                logging.error("Bailing out")

            # Configure new configuration
            response, success = ssh.execute_command("load merge TC10_112_PwScale.cfg ; commit")
            logging.info(f"\nSuccess: {success}\nResponse:\n{response}")
            if success == False :
                logging.error("Bailing out")

    except SSHConnectionError as e:
        logging.error(f"Connection failed: {e}")
    finally:
        ssh.disconnect()