# ZIP Password Cracker

A high-performance, multi-process ZIP file password recovery tool with an intuitive graphical interface. The application supports both brute force and dictionary-based attacks, utilizing multiple CPU cores for optimal performance.

## Features

### Core Functionality
- **Dual Attack Modes**
  - Brute Force: Systematically tests all possible combinations
  - Dictionary Attack: Tests passwords from a predefined wordlist
- **Multi-Process Architecture**
  - Leverages multiple CPU cores for parallel processing
  - Configurable number of worker processes
  - Optimized workload distribution
- **Progress Management**
  - Real-time progress tracking with ETA
  - Pause and resume functionality
  - Automatic progress saving
  - Progress recovery after interruption

### User Interface
- **Modern Graphical Interface**
  - Clean and intuitive layout
  - Real-time progress visualization
  - Status updates and ETA display
- **Customizable Settings**
  - Adjustable character sets for brute force attacks
  - Configurable maximum password length
  - Custom worker process count
  - Wordlist selection for dictionary attacks

## Installation

### Prerequisites
- Python 3.6 or higher
- Required Python packages:
  ```
  pyzipper
  psutil
  tkinter
  ```

### Setup
1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/zip-password-cracker.git
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Starting the Application
Run the application by executing:
```bash
python gui.py
```

### Brute Force Attack Configuration
1. Select "Brute Force" mode
2. Configure the following parameters:
   - **Max Length**: Maximum password length to try
   - **Character Set**: Choose from:
     - lowercase
     - uppercase
     - digits
     - special
   - Combine multiple sets using '+' (e.g., "lowercase + digits")

### Dictionary Attack Configuration
1. Select "Dictionary Attack" mode
2. Select your wordlist file using the browse button
3. Ensure your wordlist is a text file with one password per line

### Worker Process Configuration
- Set the number of worker processes (recommended: CPU cores - 2)
- Maximum value is automatically limited to your system's CPU count

### Control Options
- **Start Attack**: Begins the password recovery process
- **Pause/Resume**: Temporarily halts the process while preserving progress
- **Exit**: Safely terminates the application

## Technical Implementation

### Process Management
- Main process handles GUI and coordinates worker processes
- Worker processes handle password testing
- Inter-process communication via shared memory and queues

### Progress Tracking
- Real-time tracking of:
  - Passwords tried
  - Success rate
  - Estimated time remaining
  - Current progress percentage

### Error Handling
- Comprehensive error checking for:
  - File operations
  - Process management
  - Invalid input validation
  - Resource management

## Performance Considerations

### Optimization Techniques
- Batch processing of passwords
- Efficient memory management
- CPU affinity setting for workers
- Minimal inter-process communication

### Resource Usage
- Memory usage scales with number of workers
- CPU usage distributed across available cores
- Disk I/O minimized through buffering

## Security Notice

This tool is intended for legitimate password recovery of your own files. Usage should comply with applicable laws and regulations. The authors are not responsible for any misuse of this software.

## Error Codes and Troubleshooting

Common error messages and their solutions:
- "Invalid ZIP file path": Ensure the ZIP file exists and is accessible
- "Invalid number of CPU cores": Adjust worker count within system limits
- "Invalid character set": Verify character set syntax and combinations
- "ZIP file contains no files": Ensure ZIP file contains extractable content

## Contributing

Contributions are welcome! Please follow these steps:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

Ensure your code follows the project's style guidelines and includes appropriate tests.
