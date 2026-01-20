# Research: Local File Watcher Service

**Feature**: 001-local-file-watcher
**Date**: 2026-01-19
**Phase**: 0 - Research

## Overview

This document captures technology decisions and best practices research for implementing the Local File Watcher Service.

---

## Decision 1: File System Monitoring Library

### Decision
Use **watchdog** library for cross-platform file system event monitoring.

### Rationale
- **Cross-platform**: Works on Windows (ReadDirectoryChangesW), macOS (FSEvents), and Linux (inotify)
- **Event-based**: Provides real-time file creation events without polling
- **Mature**: Well-maintained, widely used (7M+ monthly downloads)
- **Simple API**: `Observer` + `FileSystemEventHandler` pattern is straightforward
- **Python 3.13 compatible**: No known compatibility issues

### Alternatives Considered

| Alternative | Reason Rejected |
|-------------|-----------------|
| `os.walk` + polling | Higher latency, more CPU usage, not event-based |
| `inotify` (Linux only) | Not cross-platform (Windows/macOS unsupported) |
| `pyinotify` | Linux-only, less actively maintained |
| `aiofiles` + polling | Async adds complexity; not event-based |

### Implementation Notes
- Use `watchdog.observers.Observer` for the main event loop
- Subclass `watchdog.events.FileSystemEventHandler` for custom handling
- Handle `on_created` event only (per FR-001: new files only)
- Ignore `on_modified`, `on_deleted`, `on_moved` events

---

## Decision 2: CLI Argument Parsing

### Decision
Use **argparse** (standard library) for command-line interface.

### Rationale
- **No external dependency**: Part of Python standard library
- **Sufficient features**: Supports required args, optional flags, help text
- **Well-documented**: Familiar to most Python developers
- **Type hints compatible**: Works with modern Python patterns

### Alternatives Considered

| Alternative | Reason Rejected |
|-------------|-----------------|
| `click` | External dependency for simple use case |
| `typer` | External dependency, overkill for 3-4 arguments |
| `sys.argv` manual parsing | Error-prone, no built-in validation |

### CLI Interface Design
```
python -m file_watcher --vault /path/to/vault --drop-folder /path/to/drop [--dry-run]
```

Required arguments:
- `--vault`: Path to Obsidian vault root
- `--drop-folder`: Path to folder to monitor

Optional flags:
- `--dry-run`: Log actions without creating files (per FR-008)
- `--help`: Display usage information

---

## Decision 3: Structured JSON Logging

### Decision
Use **python-json-logger** for structured JSON log output.

### Rationale
- **Simple integration**: Drop-in replacement for standard logging formatter
- **Constitution compliant**: Produces JSON format per Principle VI
- **Queryable output**: Logs can be parsed with jq or imported into log aggregators
- **Lightweight**: Minimal dependency footprint

### Alternatives Considered

| Alternative | Reason Rejected |
|-------------|-----------------|
| `structlog` | More complex setup than needed |
| Custom JSON formatter | Reinventing existing solution |
| Standard logging (text) | Not JSON format, harder to parse |

### Log Format
```json
{
  "timestamp": "2026-01-19T10:30:00.000Z",
  "level": "INFO",
  "message": "File detected",
  "actor": "file_watcher",
  "action_type": "file_created",
  "source_file": "/drop/report.pdf",
  "action_file": "/vault/Needs_Action/FILE_report.pdf.md"
}
```

---

## Decision 4: YAML Frontmatter Generation

### Decision
Use **PyYAML** for generating YAML frontmatter in action files.

### Rationale
- **Obsidian compatible**: Standard YAML frontmatter format
- **Safe dumping**: Prevents code injection via `safe_dump`
- **Widely used**: De facto standard for YAML in Python
- **Simple API**: `yaml.safe_dump()` handles all cases

### Alternatives Considered

| Alternative | Reason Rejected |
|-------------|-----------------|
| Manual string formatting | Error-prone for special characters |
| `ruamel.yaml` | More complex, round-trip features not needed |
| `toml` | Not standard for Obsidian frontmatter |

### Frontmatter Schema
```yaml
---
type: file_drop
original_name: report.pdf
size: 1048576
timestamp: 2026-01-19T10:30:00Z
status: pending
---
```

---

## Decision 5: Duplicate Filename Handling

### Decision
Append **timestamp suffix** (ISO format, file-safe) when duplicate detected.

### Rationale
- **Unique**: Millisecond precision ensures uniqueness
- **Sortable**: ISO format sorts chronologically
- **Debuggable**: Timestamp shows when duplicate occurred
- **Simple**: No counter state to maintain across restarts

### Pattern
```
FILE_report.pdf.md                    # First occurrence
FILE_report.pdf_2026-01-19T103005.md  # Duplicate at 10:30:05
FILE_report.pdf_2026-01-19T103010.md  # Another at 10:30:10
```

### Alternatives Considered

| Alternative | Reason Rejected |
|-------------|-----------------|
| Counter suffix (_1, _2) | Requires persistent state across restarts |
| UUID suffix | Not human-readable, harder to debug |
| Overwrite | Violates data integrity expectations |
| Reject duplicate | Poor user experience |

---

## Decision 6: Error Handling Strategy

### Decision
Use **catch-and-log** pattern with continued operation.

### Rationale
- **Crash-resistant**: Per FR-007, service must continue after errors
- **Observable**: All errors logged for debugging
- **Simple**: No complex retry or circuit-breaker logic for Bronze tier
- **User-friendly**: Service doesn't require manual restart

### Error Categories

| Error Type | Handling |
|------------|----------|
| File read error (drop folder) | Log warning, skip file, continue |
| File write error (vault) | Log error, skip file, continue |
| Permission denied | Log error, continue monitoring |
| Disk full | Log error, continue monitoring |
| Watcher crash | Log error, attempt restart |

### Implementation Notes
- Wrap each file event handler in try/except
- Log full exception details including traceback
- Never raise exceptions from event handlers
- Log at ERROR level for failures, INFO for successes

---

## Decision 7: File System Event Debouncing

### Decision
Rely on **watchdog's built-in behavior** (no custom debouncing).

### Rationale
- **Simplicity**: Avoid adding complexity for edge case
- **Watchdog handles it**: Library already coalesces rapid events
- **Bronze tier scope**: Advanced debouncing is Silver/Gold complexity
- **Idempotent design**: Duplicate detection handles any leakage

### Notes
- Large file copies may trigger multiple events; watchdog typically handles this
- If issues arise in testing, can add simple cooldown per filename
- Duplicate filename handling provides safety net

---

## Dependencies Summary

| Package | Version | Purpose |
|---------|---------|---------|
| watchdog | >=4.0.0 | File system event monitoring |
| PyYAML | >=6.0 | YAML frontmatter generation |
| python-json-logger | >=2.0.0 | Structured JSON logging |

### Development Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| pytest | >=8.0.0 | Testing framework |
| pytest-timeout | >=2.0.0 | Test timeout handling |

---

## References

- [watchdog documentation](https://python-watchdog.readthedocs.io/)
- [Obsidian YAML frontmatter](https://help.obsidian.md/Editing+and+formatting/Properties)
- [python-json-logger](https://github.com/madzak/python-json-logger)
- [Bona-Papa Constitution](../../.specify/memory/constitution.md)
