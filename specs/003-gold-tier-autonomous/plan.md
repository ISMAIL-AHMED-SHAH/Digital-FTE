# Implementation Plan: Gold Tier - Autonomous Employee

**Branch**: `003-gold-tier-autonomous` | **Date**: 2026-02-05 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-gold-tier-autonomous/spec.md`

**Note**: This plan implements the Gold Tier milestone, building upon Bronze (File Watcher) and Silver (External Connectivity) tiers to create a fully autonomous employee with Odoo accounting integration, expanded social media coverage, weekly CEO briefings, and the Ralph Wiggum autonomous loop pattern.

## Summary

Transform the AI Employee from a "Functional Assistant" (Silver) into an "Autonomous Employee" by implementing:

1. **Odoo Community ERP Integration** - MCP server using JSON-RPC APIs for draft invoices, payments, and financial reporting
2. **Facebook & Instagram Integration** - Meta Business Suite API posting via MCP servers
3. **Twitter/X Integration** - Twitter API v2 posting via MCP server
4. **Weekly Business Audit & CEO Briefing** - Scheduled autonomous audit with executive summary generation
5. **Ralph Wiggum Autonomous Loop** - Stop hook implementation for multi-step task completion
6. **Error Recovery & Graceful Degradation** - Comprehensive failure handling and Watchdog process
7. **Comprehensive Audit Logging** - 90-day retention with compression and alerting

**Technical Approach**: Additive layer on Silver Tier infrastructure. Python for orchestration and audit processes, Node.js for new MCP servers, Claude Code hooks for autonomous loop.

## Technical Context

**Language/Version**: Python 3.13+ (audit, orchestration), Node.js 24+ LTS (MCP servers), Bash (hooks)
**Primary Dependencies**:
- Python: xmlrpc.client (Odoo JSON-RPC), requests, pydantic, psutil (Watchdog), schedule
- Node.js: @modelcontextprotocol/sdk, axios, twitter-api-v2, @facebook/graph-api
**Storage**: Local filesystem (vault), SQLite (extends Silver idempotency DB), Odoo PostgreSQL (external)
**Testing**: pytest (Python), vitest (Node.js MCP servers), integration tests with Odoo sandbox
**Target Platform**: Windows 10/11, macOS 12+, Linux (Ubuntu 22.04+)
**Project Type**: Distributed system (extends Silver architecture with new MCP servers + Claude hooks)
**Performance Goals**:
- Odoo MCP: 30-second connection timeout, 99% accuracy for invoice/payment creation
- Social MCPs: Posts published within 5 minutes of approval
- CEO Briefing: Generated every Monday by 7 AM
- Ralph Wiggum Loop: 95% completion rate for 5+ step tasks
**Constraints**:
- MUST NOT modify Bronze or Silver Tier core logic
- Human-in-the-loop REQUIRED for all Odoo postings and social posts
- 90-day log retention with compression at 30 days
- Max 10 iterations per Ralph Wiggum loop (configurable)
**Scale/Scope**:
- Single Odoo instance (local or network)
- 5 social media platforms (LinkedIn from Silver + Facebook, Instagram, Twitter)
- ~10 invoices/week, ~20 social posts/week
- Weekly CEO briefing generation

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Requirement | Status | Compliance Notes |
|-----------|-------------|--------|------------------|
| **I. Local-First Architecture** | All data in Obsidian vault | ✅ PASS | Briefings, logs, approval files all in vault. Odoo is external ERP (explicit exception per spec). |
| **II. PRA Loop** | Perception → Reasoning → Action | ✅ PASS | CEO Briefing scheduled task (Perception) → Claude analyzes data (Reasoning) → MCP posts/logs (Action). |
| **III. HITL Safety** | Sensitive actions require approval | ✅ PASS | All Odoo postings and social posts require approval. FR-003 explicitly mandates draft-first workflow. |
| **IV. Autonomous Persistence** | Ralph Wiggum pattern for multi-step | ✅ PASS | FR-019-024 implement Stop hook with completion detection and max iterations guard. |
| **V. Security & Credential Mgmt** | No secrets in vault | ✅ PASS | Odoo API key in OS credential manager. Social OAuth tokens use Silver Tier pattern. |
| **VI. Audit Logging** | All actions logged, 90-day retention | ✅ PASS | FR-031-036 specify JSON logging, 90-day retention, compression, and alerting. |
| **VII. Agent Skills** | Implement as Claude Code Skills | ✅ PASS | FR-039 mandates all AI functionality as Agent Skills. |

**Gates**:
- ✅ All principles satisfied - proceed to Phase 0
- ℹ️ Odoo is an external system but explicitly required by Gold Tier spec; not a local-first violation

## Project Structure

### Documentation (this feature)

```text
specs/003-gold-tier-autonomous/
├── spec.md              # Feature requirements (completed)
├── plan.md              # This file (/sp.plan command output)
├── research.md          # Phase 0 output: Odoo JSON-RPC, Meta API, Twitter API, Claude hooks
├── data-model.md        # Phase 1 output: Invoice, Payment, SocialPost, CEOBriefing schemas
├── quickstart.md        # Phase 1 output: Odoo setup, Meta/Twitter OAuth, Ralph Wiggum config
├── contracts/           # Phase 1 output: MCP tool definitions
│   ├── odoo-mcp.json
│   ├── facebook-mcp.json
│   ├── instagram-mcp.json
│   └── twitter-mcp.json
└── tasks.md             # Phase 2 output (/sp.tasks command - NOT created by /sp.plan)
```

### Source Code (repository root)

```text
src/
├── file_watcher/        # Existing Bronze Tier (unchanged)
├── watchers/            # Existing Silver Tier (unchanged)
├── common/              # Existing Silver Tier (extends)
│   ├── credentials.py   # (unchanged)
│   ├── idempotency.py   # (unchanged)
│   ├── integrity.py     # (unchanged)
│   ├── audit_logger.py  # EXTEND: Add 90-day retention, compression, size alerting
│   └── retry.py         # (unchanged)
├── mcp_servers/         # Existing Silver Tier + NEW Gold Tier servers
│   ├── gmail/           # (unchanged from Silver)
│   ├── linkedin/        # (unchanged from Silver)
│   ├── odoo/            # NEW: Odoo JSON-RPC MCP server
│   │   ├── package.json
│   │   ├── index.ts
│   │   ├── tools/
│   │   │   ├── create_invoice.ts
│   │   │   ├── create_payment.ts
│   │   │   └── get_financial_summary.ts
│   │   └── lib/
│   │       └── odoo_client.ts
│   ├── facebook/        # NEW: Facebook Pages MCP server
│   │   ├── package.json
│   │   ├── index.ts
│   │   └── tools/
│   │       └── create_post.ts
│   ├── instagram/       # NEW: Instagram Business MCP server
│   │   ├── package.json
│   │   ├── index.ts
│   │   └── tools/
│   │       └── publish_media.ts
│   └── twitter/         # NEW: Twitter/X API v2 MCP server
│       ├── package.json
│       ├── index.ts
│       └── tools/
│           └── post_tweet.ts
├── tasks/               # NEW: Gold Tier task processors
│   ├── __init__.py
│   ├── ceo_briefing.py       # FR-013-018: Weekly audit and briefing generation
│   ├── subscription_audit.py  # FR-016: Subscription pattern analysis
│   └── bottleneck_detector.py # FR-017: Task completion time analysis
└── orchestrator/        # Existing Silver Tier (extends)
    ├── __init__.py
    ├── watchdog.py      # EXTEND: Add process monitoring and auto-restart (FR-027)
    └── action_queue.py  # EXTEND: Add graceful degradation queue (FR-028-029)

tests/
├── unit/
│   ├── test_odoo_client.py
│   ├── test_ceo_briefing.py
│   ├── test_subscription_audit.py
│   └── test_bottleneck_detector.py
├── integration/
│   ├── test_odoo_mcp.py
│   ├── test_meta_mcps.py
│   ├── test_twitter_mcp.py
│   └── test_ralph_wiggum_loop.py
└── fixtures/
    ├── mock_odoo_api.py
    ├── mock_meta_api.py
    ├── mock_twitter_api.py
    └── sample_briefing_data.py

.claude/
├── hooks/               # NEW: Ralph Wiggum Stop hook
│   └── ralph-wiggum-stop.sh
├── plugins/             # NEW: Ralph Wiggum plugin configuration
│   └── ralph-wiggum/
│       ├── manifest.json
│       └── hooks/
│           └── hooks.json
├── skills/              # Existing + NEW Gold Tier skills
│   ├── email-ops/       # (unchanged from Silver)
│   ├── social-ops/      # EXTEND: Add Facebook, Instagram, Twitter
│   ├── manage-approval/ # (unchanged from Silver)
│   ├── scheduler/       # (unchanged from Silver)
│   ├── watcher-manager/ # (unchanged from Silver)
│   ├── odoo-ops/        # NEW: Odoo accounting skill
│   │   ├── SKILL.md
│   │   └── scripts/
│   │       └── main_operation.py
│   ├── ceo-briefing/    # NEW: Weekly briefing skill
│   │   ├── SKILL.md
│   │   └── scripts/
│   │       └── main_operation.py
│   └── ralph-loop/      # NEW: Autonomous loop skill
│       ├── SKILL.md
│       └── scripts/
│           └── main_operation.py
└── settings.local.json  # Extended with Gold Tier MCP servers and hooks

config/
├── .env.example         # Extended with Odoo, Meta, Twitter credentials
├── watcher_config.yaml  # (unchanged from Silver)
└── gold_tier.yaml       # NEW: Gold Tier specific config (briefing schedule, rate limits)

scripts/
├── setup_odoo_connection.py  # NEW: Odoo connectivity test and API key setup
├── setup_meta_oauth.py       # NEW: Meta Business Suite OAuth flow
├── setup_twitter_oauth.py    # NEW: Twitter API OAuth flow
└── init_gold_tier.sql        # NEW: SQLite schema extensions for Gold Tier
```

**Structure Decision**: Extends Silver Tier architecture with new MCP servers for Odoo and social platforms. Python handles orchestration, scheduled tasks, and audit processes. Node.js handles MCP servers. Claude Code hooks implement Ralph Wiggum pattern. Preserves Bronze and Silver Tier code integrity.

## Complexity Tracking

No constitution violations requiring justification. Gold Tier builds upon Silver Tier patterns.

---

## 1. Scope and Dependencies

### In Scope (Gold Tier)

1. **Odoo Community ERP Integration**:
   - Odoo MCP server with JSON-RPC client (Odoo 19+)
   - Create draft invoices and payments (require approval before posting)
   - Retrieve financial summaries for CEO briefings
   - 30-second connection timeout, 3 retries, local queue fallback

2. **Extended Social Media Coverage**:
   - Facebook MCP server via Meta Business Suite API (Pages posting)
   - Instagram MCP server via Meta Business Suite API (Business account posting)
   - Twitter MCP server via Twitter API v2 (tweet posting)
   - Proactive OAuth token refresh (<1 hour remaining)
   - Rate limiting per platform (Facebook: 5/day, Instagram: 3/day, Twitter: 50/day)

3. **Weekly Business Audit and CEO Briefing**:
   - Scheduled audit task (default Sunday 11 PM)
   - CEO Briefing generation with: Executive Summary, Revenue, Tasks, Bottlenecks, Suggestions
   - Subscription pattern analysis for cost optimization
   - Task completion time analysis for bottleneck detection

4. **Ralph Wiggum Autonomous Loop**:
   - Stop hook implementation that intercepts Claude exit
   - Dual completion detection: promise-based + file-based
   - Max iterations guard (default 10)
   - Iteration logging and completion summaries

5. **Error Recovery and Graceful Degradation**:
   - Error categorization (Transient, Auth, Logic, Data, System)
   - Exponential backoff retry (1s initial, 60s max, 5 retries)
   - Watchdog process for auto-restart of crashed components
   - Local action queue for unavailable services
   - /Quarantine folder for corrupted files

6. **Comprehensive Audit Logging**:
   - JSON logs to /Vault/Logs/YYYY-MM-DD.json
   - 90-day retention with 30-day compression
   - Log size alerting (80% of 1GB threshold)
   - Log query support (date, action_type, target, result)

7. **Documentation and Skills**:
   - Architecture documentation
   - All AI functionality as Agent Skills
   - Lessons learned and configuration guidance

### Out of Scope (Deferred to Platinum Tier)

- Cloud deployment (always-on, 24/7)
- Multi-agent coordination (A2A protocol)
- Work-zone specialization (Cloud vs Local ownership)
- Vault sync across Cloud and Local agents
- Advanced CEO Briefing with cloud-collected data

### External Dependencies

| Dependency | Ownership | Purpose | Risk |
|------------|-----------|---------|------|
| Odoo Community | Self-hosted | ERP/Accounting | Local installation required, DB corruption possible |
| Meta Business Suite API | Meta | Facebook/Instagram posting | OAuth token expiry, API changes |
| Twitter API v2 | X Corp | Tweet posting | Rate limits, API pricing changes |
| Gmail API | Google | Email (from Silver) | Rate limits, OAuth (handled by Silver) |
| LinkedIn API | Microsoft | Social (from Silver) | Rate limits (handled by Silver) |
| Claude Code | Anthropic | Reasoning, hooks | Hook API stability |
| PM2 | OSS | Process management | Cross-platform behavior |

---

## 2. Key Decisions and Rationale

### Decision 1: Odoo JSON-RPC API vs Direct Database Access

**Options Considered**:
1. JSON-RPC API via xmlrpc.client (chosen)
2. Direct PostgreSQL database queries
3. Odoo ORM via external Python library (OdooRPC)

**Trade-offs**:
- **JSON-RPC API**: Official, stable, respects Odoo business logic, but slower than direct DB
- **Direct DB**: Fastest, but bypasses Odoo security and business rules, high maintenance
- **OdooRPC**: Convenient wrapper, but adds dependency and may lag behind Odoo versions

**Rationale**: JSON-RPC is the official external API recommended by Odoo documentation. It respects all business logic, security constraints, and workflow rules. Direct DB access is explicitly prohibited per spec constraints.

**Principles**: Uses official API (stability), respects security model, reversible (can add ORM wrapper later).

---

### Decision 2: Single Meta MCP vs Separate Facebook/Instagram MCPs

**Options Considered**:
1. Separate Facebook MCP and Instagram MCP (chosen)
2. Single unified Meta MCP handling both platforms
3. Generic Social Media MCP for all platforms

**Trade-offs**:
- **Separate MCPs**: Clearer responsibility, easier to maintain platform-specific logic, but more code
- **Unified Meta MCP**: Less duplication, but complex conditionals and harder to test
- **Generic Social MCP**: Maximum code reuse, but leaky abstraction and platform-specific edge cases

**Rationale**: Facebook Pages and Instagram Business have different posting workflows (Instagram requires container creation + publish). Separate MCPs allow platform-specific optimization and clearer error handling. The OAuth flow is shared but posting logic differs.

**Principles**: Single responsibility, testability, explicit over implicit.

---

### Decision 3: Ralph Wiggum Completion Strategy - Hybrid Approach

**Options Considered**:
1. Promise-based only (`<promise>TASK_COMPLETE</promise>`)
2. File-based only (task file in /Done)
3. Hybrid: File-based primary + Promise-based secondary (chosen)

**Trade-offs**:
- **Promise-based**: Claude explicitly signals completion, but may forget or misformat
- **File-based**: Natural workflow integration (move to Done), but requires file management
- **Hybrid**: Best of both worlds, but more complex hook logic

**Rationale**: File-based completion aligns with the vault-based workflow (Needs_Action → Done). Promise-based provides explicit control when file movement isn't applicable. Hybrid ensures multiple paths to completion.

**Principles**: Defense in depth, workflow integration, explicit completion signals.

---

### Decision 4: Watchdog Implementation - PM2 vs Custom Python

**Options Considered**:
1. PM2 process manager (extends Silver Tier)
2. Custom Python Watchdog process (chosen for monitoring logic)
3. systemd/launchd native services

**Trade-offs**:
- **PM2**: Battle-tested, cross-platform, built-in restart, but limited custom monitoring
- **Custom Python**: Full control over restart logic and alerts, but more code to maintain
- **systemd/launchd**: Native OS integration, but platform-specific

**Rationale**: Use PM2 for basic process management (already from Silver), but add custom Python Watchdog for enhanced monitoring (memory usage, health checks, alert generation). This hybrid approach provides both reliability and observability.

**Principles**: Leverage existing tools (PM2), add custom logic only where needed.

---

### Decision 5: CEO Briefing Data Aggregation - Pull vs Push

**Options Considered**:
1. Pull model: Briefing process queries all data sources at generation time (chosen)
2. Push model: Components write metrics to a central store throughout the week
3. Hybrid: Push metrics, pull raw data

**Trade-offs**:
- **Pull model**: Simpler architecture, always fresh data, but slower generation
- **Push model**: Fast generation, but complex event routing and potential data staleness
- **Hybrid**: Best accuracy, but highest complexity

**Rationale**: Pull model is simplest and ensures data freshness. Weekly briefing generation time is not critical (can take 2-3 minutes). Pushing metrics would add complexity without significant benefit at this scale.

**Principles**: Simplicity, data freshness, YAGNI (don't build push infrastructure yet).

---

## 3. Interfaces and API Contracts

### 3.1 Odoo MCP Tool Definitions

#### `create_invoice`

```json
{
  "name": "create_invoice",
  "description": "Create a draft customer invoice in Odoo. Requires approval before posting.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "customer_name": {"type": "string", "description": "Customer name or Odoo partner ID"},
      "invoice_date": {"type": "string", "format": "date", "description": "Invoice date (YYYY-MM-DD)"},
      "lines": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "description": {"type": "string"},
            "quantity": {"type": "number"},
            "unit_price": {"type": "number"}
          },
          "required": ["description", "quantity", "unit_price"]
        }
      },
      "notes": {"type": "string", "description": "Optional invoice notes"}
    },
    "required": ["customer_name", "invoice_date", "lines"]
  },
  "outputSchema": {
    "type": "object",
    "properties": {
      "invoice_id": {"type": "integer"},
      "invoice_number": {"type": "string"},
      "state": {"type": "string", "enum": ["draft"]},
      "amount_total": {"type": "number"},
      "approval_file": {"type": "string", "description": "Path to approval request file"}
    }
  }
}
```

#### `create_payment`

```json
{
  "name": "create_payment",
  "description": "Create a draft payment entry in Odoo. Requires approval before posting.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "partner_name": {"type": "string"},
      "amount": {"type": "number"},
      "payment_type": {"type": "string", "enum": ["inbound", "outbound"]},
      "reference": {"type": "string", "description": "Payment reference (e.g., invoice number)"}
    },
    "required": ["partner_name", "amount", "payment_type"]
  },
  "outputSchema": {
    "type": "object",
    "properties": {
      "payment_id": {"type": "integer"},
      "state": {"type": "string", "enum": ["draft"]},
      "approval_file": {"type": "string"}
    }
  }
}
```

#### `get_financial_summary`

```json
{
  "name": "get_financial_summary",
  "description": "Retrieve financial summary from Odoo for CEO briefing",
  "inputSchema": {
    "type": "object",
    "properties": {
      "date_from": {"type": "string", "format": "date"},
      "date_to": {"type": "string", "format": "date"}
    },
    "required": ["date_from", "date_to"]
  },
  "outputSchema": {
    "type": "object",
    "properties": {
      "total_revenue": {"type": "number"},
      "total_receivable": {"type": "number"},
      "invoice_count": {"type": "integer"},
      "payment_count": {"type": "integer"},
      "top_customers": {
        "type": "array",
        "items": {"type": "object", "properties": {"name": {"type": "string"}, "revenue": {"type": "number"}}}
      }
    }
  }
}
```

### 3.2 Social Media MCP Tool Definitions

#### Facebook `create_post`

```json
{
  "name": "create_post",
  "description": "Create a post on a Facebook Page",
  "inputSchema": {
    "type": "object",
    "properties": {
      "page_id": {"type": "string"},
      "message": {"type": "string", "maxLength": 63206},
      "link": {"type": "string", "format": "uri"},
      "image_url": {"type": "string", "format": "uri"},
      "scheduled_time": {"type": "string", "format": "date-time"}
    },
    "required": ["page_id", "message"]
  },
  "outputSchema": {
    "type": "object",
    "properties": {
      "post_id": {"type": "string"},
      "url": {"type": "string"},
      "status": {"type": "string", "enum": ["published", "scheduled", "failed"]}
    }
  }
}
```

#### Instagram `publish_media`

```json
{
  "name": "publish_media",
  "description": "Publish an image or carousel to Instagram Business account",
  "inputSchema": {
    "type": "object",
    "properties": {
      "ig_user_id": {"type": "string"},
      "media_type": {"type": "string", "enum": ["IMAGE", "VIDEO", "CAROUSEL"]},
      "media_urls": {"type": "array", "items": {"type": "string", "format": "uri"}},
      "caption": {"type": "string", "maxLength": 2200}
    },
    "required": ["ig_user_id", "media_type", "media_urls", "caption"]
  },
  "outputSchema": {
    "type": "object",
    "properties": {
      "media_id": {"type": "string"},
      "url": {"type": "string"},
      "status": {"type": "string", "enum": ["published", "failed"]}
    }
  }
}
```

#### Twitter `post_tweet`

```json
{
  "name": "post_tweet",
  "description": "Post a tweet to Twitter/X",
  "inputSchema": {
    "type": "object",
    "properties": {
      "text": {"type": "string", "maxLength": 280},
      "reply_to_tweet_id": {"type": "string"},
      "quote_tweet_id": {"type": "string"},
      "media_ids": {"type": "array", "items": {"type": "string"}}
    },
    "required": ["text"]
  },
  "outputSchema": {
    "type": "object",
    "properties": {
      "tweet_id": {"type": "string"},
      "url": {"type": "string"},
      "status": {"type": "string", "enum": ["posted", "failed"]}
    }
  }
}
```

### 3.3 CEO Briefing Output Format

```markdown
# Monday Morning CEO Briefing

**Generated**: {generated_timestamp}
**Period**: {period_start} to {period_end}

## Executive Summary

{1-2 sentence summary of key highlights}

## Revenue

- **This Week**: ${weekly_revenue}
- **MTD**: ${mtd_revenue} ({mtd_percentage}% of ${monthly_target} target)
- **Trend**: {on_track|ahead|behind}

### Top Customers This Week

| Customer | Revenue |
|----------|---------|
{customer_rows}

## Completed Tasks

{completed_task_list}

## Bottlenecks

| Task | Expected | Actual | Delay |
|------|----------|--------|-------|
{bottleneck_rows}

## Proactive Suggestions

### Cost Optimization

{subscription_suggestions}

### Upcoming Deadlines

{deadline_list}

---
*Generated by AI Employee v0.3 (Gold Tier)*
```

---

## 4. Non-Functional Requirements (NFRs) and Budgets

### 4.1 Performance

| Metric | Target | Measurement |
|--------|--------|-------------|
| Odoo MCP: invoice creation | <5 seconds | API response time |
| Odoo MCP: financial summary | <10 seconds | API response time |
| Social post publish | <5 minutes from approval | Timestamp diff |
| CEO Briefing generation | <3 minutes | Script execution time |
| Ralph Wiggum loop iteration | <2 minutes each | Iteration timestamp diff |
| Watchdog restart | <60 seconds | Process restart time |

### 4.2 Reliability

| Metric | Target | Measurement |
|--------|--------|-------------|
| Odoo MCP availability | 99% (during Odoo uptime) | Health check success rate |
| Social MCP availability | 99% | Health check success rate |
| Ralph Wiggum completion rate | 95% for 5+ step tasks | Task completion logs |
| Watchdog detection | <60 seconds for crash | Process monitoring interval |
| Error recovery | 100% for transient failures | Retry success rate |

### 4.3 Security

| Requirement | Implementation | Validation |
|-------------|----------------|------------|
| Odoo credentials | OS credential manager | Pre-commit hook for .env |
| Meta OAuth tokens | OS credential manager + proactive refresh | Token expiry monitoring |
| Twitter OAuth | OS credential manager | Token expiry monitoring |
| Audit log integrity | Append-only JSON files | No modification after write |

### 4.4 Cost

| Resource | Budget | Rationale |
|----------|--------|-----------|
| Memory | +200MB (total 700MB for Gold) | Odoo client, additional MCPs |
| Disk | +50MB for code, <20MB logs/month | Compressed logs |
| API costs | Odoo: Free (self-hosted), Meta: Free, Twitter: Free tier | Personal/small business use |

---

## 5. Operational Readiness

### 5.1 Observability

**Logs**:
- Extended audit logging with 90-day retention
- Compression of logs >30 days old (gzip)
- Size alerting at 80% of 1GB limit

**Metrics**:
- Odoo connection success/failure counts
- Social post success/failure counts
- Ralph Wiggum iteration counts and completion rates
- Watchdog restart events

### 5.2 Alerting

| Alert | Threshold | Notification |
|-------|-----------|--------------|
| Odoo connection failed | 3 consecutive failures | /Vault/Alerts/odoo_connection.md |
| Social OAuth expired | Token refresh failed 3x | /Vault/Alerts/oauth_expired.md |
| Ralph Wiggum max iterations | Loop hit limit | /Vault/Alerts/ralph_max_iter.md |
| Log size warning | >800MB (80% of 1GB) | /Vault/Alerts/log_size.md |
| Watchdog restart | Any process restart | /Vault/Alerts/process_restart.md |

### 5.3 Runbooks

**Runbook 1: Odoo Connection Failure**
1. Check Odoo service status: `systemctl status odoo` (Linux) or Odoo UI
2. Verify network connectivity to Odoo host/port
3. Check credentials in OS credential manager
4. Test with `python scripts/setup_odoo_connection.py --test`
5. Review Odoo logs for authentication errors

**Runbook 2: Ralph Wiggum Loop Stuck**
1. Check /Vault/Logs/ for iteration history
2. Review task file in /Needs_Action or /Done
3. Check if max iterations reached
4. Manually move task to /Done if complete
5. Restart Claude Code session if needed

**Runbook 3: CEO Briefing Not Generated**
1. Check scheduled task status (cron/Task Scheduler)
2. Verify Odoo connectivity for financial data
3. Review /Vault/Logs/ for errors
4. Run manually: `python src/tasks/ceo_briefing.py --manual`

---

## 6. Risk Analysis and Mitigation

### Risk 1: Odoo API Version Incompatibility

**Likelihood**: Medium (Odoo major versions may change API)
**Impact**: High (accounting integration fails)
**Mitigation**: Pin to Odoo 19+, test against specific version, document compatibility matrix
**Kill Switch**: Disable Odoo MCP via feature flag

### Risk 2: Ralph Wiggum Infinite Loop

**Likelihood**: Low (guards in place)
**Impact**: High (wasted resources, stuck session)
**Mitigation**: Max iterations (10), timeout (30 min), stagnation detection
**Kill Switch**: `stop_hook_active` flag prevents recursion

### Risk 3: Social Media API Changes

**Likelihood**: Medium (APIs change frequently)
**Impact**: Medium (posting fails until updated)
**Mitigation**: Abstract API clients, monitor changelogs, proactive token refresh
**Kill Switch**: Disable individual platform MCPs via feature flags

### Risk 4: CEO Briefing Data Inaccuracy

**Likelihood**: Low (direct queries from source systems)
**Impact**: Medium (misleading business decisions)
**Mitigation**: Data validation, Odoo reconciliation check, manual review workflow
**Kill Switch**: Generate "draft" briefing requiring human verification

---

## 7. Architectural Decision Records (ADRs)

This plan includes **FIVE significant architectural decisions**:

1. **Odoo JSON-RPC API vs Direct Database** (Impact: Security, maintainability; Scope: All accounting)
2. **Separate Facebook/Instagram MCPs** (Impact: Maintainability, testability; Scope: Social posting)
3. **Ralph Wiggum Hybrid Completion** (Impact: Reliability, workflow; Scope: Autonomous loops)
4. **PM2 + Custom Watchdog** (Impact: Reliability, observability; Scope: Process management)
5. **CEO Briefing Pull Model** (Impact: Simplicity, data freshness; Scope: Weekly audit)

📋 **Architectural decisions detected**: Document reasoning and tradeoffs? Run `/sp.adr gold-tier-architecture`

---

## Phase 0: Outline & Research

**Goal**: Document research findings for all Gold Tier technologies.

### Research Tasks

1. **Odoo JSON-RPC API** (COMPLETED in subagent research):
   - Authentication via API key (replaces password)
   - Invoice creation via `account.move` model
   - Payment creation via `account.payment` model
   - Financial queries via `search_read`
   - Connection pooling with `requests.Session`

2. **Meta Business Suite API** (COMPLETED in subagent research):
   - OAuth2 flow with Page Access Tokens
   - Facebook Pages posting via `/{page-id}/feed`
   - Instagram posting via two-step container workflow
   - Media handling and rate limits
   - Webhook patterns for engagement

3. **Twitter API v2** (COMPLETED in subagent research):
   - OAuth 1.0a required for posting (OAuth 2.0 for read-only)
   - Tweet posting via `POST /2/tweets`
   - 280 character limit, thread handling
   - Rate limits: 100 posts/15 min per user
   - Media upload via v1 API

4. **Claude Code Stop Hooks** (COMPLETED in subagent research):
   - Stop hook intercepts exit via exit code 2
   - Context persists through modified files and git history
   - Completion detection: promise-based + file-based
   - Infinite loop prevention via max iterations and `stop_hook_active`

**Output**: `specs/003-gold-tier-autonomous/research.md`

---

## Phase 1: Design & Contracts

**Prerequisites**: Research complete

### Tasks

1. **Generate `data-model.md`**:
   - OdooConnection: host, port, database, username, api_key_ref, timeout, status
   - Invoice: partner_id, lines, amount_total, state, odoo_id, vault_reference
   - Payment: partner_id, amount, type, method, state, odoo_id, vault_reference
   - SocialMediaPost: platform, content, media, scheduled_time, status, post_id
   - CEOBriefing: period_start, period_end, revenue_data, tasks, bottlenecks, suggestions
   - RalphLoop: task_prompt, completion_strategy, max_iterations, current, status, history
   - AuditLogEntry: timestamp, action_type, actor, target, parameters, approval, result, error
   - QuarantinedFile: original_path, quarantine_path, error_type, error_message, timestamp

2. **Generate contracts**:
   - `contracts/odoo-mcp.json`: create_invoice, create_payment, get_financial_summary
   - `contracts/facebook-mcp.json`: create_post
   - `contracts/instagram-mcp.json`: publish_media
   - `contracts/twitter-mcp.json`: post_tweet

3. **Generate `quickstart.md`**:
   - Prerequisites (Odoo 19+, Meta Business Account, Twitter Developer)
   - Odoo setup (install Accounting module, create API key, configure connection)
   - Meta OAuth setup (create app, get Page Access Token, configure webhooks)
   - Twitter OAuth setup (create app, get OAuth 1.0a credentials)
   - Ralph Wiggum hook setup (enable plugin, configure max iterations)
   - Test end-to-end (create test invoice, post test tweet)

4. **Update agent context**:
   - Run `.specify/scripts/powershell/update-agent-context.ps1 -AgentType claude`
   - Add: Odoo JSON-RPC, Meta Graph API, Twitter API v2, Claude hooks
   - Preserve Silver Tier entries

**Output**: `data-model.md`, `contracts/`, `quickstart.md`, updated `.claude/settings.local.json`

---

## Stop and Report

This plan ends after Phase 1 design. `/sp.tasks` command will generate `tasks.md` for Phase 2 implementation.

**Summary**:
- **Branch**: `003-gold-tier-autonomous`
- **Plan**: `C:\Code\Hackathon-0\specs\003-gold-tier-autonomous\plan.md` (this file)
- **Artifacts to Generate**:
  - Phase 0: `research.md` (Odoo, Meta, Twitter, Claude hooks)
  - Phase 1: `data-model.md`, `contracts/`, `quickstart.md`

**Next Steps**:
1. Review this plan for completeness
2. Run `/sp.tasks` to generate implementation tasks
3. Implement in order: Odoo MCP → Social MCPs → CEO Briefing → Ralph Wiggum → Error Recovery → Audit Logging
4. Test with sandbox accounts before production
