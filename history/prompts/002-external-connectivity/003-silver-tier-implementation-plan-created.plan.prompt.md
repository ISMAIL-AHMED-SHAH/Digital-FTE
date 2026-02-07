---
id: 003
title: Silver Tier Implementation Plan Created
stage: plan
date: 2026-01-25
surface: agent
model: claude-sonnet-4-5
feature: 002-external-connectivity
branch: 002-external-connectivity
user: system
command: /sp.plan
labels: ["planning", "architecture", "silver-tier", "external-connectivity", "watchers", "mcp-servers", "oauth", "idempotency"]
links:
  spec: specs/002-external-connectivity/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/002-external-connectivity/plan.md
tests:
  - N/A (planning phase)
---

## Prompt

/sp.plan
Create an implementation plan for Silver Tier (External Connectivity) based strictly on specs/002-external-connectivity/spec.md.
Focus on architecture, component boundaries, execution order, and risk mitigation.

## Response snapshot

Created comprehensive implementation plan for Silver Tier (External Connectivity) covering:

**Architecture**:
- Distributed system: Python watchers (Gmail, WhatsApp webhook, approval monitor, resource monitor) + Node.js MCP servers (Gmail send, LinkedIn post)
- File-based orchestration via Obsidian vault (PRA loop: Perception → Reasoning → Action)
- SQLite for idempotency tracking (7-day window with automatic cleanup)
- OS credential manager (Windows Credential Manager/macOS Keychain) for OAuth token storage

**Key Architectural Decisions** (5 ADRs recommended):
1. WhatsApp Business API (webhook-based) for legal compliance and real-time delivery
2. OS Credential Manager for secure, OS-encrypted OAuth token storage with fallback
3. File-based approval workflow with SHA-256 integrity hashing to prevent tampering
4. SQLite idempotency tracking with 7-day retention to prevent duplicate external actions
5. Memory budgets (100MB per watcher, 500MB total) with graceful degradation (pause LinkedIn → WhatsApp → Gmail)

**Scope**:
- In Scope: Gmail polling (2 min), WhatsApp webhooks, approval workflow, MCP servers, credential management, idempotency, memory monitoring, audit logging, scheduled tasks
- Out of Scope: Ralph Wiggum pattern (Gold), multi-agent (Platinum), Odoo (Gold), CEO Briefing (Gold), cloud deployment (Platinum)

**Risk Mitigation**:
- OAuth token expiry: Auto-refresh with 3-retry limit, alert user on failure
- Webhook signature bypass: HMAC-SHA256 validation, rate limiting (100/min)
- Tampered approvals: SHA-256 integrity hashing, reject mismatches with _TAMPERED suffix
- DB corruption: Daily backups, integrity checks on startup, recreate from backup
- Memory leaks: 60s monitoring, graceful degradation at 80% (400MB), priority-based pausing

**NFRs**:
- Performance: 95% emails detected <5 min, <500ms webhook response, <10 min email send, <5 min LinkedIn post
- Reliability: 99% uptime over 7 days, 99% OAuth refresh success, 100% duplicate prevention, 100% tampered file detection
- Security: No credentials in vault, tamper-proof approvals, webhook signature validation, audit trail immutability
- Cost: 500MB RAM total, <10MB SQLite DB, <50MB code, negligible API costs (<1000 msgs/month)

**Project Structure**:
- src/watchers/: base_watcher.py, gmail_watcher.py, whatsapp_webhook.py, approval_watcher.py, resource_monitor.py
- src/common/: credentials.py, idempotency.py, integrity.py, audit_logger.py, retry.py
- src/mcp_servers/: gmail/, linkedin/, whatsapp/ (Node.js TypeScript)
- tests/unit/, tests/integration/, tests/fixtures/
- config/: .env.example, watcher_config.yaml
- scripts/: setup_gmail_oauth.py, setup_whatsapp.py, init_idempotency_db.sql

**Phases**:
- Phase 0: Research OAuth2 flows, WhatsApp API, OS credential managers, SQLite patterns, integrity hashing, memory monitoring, LinkedIn API
- Phase 1: Design data models (Watcher, ActionFile, ApprovalRequest, IdempotencyRecord), API contracts (WhatsApp webhook OpenAPI, MCP tool definitions), quickstart guide

**Next Steps**: Run /sp.tasks to generate dependency-ordered implementation tasks

## Outcome

- ✅ Impact: Comprehensive architectural plan for Silver Tier with 5 significant architectural decisions, complete scope definition, risk mitigation strategies, and NFR specifications. Plan ready for /sp.tasks task generation.
- 🧪 Tests: No tests yet (planning phase). Test strategy defined: unit (>90% coverage), integration (watcher lifecycle, approval workflow, MCP execution), contract (OpenAPI validation), E2E (sandbox accounts), performance (24h soak test, memory leak detection).
- 📁 Files: Created specs/002-external-connectivity/plan.md (comprehensive implementation plan with 9 architecture sections)
- 🔁 Next prompts:
  1. Phase 0: Generate research.md (OAuth2, WhatsApp Business API, OS credential storage, SQLite idempotency patterns, SHA-256 integrity hashing, memory monitoring with psutil, LinkedIn API)
  2. Phase 1: Generate data-model.md, contracts/ (whatsapp-webhook.openapi.yaml, gmail-mcp.json, linkedin-mcp.json), quickstart.md
  3. Run /sp.tasks to create dependency-ordered tasks for implementation
- 🧠 Reflection: Plan successfully addresses all spec requirements (FR-001 through FR-027) and aligns with constitution principles (Local-First, PRA Loop, HITL Safety, Security, Audit Logging, Agent Skills). Five significant architectural decisions identified that warrant ADR documentation. Memory budget and graceful degradation strategy provides clear operational boundaries for resource-constrained environments. Idempotency and integrity validation provide strong safety guarantees against duplicate sends and tampered approvals.

## Evaluation notes (flywheel)

- Failure modes observed: None during planning. Anticipated failure modes documented in Risk Analysis (OAuth expiry, webhook bypass, tampered files, DB corruption, memory leaks) with mitigation strategies.
- Graders run and results (PASS/FAIL):
  - Constitution Check: PASS (all 7 principles satisfied or deferred appropriately)
  - Scope Clarity: PASS (clear In Scope / Out of Scope boundaries)
  - NFR Specificity: PASS (measurable targets for performance, reliability, security, cost)
  - Risk Coverage: PASS (5 major risks identified with mitigation and kill switches)
- Prompt variant (if applicable): N/A (standard /sp.plan command)
- Next experiment (smallest change to try): Proceed to Phase 0 research generation to validate OAuth2 and WhatsApp Business API assumptions before implementation.
