# Router Testing Automation Framework

A robust Python-based framework for automated testing of router configurations and functionality via SSH. This framework allows for systematic testing of network devices, with support for command execution, response validation, and state preservation on failure.

## Features

- **Automated SSH Connection Management**: Secure and reliable connections to network devices
- **Flexible Test Definition**: YAML-based test case definitions for easy maintenance
- **Robust Response Analysis**: Pattern matching and timeout handling for router responses
- **State Preservation**: Automatic state capture on test failures
- **Comprehensive Logging**: Detailed logging of all operations and test results
- **Error Recovery**: Graceful handling of connection issues and unexpected responses

## Prerequisites

- Python 3.8 or higher
- SSH access to target router(s)
- Network connectivity to Device Under Test (DUT)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/router-testing-automation.git
cd router-testing-automation
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install required packages:
```bash
pip install -r requirements.txt
```

## Project Structure

```
router-testing-automation/
├── src/
│   ├── __init__.py
│   ├── connection.py     # SSH connection handling
│   ├── command.py        # Command processing
│   ├── analyzer.py       # Response analysis
│   └── framework.py      # Main test framework
├── tests/
│   ├── test_cases/      # YAML test definitions
│   └── test_framework/  # Framework unit tests
├── logs/                # Test execution logs
├── requirements.txt     # Project dependencies
└── config.yaml         # Framework configuration
```

## Configuration

Create a `config.yaml` file with your router connection details:

```yaml
router:
  host: 192.168.1.1
  username: admin
  password: secret
  enable_password: enable_secret

timeouts:
  connection: 30
  command: 10
  global: 300

logging:
  level: INFO
  file: logs/router_test.log
```

## Writing Test Cases

Test cases are defined in YAML format. Example:

```yaml
test_case:
  name: "Interface Configuration Test"
  description: "Verify interface configuration and status"
  stop_on_failure: true
  commands:
    - command: "show interface GigabitEthernet0/1"
      expected_output: ".*status is up.*"
      timeout: 5
    - command: "configure terminal"
      expected_output: ".*config.*"
      timeout: 2
    - command: "interface GigabitEthernet0/1"
      expected_output: ".*config-if.*"
      timeout: 2
```

## Usage

1. Basic test execution:
```python
from src.framework import RouterTestFramework

framework = RouterTestFramework('config.yaml')
framework.run_test_suite('tests/test_cases/interface_tests.yaml')
```

2. Command line execution:
```bash
python -m src.main --config config.yaml --test-suite tests/test_cases/interface_tests.yaml
```

## Key Components

### SSHConnection Class
Handles SSH connectivity to the router:
- Connection establishment and maintenance
- Command execution
- Session management
- Timeout handling

### CommandProcessor Class
Manages command execution:
- Command sequencing
- Response collection
- Timeout management
- Error detection

### ResponseAnalyzer Class
Analyzes router responses:
- Pattern matching
- Success/failure determination
- Response validation
- Timeout processing

### TestFramework Class
Coordinates the testing process:
- Test case loading and execution
- Result collection and reporting
- State preservation
- Error handling

## Error Handling

The framework handles various error conditions:
- Connection failures
- Authentication issues
- Command timeouts
- Unexpected responses
- Pattern match failures

## Logging

Comprehensive logging is implemented:
- Test execution details
- Command inputs/outputs
- Error conditions
- Test results
- Performance metrics

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## Dependencies

- paramiko>=2.8.1
- pyyaml>=5.4.1
- pytest>=6.2.5
- pexpect>=4.8.0

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Troubleshooting

### Common Issues

1. Connection Timeouts
   - Verify network connectivity
   - Check SSH service on router
   - Confirm firewall settings

2. Authentication Failures
   - Verify credentials
   - Check enable password if required
   - Confirm user privileges

3. Pattern Match Failures
   - Review expected output patterns
   - Check for router OS version compatibility
   - Verify command syntax

## Support

For issues and feature requests, please file an issue in the GitHub repository.

## Roadmap

- [ ] Add support for multiple router vendors
- [ ] Implement parallel test execution
- [ ] Add REST API interface
- [ ] Create web-based test result viewer
- [ ] Add support for configuration backup/restore