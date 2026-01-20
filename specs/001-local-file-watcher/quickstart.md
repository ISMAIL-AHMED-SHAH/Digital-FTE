# Quickstart: Local File Watcher Service

**Feature**: 001-local-file-watcher
**Date**: 2026-01-19

## Prerequisites

- Python 3.13 or higher
- An existing Obsidian vault with `/Needs_Action` folder
- A drop folder to monitor (separate from the vault)

---

## Installation

### 1. Clone and Setup

```bash
cd /path/to/Hackathon-0
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -e .
```

### 2. Verify Installation

```bash
python -m file_watcher --help
```

Expected output:
```
usage: file-watcher [-h] --vault PATH --drop-folder PATH [--dry-run]
                    [--version]

Local File Watcher Service for Bona-Papa AI Employee. Monitors a drop folder
and creates action items in Obsidian vault.

options:
  -h, --help          show this help message and exit
  --vault PATH        Absolute path to Obsidian vault root directory
  --drop-folder PATH  Absolute path to folder to monitor for new files
  --dry-run           Log intended actions without creating files
  --version           show program's version number and exit
```

---

## Quick Start (5 minutes)

### Step 1: Prepare Your Vault

Ensure your Obsidian vault has the required folder structure:

```bash
# Create Needs_Action folder if it doesn't exist
mkdir -p /path/to/your/vault/Needs_Action
```

### Step 2: Create a Drop Folder

```bash
# Create a folder to drop files into
mkdir -p ~/DropFolder
```

### Step 3: Test with Dry Run

```bash
python -m file_watcher \
  --vault /path/to/your/vault \
  --drop-folder ~/DropFolder \
  --dry-run
```

### Step 4: Drop a Test File

In another terminal:

```bash
echo "Test content" > ~/DropFolder/test.txt
```

You should see output like:
```json
{"timestamp": "...", "level": "INFO", "message": "File detected", "action_type": "file_detected", "source_file": "~/DropFolder/test.txt", "size": 13}
{"timestamp": "...", "level": "INFO", "message": "Would create action file (dry-run)", "action_type": "action_skipped", "would_create": "/path/to/vault/Needs_Action/FILE_test.txt.md"}
```

### Step 5: Run for Real

Stop dry-run mode (Ctrl+C), then run without `--dry-run`:

```bash
python -m file_watcher \
  --vault /path/to/your/vault \
  --drop-folder ~/DropFolder
```

Drop another file and check your vault:

```bash
ls /path/to/your/vault/Needs_Action/
# Should show: FILE_test.txt.md
```

---

## Verify It Works

### Check the Action File

Open the created action file in Obsidian or view it:

```bash
cat /path/to/your/vault/Needs_Action/FILE_test.txt.md
```

Expected content:
```yaml
---
type: file_drop
original_name: test.txt
size: 13
timestamp: 2026-01-19T10:30:00Z
status: pending
source_path: /home/user/DropFolder/test.txt
---

## New File Dropped

**File**: test.txt

New file dropped for processing.
```

---

## Common Operations

### Run with Log File

```bash
python -m file_watcher \
  --vault /path/to/vault \
  --drop-folder ~/DropFolder \
  > watcher.log 2>&1 &
```

### View Logs in Real-time

```bash
tail -f watcher.log | jq .
```

### Stop the Watcher

```bash
# If running in foreground
Ctrl+C

# If running in background
pkill -f "python -m file_watcher"
```

---

## Troubleshooting

### "Vault path does not exist"

Ensure the vault path is an absolute path and the directory exists:

```bash
ls -la /path/to/your/vault
```

### "Needs_Action folder not found"

Create the required folder:

```bash
mkdir -p /path/to/your/vault/Needs_Action
```

### "Permission denied"

Ensure write permissions on the vault:

```bash
chmod 755 /path/to/your/vault/Needs_Action
```

### No files detected

1. Check the watcher is running (look for startup log)
2. Verify you're dropping files into the correct folder
3. Only new files trigger events (existing files are ignored)

---

## Next Steps

After verifying the file watcher works:

1. **Bronze Tier Complete**: You now have the perception layer for file-based tasks
2. **Add to Startup**: Consider adding to your system startup (Silver tier)
3. **Integrate with Claude Code**: Point Claude Code at your vault (next phase)

---

## Configuration Reference

| Option | Required | Description |
|--------|----------|-------------|
| `--vault` | Yes | Absolute path to Obsidian vault |
| `--drop-folder` | Yes | Absolute path to folder to monitor |
| `--dry-run` | No | Test mode - log only, no file creation |
