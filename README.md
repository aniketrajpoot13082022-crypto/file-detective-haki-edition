
# ⚔️ File Detective — Haki Edition

A Python desktop application with an anime-inspired
black-and-crimson interface that detects duplicate files.

## Features
- Animated Haki-inspired interface
- Folder and subfolder scanning
- Duplicate detection using SHA-256 hashes
- Live scan progress
- Duplicate group statistics
- CSV report export
- Read-only scanning

## Technologies
- Python
- Tkinter
- hashlib
- pathlib and os
- threading and queue
- CSV
- unittest

## Run the application

```bash
python rinkusingh.py
```

## Run the tests

```bash
python -m unittest -v test_main.py
```

## How it works

1. Scans the selected folder.
2. Groups files with matching sizes.
3. Calculates SHA-256 hashes.
4. Groups files with matching hashes.
5. Displays duplicate files and exports reports.

## Safety

The application does not automatically delete files.

## Future improvements
- Scan cancellation
- Sortable results table
- File-type filters
- Windows executable packaging
