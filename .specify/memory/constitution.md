<!--
================================================================================
SYNC IMPACT REPORT
================================================================================
Version change: 0.0.0 → 1.0.0 (MAJOR - Initial constitution ratification)

Modified principles: N/A (Initial creation)

Added sections:
  - Core Principles (7 principles)
  - Security & Privacy Requirements
  - Development Workflow
  - Governance

Removed sections: N/A (Initial creation)

Templates requiring updates:
  - .specify/templates/plan-template.md: ✅ Compatible (Constitution Check section exists)
  - .specify/templates/spec-template.md: ✅ Compatible (Requirements section aligns)
  - .specify/templates/tasks-template.md: ✅ Compatible (Phase structure supports HITL)

Follow-up TODOs: None
================================================================================
-->

# Bona-Papa Constitution

**Project**: Hackathon-0: Building Autonomous Digital FTEs in 2026
**Tagline**: *Your life and business on autopilot. Local-first, agent-driven, human-in-the-loop.*

## Core Principles

### I. Local-First Architecture

All persistent data MUST reside locally in the Obsidian vault. External cloud services are permitted only for API interactions (Gmail, WhatsApp, banking), NOT for storing user data or secrets.

**Non-negotiables:**
- Obsidian vault serves as the single source of truth for all state
- Dashboard.md provides real-time system status
- Company_Handbook.md contains all behavioral rules and thresholds
- Business_Goals.md defines success metrics and audit criteria
- No user data leaves the local machine except via explicit MCP actions

**Rationale:** Privacy-centric architecture ensures user maintains full control over personal and business data. Local storage enables offline operation and eliminates third-party data exposure.

### II. Perception-Reasoning-Action (PRA) Loop

Every autonomous operation MUST follow the three-phase cycle: Perception (Watchers detect events) → Reasoning (Claude Code analyzes and plans) → Action (MCP Servers execute).

**Non-negotiables:**
- Watchers are lightweight Python sentinel scripts that monitor external sources
- Watchers write to /Needs_Action folder; they NEVER execute actions directly
- Claude Code reads from vault, reasons about context, and creates Plan.md files
- MCP Servers are the ONLY components permitted to execute external actions
- All inter-component communication occurs via the filesystem (Markdown files)

**Rationale:** Separating perception, reasoning, and action creates clear responsibility boundaries, enables debugging at each stage, and prevents runaway autonomous behavior.

### III. Human-in-the-Loop (HITL) Safety

Sensitive actions MUST require explicit human approval via the file-based approval workflow. The system MUST NOT auto-approve actions that exceed defined thresholds.

**Non-negotiables:**
- Payments to new recipients: ALWAYS require approval
- Payments > $100: ALWAYS require approval
- Payments < $50 to known recurring payees: MAY auto-approve
- Emails to new contacts: ALWAYS require approval
- Bulk email sends: ALWAYS require approval
- Social media replies/DMs: ALWAYS require approval
- File deletions or moves outside vault: ALWAYS require approval

**Approval mechanism:**
1. Claude writes approval request to /Pending_Approval/
2. Human reviews and moves file to /Approved/ or /Rejected/
3. Orchestrator detects approved file and triggers MCP action
4. Completed items move to /Done/ with full audit trail

**Rationale:** Autonomous systems will make mistakes. HITL provides a safety net for irreversible or high-stakes actions while still enabling automation of routine tasks.

### IV. Autonomous Persistence (Ralph Wiggum Pattern)

Multi-step tasks MUST use the Ralph Wiggum stop hook pattern to ensure completion. The agent MUST continue iterating until the task reaches a defined completion state.

**Non-negotiables:**
- Stop hook intercepts Claude Code exit and re-injects prompt if task incomplete
- Completion is detected via: (a) promise output `<promise>TASK_COMPLETE</promise>`, OR (b) task file moved to /Done/
- Maximum iteration limit MUST be set to prevent infinite loops (default: 10)
- Each iteration MUST preserve Claude's previous output for context
- Failed iterations MUST be logged for debugging

**Rationale:** Standard interactive mode terminates after single response. Ralph Wiggum ensures complex multi-step tasks (like invoice generation → approval → send → log) complete without human re-prompting.

### V. Security & Credential Management

Secrets and credentials MUST NEVER be stored in the Obsidian vault or version control. All external access MUST use environment variables or system keychains.

**Non-negotiables:**
- API keys, tokens, and passwords stored ONLY in .env files (excluded from git)
- .env MUST be in .gitignore before any credentials are added
- Banking credentials use system keychain (macOS Keychain, Windows Credential Manager)
- WhatsApp sessions stored in /secure/path/ outside vault
- Credentials MUST be rotated monthly and after any suspected breach
- DEV_MODE and --dry-run flags MUST be supported for all action scripts
- Sandbox/test accounts MUST be used during development

**Rationale:** Credential exposure is the highest-risk failure mode. Defense in depth through environment isolation, system keychains, and mandatory testing modes prevents accidental data loss or unauthorized actions.

### VI. Comprehensive Audit Logging

Every action the AI takes MUST be logged in a structured, queryable format. Logs MUST be retained for minimum 90 days.

**Non-negotiables:**
- Log format: JSON with timestamp, action_type, actor, target, parameters, approval_status, approved_by, result
- Logs stored in /Vault/Logs/YYYY-MM-DD.json
- All MCP actions logged before AND after execution
- Failed actions logged with error details and stack traces
- Human approvals logged with timestamp and approver identity
- Weekly CEO Briefing MUST summarize action log highlights

**Rationale:** Audit trails enable debugging, compliance verification, and continuous improvement. Without logs, there is no way to understand what the agent did or why it failed.

### VII. Agent Skills Architecture

All AI functionality MUST be implemented as Claude Code Agent Skills. Skills encapsulate reusable capabilities that can be invoked, tested, and versioned independently.

**Non-negotiables:**
- Each distinct capability (email drafting, invoice generation, social posting) is a separate Skill
- Skills are defined in SKILL.md format per Claude Code conventions
- Skills MUST be independently testable with mock inputs
- Skills MUST declare their required MCP servers and permissions
- Skills MUST include usage examples and expected outputs
- New functionality MUST be added as Skills, not ad-hoc prompts

**Rationale:** Skills provide the "instant ramp-up" advantage of Digital FTEs. Encapsulated, documented capabilities enable scaling, sharing, and systematic improvement.

## Security & Privacy Requirements

### Threat Model

The system operates with access to sensitive personal and business data. Key threats include:
- Credential theft via exposed .env files or logs
- Unauthorized actions via compromised MCP servers
- Data exfiltration via malicious prompts or plugins
- Runaway automation causing unintended financial transactions

### Mitigations

| Threat | Mitigation | Enforcement |
|--------|------------|-------------|
| Credential exposure | Environment variables + keychain | Pre-commit hook checks |
| Unauthorized actions | HITL approval workflow | /Pending_Approval gate |
| Data exfiltration | Local-first storage | No cloud sync of vault |
| Runaway automation | Rate limiting + max iterations | Orchestrator config |

### Rate Limits (Default)

- Emails: Max 10 per hour
- Payments: Max 3 per day
- Social posts: Max 5 per platform per day
- API calls: Respect provider limits + 20% buffer

## Development Workflow

### Implementation Tiers

This project follows a tiered approach matching hackathon deliverables:

| Tier | Scope | Time Estimate |
|------|-------|---------------|
| Bronze | Vault + 1 Watcher + Claude integration | 8-12 hours |
| Silver | + Multiple Watchers + MCP + HITL + Scheduling | 20-30 hours |
| Gold | + Full integration + Odoo + CEO Briefing + Ralph Wiggum | 40+ hours |
| Platinum | + Cloud deployment + Multi-agent coordination | 60+ hours |

### Testing Requirements

- All Watchers MUST support --dry-run mode
- All MCP actions MUST be testable with mock endpoints
- Integration tests MUST use sandbox accounts
- End-to-end flows MUST be validated before production use

### Code Standards

- Python 3.13+ for all scripts
- Node.js v24+ LTS for MCP servers
- Type hints REQUIRED for Python
- Structured logging (JSON format) REQUIRED
- Error handling with exponential backoff for transient failures

## Governance

### Amendment Process

1. Propose change with rationale in GitHub issue
2. Review impact on existing Skills and workflows
3. Update constitution with version increment
4. Propagate changes to affected templates
5. Document in Sync Impact Report

### Version Policy

- MAJOR: Principle removal or redefinition (breaking change)
- MINOR: New principle or section added
- PATCH: Clarifications, wording improvements

### Compliance Review

- Weekly: Review action logs for policy violations
- Monthly: Audit credential rotation and access patterns
- Quarterly: Full security review and constitution alignment check

### Hierarchy

Constitution > Company_Handbook.md > Individual Skill rules > Ad-hoc prompts

When conflicts arise, higher-level documents take precedence. Amendments to lower-level documents MUST NOT contradict this constitution.

**Version**: 1.0.0 | **Ratified**: 2026-01-19 | **Last Amended**: 2026-01-19
