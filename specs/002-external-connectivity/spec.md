# Feature Specification: External Connectivity (Silver Tier)

**Feature Branch**: `002-external-connectivity`
**Created**: 2026-01-22
**Status**: Draft
**Input**: User description: "Silver Tier: External Connectivity - Implement multiple watchers (Gmail, WhatsApp, LinkedIn), MCP servers for external actions, and human-in-the-loop approval workflow"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Email Monitoring and Action (Priority: P1)

The AI Employee detects important emails in Gmail, creates actionable tasks in the vault, and enables the user to approve draft responses before sending.

**Why this priority**: Email communication is fundamental to business operations. Without email monitoring, the AI Employee cannot detect or respond to critical client communications, making this the highest-value integration.

**Independent Test**: Can be fully tested by sending a test email to the monitored Gmail account with priority keywords (e.g., "urgent", "invoice"), verifying that a task file is created in the vault's Needs_Action folder, and confirming that draft responses require approval before sending.

**Acceptance Scenarios**:

1. **Given** a Gmail account with unread important emails, **When** the Gmail Watcher runs, **Then** action files are created in /Needs_Action with email metadata and content
2. **Given** an action file requiring email response, **When** Claude processes it, **Then** a draft response is created in /Pending_Approval requiring human review
3. **Given** an approved email draft, **When** the Email MCP executes, **Then** the email is sent and logged in the audit trail

---

### User Story 2 - WhatsApp Message Detection (Priority: P2)

The AI Employee monitors WhatsApp messages via WhatsApp Business API webhooks for messages containing business keywords and creates task files for processing.

**Why this priority**: WhatsApp is a critical communication channel for many businesses. Automated monitoring via official API enables rapid response to customer inquiries and business requests while ensuring compliance with WhatsApp's terms of service.

**Independent Test**: Can be fully tested by sending a WhatsApp message to the monitored Business API number containing a keyword like "invoice" or "pricing", verifying that the webhook handler creates a task file, and confirming the message content is captured accurately.

**Acceptance Scenarios**:

1. **Given** WhatsApp Business API is configured with webhook endpoint, **When** a message arrives containing a monitored keyword, **Then** an action file is created with sender, message content, and timestamp
2. **Given** multiple messages in rapid succession, **When** webhooks are received, **Then** only messages matching keywords are processed to avoid noise
3. **Given** a WhatsApp action file, **When** processed by Claude, **Then** appropriate response actions are drafted for approval

---

### User Story 3 - LinkedIn Post Automation (Priority: P3)

The AI Employee drafts LinkedIn posts for business promotion and schedules them after user approval.

**Why this priority**: Consistent social media presence drives business growth. Automated post drafting reduces the cognitive load of content creation while maintaining quality control through approval.

**Independent Test**: Can be fully tested by creating a business goal or marketing calendar entry, verifying that draft LinkedIn posts are generated, reviewing the draft content, approving it, and confirming successful posting.

**Acceptance Scenarios**:

1. **Given** a marketing calendar entry, **When** a scheduled post time arrives, **Then** a draft LinkedIn post is created in /Pending_Approval
2. **Given** an approved LinkedIn post draft, **When** the LinkedIn MCP executes, **Then** the post is published and logged
3. **Given** posting frequency limits (e.g., max 5 posts per week), **When** the limit is reached, **Then** further posts are queued for the next available slot

---

### User Story 4 - Human-in-the-Loop Approval Workflow (Priority: P1)

All sensitive external actions require explicit human approval before execution.

**Why this priority**: Safety and control are paramount when automating business communications. This prevents accidental sends, financial errors, and reputational damage.

**Independent Test**: Can be fully tested by triggering any external action (email send, payment, social post), verifying it creates an approval file in /Pending_Approval, testing approval by moving the file to /Approved, testing rejection by moving to /Rejected, and confirming only approved actions execute.

**Acceptance Scenarios**:

1. **Given** Claude identifies a sensitive action is needed, **When** it creates the action plan, **Then** an approval request file is written to /Pending_Approval instead of executing immediately
2. **Given** an approval request file, **When** the user moves it to /Approved, **Then** the orchestrator detects it and executes the corresponding MCP action
3. **Given** an approval request file, **When** the user moves it to /Rejected, **Then** the action is logged as rejected and never executed
4. **Given** an approval request older than expiration time, **When** the orchestrator checks, **Then** it is automatically moved to /Expired and never executed

---

### User Story 5 - Scheduled Automation Tasks (Priority: P2)

The AI Employee runs scheduled tasks like daily briefings and weekly audits automatically.

**Why this priority**: Scheduled automation enables proactive business management. Regular briefings provide visibility into operations without manual effort.

**Independent Test**: Can be fully tested by configuring a scheduled task (e.g., daily briefing at 8am), waiting for the scheduled time (or manually triggering), and verifying the briefing is generated in the vault with correct data.

**Acceptance Scenarios**:

1. **Given** a scheduled task configured via cron/Task Scheduler, **When** the scheduled time arrives, **Then** Claude is invoked with the correct task parameters
2. **Given** a daily briefing task, **When** executed, **Then** a briefing file is created summarizing pending tasks, recent completions, and key metrics
3. **Given** a scheduled task fails, **When** the error is logged, **Then** the user is notified and the task is retried according to retry policy

---

## Clarifications

### Session 2026-01-23

- Q: Given WhatsApp's prohibition on automated access to WhatsApp Web, which approach should the Silver Tier specification adopt for WhatsApp message monitoring to balance functionality, legal compliance, and implementation safety? → A: Require WhatsApp Business API with official credentials, eliminating Playwright and using webhook-based message detection instead of polling (recommended for production)
- Q: Where and how should Gmail OAuth2 access tokens and refresh tokens be securely stored for the long-running Gmail Watcher process to prevent credential exposure while enabling automatic token refresh? → A: Store in OS credential manager (Windows Credential Manager / macOS Keychain) with automatic refresh logic and fallback to encrypted file if OS credential manager unavailable
- Q: How should the system implement approval file integrity validation (FR-020) to prevent modified approval files from executing with altered parameters while keeping the workflow simple and transparent? → A: Generate SHA-256 hash of critical fields (action_type, parameters, timestamp) when creating approval file, embed hash in YAML frontmatter, verify on read before execution
- Q: What specific memory budgets and resource management policies should be defined for running multiple watchers (Gmail, WhatsApp, approval folder monitors) simultaneously on Windows to prevent system slowdown while ensuring reliable operation? → A: Set maximum 100MB RAM per watcher process, 500MB total budget for all watchers; implement monitoring with alerts at 80% threshold; graceful degradation pauses lowest-priority watcher (LinkedIn → WhatsApp → Gmail order)
- Q: How should the system implement idempotency checks to prevent duplicate email sends and social media posts when retries occur due to transient failures or watcher restarts? → A: Store Message-ID header (emails) / content hash (WhatsApp) in SQLite database with timestamp index; 7-day deduplication window with automatic cleanup; query before sending

---

### Edge Cases

- What happens when Gmail API rate limits are reached?
  - The watcher should implement exponential backoff and queue emails for later processing
- What happens when Gmail OAuth2 token expires during watcher operation?
  - The system automatically refreshes the token using the stored refresh token from OS credential manager; if refresh fails after 3 retries, the watcher pauses and alerts the user
- What happens when WhatsApp Business API webhook endpoint becomes unreachable?
  - The API will retry webhook delivery according to its retry policy; the system should implement a health check endpoint and alert the user if webhooks fail consistently
- What happens when an approval request file is modified instead of moved?
  - The system validates the SHA-256 integrity hash embedded in the file's YAML frontmatter against critical fields; if the hash doesn't match, the file is rejected, moved to /Rejected with "_TAMPERED" suffix, and an alert is logged
- What happens when an approval file is missing the integrity_hash field?
  - The file is treated as invalid/corrupted, rejected, and moved to /Rejected with "_INVALID" suffix; user is notified to regenerate the approval request
- What happens when network connectivity is lost during an MCP action?
  - The action is retried with exponential backoff (max 5 retries); before each retry, the system queries the SQLite idempotency database using Message-ID (emails) or content hash (WhatsApp/LinkedIn) to check if the action already succeeded within the 7-day window; if found, skip retry and mark as completed
- What happens when Claude misinterprets an email and drafts an inappropriate response?
  - The human approval workflow prevents sending; user feedback should improve future interpretations
- What happens when multiple approval requests accumulate?
  - The dashboard should display approval queue counts with priority indicators
- What happens when a watcher process exceeds its 100MB memory limit?
  - The resource monitor detects the violation, logs a warning, and if the watcher continues to exceed the limit, it is paused and the user is alerted with specific memory usage details
- What happens when total watcher memory usage exceeds the 500MB budget?
  - Graceful degradation activates: LinkedIn watcher pauses first, then WhatsApp if still over budget, preserving Gmail (highest priority); user receives alert with current usage breakdown
- What happens when all watchers are paused due to resource constraints?
  - System enters degraded mode, alerts user with critical notification, and provides guidance to either increase resources, reduce watcher check intervals, or disable non-essential watchers
- What happens when the SQLite idempotency database becomes corrupted or unavailable?
  - The system attempts to recreate the database from backup if available; if recreation fails, the system operates in cautious mode where external actions are paused and user is alerted to manually verify no duplicates before resuming
- What happens when an action is retried after the 7-day deduplication window expires?
  - The system treats it as a new action since the original idempotency record has been cleaned up; this is acceptable as 7-day separation indicates legitimate re-send intent rather than accidental duplicate

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST implement a Gmail Watcher that polls for unread important emails every 2 minutes
- **FR-002**: System MUST implement a WhatsApp Webhook Handler using WhatsApp Business API that receives messages in real-time and filters by configured keywords
- **FR-002a**: System MUST implement a publicly accessible HTTPS webhook endpoint for WhatsApp Business API callbacks with signature verification for security
- **FR-003**: System MUST create action files in /Vault/Needs_Action folder with structured metadata (type, sender, subject/content, priority, timestamp)
- **FR-004**: System MUST implement an Email MCP server that can send emails via Gmail API
- **FR-005**: System MUST implement a LinkedIn MCP server that can create and publish posts
- **FR-006**: System MUST implement a human-in-the-loop approval workflow using file-based signaling
- **FR-007**: System MUST create approval request files in /Vault/Pending_Approval with action details, parameters, and expiration time
- **FR-008**: System MUST monitor /Approved folder and execute corresponding MCP actions when files are moved there
- **FR-009**: System MUST monitor /Rejected folder and log rejections without executing actions
- **FR-010**: System MUST automatically expire approval requests older than 24 hours
- **FR-011**: System MUST implement scheduled task execution via cron (Mac/Linux) or Task Scheduler (Windows)
- **FR-012**: System MUST log all external actions to /Vault/Logs with timestamp, action type, parameters, approval status, and result
- **FR-013**: System MUST implement retry logic with exponential backoff for transient API failures (initial delay 1s, max delay 60s, max 5 retries)
- **FR-014**: System MUST persist processed message IDs in SQLite database to prevent duplicate processing: use Message-ID header for emails, SHA-256 content hash for WhatsApp messages, maintain 7-day retention window with automatic cleanup
- **FR-014a**: System MUST implement idempotency checks before executing external actions (email send, WhatsApp message, LinkedIn post) by querying SQLite sent-actions table with 7-day deduplication window
- **FR-015**: System MUST implement audit logging for all watcher detections and MCP executions
- **FR-016**: System MUST convert all AI functionality to Claude Agent Skills for reusability
- **FR-017**: System MUST update Dashboard.md with recent activity summaries after each action
- **FR-018**: System MUST implement rate limiting to prevent API abuse (max 50 emails/day, max 10 LinkedIn posts/day)
- **FR-019**: System MUST support dry-run mode for testing without executing real external actions
- **FR-020**: System MUST validate approval file integrity by generating SHA-256 hash of critical fields (action_type, parameters, created_timestamp) when creating approval file, embedding hash in YAML frontmatter, and verifying hash before execution; reject files with mismatched hashes
- **FR-021**: System MUST store OAuth2 tokens (Gmail, LinkedIn) in OS credential manager (Windows Credential Manager / macOS Keychain) with fallback to AES-256 encrypted file using machine-specific key
- **FR-022**: System MUST implement automatic OAuth2 token refresh when tokens expire, with exponential backoff on refresh failures
- **FR-023**: System MUST alert user and pause watcher if OAuth2 token refresh fails after 3 retry attempts
- **FR-024**: System MUST enforce maximum 100MB RAM limit per individual watcher process and 500MB total budget for all watchers combined
- **FR-025**: System MUST monitor memory usage of all watcher processes every 60 seconds and alert user when total usage exceeds 400MB (80% of budget)
- **FR-026**: System MUST implement graceful degradation by pausing watchers in priority order (LinkedIn first, then WhatsApp, then Gmail) when total memory budget is exceeded
- **FR-027**: System MUST automatically resume paused watchers when memory usage drops below 350MB (70% of budget)

### Key Entities

- **Watcher**: Background process that monitors external sources (Gmail polls, WhatsApp webhooks, LinkedIn polls) and creates action files
  - Attributes: name, check_interval (null for webhook-based), last_run, processed_ids, status (running/stopped/error/paused), memory_limit_mb (100MB per watcher), priority (Gmail=1/high, WhatsApp=2/medium, LinkedIn=3/low), current_memory_usage_mb
  - Relationships: Creates ActionFile entities

- **ActionFile**: Markdown file representing a detected event requiring processing
  - Attributes: type (email/whatsapp/file_drop), source, content, metadata, priority, status, created_timestamp
  - Relationships: May generate ApprovalRequest entities

- **ApprovalRequest**: File requesting human approval before executing an action
  - Attributes: action_type, parameters, reason, created_timestamp, expires_timestamp, status (pending/approved/rejected/expired), integrity_hash (SHA-256 hash of action_type + parameters + created_timestamp for tamper detection)
  - Relationships: References original ActionFile, triggers MCP execution when approved

- **MCPServer**: Integration server enabling Claude to perform external actions
  - Attributes: name, capabilities, endpoint, auth_config (references OS credential manager entries for OAuth tokens), rate_limits
  - Relationships: Executes actions from approved ApprovalRequest entities

- **AuditLog**: Record of all system actions for compliance and debugging
  - Attributes: timestamp, action_type, actor, target, parameters, approval_status, result, error_message
  - Relationships: References ActionFile and ApprovalRequest IDs

- **IdempotencyRecord**: SQLite database record for preventing duplicate external actions
  - Attributes: action_identifier (Message-ID header for emails, SHA-256 content hash for WhatsApp/LinkedIn), action_type (email_send/whatsapp_send/linkedin_post), timestamp, expiry_timestamp (timestamp + 7 days), recipient, result_status
  - Relationships: Referenced by MCP servers before executing actions; automatically cleaned up after 7-day retention window

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Gmail Watcher successfully detects and creates action files for 95% of important emails within 5 minutes of arrival
- **SC-002**: WhatsApp Webhook Handler successfully receives and processes messages containing monitored keywords with 99% reliability (webhook delivery success rate)
- **SC-003**: Users can review and approve/reject external actions in under 1 minute from the Obsidian dashboard
- **SC-004**: Zero unauthorized external actions occur (100% of sensitive actions go through approval workflow)
- **SC-005**: Email responses are sent within 10 minutes of user approval
- **SC-006**: LinkedIn posts are published within 5 minutes of user approval
- **SC-007**: System maintains 99% uptime for watcher processes over a 7-day period
- **SC-008**: All external actions are logged with complete audit trails for compliance review
- **SC-009**: Users can complete daily briefing review in under 3 minutes
- **SC-010**: System handles API rate limits gracefully with zero data loss (all events are eventually processed)
- **SC-011**: Approval workflow prevents 100% of potentially harmful actions from executing without review
- **SC-012**: Dry-run mode allows safe testing with zero risk of accidental external actions
- **SC-018**: Integrity validation detects and rejects 100% of tampered approval files, preventing modified actions from executing

### Quality Metrics

- **SC-013**: User satisfaction rating of 4/5 or higher for approval workflow usability
- **SC-014**: Reduce manual email monitoring time by 70%
- **SC-015**: Reduce time spent on social media posting by 80%
- **SC-016**: Zero security incidents related to credential exposure or unauthorized access
- **SC-017**: OAuth2 tokens successfully refresh automatically with 99% success rate, preventing watcher downtime due to token expiration
- **SC-019**: All watcher processes stay within 100MB per-process memory limit during normal operation (95% of runtime)
- **SC-020**: Total watcher memory usage stays within 500MB budget during normal operation (98% of runtime)
- **SC-021**: Graceful degradation activates successfully when memory budget exceeded, with automatic recovery when usage drops below 70%
- **SC-022**: Idempotency checks prevent 100% of duplicate external actions (emails, posts) during retry scenarios within 7-day window
- **SC-023**: SQLite idempotency database maintains accurate records with automatic cleanup of entries older than 7 days, keeping database size under 10MB

## Assumptions

- Gmail API credentials and OAuth2 tokens are available or can be generated following Google's quickstart guide; tokens will be stored securely in OS credential manager (Windows Credential Manager / macOS Keychain) with automatic refresh capability
- WhatsApp Business API access with approved business account and webhook endpoint capability is available or will be obtained for message monitoring
- LinkedIn API access is available or will be obtained for automated posting
- The Obsidian vault structure from Bronze Tier exists (/Needs_Action, /Pending_Approval, /Approved, /Rejected, /Done, /Logs folders)
- Python 3.13+ is installed for watcher scripts with SQLite3 module (included in standard library)
- Node.js 24+ LTS is installed for MCP servers
- The user has appropriate permissions and credentials for all external services being integrated
- Scheduled task configuration (cron or Task Scheduler) is available on the host system
- The system has stable internet connectivity for API calls
- Process management tools (PM2 or equivalent) are available for keeping watchers running continuously
- The host system has at least 4GB RAM with 1GB available for AI Employee processes (500MB for watchers, 500MB for orchestrator and MCP servers)
