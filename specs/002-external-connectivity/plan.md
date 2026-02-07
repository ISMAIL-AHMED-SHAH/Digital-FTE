# Implementation Plan: External Connectivity (Silver Tier)

**Branch**: `002-external-connectivity` | **Date**: 2026-01-25 | **Spec**: [specs/002-external-connectivity/spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-external-connectivity/spec.md`

**Note**: This plan implements the Silver Tier milestone, adding external integrations (Gmail, WhatsApp, LinkedIn) with human-in-the-loop approval workflow and scheduled automation.

## Summary

Implement multiple external watchers (Gmail polling, WhatsApp webhooks, LinkedIn), MCP servers for executing approved actions (email send, social post), and file-based human-in-the-loop approval workflow. Includes OAuth2 credential management via OS credential managers, integrity validation for approval files, idempotency tracking via SQLite, memory-constrained resource management, and scheduled task execution via cron/Task Scheduler.

## Technical Context

**Language/Version**: Python 3.13+ (watchers), Node.js 24+ LTS (MCP servers)
**Primary Dependencies**:
- Python: google-auth-oauthlib, google-api-python-client, fastapi (webhook endpoint), uvicorn, pydantic, keyring, cryptography, watchdog (from Bronze)
- Node.js: @modelcontextprotocol/sdk, @google/generative-ai (optional), linkedin-api-client
**Storage**: SQLite3 (idempotency records, processed message IDs), filesystem (Markdown vault, JSON logs, .env)
**Testing**: pytest (Python), vitest or jest (Node.js MCP servers), integration tests with mock API endpoints
**Target Platform**: Windows 10/11, macOS 12+, Linux (Ubuntu 22.04+)
**Project Type**: Distributed system (multiple Python watchers + Node.js MCP servers + file-based orchestration)
**Performance Goals**:
- Gmail watcher: poll every 2 minutes, detect 95% of emails within 5 minutes
- WhatsApp webhook: <500ms response time to acknowledge webhook
- Approval workflow: user can review and approve in <1 minute
- MCP execution: send email within 10 minutes of approval, post to LinkedIn within 5 minutes
**Constraints**:
- Max 100MB RAM per watcher process, 500MB total for all watchers
- 7-day idempotency window with automatic cleanup
- No duplicate external actions during retries (100% idempotency)
- 99% uptime for watcher processes over 7 days
**Scale/Scope**:
- 3-5 concurrent watchers (Gmail, WhatsApp webhook handler, approval folder monitor, resource monitor, scheduled tasks)
- ~50 emails/day, ~20 WhatsApp messages/day, ~5 LinkedIn posts/week
- <1000 action files per month, <10MB SQLite database

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Requirement | Status | Compliance Notes |
|-----------|-------------|---------|------------------|
| **I. Local-First Architecture** | All data in Obsidian vault, no cloud storage except API calls | ✅ PASS | Action files, approval requests, logs all written to vault. OAuth tokens in OS keychain (local). SQLite database local. |
| **II. PRA Loop** | Perception → Reasoning → Action with filesystem communication | ✅ PASS | Watchers detect (Perception) → write to /Needs_Action → Claude reasons → writes to /Pending_Approval → MCP executes (Action). All via files. |
| **III. HITL Safety** | Sensitive actions require approval | ✅ PASS | All external actions (emails, posts, WhatsApp) go through /Pending_Approval. Integrity hashing prevents tampering (FR-020). Auto-expire after 24h. |
| **IV. Autonomous Persistence** | Multi-step tasks use Ralph Wiggum pattern | ⚠️ DEFERRED | Ralph Wiggum pattern is Gold Tier feature. Silver Tier uses manual orchestration via scheduled tasks and file watchers. |
| **V. Security & Credential Mgmt** | No secrets in vault, use .env and keychains | ✅ PASS | OAuth2 tokens in Windows Credential Manager/macOS Keychain (FR-021). API keys in .env (gitignored). DEV_MODE and --dry-run supported (FR-019). |
| **VI. Audit Logging** | All actions logged, 90-day retention | ✅ PASS | JSON logs to /Vault/Logs/YYYY-MM-DD.json with timestamp, action_type, parameters, approval_status, result (FR-012, FR-015). |
| **VII. Agent Skills** | Implement as Claude Code Skills | ✅ PASS | Email ops, social ops, approval management, scheduler already exist as Skills in `.claude/skills/`. Silver Tier extends these. |

**Gates**:
- ✅ No violations - proceed to Phase 0
- ⚠️ Ralph Wiggum deferred to Gold Tier per tiered roadmap

## Project Structure

### Documentation (this feature)

```text
specs/002-external-connectivity/
├── spec.md              # Feature requirements (already exists)
├── plan.md              # This file (/sp.plan command output)
├── research.md          # Phase 0 output: OAuth2, WhatsApp Business API, credential storage research
├── data-model.md        # Phase 1 output: Watcher, ActionFile, ApprovalRequest, IdempotencyRecord schemas
├── quickstart.md        # Phase 1 output: Setup guide for Gmail/WhatsApp/LinkedIn credentials
├── contracts/           # Phase 1 output: OpenAPI specs for webhook endpoints, MCP tool definitions
│   ├── whatsapp-webhook.openapi.yaml
│   ├── gmail-mcp.json
│   └── linkedin-mcp.json
└── tasks.md             # Phase 2 output (/sp.tasks command - NOT created by /sp.plan)
```

### Source Code (repository root)

```text
src/
├── file_watcher/        # Existing Bronze Tier implementation
│   ├── __init__.py
│   ├── config.py
│   ├── watcher.py
│   ├── action_file.py
│   └── logger.py
├── watchers/            # NEW: External service watchers (Silver Tier)
│   ├── __init__.py
│   ├── base_watcher.py         # Abstract base class with memory monitoring, dry-run, logging
│   ├── gmail_watcher.py        # FR-001: Poll Gmail API every 2 minutes
│   ├── whatsapp_webhook.py     # FR-002, FR-002a: FastAPI webhook handler
│   ├── approval_watcher.py     # FR-008, FR-009: Monitor /Approved, /Rejected folders
│   ├── resource_monitor.py     # FR-024, FR-025, FR-026: Memory monitoring and graceful degradation
│   └── config.py               # Watcher-specific config (extends Bronze config pattern)
├── common/              # NEW: Shared utilities across watchers and MCP servers
│   ├── __init__.py
│   ├── credentials.py          # FR-021, FR-022: OS credential manager integration
│   ├── idempotency.py          # FR-014, FR-014a: SQLite idempotency database
│   ├── integrity.py            # FR-020: SHA-256 hash generation and validation
│   ├── audit_logger.py         # FR-012, FR-015: Structured JSON logging
│   └── retry.py                # FR-013: Exponential backoff retry logic
└── mcp_servers/         # NEW: Model Context Protocol servers (Node.js)
    ├── gmail/
    │   ├── package.json
    │   ├── index.ts            # FR-004: Gmail send email MCP server
    │   └── tools/
    │       └── send_email.ts
    ├── linkedin/
    │   ├── package.json
    │   ├── index.ts            # FR-005: LinkedIn post MCP server
    │   └── tools/
    │       └── create_post.ts
    └── whatsapp/
        ├── package.json        # (Future: WhatsApp send if needed)
        └── index.ts

tests/
├── unit/
│   ├── test_gmail_watcher.py
│   ├── test_whatsapp_webhook.py
│   ├── test_approval_watcher.py
│   ├── test_credentials.py
│   ├── test_idempotency.py
│   └── test_integrity.py
├── integration/
│   ├── test_watcher_lifecycle.py
│   ├── test_approval_workflow.py
│   ├── test_mcp_gmail.py
│   └── test_mcp_linkedin.py
└── fixtures/
    ├── mock_gmail_api.py
    ├── mock_whatsapp_webhook.py
    └── sample_approval_files.py

.claude/skills/           # Existing Claude Code Skills (extend for Silver Tier)
├── email-ops/            # Extend: integrate with Gmail MCP
├── social-ops/           # Extend: integrate with LinkedIn MCP
├── manage-approval/      # Extend: add integrity validation
├── scheduler/            # Use as-is for FR-011
└── watcher-manager/      # Extend: add Gmail/WhatsApp/resource monitor management

config/
├── .env.example          # Template for API keys (not committed)
└── watcher_config.yaml   # Watcher-specific settings (intervals, keywords, rate limits)

scripts/
├── setup_gmail_oauth.py  # Helper: Gmail OAuth2 flow for initial token
├── setup_whatsapp.py     # Helper: WhatsApp Business API webhook registration
├── test_webhook.sh       # Helper: Test WhatsApp webhook endpoint locally
└── init_idempotency_db.sql  # SQLite schema for idempotency tables
```

**Structure Decision**: Hybrid structure with Python watchers (extends Bronze Tier pattern) and Node.js MCP servers (new). This follows the constitution's PRA loop: Python watchers handle Perception, filesystem handles inter-process communication, and Node.js MCP servers handle Action execution. Reuses Bronze Tier's `src/file_watcher` module pattern (config.py, watcher.py, action_file.py, logger.py) for consistency.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

N/A - No constitution violations requiring justification.

---

## 1. Scope and Dependencies

### In Scope (Silver Tier)

1. **External Service Watchers**:
   - Gmail Watcher: Poll Gmail API every 2 minutes for important/unread emails (FR-001)
   - WhatsApp Webhook Handler: FastAPI endpoint receiving WhatsApp Business API webhooks (FR-002, FR-002a)
   - Approval Folder Watcher: Monitor /Pending_Approval, /Approved, /Rejected folders (FR-008, FR-009)
   - Resource Monitor: Track memory usage, enforce limits, trigger graceful degradation (FR-024, FR-025, FR-026)

2. **MCP Servers for External Actions**:
   - Gmail MCP: Send emails via Gmail API (FR-004)
   - LinkedIn MCP: Create and publish LinkedIn posts (FR-005)

3. **Human-in-the-Loop Approval Workflow**:
   - File-based approval signaling (move files between folders) (FR-006, FR-007)
   - Integrity validation via SHA-256 hashes to prevent tampering (FR-020)
   - Automatic expiration after 24 hours (FR-010)

4. **Security & Credential Management**:
   - OAuth2 tokens stored in OS credential manager (Windows Credential Manager, macOS Keychain) with AES-256 encrypted file fallback (FR-021)
   - Automatic token refresh with retry logic (FR-022, FR-023)

5. **Idempotency & Retry Logic**:
   - SQLite database tracking sent emails/posts to prevent duplicates during retries (FR-014, FR-014a)
   - Exponential backoff retry for transient failures (FR-013)
   - 7-day deduplication window with automatic cleanup

6. **Scheduled Automation**:
   - Cron (Mac/Linux) or Task Scheduler (Windows) integration for daily briefings, audits (FR-011)

7. **Audit Logging**:
   - JSON logs to /Vault/Logs/YYYY-MM-DD.json (FR-012, FR-015)
   - Log all watcher detections, approvals, MCP executions, errors

8. **Operational Features**:
   - Dry-run mode for safe testing (FR-019)
   - Rate limiting (50 emails/day, 10 LinkedIn posts/day) (FR-018)
   - Dashboard.md updates after each action (FR-017)

### Out of Scope (Deferred to Gold/Platinum Tiers)

- Ralph Wiggum autonomous persistence pattern (Gold Tier)
- Multi-agent coordination (Platinum Tier)
- Odoo ERP integration (Gold Tier)
- CEO Briefing weekly summaries (Gold Tier)
- Cloud deployment (Platinum Tier)
- WhatsApp message sending (not required by spec; only receiving)
- Advanced AI features (sentiment analysis, auto-categorization)

### External Dependencies

| Dependency | Ownership | Purpose | Risk |
|------------|-----------|---------|------|
| Gmail API | Google | Email polling and sending | Rate limits, OAuth token expiry |
| WhatsApp Business API | Meta | Webhook message delivery | Webhook reliability, credential validation |
| LinkedIn API | Microsoft | Post publishing | Rate limits, API deprecation |
| OS Credential Manager | Windows/macOS | Secure token storage | Platform-specific implementations |
| SQLite | Python stdlib | Idempotency tracking | Database corruption (mitigated with backups) |
| Claude Code | Anthropic | Reasoning and action planning | API availability, token limits |
| Obsidian Vault | User | File-based state storage | User must maintain vault structure |

---

## 2. Key Decisions and Rationale

### Decision 1: WhatsApp Business API (Webhook-Based) vs. Unofficial WhatsApp Web Automation

**Options Considered**:
1. WhatsApp Business API with official webhooks (chosen)
2. Playwright-based WhatsApp Web scraping
3. Third-party WhatsApp gateway services

**Trade-offs**:
- **Business API**: Legal, reliable, webhook-based (real-time), but requires business account approval
- **Playwright**: Fast to prototype, but violates WhatsApp ToS, high risk of account ban
- **Third-party**: Convenient, but introduces data privacy risk and vendor lock-in

**Rationale**: Business API is the only legally compliant option for production use. Webhook-based architecture eliminates polling overhead and provides real-time message delivery. Clarification confirmed this choice (spec.md line 95).

**Principles**: Prioritizes legal compliance, production safety, and real-time performance over rapid prototyping.

---

### Decision 2: OS Credential Manager (Windows Credential Manager / macOS Keychain) for OAuth Tokens

**Options Considered**:
1. OS credential manager with encrypted file fallback (chosen)
2. Encrypted .env files only
3. Cloud secret management (AWS Secrets Manager, Azure Key Vault)

**Trade-offs**:
- **OS Credential Manager**: Most secure (OS-level encryption), automatic rotation support, but platform-specific code
- **Encrypted .env**: Simpler, but requires manual key management and rotation
- **Cloud Secrets**: Enterprise-grade, but violates Local-First principle and adds external dependency

**Rationale**: OS credential managers provide OS-level encryption and integrate with automatic token refresh flows. Fallback to encrypted file ensures cross-platform compatibility. Clarification confirmed this approach (spec.md line 96).

**Principles**: Balances security (OS encryption) with local-first architecture. Reversible via fallback mechanism.

---

### Decision 3: File-Based Approval Workflow with SHA-256 Integrity Hashing

**Options Considered**:
1. File-based signaling with integrity hashing (chosen)
2. File-based signaling without validation
3. Web UI approval dashboard
4. CLI approval tool

**Trade-offs**:
- **File + Hashing**: Tamper-proof, Obsidian-native, auditable, but requires hash validation logic
- **File without Hashing**: Simpler, but allows malicious file modification to change action parameters
- **Web UI**: Better UX, but violates Local-First and requires server infrastructure
- **CLI**: More secure than files, but higher friction for user (must leave Obsidian)

**Rationale**: File-based workflow keeps user in Obsidian (familiar environment). SHA-256 hashing prevents parameter tampering while maintaining transparency (hash is human-readable in YAML). Clarification confirmed this approach (spec.md line 97).

**Principles**: Prioritizes security (tamper-proofing) and user experience (stay in Obsidian) over implementation simplicity.

---

### Decision 4: SQLite for Idempotency Tracking with 7-Day Retention

**Options Considered**:
1. SQLite with 7-day retention (chosen)
2. In-memory cache (e.g., Redis)
3. Flat file log parsing
4. No idempotency checks (rely on external API idempotency)

**Trade-offs**:
- **SQLite**: Persistent, queryable, local-first, but requires database maintenance
- **In-memory**: Fastest, but data lost on restart (defeats purpose)
- **Flat file**: Simplest, but slow lookups and no indexing
- **No checks**: Simplest, but risks duplicate sends on retries

**Rationale**: SQLite provides persistent, indexed storage with sub-millisecond lookups. 7-day window balances safety (covers retries) with storage (auto-cleanup prevents bloat). Clarification confirmed this approach (spec.md line 99).

**Principles**: Smallest viable solution with measurable retention policy. Reversible (can extend retention if needed).

---

### Decision 5: Memory Budget (100MB per Watcher, 500MB Total) with Graceful Degradation

**Options Considered**:
1. Fixed memory limits with graceful degradation (chosen)
2. Unlimited memory with monitoring alerts only
3. Docker containers with cgroup limits
4. Dynamic scaling based on system resources

**Trade-offs**:
- **Fixed limits + degradation**: Predictable resource usage, prevents system slowdown, but may pause low-priority watchers
- **Unlimited + alerts**: Simpler, but risks system slowdown if watchers leak memory
- **Docker**: Strongest isolation, but adds deployment complexity and violates simplicity principle
- **Dynamic scaling**: Most flexible, but complex to implement and reason about

**Rationale**: Fixed budgets provide predictable performance on constrained systems. Graceful degradation (pause LinkedIn → WhatsApp → Gmail) ensures critical functionality (Gmail) remains available. Clarification confirmed this approach (spec.md line 98).

**Principles**: Prioritizes reliability and user control over maximum throughput. Clear priority order (Gmail > WhatsApp > LinkedIn) aligns with business value.

---

## 3. Interfaces and API Contracts

### 3.1 Watcher → Vault Interface (Action Files)

**Input**: External event (new Gmail message, WhatsApp webhook, file drop)

**Output**: Markdown file written to `/Vault/Needs_Action/` with YAML frontmatter

**Contract**:
```yaml
---
type: "email" | "whatsapp" | "file_drop"
source: string (email address, phone number, or file path)
subject: string (email subject, WhatsApp message preview, or filename)
content: string (full message body or file metadata)
priority: "high" | "normal" | "low"
timestamp: string (ISO 8601 UTC format)
status: "pending"
message_id: string (Message-ID header for emails, SHA-256 hash for WhatsApp)
---

## [Type-Specific Title]

[Markdown body with formatted content]
```

**Error Handling**:
- Missing required fields → Log error, skip file creation (resilient mode)
- Duplicate message_id → Skip (already processed via idempotency check)
- Vault write failure → Retry with exponential backoff (max 5 retries), log error

**Idempotency**: Watchers query SQLite `processed_messages` table before creating action files to prevent duplicate processing.

---

### 3.2 Vault → MCP Server Interface (Approval Requests)

**Input**: Markdown file in `/Vault/Pending_Approval/` with YAML frontmatter

**Output**: MCP tool execution (email send, LinkedIn post)

**Contract**:
```yaml
---
action_type: "email_send" | "linkedin_post"
parameters:
  to: string (email address or LinkedIn visibility)
  subject: string (email subject or post title)
  body: string (email body or post content)
  cc: string[] (optional, email only)
  attachments: string[] (optional, file paths)
created_timestamp: string (ISO 8601 UTC)
expires_timestamp: string (ISO 8601 UTC, created + 24h)
status: "pending"
integrity_hash: string (SHA-256 of action_type + parameters + created_timestamp)
reason: string (why this action is needed)
approval_requested_by: "claude-code"
---

## Approval Required: [Action Description]

[Markdown explanation of what will be done and why]
```

**Approval Signaling**:
- User moves file to `/Vault/Approved/` → Execute action
- User moves file to `/Vault/Rejected/` → Log rejection, do not execute
- File remains in `/Pending_Approval/` > 24h → Auto-move to `/Vault/Expired/`

**Integrity Validation**:
1. Read file from `/Vault/Approved/`
2. Extract `integrity_hash` from YAML
3. Recompute hash from `action_type + parameters + created_timestamp`
4. If mismatch → Move to `/Vault/Rejected/_TAMPERED_[filename]`, log alert, do NOT execute

**Error Handling**:
- Missing `integrity_hash` → Reject as invalid, move to `/Rejected/_INVALID_[filename]`
- MCP execution failure → Retry with exponential backoff, check idempotency DB before each retry
- Timeout (>10 min for email, >5 min for LinkedIn) → Log failure, alert user

**Idempotency**: Before executing, query SQLite `sent_actions` table with action identifier (email Message-ID or content hash). If found within 7-day window, skip execution and mark as completed.

---

### 3.3 WhatsApp Business API Webhook Interface

**Endpoint**: `POST /webhooks/whatsapp`

**Input** (from Meta):
```json
{
  "object": "whatsapp_business_account",
  "entry": [{
    "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
    "changes": [{
      "value": {
        "messaging_product": "whatsapp",
        "metadata": {"phone_number_id": "PHONE_NUMBER_ID"},
        "messages": [{
          "from": "SENDER_PHONE",
          "id": "MESSAGE_ID",
          "timestamp": "UNIX_TIMESTAMP",
          "type": "text",
          "text": {"body": "MESSAGE_CONTENT"}
        }]
      }
    }]
  }]
}
```

**Output**:
- HTTP 200 (acknowledge receipt within 500ms)
- Action file written to `/Vault/Needs_Action/` asynchronously

**Security**:
- Validate `X-Hub-Signature-256` header using app secret
- Reject requests with invalid signatures (HTTP 401)
- Rate limit: max 100 requests/min per IP (prevent DoS)

**Keyword Filtering**:
- Only process messages containing configured keywords (e.g., "invoice", "pricing", "support")
- Skip messages without keywords to reduce noise

**Error Handling**:
- Signature validation failure → HTTP 401, log security event
- Vault write failure → HTTP 200 (acknowledge to Meta), retry write in background, alert user if retries exhausted

---

### 3.4 MCP Tool Definitions

#### Gmail MCP: `send_email`

```typescript
{
  "name": "send_email",
  "description": "Send an email via Gmail API",
  "inputSchema": {
    "type": "object",
    "properties": {
      "to": {"type": "string", "format": "email"},
      "subject": {"type": "string"},
      "body": {"type": "string"},
      "cc": {"type": "array", "items": {"type": "string", "format": "email"}},
      "bcc": {"type": "array", "items": {"type": "string", "format": "email"}},
      "attachments": {"type": "array", "items": {"type": "string"}}
    },
    "required": ["to", "subject", "body"]
  },
  "outputSchema": {
    "type": "object",
    "properties": {
      "message_id": {"type": "string"},
      "status": {"type": "string", "enum": ["sent", "failed"]},
      "error": {"type": "string"}
    }
  }
}
```

**Rate Limits**: Max 50 emails/day (enforced by MCP server via counter in SQLite)

**Idempotency**: Generate stable Message-ID from `to + subject + body hash`. Check `sent_actions` table before sending.

---

#### LinkedIn MCP: `create_post`

```typescript
{
  "name": "create_post",
  "description": "Create a LinkedIn post",
  "inputSchema": {
    "type": "object",
    "properties": {
      "content": {"type": "string", "maxLength": 3000},
      "visibility": {"type": "string", "enum": ["PUBLIC", "CONNECTIONS"]},
      "media": {"type": "array", "items": {"type": "string"}}
    },
    "required": ["content", "visibility"]
  },
  "outputSchema": {
    "type": "object",
    "properties": {
      "post_id": {"type": "string"},
      "url": {"type": "string"},
      "status": {"type": "string", "enum": ["published", "failed"]},
      "error": {"type": "string"}
    }
  }
}
```

**Rate Limits**: Max 10 posts/day (enforced by MCP server)

**Idempotency**: Hash `content + visibility + timestamp` (rounded to minute). Check `sent_actions` table before posting.

---

## 4. Non-Functional Requirements (NFRs) and Budgets

### 4.1 Performance

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Gmail watcher: detection latency | 95% of emails detected within 5 min | Timestamp diff between email arrival (Gmail API) and action file creation |
| WhatsApp webhook: response time | <500ms HTTP 200 response | Webhook handler timing logs |
| Approval workflow: review latency | User can approve in <1 min | File modification timestamp diff |
| Email send latency | Within 10 min of approval | Timestamp diff between approval and Gmail API send |
| LinkedIn post latency | Within 5 min of approval | Timestamp diff between approval and LinkedIn API post |
| Idempotency check latency | <10ms per query | SQLite query timing logs |

### 4.2 Reliability

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Watcher uptime | 99% over 7 days | Calculate `(uptime - downtime) / uptime` from process logs |
| OAuth token refresh success rate | 99% | Count successful refreshes / total refresh attempts |
| Idempotency accuracy | 100% duplicate prevention | Zero duplicate sends in audit logs during retries |
| Integrity validation accuracy | 100% tampered file detection | Reject all files with mismatched hashes |
| Zero unauthorized actions | 100% compliance | All sensitive actions logged with approval_status="approved" |

**Error Budgets**:
- Max 1% watcher downtime per week (≈1.68 hours)
- Max 1% token refresh failures (auto-recoverable via retry)
- Zero tolerance for integrity violations or unauthorized actions

**Degradation Strategy**:
- Memory budget exceeded → Pause low-priority watchers (LinkedIn → WhatsApp → Gmail)
- OAuth token refresh fails after 3 retries → Pause watcher, alert user
- Vault unavailable → Queue action files in memory (max 100), write when available
- API rate limit hit → Queue requests, resume after rate limit window

### 4.3 Security

| Requirement | Implementation | Validation |
|-------------|----------------|------------|
| No credentials in vault | OAuth tokens in OS credential manager, API keys in .env (gitignored) | Pre-commit hook checks for secrets |
| Tamper-proof approvals | SHA-256 integrity hashing of critical fields | 100% rejection of tampered files in tests |
| Encrypted credential fallback | AES-256 encryption with machine-specific key | Decrypt test in unit tests |
| Webhook signature validation | HMAC-SHA256 verification using app secret | Reject invalid signatures (HTTP 401) |
| Audit trail immutability | Append-only JSON logs | No deletion/modification of log files |

**AuthN/AuthZ**:
- Gmail: OAuth2 with `gmail.send` and `gmail.readonly` scopes
- LinkedIn: OAuth2 with `w_member_social` scope
- WhatsApp: App secret verification for webhook signatures
- OS Credential Manager: User-level access (no system-wide storage)

**Data Handling**:
- Email content: Stored in vault action files (user-controlled), not sent to third parties
- WhatsApp messages: Stored in vault action files, signatures validated before storage
- OAuth tokens: Encrypted at rest (OS credential manager or AES-256 file)
- Logs: Contain metadata only (no email bodies or sensitive content)

**Secrets Rotation**:
- Manual rotation: User must re-authenticate (OAuth flow) to update tokens
- Automatic: OAuth refresh tokens updated automatically on expiry
- Audit: Log all credential access and refresh attempts

### 4.4 Cost

| Resource | Budget | Rationale |
|----------|--------|-----------|
| Memory | 500MB total (100MB per watcher) | Fits on 4GB RAM systems with room for OS and Claude |
| Disk | <50MB for code, <10MB for SQLite DB | Lightweight, no large dependencies |
| API costs | Gmail: Free (personal account), LinkedIn: Free (personal), WhatsApp: ~$0.005/message | Business API costs negligible at <1000 msgs/month |
| Compute | CPU <5% avg (polling watchers sleep) | Efficient polling with long sleep intervals |

---

## 5. Data Management and Migration

### 5.1 Source of Truth

- **Vault**: Obsidian vault (`/Vault/`) is the single source of truth for all action files, approval requests, logs
- **SQLite**: Idempotency database (`idempotency.db`) is the source of truth for processed message IDs and sent action identifiers
- **OS Credential Manager**: OAuth tokens (authoritative for authentication)

### 5.2 Schema Evolution

**SQLite Schema** (`scripts/init_idempotency_db.sql`):
```sql
CREATE TABLE processed_messages (
    message_id TEXT PRIMARY KEY,
    source TEXT NOT NULL,  -- 'gmail', 'whatsapp', 'file_drop'
    processed_at TEXT NOT NULL,  -- ISO 8601 UTC
    expires_at TEXT NOT NULL  -- processed_at + 7 days
);

CREATE INDEX idx_expires_at ON processed_messages(expires_at);

CREATE TABLE sent_actions (
    action_id TEXT PRIMARY KEY,  -- Message-ID or content hash
    action_type TEXT NOT NULL,  -- 'email_send', 'linkedin_post'
    recipient TEXT,  -- email or LinkedIn visibility
    sent_at TEXT NOT NULL,  -- ISO 8601 UTC
    expires_at TEXT NOT NULL,  -- sent_at + 7 days
    result_status TEXT NOT NULL  -- 'success', 'failed'
);

CREATE INDEX idx_sent_expires_at ON sent_actions(expires_at);
```

**Migration Strategy**:
- V1 → V2: ALTER TABLE to add columns (backward compatible)
- Versioning: Store schema version in `PRAGMA user_version`
- Rollback: Restore from `.db-backup` file created daily

### 5.3 Data Retention

| Data Type | Retention | Cleanup Method | Rationale |
|-----------|-----------|----------------|-----------|
| Action files | User-controlled | Manual deletion from vault | User may need historical reference |
| Approval requests | 30 days (suggested) | Manual or scheduled cleanup | Audit trail for compliance |
| Logs | 90 days | Scheduled deletion via cron/Task Scheduler | Constitution requirement (Principle VI) |
| SQLite idempotency records | 7 days | Automatic: `DELETE WHERE expires_at < NOW()` daily | Balance safety with storage |
| OAuth tokens | Until revoked | Manual revocation or automatic refresh | Persistent authentication |

**Backup Strategy**:
- SQLite: Daily backup to `idempotency.db-backup` before cleanup
- Vault: User's existing Obsidian vault backup (e.g., git, cloud sync)
- Logs: Compress logs older than 7 days to `.gz` (90-day retention still applies)

---

## 6. Operational Readiness

### 6.1 Observability

**Logs**:
- **Format**: JSON lines (one JSON object per line)
- **Location**: `/Vault/Logs/YYYY-MM-DD.json`
- **Fields**: `timestamp`, `level`, `component`, `action_type`, `actor`, `target`, `parameters`, `approval_status`, `result`, `error`, `traceback`

**Example Log Entry**:
```json
{
  "timestamp": "2026-01-25T14:32:10Z",
  "level": "INFO",
  "component": "gmail_watcher",
  "action_type": "email_detected",
  "actor": "gmail_watcher",
  "target": "sender@example.com",
  "parameters": {"subject": "Invoice #1234", "message_id": "abc123"},
  "approval_status": null,
  "result": "action_file_created",
  "error": null
}
```

**Metrics** (logged to `/Vault/Logs/metrics-YYYY-MM-DD.json`):
- Watcher memory usage (MB): logged every 60s by resource_monitor
- Email detection count: incremented per detected email
- Approval latency: time from /Pending_Approval write to /Approved move
- MCP execution duration: time from approval to API response
- Idempotency cache hits: count of duplicate detections prevented

**Traces**:
- No distributed tracing (single-machine system)
- Correlation ID: Use action file filename to trace end-to-end flow (detection → approval → execution)

### 6.2 Alerting

| Alert | Threshold | Notification Method | Owner |
|-------|-----------|-------------------|--------|
| Watcher down | Process exit or 5 min no heartbeat | Write to `/Vault/Alerts/watcher_down.md`, dashboard update | User |
| Memory budget exceeded | >400MB (80% of 500MB) | Write to `/Vault/Alerts/memory_warning.md` | User |
| OAuth token refresh failed | 3 consecutive failures | Write to `/Vault/Alerts/oauth_failure.md`, pause watcher | User |
| Idempotency DB corruption | SQLite integrity check fails | Write to `/Vault/Alerts/db_corrupted.md` | User |
| Tampered approval file | integrity_hash mismatch | Write to `/Vault/Alerts/tampered_approval.md`, move to /Rejected | User |
| API rate limit hit | HTTP 429 response | Log warning, queue request, retry after backoff | User (informational) |

**On-Call**: N/A (personal/small business use). User reviews dashboard daily.

### 6.3 Runbooks

**Runbook 1: Watcher Won't Start**
1. Check logs in `/Vault/Logs/YYYY-MM-DD.json` for errors
2. Verify vault structure (Needs_Action, Pending_Approval, Approved, Rejected folders exist)
3. Check OS credential manager for OAuth tokens (Windows: `cmdkey /list`, macOS: `security find-generic-password`)
4. Re-run OAuth setup script: `python scripts/setup_gmail_oauth.py`
5. Test with `--dry-run` flag: `python -m watchers.gmail_watcher --dry-run`

**Runbook 2: OAuth Token Expired**
1. Check alert: `/Vault/Alerts/oauth_failure.md`
2. Run setup script to refresh: `python scripts/setup_gmail_oauth.py`
3. Verify token in credential manager
4. Restart watcher: `pm2 restart gmail-watcher`

**Runbook 3: Memory Budget Exceeded**
1. Check resource_monitor logs for memory usage breakdown
2. Identify highest memory watcher
3. Options: (a) Increase check interval to reduce memory, (b) Restart watcher, (c) Disable low-priority watchers
4. Monitor metrics to confirm memory drops below threshold

**Runbook 4: Duplicate Emails Sent**
1. Check audit logs for duplicate `message_id` in `sent_actions` table
2. Query SQLite: `SELECT * FROM sent_actions WHERE action_id = 'MESSAGE_ID'`
3. If duplicates found → BUG, investigate idempotency logic
4. Remediation: Manual apology email, add test case for this scenario

### 6.4 Deployment and Rollback

**Deployment Steps**:
1. Install Python dependencies: `pip install -r requirements.txt`
2. Install Node.js MCP server dependencies: `cd src/mcp_servers/gmail && npm install`
3. Initialize SQLite database: `sqlite3 idempotency.db < scripts/init_idempotency_db.sql`
4. Configure credentials:
   - Run `python scripts/setup_gmail_oauth.py` (stores token in OS credential manager)
   - Run `python scripts/setup_whatsapp.py` (registers webhook endpoint)
   - Add LinkedIn credentials to `.env` file
5. Start watchers via PM2:
   ```bash
   pm2 start config/pm2.config.js
   ```
6. Verify watchers running: `pm2 status`
7. Test with dry-run: Create test email, verify action file appears in /Needs_Action

**Rollback Steps**:
1. Stop all watchers: `pm2 stop all`
2. Restore SQLite backup: `cp idempotency.db-backup idempotency.db`
3. Restore code from git: `git checkout <previous-tag>`
4. Restart watchers: `pm2 restart all`
5. Verify logs for normal operation

**Feature Flags**:
- `DRY_RUN=true` in `.env`: Enable dry-run mode (log only, no file writes)
- `ENABLE_WHATSAPP=false`: Disable WhatsApp webhook handler
- `ENABLE_LINKEDIN=false`: Disable LinkedIn MCP server

**Compatibility**:
- Backward compatible: New watchers can coexist with Bronze Tier file_watcher
- Forward compatible: Vault file format unchanged, safe to upgrade

### 6.5 Testing Strategy

**Unit Tests** (pytest):
- `test_gmail_watcher.py`: Mock Gmail API responses, verify action file creation
- `test_credentials.py`: Mock OS credential manager, test token retrieval and refresh
- `test_idempotency.py`: Test SQLite queries, duplicate detection, cleanup
- `test_integrity.py`: Test SHA-256 hash generation and validation

**Integration Tests** (pytest):
- `test_watcher_lifecycle.py`: Start watcher, trigger event, verify action file, stop watcher
- `test_approval_workflow.py`: Create approval file, move to /Approved, verify MCP execution
- `test_mcp_gmail.py`: Mock Gmail API, send test email via MCP, verify idempotency

**Contract Tests**:
- Validate WhatsApp webhook payload against OpenAPI spec
- Validate MCP tool schemas against @modelcontextprotocol/sdk types

**End-to-End Tests** (manual with sandbox accounts):
1. Send test email to Gmail sandbox account → Verify action file created
2. Move approval file to /Approved → Verify email sent via Gmail
3. Send WhatsApp test message → Verify webhook received and action file created
4. Tamper with approval file (modify `to` address) → Verify rejection with `_TAMPERED` suffix

**Performance Tests**:
- Memory leak test: Run watchers for 24 hours, monitor memory usage (should stay <100MB per watcher)
- Load test: Send 100 WhatsApp webhooks in 1 minute → Verify all processed without drops

---

## 7. Risk Analysis and Mitigation

### Risk 1: OAuth Token Expiry Causes Watcher Downtime

**Likelihood**: Medium (tokens expire every 1-7 days depending on provider)
**Impact**: High (watcher can't access Gmail/LinkedIn APIs)
**Blast Radius**: Single watcher (Gmail or LinkedIn)

**Mitigation**:
- Automatic token refresh with exponential backoff (FR-022)
- Alert user after 3 failed refresh attempts (FR-023)
- Graceful degradation: Pause watcher until user re-authenticates

**Kill Switch**: Stop watcher via PM2: `pm2 stop gmail-watcher`

**Guardrails**:
- Test token refresh in integration tests
- Monitor token expiry timestamps in logs

---

### Risk 2: WhatsApp Webhook Signature Validation Bypass

**Likelihood**: Low (requires attacker to know app secret)
**Impact**: Critical (malicious messages could trigger unintended actions)
**Blast Radius**: All WhatsApp-triggered actions

**Mitigation**:
- Strict HMAC-SHA256 signature validation (reject on mismatch)
- App secret stored in .env, never logged or exposed
- Rate limiting (max 100 webhooks/min) to prevent DoS

**Kill Switch**: Disable WhatsApp webhook handler via feature flag: `ENABLE_WHATSAPP=false`

**Guardrails**:
- Unit test for signature validation with known test vectors
- Log all webhook signature validation failures for security monitoring

---

### Risk 3: Tampered Approval Files Execute Modified Actions

**Likelihood**: Low (requires user to manually edit file after creation)
**Impact**: Critical (could send email to wrong recipient, post unintended content)
**Blast Radius**: Single action

**Mitigation**:
- SHA-256 integrity hashing of critical fields (FR-020)
- Reject files with mismatched hashes, move to /Rejected with `_TAMPERED` suffix
- Alert user via `/Vault/Alerts/tampered_approval.md`

**Kill Switch**: Disable approval workflow processing: Stop `approval_watcher` via PM2

**Guardrails**:
- Unit test: Modify approval file parameters, verify rejection
- Integration test: End-to-end tamper detection with real file system

---

### Risk 4: Idempotency Database Corruption Causes Duplicate Sends

**Likelihood**: Low (SQLite is robust, but corruption possible on disk failure)
**Impact**: High (duplicate emails, posts cause user embarrassment, waste API quota)
**Blast Radius**: All external actions

**Mitigation**:
- Daily backup of `idempotency.db` to `idempotency.db-backup`
- SQLite integrity check on watcher startup: `PRAGMA integrity_check`
- Fallback: If corruption detected, attempt to recreate from backup, pause actions until verified

**Kill Switch**: Pause all MCP executions: Stop `approval_watcher` via PM2

**Guardrails**:
- Test database recreation from backup in integration tests
- Monitor database file size (alert if exceeds 10MB, indicating cleanup failure)

---

### Risk 5: Memory Leak in Watcher Exceeds Budget, Slows System

**Likelihood**: Medium (Python long-running processes can leak if not carefully managed)
**Impact**: Medium (system slowdown, potential crash)
**Blast Radius**: All watchers

**Mitigation**:
- Memory monitoring every 60 seconds (resource_monitor) (FR-025)
- Graceful degradation: Pause watchers in priority order when >80% budget (FR-026)
- Automatic restart if single watcher exceeds 100MB limit (FR-024)

**Kill Switch**: Stop all watchers: `pm2 stop all`, investigate memory leak

**Guardrails**:
- 24-hour soak test: Run watchers under load, verify memory stays below 100MB
- Alert user at 80% budget (400MB total) to take action before critical threshold

---

## 8. Evaluation and Validation

### 8.1 Definition of Done

**Functional Completion**:
- [ ] All FR-001 through FR-027 requirements implemented and tested
- [ ] Gmail watcher polls every 2 minutes, creates action files for important emails
- [ ] WhatsApp webhook handler receives messages, validates signatures, filters by keywords
- [ ] Approval workflow: move files between /Pending_Approval, /Approved, /Rejected triggers MCP execution
- [ ] Integrity validation rejects tampered files with mismatched SHA-256 hashes
- [ ] OAuth tokens stored in OS credential manager with automatic refresh
- [ ] Idempotency checks prevent duplicate sends during retries (7-day window)
- [ ] Memory monitoring enforces 100MB per watcher, 500MB total with graceful degradation
- [ ] Audit logs record all actions to `/Vault/Logs/YYYY-MM-DD.json`
- [ ] Dry-run mode supported for safe testing

**Testing Completion**:
- [ ] All unit tests pass (>90% code coverage for core logic)
- [ ] All integration tests pass (watcher lifecycle, approval workflow, MCP execution)
- [ ] Contract tests validate WhatsApp webhook and MCP tool schemas
- [ ] End-to-end test with sandbox accounts: email send, LinkedIn post
- [ ] Performance test: watchers run 24h without exceeding memory budget
- [ ] Security test: tampered approval file rejected, webhook signature validation enforced

**Documentation Completion**:
- [ ] `research.md`: OAuth2 flow, WhatsApp Business API setup, credential storage patterns
- [ ] `data-model.md`: Watcher, ActionFile, ApprovalRequest, IdempotencyRecord schemas
- [ ] `quickstart.md`: Step-by-step setup guide for Gmail, WhatsApp, LinkedIn credentials
- [ ] `contracts/`: OpenAPI spec for WhatsApp webhook, MCP tool definitions for Gmail and LinkedIn
- [ ] README: Updated with Silver Tier features, deployment instructions, runbooks

**Operational Readiness**:
- [ ] Deployment script tested on clean Windows and macOS environments
- [ ] Runbooks validated (watcher restart, OAuth refresh, memory troubleshooting)
- [ ] Alerts configured and tested (watcher down, OAuth failure, tampered file)
- [ ] Backup/restore tested for SQLite database

### 8.2 Output Validation

**Format Validation**:
- Action files: Valid YAML frontmatter, Markdown body follows template
- Approval files: All required fields present, integrity_hash matches computed hash
- Logs: Valid JSON lines, all required fields present
- SQLite: Schema matches `init_idempotency_db.sql`, indexes exist

**Requirements Validation**:
- FR-001: Gmail watcher detects 95% of emails within 5 minutes (measure via timestamps)
- FR-020: 100% of tampered files rejected (test with modified approval files)
- FR-014a: Zero duplicate sends during retry scenarios (test with simulated API failures)
- FR-024: All watchers stay within 100MB limit during 24h soak test

**Safety Validation**:
- Zero unauthorized actions: All sensitive actions have `approval_status="approved"` in logs
- Zero credential exposure: No OAuth tokens, API keys, or secrets in git history or logs
- Zero data exfiltration: All data stays local (vault, SQLite, OS credential manager)

---

## 9. Architectural Decision Records (ADRs)

This plan includes **FIVE significant architectural decisions** that meet the ADR significance test:

1. **WhatsApp Business API (Webhook-Based) vs. Unofficial Automation** (Impact: Legal compliance, reliability; Alternatives: Playwright, third-party; Scope: All WhatsApp integrations)

2. **OS Credential Manager for OAuth Tokens** (Impact: Security, token management; Alternatives: Encrypted .env, cloud secrets; Scope: All external API authentication)

3. **File-Based Approval with SHA-256 Integrity Hashing** (Impact: Security, user experience; Alternatives: Web UI, CLI tool; Scope: All approval workflows)

4. **SQLite Idempotency Tracking with 7-Day Retention** (Impact: Data consistency, retry safety; Alternatives: In-memory, flat file; Scope: All external actions)

5. **Memory Budget with Graceful Degradation** (Impact: Reliability, resource management; Alternatives: Unlimited, Docker, dynamic scaling; Scope: All watcher processes)

📋 **Architectural decisions detected**: Five significant decisions documented above. These decisions have long-term consequences, multiple valid alternatives, and cross-cutting impact. Document reasoning and tradeoffs? Run `/sp.adr whatsapp-oauth-idempotency-memory-approval-architecture`

---

## Phase 0: Outline & Research

**Goal**: Resolve all "NEEDS CLARIFICATION" items from Technical Context (already resolved via spec clarifications) and research best practices for implementation.

### Research Tasks

1. **Gmail API OAuth2 Flow**:
   - Research: Google OAuth2 quickstart for server-side Python apps
   - Output: Step-by-step OAuth flow, token storage in OS credential manager
   - Rationale: Gmail API requires OAuth2; need to understand refresh token handling

2. **WhatsApp Business API Webhook Setup**:
   - Research: Meta's WhatsApp Business API documentation for webhook configuration
   - Output: Webhook registration steps, signature validation algorithm, test tools
   - Rationale: Webhook-based architecture requires understanding Meta's requirements

3. **OS Credential Manager Integration** (Windows Credential Manager, macOS Keychain):
   - Research: Python `keyring` library usage, fallback to encrypted file
   - Output: Code examples for storing/retrieving OAuth tokens
   - Rationale: Secure credential storage is critical for security

4. **SQLite Idempotency Patterns**:
   - Research: Best practices for idempotency tables, indexing strategies
   - Output: Schema design, query patterns, cleanup strategies
   - Rationale: Must prevent duplicate sends while maintaining performance

5. **SHA-256 Integrity Hashing**:
   - Research: Python `hashlib` usage, YAML field serialization for stable hashing
   - Output: Hash generation and validation code
   - Rationale: Tamper-proofing approval files requires cryptographic hashing

6. **Memory Monitoring in Python**:
   - Research: `psutil` library for cross-platform process memory tracking
   - Output: Code to monitor watcher memory usage every 60s
   - Rationale: Graceful degradation requires accurate memory monitoring

7. **LinkedIn API Post Publishing**:
   - Research: LinkedIn REST API for creating posts, OAuth scopes required
   - Output: API endpoint, request format, rate limits
   - Rationale: Need to understand LinkedIn API capabilities and constraints

**Output**: `specs/002-external-connectivity/research.md` with all findings documented

---

## Phase 1: Design & Contracts

**Prerequisites**: `research.md` complete

### Tasks

1. **Extract Entities and Generate `data-model.md`**:
   - Watcher: name, check_interval, last_run, processed_ids, status, memory_limit_mb, priority, current_memory_usage_mb
   - ActionFile: type, source, content, metadata, priority, status, created_timestamp, message_id
   - ApprovalRequest: action_type, parameters, reason, created_timestamp, expires_timestamp, status, integrity_hash
   - MCPServer: name, capabilities, endpoint, auth_config, rate_limits
   - AuditLog: timestamp, action_type, actor, target, parameters, approval_status, result, error_message
   - IdempotencyRecord: action_identifier, action_type, timestamp, expiry_timestamp, recipient, result_status
   - **Validation Rules**: message_id must be unique, integrity_hash must match computed hash, expires_timestamp = created_timestamp + 24h
   - **State Transitions**: ActionFile: pending → processing → done; ApprovalRequest: pending → approved/rejected/expired

2. **Generate API Contracts in `/contracts/`**:

   **`contracts/whatsapp-webhook.openapi.yaml`**:
   - `POST /webhooks/whatsapp`: WhatsApp Business API webhook endpoint
   - Input: JSON payload with messages array, metadata
   - Output: HTTP 200 acknowledgment
   - Security: `X-Hub-Signature-256` header validation

   **`contracts/gmail-mcp.json`**:
   - MCP tool definition for `send_email`
   - Input schema: to, subject, body, cc, bcc, attachments
   - Output schema: message_id, status, error

   **`contracts/linkedin-mcp.json`**:
   - MCP tool definition for `create_post`
   - Input schema: content, visibility, media
   - Output schema: post_id, url, status, error

3. **Generate `quickstart.md`**:
   - Section 1: Prerequisites (Python 3.13+, Node.js 24+, Gmail account, WhatsApp Business account, LinkedIn account)
   - Section 2: Gmail OAuth2 Setup (run `scripts/setup_gmail_oauth.py`, verify token in credential manager)
   - Section 3: WhatsApp Business API Setup (register webhook URL, configure app secret in .env)
   - Section 4: LinkedIn API Setup (create LinkedIn app, obtain OAuth credentials, add to .env)
   - Section 5: Vault Structure Setup (create /Needs_Action, /Pending_Approval, /Approved, /Rejected, /Logs folders)
   - Section 6: Start Watchers (via PM2 or manual Python execution)
   - Section 7: Test End-to-End (send test email, verify action file, approve, verify email sent)

4. **Update Agent Context** (`.claude/settings.local.json`):
   - Run `.specify/scripts/powershell/update-agent-context.ps1 -AgentType claude`
   - Add new technologies: FastAPI, uvicorn, keyring, cryptography, google-auth-oauthlib
   - Preserve existing Bronze Tier entries

**Output**: `data-model.md`, `contracts/`, `quickstart.md`, updated `.claude/settings.local.json`

---

## Stop and Report

This plan ends after Phase 1 design. `/sp.tasks` command will generate `tasks.md` for Phase 2 implementation.

**Summary**:
- **Branch**: `002-external-connectivity`
- **Plan**: `C:\Code\Hackathon-0\specs\002-external-connectivity\plan.md` (this file)
- **Artifacts to Generate**:
  - Phase 0: `research.md` (OAuth, webhooks, credential storage, idempotency, integrity hashing, memory monitoring, LinkedIn API)
  - Phase 1: `data-model.md`, `contracts/whatsapp-webhook.openapi.yaml`, `contracts/gmail-mcp.json`, `contracts/linkedin-mcp.json`, `quickstart.md`, updated `.claude/settings.local.json`

**Next Steps**:
1. Review this plan for completeness and alignment with spec
2. Run `/sp.tasks` to generate dependency-ordered tasks for implementation
3. Execute tasks in red-green-refactor cycles
4. Test end-to-end with sandbox accounts before production use
