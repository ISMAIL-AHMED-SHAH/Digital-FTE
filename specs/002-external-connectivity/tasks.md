# Tasks: External Connectivity (Silver Tier)

**Input**: Design documents from `/specs/002-external-connectivity/`
**Prerequisites**: plan.md (complete), spec.md (complete)
**Branch**: `002-external-connectivity`

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1-US5)
- All paths are relative to repository root

## User Stories Reference

| Story | Title | Priority | Description |
|-------|-------|----------|-------------|
| US1 | Email Monitoring and Action | P1 | Gmail Watcher + Email send via MCP |
| US2 | WhatsApp Message Detection | P2 | WhatsApp Business API webhook handler |
| US3 | LinkedIn Post Automation | P3 | LinkedIn MCP server for post publishing |
| US4 | Human-in-the-Loop Approval Workflow | P1 | File-based approval with integrity validation |
| US5 | Scheduled Automation Tasks | P2 | Cron/Task Scheduler integration |

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, dependencies, and shared modules

- [x] T001 Create directory structure per plan.md: src/watchers/, src/common/, src/mcp_servers/, tests/unit/, tests/integration/, config/, scripts/
- [x] T002 Create Python requirements.txt with dependencies: google-auth-oauthlib, google-api-python-client, fastapi, uvicorn, pydantic, keyring, cryptography, psutil, watchdog
- [x] T003 [P] Create .env.example template with placeholders for GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, WHATSAPP_APP_SECRET, LINKEDIN_CLIENT_ID, LINKEDIN_CLIENT_SECRET, VAULT_PATH, DRY_RUN, DEV_MODE
- [x] T004 [P] Create config/watcher_config.yaml with default settings for poll intervals, keywords, rate limits, memory budgets
- [x] T005 Initialize SQLite schema in scripts/init_idempotency_db.sql with processed_messages and sent_actions tables per plan.md section 5.2

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story

**CRITICAL**: No user story work can begin until this phase is complete

### Common Utilities

- [x] T006 Implement credential manager abstraction in src/common/credentials.py with get_token(), store_token(), refresh_token() methods supporting Windows Credential Manager and macOS Keychain via keyring library, with AES-256 encrypted file fallback
- [x] T007 [P] Implement idempotency database module in src/common/idempotency.py with SQLite connection, is_processed(), mark_processed(), cleanup_expired() methods, 7-day retention window
- [x] T008 [P] Implement integrity hash module in src/common/integrity.py with generate_hash(), validate_hash() using SHA-256 on action_type + parameters + created_timestamp
- [x] T009 [P] Implement audit logger in src/common/audit_logger.py with JSON-lines format output to /Vault/Logs/YYYY-MM-DD.json, fields: timestamp, level, component, action_type, actor, target, parameters, approval_status, result, error
- [x] T010 [P] Implement retry logic in src/common/retry.py with exponential_backoff() decorator, initial_delay=1s, max_delay=60s, max_retries=5

### Base Watcher Framework

- [x] T011 Implement abstract base watcher class in src/watchers/base_watcher.py with: start(), stop(), process_event(), check_memory(), dry_run support, logging integration, memory_limit_mb=100
- [x] T012 Implement watcher configuration in src/watchers/config.py extending Bronze Tier pattern with: vault_path, poll_interval, keywords, memory_budget, priority, rate_limits

### Vault Folder Structure Verification

- [x] T013 Create vault initialization utility in src/common/vault.py that verifies/creates required folders: Needs_Action, Pending_Approval, Approved, Rejected, Expired, Logs, Alerts

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 4 - Human-in-the-Loop Approval Workflow (Priority: P1)

**Goal**: All sensitive external actions require explicit human approval via file-based signaling with integrity validation

**Independent Test**: Trigger any external action, verify approval file is created in /Pending_Approval with integrity hash, move to /Approved and verify execution, move to /Rejected and verify no execution, test tampering detection

**Why First**: US1 (Email) and US3 (LinkedIn) depend on approval workflow to execute MCP actions. Build the approval infrastructure first.

### Implementation for User Story 4

- [x] T014 [US4] Create ApprovalRequest Pydantic model in src/watchers/models.py with fields: action_type, parameters (dict), reason, created_timestamp, expires_timestamp, status, integrity_hash
- [x] T015 [US4] Implement approval file creator in src/watchers/approval_creator.py with create_approval_file() that writes YAML frontmatter + Markdown body to /Pending_Approval, includes integrity_hash generated via src/common/integrity.py
- [x] T016 [US4] Implement approval watcher in src/watchers/approval_watcher.py that monitors /Approved and /Rejected folders using watchdog, inherits from base_watcher.py
- [x] T017 [US4] Add integrity validation to approval_watcher.py: on file detected in /Approved, extract integrity_hash from YAML, recompute hash, if mismatch move to /Rejected with _TAMPERED suffix and log alert
- [x] T018 [US4] Add expiration check to approval_watcher.py: scan /Pending_Approval every 5 minutes, move files older than 24h to /Expired folder
- [x] T019 [US4] Add rejection handler to approval_watcher.py: when file detected in /Rejected, log rejection with full audit trail, do not execute action
- [x] T020 [US4] Create alert file writer in src/common/alerts.py that writes to /Vault/Alerts/ for tampered files, OAuth failures, memory warnings
- [x] T021 [US4] Update Dashboard.md writer in src/common/dashboard.py with update_approval_queue() that shows pending approval count, recent approvals/rejections

**Checkpoint**: Approval workflow complete - can now build MCP servers that use it

---

## Phase 4: User Story 1 - Email Monitoring and Action (Priority: P1) MVP

**Goal**: Detect important emails in Gmail, create action files, enable approved draft responses to be sent via MCP

**Independent Test**: Send test email with "urgent" keyword, verify action file created in /Needs_Action, process with Claude to create draft, approve draft, verify email sent via Gmail API

### Implementation for User Story 1

#### Gmail Watcher (Python)

- [x] T022 [P] [US1] Implement Gmail API client wrapper in src/watchers/gmail_client.py with: authenticate_oauth(), list_unread_important(), get_message_content(), mark_as_read() using google-api-python-client
- [x] T023 [US1] Implement Gmail watcher in src/watchers/gmail_watcher.py inheriting from base_watcher.py with: 2-minute poll interval, keyword filtering (urgent, invoice, important), idempotency check via message_id, action file creation in /Needs_Action
- [x] T024 [US1] Add OAuth token refresh logic to gmail_watcher.py: on 401 error, call credentials.refresh_token(), if fails 3x pause watcher and write alert
- [x] T025 [US1] Create Gmail OAuth setup script in scripts/setup_gmail_oauth.py that runs OAuth2 flow and stores tokens in OS credential manager

#### Gmail MCP Server (Node.js)

- [x] T026 [P] [US1] Initialize Node.js project in src/mcp_servers/gmail/ with package.json including @modelcontextprotocol/sdk, googleapis dependencies
- [x] T027 [US1] Implement Gmail MCP server entry point in src/mcp_servers/gmail/index.ts with MCP server setup and tool registration
- [x] T028 [US1] Implement send_email tool in src/mcp_servers/gmail/tools/send_email.ts with: to, subject, body, cc, bcc, attachments parameters, idempotency check before send, rate limit enforcement (50/day)
- [x] T029 [US1] Add credential retrieval to Gmail MCP server: read OAuth token from OS credential manager or fallback encrypted file
- [x] T030 [US1] Create MCP tool definition contract in specs/002-external-connectivity/contracts/gmail-mcp.json per plan.md section 3.4

**Checkpoint**: Gmail monitoring and sending complete - can detect emails and send approved responses

---

## Phase 5: User Story 2 - WhatsApp Message Detection (Priority: P2)

**Goal**: Monitor WhatsApp Business API webhooks for messages containing business keywords, create action files

**Independent Test**: Send WhatsApp message containing "invoice" keyword to Business API number, verify webhook received, verify action file created with sender and content

### Implementation for User Story 2

- [x] T031 [P] [US2] Implement FastAPI webhook handler in src/watchers/whatsapp_webhook.py with POST /webhooks/whatsapp endpoint, X-Hub-Signature-256 validation, 200 response within 500ms
- [x] T032 [US2] Add message extraction to whatsapp_webhook.py: parse Meta webhook payload, extract sender phone, message_id, timestamp, text content
- [x] T033 [US2] Add keyword filtering to whatsapp_webhook.py: only process messages containing configured keywords from watcher_config.yaml
- [x] T034 [US2] Add action file creation to whatsapp_webhook.py: write to /Needs_Action with type=whatsapp, include SHA-256 content hash as message_id for idempotency
- [x] T035 [US2] Add rate limiting to whatsapp_webhook.py: max 100 requests/minute per IP using in-memory counter with 60s window
- [x] T036 [US2] Create WhatsApp setup script in scripts/setup_whatsapp.py that outputs webhook URL and verification steps for Meta Business API configuration
- [x] T037 [US2] Create webhook OpenAPI contract in specs/002-external-connectivity/contracts/whatsapp-webhook.openapi.yaml per plan.md section 3.3

**Checkpoint**: WhatsApp message detection complete - can receive and process business messages

---

## Phase 6: User Story 3 - LinkedIn Post Automation (Priority: P3)

**Goal**: Draft LinkedIn posts and publish them after user approval via MCP

**Independent Test**: Create marketing entry requesting post, verify draft created in /Pending_Approval, approve and verify post published to LinkedIn

### Implementation for User Story 3

- [x] T038 [P] [US3] Initialize Node.js project in src/mcp_servers/linkedin/ with package.json including @modelcontextprotocol/sdk, axios (for LinkedIn REST API)
- [x] T039 [US3] Implement LinkedIn MCP server entry point in src/mcp_servers/linkedin/index.ts with MCP server setup and tool registration
- [x] T040 [US3] Implement create_post tool in src/mcp_servers/linkedin/tools/create_post.ts with: content (max 3000 chars), visibility (PUBLIC/CONNECTIONS), media parameters
- [x] T041 [US3] Add LinkedIn OAuth2 authentication to linkedin MCP server: read credentials from OS credential manager, implement token refresh
- [x] T042 [US3] Add idempotency check to create_post.ts: hash content + visibility + timestamp (rounded to minute), query sent_actions table before posting
- [x] T043 [US3] Add rate limiting to create_post.ts: max 10 posts/day counter with daily reset
- [x] T044 [US3] Create MCP tool definition contract in specs/002-external-connectivity/contracts/linkedin-mcp.json per plan.md section 3.4

**Checkpoint**: LinkedIn automation complete - can draft and publish approved posts

---

## Phase 7: User Story 5 - Scheduled Automation Tasks (Priority: P2)

**Goal**: Run scheduled tasks like daily briefings automatically via cron/Task Scheduler

**Independent Test**: Configure daily briefing schedule, trigger manually, verify briefing file generated with correct data

### Implementation for User Story 5

- [x] T045 [P] [US5] Create scheduled task runner in src/watchers/scheduler.py that invokes configured tasks with parameters, logs execution to audit logger
- [x] T046 [US5] Create daily briefing task in src/tasks/daily_briefing.py that generates /Vault/Briefings/YYYY-MM-DD.md with: pending tasks count, approval queue status, recent completions, key metrics
- [x] T047 [US5] Create PM2 ecosystem config in config/pm2.config.js with process definitions for: gmail-watcher, whatsapp-webhook, approval-watcher, resource-monitor
- [x] T048 [US5] Create cron setup script in scripts/setup_cron.sh (Mac/Linux) that registers daily briefing at 8am
- [x] T049 [US5] Create Task Scheduler setup script in scripts/setup_scheduler.ps1 (Windows) that registers daily briefing at 8am
- [x] T050 [US5] Document scheduler setup in specs/002-external-connectivity/quickstart.md section on scheduled tasks

**Checkpoint**: Scheduled automation complete - daily briefings run automatically

---

## Phase 8: Resource Monitoring & Graceful Degradation

**Purpose**: Memory monitoring, enforcement, and graceful degradation per FR-024 through FR-027

- [x] T051 Implement resource monitor in src/watchers/resource_monitor.py using psutil with: memory_usage_by_process(), total_memory_usage(), exceeds_budget() checks every 60 seconds
- [x] T052 Add graceful degradation to resource_monitor.py: when total > 400MB alert, when total > 500MB pause watchers in order (LinkedIn -> WhatsApp -> Gmail)
- [x] T053 Add automatic recovery to resource_monitor.py: when total < 350MB, resume paused watchers in reverse priority order
- [x] T054 Add memory metrics logging to resource_monitor.py: write to /Vault/Logs/metrics-YYYY-MM-DD.json every 60 seconds
- [x] T055 Integrate resource_monitor with PM2 config: add as managed process that monitors all watcher processes

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, integration, and final validation

### Documentation

- [x] T056 [P] Create research.md in specs/002-external-connectivity/ documenting OAuth2 flow, WhatsApp Business API setup, credential storage patterns, SQLite idempotency
- [x] T057 [P] Create data-model.md in specs/002-external-connectivity/ with Pydantic model definitions for all entities
- [x] T058 Create quickstart.md in specs/002-external-connectivity/ with step-by-step setup guide per plan.md section Phase 1

### Skills Integration

- [x] T059 [P] Update .claude/skills/email-ops/ skill to integrate with Gmail MCP server
- [x] T060 [P] Update .claude/skills/social-ops/ skill to integrate with LinkedIn MCP server
- [x] T061 [P] Update .claude/skills/manage-approval/ skill to use integrity validation
- [x] T062 [P] Update .claude/skills/watcher-manager/ skill to manage Gmail, WhatsApp, and resource monitor processes

### Dry-Run Mode

- [x] T063 Add dry-run flag support to all watchers: when DRY_RUN=true in .env, log actions instead of executing, write [DRY-RUN] prefix to action files
- [x] T064 Add dry-run support to MCP servers: when dry-run parameter true, return simulated success without API calls

### Final Validation

- [x] T065 Create end-to-end test script in scripts/test_e2e.sh that: sends test email, verifies action file, creates approval, verifies send (with dry-run)
- [x] T066 Update README.md with Silver Tier features, deployment instructions, runbook references
- [x] T067 Validate all contracts in specs/002-external-connectivity/contracts/ match implemented tool schemas

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1: Setup
    ↓
Phase 2: Foundational (BLOCKS all user stories)
    ↓
Phase 3: US4 - Approval Workflow (P1) ← Required by US1, US3
    ↓
┌───────────────┬───────────────┬───────────────┐
│ Phase 4: US1  │ Phase 5: US2  │ Phase 6: US3  │
│ Email (P1)    │ WhatsApp (P2) │ LinkedIn (P3) │
└───────────────┴───────────────┴───────────────┘
    ↓               ↓               ↓
Phase 7: US5 - Scheduled Tasks (P2)
    ↓
Phase 8: Resource Monitoring
    ↓
Phase 9: Polish
```

### User Story Dependencies

| Story | Depends On | Can Run In Parallel With |
|-------|------------|--------------------------|
| US4 (Approval) | Foundational | - |
| US1 (Email) | Foundational, US4 | US2, US3 (after US4 complete) |
| US2 (WhatsApp) | Foundational | US1, US3 (after US4 complete) |
| US3 (LinkedIn) | Foundational, US4 | US1, US2 (after US4 complete) |
| US5 (Scheduled) | US1, US2, US3 | - |

### Within Each Phase

- Tasks marked [P] can run in parallel
- Foundational T006-T010 are independent utility modules - can parallel
- US4 approval workflow must complete before US1/US3 can execute actions
- US1 watcher (T022-T025) can parallel with MCP server (T026-T030)
- US2 is fully independent after foundational
- US3 depends on approval workflow for post execution

---

## Parallel Execution Examples

### Phase 2: Foundational (All [P] tasks in parallel)

```
# Parallel batch 1:
T006: credentials.py
T007: idempotency.py
T008: integrity.py
T009: audit_logger.py
T010: retry.py

# Parallel batch 2 (after batch 1):
T011: base_watcher.py
T012: config.py
T013: vault.py
```

### Phase 4: US1 Email (Gmail watcher + MCP in parallel)

```
# After T025 (OAuth setup), these can parallel:
Batch 1: T022 (gmail_client.py) || T026 (npm init)
Batch 2: T023 (gmail_watcher.py) || T027, T028 (MCP server)
```

### Multiple User Stories (After US4 complete)

```
# Team of 3 developers:
Dev A: Phase 4 (US1 Email)
Dev B: Phase 5 (US2 WhatsApp)
Dev C: Phase 6 (US3 LinkedIn)
```

---

## Implementation Strategy

### MVP First (US4 + US1 Only)

1. Complete Phase 1: Setup (T001-T005)
2. Complete Phase 2: Foundational (T006-T013)
3. Complete Phase 3: US4 Approval Workflow (T014-T021)
4. Complete Phase 4: US1 Email (T022-T030)
5. **STOP and VALIDATE**: Test email detection → approval → send flow
6. Deploy with Gmail monitoring only

### Incremental Delivery

1. MVP: Setup + Foundational + US4 + US1 → Email monitoring works
2. Add US2 → WhatsApp messages detected
3. Add US3 → LinkedIn posts can be approved and published
4. Add US5 → Daily briefings run automatically
5. Add Phase 8 → Resource monitoring protects system
6. Add Phase 9 → Documentation and polish complete

---

## Task Summary

| Phase | Task Count | Parallel Tasks | Story |
|-------|------------|----------------|-------|
| Phase 1: Setup | 5 | 2 | - |
| Phase 2: Foundational | 8 | 5 | - |
| Phase 3: US4 Approval | 8 | 0 | US4 |
| Phase 4: US1 Email | 9 | 2 | US1 |
| Phase 5: US2 WhatsApp | 7 | 1 | US2 |
| Phase 6: US3 LinkedIn | 7 | 1 | US3 |
| Phase 7: US5 Scheduled | 6 | 1 | US5 |
| Phase 8: Resource Monitor | 5 | 0 | - |
| Phase 9: Polish | 12 | 6 | - |
| **Total** | **67** | **18** | - |

### By User Story

| Story | Tasks | Key Files |
|-------|-------|-----------|
| US1 (Email) | 9 | gmail_watcher.py, gmail_client.py, src/mcp_servers/gmail/ |
| US2 (WhatsApp) | 7 | whatsapp_webhook.py |
| US3 (LinkedIn) | 7 | src/mcp_servers/linkedin/ |
| US4 (Approval) | 8 | approval_watcher.py, approval_creator.py, integrity.py |
| US5 (Scheduled) | 6 | scheduler.py, daily_briefing.py, pm2.config.js |

### Independent Test Criteria

| Story | Test Method |
|-------|-------------|
| US1 | Send email with "urgent" keyword → action file → approve → email sent |
| US2 | Send WhatsApp with "invoice" keyword → webhook → action file created |
| US3 | Create post request → draft in /Pending_Approval → approve → LinkedIn post |
| US4 | Any action → approval file with hash → move to /Approved → executes |
| US5 | Configure briefing → wait for schedule → briefing file generated |

---

## Notes

- All watchers inherit from base_watcher.py for consistent memory monitoring and logging
- All MCP servers use OS credential manager for OAuth tokens
- All external actions check idempotency DB before execution
- DRY_RUN=true in .env enables safe testing without real API calls
- PM2 manages all watcher processes with automatic restart
