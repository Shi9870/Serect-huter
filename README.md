# Serect-hunter

A lightweight **Static Application Security Testing (SAST)** tool designed to scan directories and detect exposed sensitive information (e.g., API keys, passwords, tokens) in your source code or configuration files.

**Automated Scanning**: Recursively scans files in the dedicated target directory.

**Regex-Based Detection**: Uses regular expressions for efficient and flexible pattern matching.

**Configurable Rules**: Custom detection rules can be defined in `keyword.txt` without modifying the source code.

**Safe Architecture**: Scans a dedicated `checkingFile` directory to prevent accidental scanning of system files or the tool itself.
---
## Installation & Usage
### 1. Clone the repository
```bash
git clone [https://github.com/Shi9870/Serect-huter.git](https://github.com/Shi9870/Serect-huter.git)
cd Serect-huter
```
2.Prepare the enviroment
Ensure there is a folder named checkingFile inside the project directory. Place the files you want to scan inside it.
```
Secret Hunter/
├── scanner.py
├── keyword.txt
└── checkingFile/       
    ├── config.txt
    └── user_data.json
```
3.Run the scanner
Execute the script using Python:
```python scanner.py```
#Configuration
You can customize the detection logic by editing the keyword.txt file. Add specific keywords or patterns you want to search for (one per line).
Example keyword.txt:
```
password
secret
api_key
access_token
AWS_ACCESS_KEY_ID
```
Example Output
```
============== Scan Start ==============
  leaking file: ...\checkingFile\config.txt
   Line: 12
   Content: AWS_SECRET_KEY = "AKIAIOSFODNN7EXAMPLE"
------------------------------
```
---

# Disclaimer
This tool is intended for educational purposes and self-assessment only. Please do not use it to scan codebases or systems you do not have permission to access.

---
Created by Shi9870
