# Tasks: Local File Watcher Service

**Input**: Design documents from `/specs/001-local-file-watcher/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/cli-interface.md

**Tests**: Tests are included as the spec requires validation of acceptance scenarios.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Project initialization and basic structure

- [X] T001 Create project structure with src/file_watcher/ and tests/ directories
- [X] T002 Create pyproject.toml with dependencies: watchdog>=4.0.0, PyYAML>=6.0, python-json-logger>=2.0.0, pytest>=8.0.0
- [X] T003 [P] Create src/file_watcher/__init__.py with version string "0.1.0"
- [X] T004 [P] Create tests/__init__.py as empty module marker
- [X] T005 [P] Create tests/conftest.py with pytest fixtures for temp vault and drop folder

**Checkpoint**: Project skeleton ready, dependencies installable with `pip install -e .`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**CRITICAL**: No user story work can begin until this phase is complete

- [X] T006 Implement WatcherConfig dataclass in src/file_watcher/config.py with vault_path, drop_folder, dry_run fields
- [X] T007 Implement CLI argument parsing with argparse in src/file_watcher/config.py (--vault, --drop-folder, --dry-run, --help, --version)
- [X] T008 Implement path validation in src/file_watcher/config.py (check paths exist, are different, Needs_Action folder exists)
- [X] T009 [P] Implement JSON logger setup in src/file_watcher/logger.py using python-json-logger
- [X] T010 [P] Create tests/unit/test_config.py with tests for argument parsing and validation

**Checkpoint**: Foundation ready - CLI works with `python -m file_watcher --help`, config validation complete

---

## Phase 3: User Story 1 - Drop File for Processing (Priority: P1)

**Goal**: Detect new files in drop folder and create action items in /Needs_Action

**Independent Test**: Drop a file into drop folder, verify .md file appears in /Needs_Action within 5 seconds

### Implementation for User Story 1

- [X] T011 [US1] Implement ActionFile dataclass in src/file_watcher/action_file.py with type, original_name, size, timestamp, status, source_path fields
- [X] T012 [US1] Implement generate_action_content() in src/file_watcher/action_file.py to create YAML frontmatter + markdown body
- [X] T013 [US1] Implement generate_action_filename() in src/file_watcher/action_file.py with FILE_ prefix pattern
- [X] T014 [US1] Implement DropFolderHandler class extending FileSystemEventHandler in src/file_watcher/watcher.py
- [X] T015 [US1] Implement on_created() method in src/file_watcher/watcher.py to detect new files (ignore directories per FR-006)
- [X] T016 [US1] Implement write_action_file() in src/file_watcher/watcher.py to save action file to /Needs_Action
- [X] T017 [US1] Implement start_watching() function in src/file_watcher/watcher.py using watchdog Observer
- [X] T018 [US1] Create src/file_watcher/__main__.py entry point that parses args, validates config, starts watcher
- [X] T019 [US1] Add dry-run mode check in watcher.py - log intended action without writing file (FR-008)
- [X] T020 [P] [US1] Create tests/unit/test_action_file.py with tests for content generation and filename patterns
- [X] T021 [US1] Create tests/integration/test_watcher.py with end-to-end test: drop file → verify action file created

**Checkpoint**: User Story 1 complete - can drop files and see action items created in /Needs_Action

---

## Phase 4: User Story 2 - View Pending Actions in Dashboard (Priority: P2)

**Goal**: Ensure action files are properly formatted for Obsidian viewing with correct metadata

**Independent Test**: Open created action files in Obsidian, verify YAML frontmatter renders correctly

### Implementation for User Story 2

- [X] T022 [US2] Add source_path field to ActionFile in src/file_watcher/action_file.py (absolute path to original file)
- [X] T023 [US2] Ensure YAML frontmatter uses safe_dump with proper quoting in src/file_watcher/action_file.py
- [X] T024 [US2] Handle special characters in filenames (spaces, unicode, parentheses) in src/file_watcher/action_file.py (FR-005)
- [X] T025 [US2] Implement duplicate filename detection with timestamp suffix in src/file_watcher/action_file.py (FR-012)
- [X] T026 [P] [US2] Add tests for special character handling in tests/unit/test_action_file.py
- [X] T027 [P] [US2] Add tests for duplicate filename handling in tests/unit/test_action_file.py

**Checkpoint**: User Story 2 complete - action files display correctly in Obsidian with all metadata

---

## Phase 5: User Story 3 - Service Resilience (Priority: P3)

**Goal**: Service continues running after errors, logs all operations in structured format

**Independent Test**: Make /Needs_Action read-only, drop file, verify error logged and service continues

### Implementation for User Story 3

- [X] T028 [US3] Wrap on_created() handler in try/except in src/file_watcher/watcher.py (FR-007)
- [X] T029 [US3] Log errors with full traceback using structured JSON in src/file_watcher/watcher.py
- [X] T030 [US3] Add startup log entry with config details in src/file_watcher/__main__.py
- [X] T031 [US3] Implement graceful shutdown with SIGINT/SIGTERM handlers in src/file_watcher/__main__.py
- [X] T032 [US3] Add shutdown log entry with reason in src/file_watcher/__main__.py
- [X] T033 [US3] Ensure read-only access to drop folder - never modify source files in src/file_watcher/watcher.py (FR-013)
- [X] T034 [P] [US3] Add tests for error handling in tests/integration/test_watcher.py (permission denied scenario)
- [X] T035 [P] [US3] Add tests for log format validation in tests/unit/test_logger.py

**Checkpoint**: User Story 3 complete - service runs reliably with full observability

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and documentation

- [X] T036 [P] Verify all exit codes match CLI contract (0, 1, 2) in src/file_watcher/__main__.py
- [X] T037 [P] Add --version flag implementation in src/file_watcher/config.py
- [X] T038 Run all tests and verify 100% of acceptance scenarios pass
- [X] T039 Manual validation: run quickstart.md steps end-to-end
- [X] T040 Update quickstart.md if any steps changed during implementation

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Builds on US1's action_file.py - can start after T013 complete
- **User Story 3 (P3)**: Builds on US1's watcher.py - can start after T017 complete

### Within Each User Story

- Implementation tasks depend on prior tasks in sequence
- Test tasks marked [P] can run in parallel with implementation
- Complete all tasks before moving to next story for cleanest flow

### Parallel Opportunities

```text
# Phase 1 parallel (after T001, T002):
T003, T004, T005 can run in parallel

# Phase 2 parallel (after T006, T007, T008):
T009, T010 can run in parallel

# User Story 1 test parallel (after T019):
T020 can run while T021 is being written

# User Story 2 tests parallel:
T026, T027 can run in parallel

# User Story 3 tests parallel:
T034, T035 can run in parallel

# Phase 6 parallel:
T036, T037 can run in parallel
```

---

## Parallel Example: User Story 1

```bash
# After Foundational phase complete, launch US1 implementation:
T011: Implement ActionFile dataclass
T012: Implement generate_action_content()  # depends on T011
T013: Implement generate_action_filename() # depends on T011
T014: Implement DropFolderHandler          # can start with T012
T015: Implement on_created()               # depends on T014
T016: Implement write_action_file()        # depends on T012, T015
T017: Implement start_watching()           # depends on T016
T018: Create __main__.py entry point       # depends on T017
T019: Add dry-run mode                     # depends on T018

# Tests can start once T013 complete:
T020: Unit tests for action_file.py        # [P] after T013
T021: Integration test                      # after T019
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Drop a file, verify action file created
5. Can demo/use at this point - core functionality works

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → **MVP Ready!**
3. Add User Story 2 → Test independently → Better Obsidian experience
4. Add User Story 3 → Test independently → Production-ready resilience
5. Polish phase → Ship it

### Suggested MVP Scope

For Bronze Tier minimum viable deliverable, complete through **User Story 1** (Phase 3).
This delivers:
- Working file watcher
- Action file creation
- Basic CLI
- Dry-run mode

User Stories 2 and 3 enhance quality but MVP works without them.

---

## Task Summary

| Phase | Tasks | Parallel Opportunities |
|-------|-------|------------------------|
| Setup | 5 | 3 tasks parallelizable |
| Foundational | 5 | 2 tasks parallelizable |
| US1 (P1) | 11 | 1 test parallelizable |
| US2 (P2) | 6 | 2 tests parallelizable |
| US3 (P3) | 8 | 2 tests parallelizable |
| Polish | 5 | 2 tasks parallelizable |
| **Total** | **40** | **12 parallel opportunities** |

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Tests included per spec acceptance scenarios requirement
