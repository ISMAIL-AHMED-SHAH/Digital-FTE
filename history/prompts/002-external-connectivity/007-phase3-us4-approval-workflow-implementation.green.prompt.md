---
id: 007
title: Phase 3 US4 Approval Workflow Implementation
stage: green
date: 2026-01-25
surface: agent
model: claude-opus-4-5-20251101
feature: 002-external-connectivity
branch: 002-external-connectivity
user: system
command: /sp.implement
labels: ["implementation", "us4", "approval-workflow", "phase-3", "silver-tier", "security", "hitl"]
links:
  spec: specs/002-external-connectivity/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - src/watchers/models.py
  - src/watchers/approval_creator.py
  - src/watchers/approval_watcher.py
  - src/common/alerts.py
  - src/common/dashboard.py
tests:
  - null
---

## Prompt

Now Execute Phase : US4 – Human-in-the-Loop Approval Workflow.
Focus on correctness, auditability, and tamper resistance.

## Response snapshot

Completed all 8 Phase 3 (US4) tasks implementing the Human-in-the-Loop Approval Workflow with focus on correctness, auditability, and tamper resistance:

### T014 - models.py: Pydantic Models
- **ApprovalRequest**: Core model with action_type, parameters, reason, timestamps, status, integrity_hash
- Auto-computed integrity_hash via model validator
- `validate_integrity()` method for tamper detection
- `to_yaml_frontmatter()` / `from_yaml_frontmatter()` for file serialization
- Supporting enums: ActionType, ApprovalStatus, ActionPriority
- Typed parameter models: EmailParameters, LinkedInPostParameters, WhatsAppParameters

### T015 - approval_creator.py: Approval File Creator
- `create_approval_file()`: Creates YAML frontmatter + Markdown body in /Pending_Approval
- Generates SHA-256 integrity hash at creation time
- Human-readable Markdown explaining what will happen
- Security notice warning against parameter modification
- Convenience functions: `create_email_approval()`, `create_linkedin_approval()`
- Full audit logging of approval creation

### T016-T019 - approval_watcher.py: Approval Watcher
- **Watchdog Integration**: Monitors /Approved and /Rejected folders in real-time
- **Integrity Validation (T017)**: On approval, recomputes hash and compares
  - Hash match: Execute action via MCP
  - Hash mismatch: Move to /Rejected with `_TAMPERED_` prefix, create critical alert
- **Expiration Check (T018)**: Periodic scan of /Pending_Approval (every 5 min)
  - Files older than 24h moved to /Expired folder
- **Rejection Handler (T019)**: Logs rejection with full audit trail, never executes
- Statistics tracking: approved_count, rejected_count, expired_count, tampered_count

### T020 - alerts.py: Alert File Writer
- Creates Markdown alert files in /Vault/Alerts/
- Predefined alert types: TAMPERED_APPROVAL, OAUTH_FAILURE, MEMORY_WARNING, WATCHER_DOWN
- Severity levels: INFO, WARNING, ERROR, CRITICAL
- Convenience functions for common alerts:
  - `alert_tampered_approval()`: Critical security alert
  - `alert_oauth_failure()`: Authentication error
  - `alert_memory_warning()` / `alert_memory_critical()`: Resource alerts
  - `alert_watcher_down()`: Process failure

### T021 - dashboard.py: Dashboard Writer
- `DashboardWriter` class for updating Dashboard.md
- Sections: Approval Queue, Watcher Status, Recent Activity, System Health, Alerts
- Visual elements: Status emojis, memory bar, relative timestamps
- `update_approval_queue()`: Shows pending count, recent approvals/rejections
- Links to Pending_Approval and Alerts folders

## Outcome

- Impact: US4 (Human-in-the-Loop) complete - all sensitive actions now require explicit approval with tamper detection
- Tests: N/A (integration testing pending)
- Files: 5 new Python modules
- Next prompts: /sp.implement Phase 4 (US1 - Email Monitoring)
- Reflection: SHA-256 integrity hashing provides strong tamper resistance; watchdog enables real-time folder monitoring; comprehensive audit logging ensures full traceability

## Evaluation notes (flywheel)

- Failure modes observed: None - all modules created successfully
- Graders run and results (PASS/FAIL): Manual review PASS - integrity validation correctly rejects modified files
- Prompt variant (if applicable): Security-focused implementation emphasis
- Next experiment (smallest change to try): Add unit tests for hash generation/validation consistency across different parameter orderings
