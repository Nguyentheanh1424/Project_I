# Password Cracker

A multi-threaded password cracker for ZIP files, supporting both brute force and dictionary-based attacks. Designed for high performance and flexibility, it uses multiple processes to efficiently test passwords.

## Features

- **Brute Force Attack:** Test all possible password combinations for ZIP files, customizable by character set and password length.
- **Dictionary Attack:** Use a wordlist to try known passwords.
- **Multi-Processing:** Utilizes multiple CPU cores for faster execution.
- **Pause and Resume:** Support for pausing and resuming operations.

### Prerequisites

- Python 3.7 or higher
- Required libraries (listed in `requirements.txt`)

### Steps

1. Clone the repository:
    ```cmd
    git clone [https://github.com/yourusername/password-cracker.git](https://github.com/Nguyentheanh1424/Project_I)
    ```
2. Install dependencies:
    ```cmd
    pip install -r requirements.txt
    ```

## Usage

### Brute Force Attack
Run the brute force attack mode with:
```cmd
python main.py --mode brute_force --zip_path <path_to_zip> --charset <charset> --min_length <min> --max_length <max>
```
Example:
```cmd
python main.py --mode brute_force --zip_path example.zip --charset abcdef123 --min_length 4 --max_length 6
```

### Dictionary Attack
Run the dictionary attack mode with:
```cmd
python main.py --mode dictionary --zip_path <path_to_zip> --wordlist_path <path_to_wordlist>
```
Example:
```cmd
python main.py --mode dictionary --zip_path example.zip --wordlist_path wordlist.txt
```

## Configuration

Settings can be customized in the `settings.json` file:
```json
{
  "charset": "abcdefghijklmnopqrstuvwxyz0123456789",
  "current_length": 4,
  "max_length": 8,
  "number_workers": 4,
  "zip_path": "example.zip",
  "wordlist_path": "wordlist.txt"
}
```

## How It Works

### Brute Force
1. The program splits the workload among multiple processes.
2. Each process generates a range of passwords to test.
3. The password is checked by attempting to extract a file from the ZIP archive.

### Dictionary
1. The wordlist is divided among multiple processes based on the line index.
2. Each process tests passwords from its assigned portion of the wordlist.

## Example

### Success Case
If the password is found, the program outputs:
```
Password: your_password, cracking time: 120.50 seconds
```

### Failure Case
If the password is not found after exhausting all possibilities:
```
Password not found, cracking time: 180.00 seconds
```

## Contributing

We welcome contributions! To get started:

1. Fork the repository.
2. Create a new branch (`git checkout -b feature-name`).
3. Commit your changes (`git commit -m "Add feature"`).
4. Push to your branch (`git push origin feature-name`).
5. Open a pull request.


## Disclaimer,

This tool is intended for educational purposes only. The author is not responsible for any misuse.

