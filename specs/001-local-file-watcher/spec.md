# Feature Specification: Local File Watcher Service

**Feature Branch**: `001-local-file-watcher`
**Created**: 2026-01-19
**Status**: Draft
**Tier**: Bronze (Foundation)
**Input**: User description: "Create a Local File Watcher Service for Bronze Tier that monitors file system for dropped files and creates action items in Obsidian vault"

## Clarifications

### Session 2026-01-19

- Q: What happens to the original dropped file after processing? → A: Leave in drop folder (user manages cleanup)
- Q: What content goes in the action file body after frontmatter? → A: Brief template text ("New file dropped for processing.") with filename
- Q: Where should logs be written? → A: Stdout/stderr only (user redirects if needed)

## Purpose

The Local File Watcher Service is the perception layer component responsible for monitoring a designated "drop folder" on the local file system. When users drop files into this folder, the service detects new files and creates corresponding action items in the Obsidian vault's `/Needs_Action` folder. This enables the Bona-Papa AI Employee to process user-initiated tasks without requiring manual file placement in the vault.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Drop File for Processing (Priority: P1)

As a user, I want to drop a file into a designated folder so that my AI Employee automatically creates a task to process it.

**Why this priority**: This is the core functionality of the File Watcher. Without this, the service has no value. It represents the fundamental "perception" capability that enables the AI Employee to detect user intent from the file system.

**Independent Test**: Can be fully tested by dropping a single file into the drop folder and verifying that a corresponding `.md` action file appears in `/Needs_Action` within the expected time window.

**Acceptance Scenarios**:

1. **Given** the File Watcher is running and the drop folder exists, **When** I copy a PDF file into the drop folder, **Then** a new markdown file appears in `/Needs_Action` within 5 seconds containing the original filename and file size.

2. **Given** the File Watcher is running, **When** I drop multiple files simultaneously (3 files), **Then** each file gets its own action item in `/Needs_Action`, all created within 10 seconds.

3. **Given** the File Watcher is running, **When** I drop a file with spaces or special characters in the name (e.g., "My Report (Final).pdf"), **Then** the action file is created successfully with the original filename preserved in metadata.

---

### User Story 2 - View Pending Actions in Dashboard (Priority: P2)

As a user, I want to see new file-based tasks appear in my Obsidian vault so that I can track what the AI Employee needs to process.

**Why this priority**: While file detection is critical, the user experience of seeing pending tasks in Obsidian makes the system usable and transparent. This supports the "local-first" principle from the constitution.

**Independent Test**: After files are dropped and action items created, open Obsidian and navigate to `/Needs_Action` to verify files are visible and contain correct metadata.

**Acceptance Scenarios**:

1. **Given** a file has been dropped and processed, **When** I open the `/Needs_Action` folder in Obsidian, **Then** I see a markdown file with YAML frontmatter showing type, original filename, file size, and creation timestamp.

2. **Given** multiple files have been processed over time, **When** I browse `/Needs_Action`, **Then** files are named with a prefix that groups them by type (e.g., `FILE_document.pdf.md`).

---

### User Story 3 - Service Resilience (Priority: P3)

As a user, I want the File Watcher to recover from errors gracefully so that I don't lose file drop events during temporary issues.

**Why this priority**: Reliability is important for trust, but Bronze Tier focuses on getting the core working. Basic error handling prevents silent failures without requiring advanced recovery mechanisms.

**Independent Test**: Simulate errors (e.g., temporarily make `/Needs_Action` read-only) and verify the service logs errors but continues running after the condition is resolved.

**Acceptance Scenarios**:

1. **Given** the `/Needs_Action` folder is temporarily inaccessible, **When** a file is dropped, **Then** the service logs an error and continues running (does not crash).

2. **Given** the service has been running for 1 hour, **When** I check the logs, **Then** I see structured log entries showing startup, any files processed, and any errors encountered.

---

### Edge Cases

- What happens when a file with the same name is dropped twice? The system creates unique action files by appending timestamp or counter to avoid overwrites.
- What happens when a directory is dropped instead of a file? The system ignores directories and only processes files.
- What happens when a very large file (>1GB) is dropped? The system processes it normally since only metadata is captured, not file contents.
- What happens when files are dropped while the watcher is starting up? Files present before startup are not processed; only new files trigger events.
- What happens when the drop folder doesn't exist? The service fails to start with a clear error message indicating the missing folder.

## Scope

### In Scope (Bronze Tier)

- Single drop folder monitoring
- File creation detection (new files only)
- Markdown action file generation with YAML frontmatter
- Structured JSON logging
- Command-line configuration for vault path and drop folder
- Support for `--dry-run` mode per constitution

### Out of Scope (Silver/Gold Tier - Explicit Non-Goals)

- Multiple drop folder monitoring
- Gmail, WhatsApp, or other external service watchers
- File modification or deletion detection
- File content analysis or parsing
- Integration with Claude Code reasoning loop
- MCP server integration
- Scheduling or cron-based triggering
- Process management (PM2, systemd)
- Cloud deployment
- Approval workflows

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Service MUST monitor a single configurable drop folder for new file creation events
- **FR-002**: Service MUST create a corresponding markdown action file in `/Needs_Action` for each new file detected
- **FR-003**: Action files MUST include YAML frontmatter with: type (`file_drop`), original filename, file size in bytes, and timestamp (ISO 8601), followed by a markdown body containing brief template text ("New file dropped for processing.") and the original filename
- **FR-004**: Action files MUST be named with pattern `FILE_{original_filename}.md` to enable grouping by source type
- **FR-005**: Service MUST handle filenames with spaces, special characters, and unicode characters
- **FR-006**: Service MUST ignore directory creation events (files only)
- **FR-007**: Service MUST continue running after encountering errors (crash-resistant loop)
- **FR-008**: Service MUST support `--dry-run` flag that logs intended actions without creating files
- **FR-009**: Service MUST log all operations in structured JSON format to stdout (info/debug) and stderr (errors); file-based logging is the user's responsibility via shell redirection
- **FR-010**: Service MUST accept vault path and drop folder path via command-line arguments
- **FR-011**: Service MUST validate that both vault path and drop folder exist at startup, failing with clear error if not
- **FR-012**: Service MUST handle duplicate filenames by generating unique action file names (append counter or timestamp)
- **FR-013**: Service MUST NOT modify, move, or delete the original dropped file (read-only access to drop folder)

### Key Entities

- **Drop Folder**: The monitored source directory where users place files for processing. Configured at startup.
- **Action File**: A markdown file in `/Needs_Action` representing a task for the AI Employee. Contains YAML frontmatter with metadata about the dropped file.
- **Vault**: The Obsidian vault root directory containing the `/Needs_Action`, `/Done`, and other standard folders.

## Assumptions

- The Obsidian vault folder structure (`/Needs_Action`, `/Inbox`, `/Done`) is created separately (either manually or by vault setup)
- The drop folder is a different location from the vault (to avoid recursive watching)
- File events are processed in near-real-time (within seconds, not batched)
- The service runs as a foreground process for Bronze Tier (no daemonization required)
- Default check interval of 1 second is acceptable for responsiveness vs. resource usage

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: New files are detected and action items created within 5 seconds of file drop completion
- **SC-002**: Service runs continuously for 24 hours without crashing under normal operation (no dropped files or occasional files)
- **SC-003**: 100% of dropped files result in corresponding action items (no silent failures)
- **SC-004**: Action files contain all required metadata fields with correct values
- **SC-005**: Service starts successfully within 2 seconds when vault and drop folder exist
- **SC-006**: Service fails to start with clear error message within 1 second when required folders are missing
- **SC-007**: Dry-run mode produces log output matching what would be created, without creating files

## Dependencies

- Obsidian vault must be initialized with `/Needs_Action` folder
- Drop folder must exist and be readable
- Write permissions required for `/Needs_Action` folder
- File system must support file creation events (standard on Windows, macOS, Linux)

## Constraints

- Must run on Windows, macOS, and Linux (cross-platform)
- Must use Python 3.13+ per constitution code standards
- Must use structured JSON logging per constitution
- Must support `--dry-run` mode per constitution security requirements
- No external network calls (local file system only)
