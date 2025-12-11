# Serect-hunter

A lightweight **Static Application Security Testing (SAST)** tool designed to scan directories and detect exposed sensitive information (e.g., API keys, passwords, tokens) in your source code or configuration files.

**Automated Scanning**: Recursively scans files in the dedicated target directory.

**Regex-Based Detection**: Uses regular expressions for efficient and flexible pattern matching.

**Configurable Rules**: Custom detection rules can be defined in `keyword.txt` without modifying the source code.

**Safe Architecture**: Scans a dedicated `checkingFile` directory to prevent accidental scanning of system files or the tool itself.
