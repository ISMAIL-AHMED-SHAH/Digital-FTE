# Implementation Plan: Local File Watcher Service

**Branch**: `001-local-file-watcher` | **Date**: 2026-01-19 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-local-file-watcher/spec.md`

## Summary

Build a Python-based file system watcher that monitors a designated "drop folder" for new files and creates corresponding action items (Markdown files with YAML frontmatter) in the Obsidian vault's `/Needs_Action` folder. This is the perception layer component for the Bona-Papa AI Employee, enabling file-based task triggering without manual vault interaction.

**Technical Approach**: Use Python's `watchdog` library for cross-platform file system event monitoring, with `argparse` for CLI configuration and Python's built-in `json` module for structured logging.

## Technical Context

**Language/Version**: Python 3.13+
**Primary Dependencies**: watchdog (file system monitoring), pathlib (path handling), argparse (CLI)
**Storage**: Local file system only (Markdown files in Obsidian vault)
**Testing**: pytest with temporary directories for isolation
**Target Platform**: Windows, macOS, Linux (cross-platform)
**Project Type**: Single CLI application
**Performance Goals**: File detection within 5 seconds, startup within 2 seconds
**Constraints**: No network calls, read-only access to drop folder, write access to vault
**Scale/Scope**: Single user, single drop folder, moderate file volume (10-100 files/day)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Requirement | Status | Notes |
|-----------|-------------|--------|-------|
| I. Local-First | Data in Obsidian vault only | ✅ PASS | All output to local `/Needs_Action` folder |
| II. PRA Loop | Watcher writes to /Needs_Action, no actions | ✅ PASS | Perception layer only, no MCP integration |
| III. HITL Safety | N/A for watchers | ✅ PASS | File watcher has no sensitive actions |
| IV. Ralph Wiggum | N/A for Bronze tier | ✅ PASS | Watcher runs continuously, not task-based |
| V. Security | --dry-run support, no credentials | ✅ PASS | FR-008 requires dry-run; no external APIs |
| VI. Audit Logging | Structured JSON logging | ✅ PASS | FR-009 requires JSON to stdout/stderr |
| VII. Agent Skills | N/A for infrastructure | ✅ PASS | Watcher is infrastructure, not a Skill |

**Gate Result**: ✅ All applicable principles satisfied. Proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/001-local-file-watcher/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (/sp.tasks command)
```

### Source Code (repository root)

```text
src/
├── file_watcher/
│   ├── __init__.py
│   ├── __main__.py      # Entry point: python -m file_watcher
│   ├── watcher.py       # Core watcher logic using watchdog
│   ├── action_file.py   # Action file generation (Markdown + YAML)
│   ├── config.py        # CLI argument parsing and validation
│   └── logger.py        # Structured JSON logging setup

tests/
├── unit/
│   ├── test_action_file.py
│   ├── test_config.py
│   └── test_logger.py
├── integration/
│   └── test_watcher.py  # Full watcher flow with temp directories
└── conftest.py          # Shared fixtures (temp vault, drop folder)

pyproject.toml           # Project configuration and dependencies
```

**Structure Decision**: Single project layout selected. This is a standalone CLI tool with no web/mobile components. The `file_watcher` package is self-contained with clear module responsibilities.

## Complexity Tracking

No constitution violations requiring justification. Design follows simplest viable approach.
