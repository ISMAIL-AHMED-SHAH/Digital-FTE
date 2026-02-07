---
id: 005
title: Phase 1 Setup Implementation
stage: green
date: 2026-01-25
surface: agent
model: claude-opus-4-5-20251101
feature: 002-external-connectivity
branch: 002-external-connectivity
user: system
command: /sp.implement
labels: ["implementation", "setup", "phase-1", "silver-tier"]
links:
  spec: specs/002-external-connectivity/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - src/watchers/__init__.py
  - src/common/__init__.py
  - tests/fixtures/__init__.py
  - tests/__init__.py
  - tests/unit/__init__.py
  - tests/integration/__init__.py
  - pyproject.toml
  - requirements.txt
  - config/.env.example
  - config/watcher_config.yaml
  - scripts/init_idempotency_db.sql
  - data/idempotency.db
  - .gitignore
tests:
  - null
---

## Prompt

Execute ONLY Phase 1: Setup (Shared Infrastructure) from specs/002-external-connectivity/tasks.md. for now.

## Response snapshot

Completed all 5 Phase 1 Setup tasks for Silver Tier External Connectivity:

**T001** - Created directory structure:
- src/watchers/ - External service watchers
- src/common/ - Shared utilities
- src/mcp_servers/gmail/tools, linkedin/tools, whatsapp/ - MCP servers
- tests/unit, integration, fixtures/ - Test directories
- config/, scripts/ - Configuration and helper scripts

**T002** - Updated pyproject.toml with Silver Tier dependencies:
- google-auth-oauthlib, google-api-python-client (Gmail)
- fastapi, uvicorn (WhatsApp webhook)
- pydantic, keyring, cryptography, psutil, python-dotenv
- Created requirements.txt for convenience

**T003** - Created config/.env.example with placeholders for:
- Gmail OAuth2 credentials
- WhatsApp Business API configuration
- LinkedIn API credentials
- Vault path and operational modes

**T004** - Created config/watcher_config.yaml with:
- Global memory budgets (500MB total, 100MB per watcher)
- Gmail polling settings (2-minute interval, keywords)
- WhatsApp webhook settings (rate limits, keywords)
- LinkedIn rate limits (10 posts/day)
- Approval workflow settings (24h expiration)
- Retry configuration (exponential backoff)

**T005** - Created scripts/init_idempotency_db.sql with:
- processed_messages table (for watcher deduplication)
- sent_actions table (for MCP idempotency)
- rate_limits table (for daily quotas)
- schema_version table (for migrations)
- Initialized data/idempotency.db

## Outcome

- Impact: Phase 1 complete - project structure and configuration ready for Phase 2
- Tests: N/A (setup phase, no code to test)
- Files: 12 files created/modified
- Next prompts: /sp.implement Phase 2 (Foundational utilities)
- Reflection: Setup phase establishes consistent patterns from Bronze Tier while adding Silver Tier specific configuration

## Evaluation notes (flywheel)

- Failure modes observed: sqlite3 CLI not available on Windows, used Python fallback
- Graders run and results (PASS/FAIL): Directory structure verified, database initialized successfully
- Prompt variant (if applicable): Phase-scoped implementation (Phase 1 only)
- Next experiment (smallest change to try): Consider adding a setup verification script to validate all config files exist
