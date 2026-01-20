# Data Model: Local File Watcher Service

**Feature**: 001-local-file-watcher
**Date**: 2026-01-19
**Phase**: 1 - Design

## Overview

This document defines the data structures and file formats used by the Local File Watcher Service. As a file-based system with no database, the "data model" consists of file formats, naming conventions, and directory structures.

---

## Entities

### 1. ActionFile

Represents a task created in the Obsidian vault when a file is dropped.

**Location**: `{vault_path}/Needs_Action/FILE_{original_filename}.md`

**Structure**:
```yaml
---
type: file_drop
original_name: string      # Original filename with extension
size: integer             # File size in bytes
timestamp: string         # ISO 8601 format (UTC)
status: string            # Always "pending" on creation
source_path: string       # Absolute path to original file
---

## New File Dropped

**File**: {original_name}

New file dropped for processing.
```

**Field Definitions**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| type | string | Yes | Always `file_drop` for this watcher |
| original_name | string | Yes | Original filename including extension |
| size | integer | Yes | File size in bytes (0 for empty files) |
| timestamp | string | Yes | Creation time in ISO 8601 UTC format |
| status | string | Yes | Always `pending` when created |
| source_path | string | Yes | Absolute path to file in drop folder |

**Validation Rules**:
- `type` must be exactly `file_drop`
- `original_name` must not be empty
- `size` must be >= 0
- `timestamp` must be valid ISO 8601 format
- `source_path` must exist at creation time

**Example**:
```yaml
---
type: file_drop
original_name: Quarterly_Report_2026.pdf
size: 2458624
timestamp: 2026-01-19T10:30:00Z
status: pending
source_path: C:/Users/user/DropFolder/Quarterly_Report_2026.pdf
---

## New File Dropped

**File**: Quarterly_Report_2026.pdf

New file dropped for processing.
```

---

### 2. WatcherConfig

Runtime configuration for the file watcher service.

**Not persisted** - exists only as in-memory state from CLI arguments.

**Fields**:

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| vault_path | Path | Yes | - | Absolute path to Obsidian vault root |
| drop_folder | Path | Yes | - | Absolute path to monitored folder |
| dry_run | boolean | No | false | If true, log only without creating files |
| needs_action_path | Path | Derived | - | `{vault_path}/Needs_Action` |

**Validation Rules**:
- `vault_path` must exist and be a directory
- `drop_folder` must exist and be a directory
- `vault_path` and `drop_folder` must be different paths
- `needs_action_path` must exist (derived from vault_path)

---

### 3. LogEntry

Structured log entry format for all watcher operations.

**Output**: stdout (INFO, DEBUG) and stderr (ERROR, WARNING)

**Schema**:
```json
{
  "timestamp": "2026-01-19T10:30:00.000Z",
  "level": "INFO",
  "logger": "file_watcher",
  "message": "string",
  "action_type": "string",
  "details": {}
}
```

**Action Types**:

| action_type | Description | Additional Fields |
|-------------|-------------|-------------------|
| startup | Service started | vault_path, drop_folder, dry_run |
| file_detected | New file found | source_file, size |
| action_created | Action file written | source_file, action_file |
| action_skipped | Dry-run mode skip | source_file, would_create |
| error | Operation failed | source_file, error, traceback |
| shutdown | Service stopping | reason |

---

## File Naming Conventions

### Action File Names

**Pattern**: `FILE_{original_filename}.md`

**Rules**:
1. Prefix: Always `FILE_` to identify source type
2. Original name: Preserved exactly, including extension
3. Suffix: Always `.md` for Markdown

**Duplicate Handling**:
When a file with the same name already exists in `/Needs_Action`:

**Pattern**: `FILE_{original_filename}_{timestamp}.md`

Where timestamp is: `YYYYMMDDTHHMMSS` (file-safe ISO format)

**Examples**:
```
FILE_report.pdf.md                      # First occurrence
FILE_report.pdf_20260119T103005.md      # Duplicate at 10:30:05
FILE_My Report (Final).pdf.md           # Spaces and special chars preserved
FILE_日本語ファイル.txt.md               # Unicode preserved
```

---

## Directory Structure

### Obsidian Vault (Pre-existing)

```
{vault_path}/
├── Needs_Action/          # Target for action files (MUST exist)
│   ├── FILE_*.md         # Created by file watcher
│   └── EMAIL_*.md        # Created by other watchers (future)
├── Done/                  # Completed tasks (managed elsewhere)
├── Inbox/                 # General inbox (not used by watcher)
└── Dashboard.md           # Main dashboard (not used by watcher)
```

### Drop Folder (User-managed)

```
{drop_folder}/
├── report.pdf            # Files dropped by user
├── invoice.xlsx          # Stay here after processing
└── photo.jpg             # User cleans up manually
```

---

## State Transitions

The ActionFile entity has a simple lifecycle:

```
[Created] → pending → (processed by Claude Code) → moved to /Done
```

**File Watcher Responsibility**: Only the `pending` state (creation)

**Out of Scope**: All subsequent state transitions are handled by Claude Code reasoning layer.

---

## Relationships

```
┌─────────────────┐         ┌─────────────────┐
│   Drop Folder   │         │  Obsidian Vault │
│                 │         │                 │
│  ┌───────────┐  │  1:1    │  ┌───────────┐  │
│  │ User File │──┼────────▶│  │ActionFile │  │
│  └───────────┘  │ creates │  └───────────┘  │
│                 │         │                 │
└─────────────────┘         └─────────────────┘
         │                           │
         │                           │
         ▼                           ▼
    [Unchanged]                [Consumed by
     by watcher               Claude Code]
```

**Cardinality**:
- Each dropped file creates exactly one ActionFile
- ActionFile references source file via `source_path`
- Original file is never modified by watcher
