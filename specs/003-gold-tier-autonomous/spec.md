# Feature Specification: Gold Tier - Autonomous Employee

**Feature Branch**: `003-gold-tier-autonomous`
**Created**: 2026-02-05
**Status**: Draft
**Tier**: Gold (Autonomous Employee)
**Input**: User description: "Gold Tier: Autonomous Employee - Full cross-domain integration (Personal + Business), Odoo accounting integration, social media expansion (Facebook, Instagram, Twitter/X), weekly business audits with CEO briefings, Ralph Wiggum autonomous loop, error recovery, graceful degradation, and comprehensive audit logging"

## Purpose

The Gold Tier transforms the AI Employee from a "Functional Assistant" (Silver) into an "Autonomous Employee" capable of managing complete business operations with minimal human intervention. This tier introduces:

1. **Full Cross-Domain Integration** - Unified management of personal and business affairs
2. **Odoo Community ERP Integration** - Self-hosted accounting system connected via MCP server using JSON-RPC APIs
3. **Extended Social Media Coverage** - Facebook, Instagram, and Twitter/X integrations for comprehensive marketing automation
4. **Proactive Business Intelligence** - Weekly automated audits with CEO-style briefings
5. **Autonomous Multi-Step Execution** - Ralph Wiggum loop pattern for completing complex tasks without intervention
6. **Enterprise-Grade Reliability** - Comprehensive error recovery, graceful degradation, and audit logging

This builds upon the fully-implemented Bronze and Silver tiers without modifying their core logic.

## Clarifications

### Session 2026-02-05

- Q: What connection timeout and retry behavior should be used for Odoo before falling back to local queuing? → A: 30-second connection timeout, queue after 3 failed retries
- Q: How should the system handle OAuth token expiration for Meta and Twitter APIs? → A: Proactive refresh - check token expiry before each API call, refresh if <1 hour remaining

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Odoo Accounting Integration (Priority: P1)

As a business owner, I want the AI Employee to manage my accounting in Odoo so that invoices, payments, and financial records are automatically synchronized with my business operations.

**Why this priority**: Financial management is the backbone of business operations. Without accounting integration, the AI Employee cannot provide meaningful business intelligence or CEO briefings. Odoo Community is specified as the ERP system per the Gold Tier requirements.

**Independent Test**: Can be fully tested by creating a customer invoice in the vault, triggering the Odoo MCP server to draft the invoice, verifying human approval workflow, executing the posting, and confirming the invoice appears correctly in Odoo with proper accounting entries.

**Acceptance Scenarios**:

1. **Given** Odoo Community is running locally with the Accounting module enabled, **When** a client payment is recorded in the vault, **Then** the Odoo MCP creates a draft payment entry pending human approval
2. **Given** an approved invoice draft exists, **When** the approval workflow completes, **Then** the invoice is posted to Odoo with correct partner, amounts, and account codes
3. **Given** a CEO briefing is requested, **When** the audit process runs, **Then** it retrieves accurate revenue, expenses, and outstanding receivables from Odoo via JSON-RPC API
4. **Given** an Odoo API failure occurs, **When** the MCP encounters the error, **Then** it logs the failure, retries with exponential backoff, and queues the action for later if retries exhaust

---

### User Story 2 - Weekly Business Audit and CEO Briefing (Priority: P1)

As a business owner, I want the AI Employee to automatically audit my business weekly and produce a Monday Morning CEO Briefing so that I can start each week with clear visibility into revenue, bottlenecks, and proactive suggestions.

**Why this priority**: The CEO Briefing feature is explicitly called out in the GOAL document as the "standout idea" that transforms the AI from a chatbot into a proactive business partner. It synthesizes data from multiple sources (tasks, accounting, goals) into actionable intelligence.

**Independent Test**: Can be fully tested by configuring the weekly audit schedule, running the audit process manually or waiting for scheduled execution, and verifying the briefing file contains accurate revenue figures, completed tasks, bottlenecks, and actionable suggestions.

**Acceptance Scenarios**:

1. **Given** Sunday night scheduled task is configured, **When** the scheduled time arrives, **Then** the autonomous audit process begins without human intervention
2. **Given** the audit process has access to Business_Goals.md and Odoo data, **When** it analyzes the week's performance, **Then** the CEO Briefing includes: weekly revenue, MTD progress vs target, completed tasks, bottlenecks (tasks exceeding expected duration), and proactive suggestions
3. **Given** unused subscriptions are detected (no login > 30 days), **When** the briefing is generated, **Then** it includes a cost optimization suggestion with specific subscription and monthly cost
4. **Given** upcoming deadlines within 14 days, **When** the briefing is generated, **Then** it includes a list of projects/tasks approaching deadline with days remaining

---

### User Story 3 - Facebook and Instagram Integration (Priority: P2)

As a business owner, I want the AI Employee to post updates to Facebook and Instagram so that my business maintains consistent social media presence across all major platforms.

**Why this priority**: Per GOAL requirements, Gold Tier must integrate Facebook and Instagram. These platforms combined with LinkedIn (Silver Tier) provide comprehensive B2B and B2C marketing coverage.

**Independent Test**: Can be fully tested by creating a marketing content file, triggering draft post creation, approving the post through the HITL workflow, and verifying the post appears on both Facebook Page and Instagram Business account with correct content and any media attachments.

**Acceptance Scenarios**:

1. **Given** a Facebook Page and Instagram Business account are connected via Meta Business Suite API, **When** a marketing calendar entry triggers, **Then** draft posts are created for both platforms in /Pending_Approval
2. **Given** an approved Facebook post, **When** the Facebook MCP executes, **Then** the post is published to the configured Page and logged in the audit trail
3. **Given** an approved Instagram post with an image, **When** the Instagram MCP executes, **Then** the post is published with the image and caption and logged
4. **Given** posting frequency limits (max 3 posts/day per platform), **When** the limit is reached, **Then** additional posts are queued for the next available slot

---

### User Story 4 - Twitter/X Integration (Priority: P2)

As a business owner, I want the AI Employee to post updates to Twitter/X so that I can engage with the real-time news cycle and professional network on this platform.

**Why this priority**: Per GOAL requirements, Gold Tier must integrate Twitter/X. This platform serves different engagement patterns than Facebook/Instagram/LinkedIn and is important for thought leadership and industry engagement.

**Independent Test**: Can be fully tested by creating tweet content, triggering draft creation, approving through HITL workflow, and verifying the tweet appears on the configured Twitter/X account with correct text (respecting character limits).

**Acceptance Scenarios**:

1. **Given** a Twitter/X Developer account with API access is configured, **When** a marketing calendar entry triggers, **Then** a draft tweet is created in /Pending_Approval respecting the 280-character limit
2. **Given** an approved tweet draft, **When** the Twitter MCP executes, **Then** the tweet is posted and logged in the audit trail
3. **Given** content exceeds 280 characters, **When** the draft is created, **Then** it is automatically truncated with ellipsis or split into a thread (user configurable)
4. **Given** rate limits are approached (per Twitter API limits), **When** posting is attempted, **Then** the system queues the post and retries during the next available window

---

### User Story 5 - Ralph Wiggum Autonomous Loop (Priority: P1)

As a user, I want the AI Employee to autonomously complete multi-step tasks without my intervention until the task is done so that complex workflows execute to completion even when I'm away.

**Why this priority**: The Ralph Wiggum loop is the core mechanism that enables "autonomous employee" behavior. Without it, the system remains reactive. This is explicitly required for Gold Tier and referenced in Section 2D of the GOAL document.

**Independent Test**: Can be fully tested by starting a multi-step task (e.g., "Process all files in /Needs_Action and update Dashboard"), observing the loop continue through multiple reasoning iterations, and verifying completion when the task file moves to /Done.

**Acceptance Scenarios**:

1. **Given** a task is started with `/ralph-loop` command, **When** Claude attempts to exit, **Then** the Stop hook intercepts and re-injects the prompt with context
2. **Given** the task file has moved to /Done, **When** the Stop hook checks completion, **Then** Claude is allowed to exit (task complete)
3. **Given** a max iteration limit is configured (e.g., 10), **When** iterations exceed the limit, **Then** the loop terminates with a summary of progress and remaining work
4. **Given** an error occurs during a loop iteration, **When** the error is non-fatal, **Then** the loop logs the error and continues with the next step
5. **Given** the promise-based completion strategy, **When** Claude outputs `<promise>TASK_COMPLETE</promise>`, **Then** the Stop hook allows exit

---

### User Story 6 - Error Recovery and Graceful Degradation (Priority: P2)

As a user, I want the AI Employee to handle errors gracefully so that temporary failures don't cause data loss or require manual intervention.

**Why this priority**: Enterprise-grade reliability is essential for an "autonomous employee" that operates without constant supervision. This builds on Silver Tier's error handling but adds comprehensive recovery strategies per GOAL Section 7.

**Independent Test**: Can be fully tested by simulating various failure modes (API timeouts, credential expiration, disk full), observing retry behavior, graceful degradation activation, and recovery when conditions improve.

**Acceptance Scenarios**:

1. **Given** a transient API failure (network timeout, rate limit), **When** the action fails, **Then** exponential backoff retry is applied (initial 1s, max 60s, max 5 retries)
2. **Given** an authentication failure (expired token, revoked access), **When** detected, **Then** the affected watcher pauses, alerts the user, and other watchers continue operating
3. **Given** a data corruption (malformed file, missing field), **When** detected, **Then** the file is moved to /Quarantine with an alert, and processing continues with other files
4. **Given** the Orchestrator crashes, **When** the Watchdog detects the crash, **Then** it auto-restarts the Orchestrator and logs the event
5. **Given** Gmail API is unavailable, **When** outgoing emails fail, **Then** they are queued locally and processed when the API recovers (graceful degradation)

---

### User Story 7 - Comprehensive Audit Logging (Priority: P2)

As a business owner, I want every action the AI Employee takes to be logged in detail so that I can review decisions, troubleshoot issues, and maintain compliance.

**Why this priority**: Audit logging is explicitly required for Gold Tier and is essential for accountability when operating autonomously. The GOAL document specifies the required log format and 90-day retention.

**Independent Test**: Can be fully tested by triggering various actions (email send, social post, Odoo entry), verifying each creates a log entry with all required fields, and confirming logs are searchable and retained for 90 days.

**Acceptance Scenarios**:

1. **Given** any external action is executed, **When** the action completes, **Then** a JSON log entry is created with: timestamp, action_type, actor, target, parameters, approval_status, approved_by, result
2. **Given** logs accumulate over 90 days, **When** the retention policy runs, **Then** logs older than 90 days are archived/deleted per configuration
3. **Given** a compliance review request, **When** logs are queried, **Then** they can be filtered by date range, action type, target, and result status
4. **Given** an action fails, **When** logged, **Then** the log entry includes error_message and stack trace where applicable

---

### Edge Cases

- What happens when Odoo is unreachable during CEO briefing generation?
  - The system generates a partial briefing with available data (vault tasks, goals) and clearly notes "Accounting data unavailable - Odoo connection failed" with retry scheduled
- What happens when multiple Ralph Wiggum loops are started simultaneously?
  - Only one loop can be active at a time; subsequent starts are rejected with "Loop already active" message
- What happens when a CEO briefing has no data (empty week)?
  - The briefing is still generated with "No activity recorded this week" sections and a prompt to review watcher health
- What happens when social media APIs change their authentication requirements?
  - The system detects auth failures, alerts the user, pauses the affected MCP, and continues with other platforms
- What happens when Odoo database is corrupted or needs migration?
  - The Odoo MCP fails gracefully, queues operations locally, and alerts the user to check Odoo health; no data loss occurs
- What happens when the Ralph Wiggum loop gets stuck in an infinite reasoning cycle?
  - The max_iterations guard terminates the loop, generates a summary of where it got stuck, and alerts the user
- What happens when audit logs consume excessive disk space?
  - The system monitors log directory size and alerts when approaching configured threshold (default 1GB); automatic compression of older logs is applied

## Requirements *(mandatory)*

### Functional Requirements

#### Odoo Integration

- **FR-001**: System MUST integrate with Odoo Community Edition (self-hosted, local) via JSON-RPC APIs (Odoo 19+)
- **FR-002**: System MUST implement an Odoo MCP server exposing accounting capabilities: create draft invoices, create draft payments, retrieve financial summaries
- **FR-003**: System MUST ensure all Odoo accounting actions create drafts requiring human approval before posting
- **FR-004**: System MUST retrieve from Odoo: total revenue (period), outstanding receivables, recent transactions, and account balances for CEO briefings
- **FR-005**: System MUST handle Odoo connection failures with 30-second connection timeout and retry logic (max 3 retries with exponential backoff); after retries exhaust, operations MUST be queued locally for later processing

#### Social Media Integration

- **FR-006**: System MUST implement a Facebook MCP server for posting to Facebook Pages via Meta Business Suite API
- **FR-007**: System MUST implement an Instagram MCP server for posting to Instagram Business accounts via Meta Business Suite API
- **FR-008**: System MUST implement a Twitter/X MCP server for posting tweets via Twitter API v2
- **FR-009**: System MUST enforce platform-specific content limits (Twitter 280 chars, Instagram caption 2200 chars)
- **FR-010**: System MUST support image/media attachments for Facebook and Instagram posts
- **FR-011**: System MUST implement rate limiting per platform (Facebook: 5 posts/day, Instagram: 3 posts/day, Twitter: 50 tweets/day)
- **FR-012**: System MUST generate social media activity summaries for CEO briefings
- **FR-012a**: System MUST implement proactive OAuth token refresh for Meta and Twitter APIs: check token expiry before each API call and refresh if less than 1 hour remaining

#### Weekly Business Audit and CEO Briefing

- **FR-013**: System MUST execute automated business audit via scheduled task (configurable, default Sunday 11 PM)
- **FR-014**: System MUST generate Monday Morning CEO Briefing document in /Vault/Briefings/ folder
- **FR-015**: CEO Briefing MUST include: Executive Summary, Revenue (weekly/MTD/vs target), Completed Tasks list, Bottlenecks (tasks exceeding expected duration), Proactive Suggestions (cost optimization, upcoming deadlines)
- **FR-016**: System MUST analyze transactions against subscription patterns to identify unused services
- **FR-017**: System MUST compare task completion times against estimates to identify bottlenecks
- **FR-018**: System MUST reference Business_Goals.md for targets and metrics

#### Ralph Wiggum Autonomous Loop

- **FR-019**: System MUST implement Stop hook that intercepts Claude exit attempts
- **FR-020**: System MUST support two completion strategies: promise-based (`<promise>TASK_COMPLETE</promise>`) and file-movement-based (task file in /Done)
- **FR-021**: System MUST re-inject the original prompt with previous context when blocking exit
- **FR-022**: System MUST enforce configurable max_iterations limit (default 10)
- **FR-023**: System MUST log each loop iteration with summary of actions taken
- **FR-024**: System MUST generate completion summary when loop ends (success or max iterations)

#### Error Recovery and Graceful Degradation

- **FR-025**: System MUST categorize errors: Transient (retry), Authentication (pause + alert), Logic (human review), Data (quarantine + alert), System (auto-restart)
- **FR-026**: System MUST implement exponential backoff retry: initial 1s, max 60s, max 5 retries for transient errors
- **FR-027**: System MUST implement Watchdog process that monitors critical processes (Orchestrator, watchers) and auto-restarts on crash
- **FR-028**: System MUST queue failed actions locally when external services are unavailable
- **FR-029**: System MUST automatically process queued actions when services recover
- **FR-030**: System MUST implement /Quarantine folder for corrupted/invalid files with alerting

#### Audit Logging

- **FR-031**: System MUST log all actions in JSON format to /Vault/Logs/YYYY-MM-DD.json
- **FR-032**: Log entries MUST include: timestamp, action_type, actor, target, parameters, approval_status, approved_by, result, error_message (if applicable)
- **FR-033**: System MUST retain logs for minimum 90 days
- **FR-034**: System MUST support log queries by date range, action type, target, and result status
- **FR-035**: System MUST compress logs older than 30 days to conserve space
- **FR-036**: System MUST alert when log directory exceeds 80% of configured size limit (default 1GB)

#### Documentation

- **FR-037**: System MUST include comprehensive architecture documentation
- **FR-038**: System MUST document lessons learned and configuration guidance
- **FR-039**: All AI functionality MUST be implemented as Claude Agent Skills per GOAL requirements

### Key Entities

- **OdooConnection**: Configuration for connecting to self-hosted Odoo instance
  - Attributes: host, port, database, username, api_key_reference (OS credential manager), version, status
  - Relationships: Used by Odoo MCP server for all operations

- **Invoice**: Financial document representing goods/services provided to a customer
  - Attributes: partner_id, invoice_lines, amount_total, state (draft/posted/paid), odoo_id, vault_reference
  - Relationships: Created in Odoo via MCP, linked to vault action files

- **Payment**: Financial transaction recording money received or sent
  - Attributes: partner_id, amount, payment_type, payment_method, state (draft/posted), odoo_id, vault_reference
  - Relationships: Created in Odoo via MCP, linked to vault action files

- **SocialMediaPost**: Content to be published on social platforms
  - Attributes: platform (facebook/instagram/twitter), content_text, media_attachments, scheduled_time, status (draft/approved/posted), post_id, engagement_metrics
  - Relationships: Created from marketing calendar, requires approval, executed by platform MCP

- **CEOBriefing**: Weekly executive summary document
  - Attributes: period_start, period_end, revenue_data, completed_tasks, bottlenecks, suggestions, generated_timestamp
  - Relationships: Aggregates data from Odoo, vault tasks, Business_Goals.md

- **RalphLoop**: Autonomous execution context for multi-step tasks
  - Attributes: task_prompt, completion_strategy (promise/file), max_iterations, current_iteration, status (running/complete/max_reached), start_time, context_history
  - Relationships: Controls Claude execution lifecycle

- **AuditLogEntry**: Individual action record for compliance
  - Attributes: timestamp, action_type, actor, target, parameters, approval_status, approved_by, result, error_message
  - Relationships: References action files, approval requests, and MCP executions

- **QuarantinedFile**: File moved due to validation/processing errors
  - Attributes: original_path, quarantine_path, error_type, error_message, quarantine_timestamp, resolution_status
  - Relationships: Created when file processing fails, requires human review

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Odoo MCP successfully creates draft invoices and payments with 99% accuracy (matching vault data)
- **SC-002**: CEO Briefings are generated automatically every Monday by 7 AM with all required sections populated
- **SC-003**: CEO Briefing revenue figures match Odoo data within 1% accuracy
- **SC-004**: Social media posts (Facebook, Instagram, Twitter) are published within 5 minutes of approval
- **SC-005**: Ralph Wiggum loop completes multi-step tasks (5+ steps) without human intervention 95% of the time
- **SC-006**: System recovers from transient failures within 5 minutes (successful retry or graceful degradation)
- **SC-007**: Zero unauthorized external actions occur (100% of Odoo postings and social posts go through approval)
- **SC-008**: Audit logs capture 100% of external actions with all required fields
- **SC-009**: Log queries return results within 5 seconds for 90-day ranges
- **SC-010**: Watchdog restarts crashed processes within 60 seconds
- **SC-011**: System maintains 98% uptime over 30-day periods (excluding scheduled maintenance)
- **SC-012**: Users can complete weekly CEO Briefing review in under 5 minutes
- **SC-013**: Social media engagement visibility (posts show engagement metrics within 24 hours in dashboard)
- **SC-014**: Error recovery prevents data loss in 100% of transient failure scenarios

### Quality Metrics

- **SC-015**: Documentation completeness: architecture diagram, setup guide, troubleshooting FAQ all present
- **SC-016**: All AI functionality packaged as reusable Agent Skills
- **SC-017**: Code coverage of critical paths (MCP actions, approval workflow, Ralph Wiggum loop) at 80%+
- **SC-018**: No security incidents related to credential exposure or unauthorized Odoo/social media access
- **SC-019**: Graceful degradation activates correctly, maintaining partial functionality when components fail

## Assumptions

- Odoo Community Edition (version 19+) is installed and running locally or on accessible infrastructure
- Odoo has the Accounting module installed and configured with a chart of accounts
- Meta Business Suite (Facebook/Instagram) API access is available with appropriate business account permissions
- Twitter API v2 access (Developer account with Elevated access) is available for posting
- Silver Tier is fully implemented and operational (Gmail watcher, LinkedIn MCP, approval workflow, scheduling)
- Bronze Tier file watcher remains operational as the base perception layer
- The system has sufficient resources: 16GB RAM recommended, 2GB minimum available for Gold Tier components
- Stable internet connectivity for API calls to Odoo (if remote), Meta, and Twitter
- User has familiarity with Odoo Community administration for initial setup
- Claude Code Stop hooks are supported in the runtime environment

## Constraints

- MUST NOT modify Bronze or Silver Tier core logic or stability guarantees
- MUST build as an additive layer on top of existing infrastructure
- MUST use Odoo's official JSON-RPC API (no direct database access)
- MUST comply with each social platform's Terms of Service and API usage policies
- MUST maintain human-in-the-loop for all financial postings (no auto-posting invoices/payments)
- MUST use existing approval workflow infrastructure from Silver Tier
- MUST follow existing security patterns (credential storage, dry-run mode, audit logging)
- Cross-platform compatibility: Windows, macOS, Linux

## Dependencies

- Bronze Tier: Local File Watcher Service (for file-based task detection)
- Silver Tier: Gmail Watcher, LinkedIn MCP, Approval Workflow, Scheduling, Audit Infrastructure
- Odoo Community Edition 19+ with Accounting module
- Meta Business Suite API (Graph API v18+)
- Twitter API v2 with Elevated access
- Python 3.13+ with required libraries (xmlrpc.client for Odoo, requests-oauthlib for social APIs)
- Node.js 24+ LTS for MCP servers
- PM2 or equivalent process manager for Watchdog functionality
