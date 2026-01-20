# CLI Interface Contract: Local File Watcher

**Feature**: 001-local-file-watcher
**Date**: 2026-01-19
**Type**: Command-Line Interface

## Overview

The Local File Watcher is a CLI application with no REST/GraphQL API. This document defines the command-line interface contract.

---

## Command

```bash
python -m file_watcher [OPTIONS]
```

Or if installed via pip:

```bash
file-watcher [OPTIONS]
```

---

## Arguments

### Required Arguments

| Argument | Type | Description |
|----------|------|-------------|
| `--vault` | PATH | Absolute path to Obsidian vault root directory |
| `--drop-folder` | PATH | Absolute path to folder to monitor for new files |

### Optional Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--dry-run` | FLAG | false | Log intended actions without creating files |
| `--help`, `-h` | FLAG | - | Display help message and exit |
| `--version` | FLAG | - | Display version and exit |

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Clean shutdown (SIGINT/SIGTERM) |
| 1 | Configuration error (missing args, invalid paths) |
| 2 | Startup error (folder validation failed) |

---

## Usage Examples

### Basic Usage

```bash
python -m file_watcher \
  --vault /home/user/ObsidianVault \
  --drop-folder /home/user/DropBox
```

### Dry Run Mode

```bash
python -m file_watcher \
  --vault /home/user/ObsidianVault \
  --drop-folder /home/user/DropBox \
  --dry-run
```

### Windows Paths

```powershell
python -m file_watcher `
  --vault "C:\Users\user\ObsidianVault" `
  --drop-folder "C:\Users\user\DropFolder"
```

### With Log Redirection

```bash
python -m file_watcher \
  --vault /path/to/vault \
  --drop-folder /path/to/drop \
  > watcher.log 2>&1
```

---

## Output Format

### Standard Output (stdout)

JSON-formatted log entries for INFO and DEBUG levels:

```json
{"timestamp": "2026-01-19T10:30:00.000Z", "level": "INFO", "message": "File watcher started", "action_type": "startup", "vault_path": "/path/to/vault", "drop_folder": "/path/to/drop", "dry_run": false}
{"timestamp": "2026-01-19T10:30:05.000Z", "level": "INFO", "message": "File detected", "action_type": "file_detected", "source_file": "/path/to/drop/report.pdf", "size": 1048576}
{"timestamp": "2026-01-19T10:30:05.050Z", "level": "INFO", "message": "Action file created", "action_type": "action_created", "source_file": "/path/to/drop/report.pdf", "action_file": "/path/to/vault/Needs_Action/FILE_report.pdf.md"}
```

### Standard Error (stderr)

JSON-formatted log entries for ERROR and WARNING levels:

```json
{"timestamp": "2026-01-19T10:30:10.000Z", "level": "ERROR", "message": "Failed to create action file", "action_type": "error", "source_file": "/path/to/drop/report.pdf", "error": "Permission denied", "traceback": "..."}
```

---

## Validation Errors

### Missing Required Arguments

```
usage: file_watcher [-h] --vault VAULT --drop-folder DROP_FOLDER [--dry-run]
file_watcher: error: the following arguments are required: --vault, --drop-folder
```

Exit code: 1

### Invalid Vault Path

```json
{"timestamp": "...", "level": "ERROR", "message": "Vault path does not exist", "path": "/invalid/path"}
```

Exit code: 2

### Invalid Drop Folder Path

```json
{"timestamp": "...", "level": "ERROR", "message": "Drop folder does not exist", "path": "/invalid/path"}
```

Exit code: 2

### Missing Needs_Action Folder

```json
{"timestamp": "...", "level": "ERROR", "message": "Needs_Action folder not found in vault", "expected_path": "/path/to/vault/Needs_Action"}
```

Exit code: 2

### Same Path Error

```json
{"timestamp": "...", "level": "ERROR", "message": "Vault and drop folder cannot be the same path", "path": "/same/path"}
```

Exit code: 2

---

## Signal Handling

| Signal | Behavior |
|--------|----------|
| SIGINT (Ctrl+C) | Graceful shutdown, log shutdown message, exit 0 |
| SIGTERM | Graceful shutdown, log shutdown message, exit 0 |

### Shutdown Log

```json
{"timestamp": "...", "level": "INFO", "message": "File watcher stopped", "action_type": "shutdown", "reason": "SIGINT received"}
```

---

## Environment Variables

None required. All configuration via CLI arguments.

Future consideration (Silver tier): `FILE_WATCHER_CONFIG` for config file path.
