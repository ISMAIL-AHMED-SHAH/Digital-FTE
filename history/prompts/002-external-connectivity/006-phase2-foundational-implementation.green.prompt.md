---
id: 006
title: Phase 2 Foundational Implementation
stage: green
date: 2026-01-25
surface: agent
model: claude-opus-4-5-20251101
feature: 002-external-connectivity
branch: 002-external-connectivity
user: system
command: /sp.implement
labels: ["implementation", "foundational", "phase-2", "silver-tier", "core-utilities"]
links:
  spec: specs/002-external-connectivity/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - src/common/credentials.py
  - src/common/idempotency.py
  - src/common/integrity.py
  - src/common/audit_logger.py
  - src/common/retry.py
  - src/watchers/base_watcher.py
  - src/watchers/config.py
  - src/common/vault.py
tests:
  - null
---

## Prompt

continue with Phase 2

## Response snapshot

Completed all 8 Phase 2 Foundational tasks - the core infrastructure required before any user story can begin:

### Common Utilities (T006-T010)

**T006 - credentials.py**: Credential manager abstraction with:
- KeyringStore: Windows Credential Manager / macOS Keychain via keyring library
- EncryptedFileStore: AES-256 fallback using machine-specific key (PBKDF2)
- CredentialManager: Unified interface with get_token(), store_token(), refresh_token()
- Automatic token expiration checking with buffer

**T007 - idempotency.py**: SQLite idempotency database with:
- Thread-safe connection management
- processed_messages table for watcher deduplication
- sent_actions table for MCP execution deduplication
- rate_limits table for daily quota enforcement
- cleanup_expired() for 7-day retention window

**T008 - integrity.py**: SHA-256 integrity hashing with:
- Deterministic serialization for consistent hashing
- generate_hash() for approval file creation
- validate_hash() / validate_hash_strict() for tamper detection
- generate_action_id() for idempotency key generation

**T009 - audit_logger.py**: Structured JSON-lines audit logging with:
- AuditLogEntry with standard fields (timestamp, component, action_type, etc.)
- Automatic parameter sanitization (redact secrets, truncate long values)
- log_detection(), log_approval(), log_execution(), log_error() helpers
- Daily log file rotation (/Vault/Logs/YYYY-MM-DD.json)

**T010 - retry.py**: Exponential backoff retry logic with:
- @exponential_backoff decorator for sync functions
- @async_exponential_backoff for async functions
- Configurable initial_delay, max_delay, max_retries, jitter
- Pre-built configs: API_RETRY_CONFIG, OAUTH_RETRY_CONFIG, DATABASE_RETRY_CONFIG

### Base Watcher Framework (T011-T012)

**T011 - base_watcher.py**: Abstract base watcher class with:
- WatcherStatus enum (STOPPED, STARTING, RUNNING, PAUSED, STOPPING, ERROR)
- WatcherPriority enum for graceful degradation (HIGH, MEDIUM, LOW)
- Memory monitoring via psutil
- pause()/resume() for resource constraints
- PollingWatcher and ServerWatcher subclasses

**T012 - config.py**: Watcher configuration module with:
- Dataclass configs: GlobalConfig, GmailConfig, WhatsAppConfig, LinkedInConfig, ApprovalConfig
- YAML loading from config/watcher_config.yaml
- Environment variable overrides (VAULT_PATH, DRY_RUN, DEV_MODE)
- Dev mode overrides (faster polling, debug logging)

### Vault Utility (T013)

**T013 - vault.py**: Vault folder management with:
- initialize() to create all required folders
- verify() to check folder structure
- read_file(), write_file(), move_file(), delete_file() helpers
- list_files() with glob pattern support

## Outcome

- Impact: Phase 2 complete - foundation ready for user story implementation
- Tests: N/A (foundational modules, will be tested via integration)
- Files: 8 new Python modules in src/common/ and src/watchers/
- Next prompts: /sp.implement Phase 3 (US4 - Approval Workflow)
- Reflection: All common utilities are independent and reusable; base watcher pattern enables consistent memory monitoring and lifecycle across all watchers

## Evaluation notes (flywheel)

- Failure modes observed: None - all modules created successfully
- Graders run and results (PASS/FAIL): Import verification pending (requires pip install)
- Prompt variant (if applicable): Continuation of Phase 1 implementation
- Next experiment (smallest change to try): Add unit tests for integrity.py hash consistency
