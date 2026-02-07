---
id: 003
title: Gold Tier Implementation Plan
stage: plan
date: 2026-02-05
surface: agent
model: claude-opus-4-5
feature: 003-gold-tier-autonomous
branch: 003-gold-tier-autonomous
user: user
command: /sp.plan
labels: ["gold-tier", "planning", "architecture", "odoo", "social-media", "ralph-wiggum"]
links:
  spec: specs/003-gold-tier-autonomous/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/003-gold-tier-autonomous/plan.md
  - specs/003-gold-tier-autonomous/research.md
tests:
  - Constitution check validation (all 7 principles passed)
  - Research task completion (4 subagent tasks completed)
---

## Prompt

/sp.plan

Create an implementation plan for the Gold Tier (Autonomous Employee) based on the approved specification.

## Response snapshot

Created comprehensive implementation plan with:

1. **Technical Context**: Python 3.13+ for orchestration, Node.js 24+ for MCP servers, Bash for hooks
2. **Constitution Check**: All 7 principles validated (Local-First, PRA Loop, HITL Safety, Autonomous Persistence, Security, Audit Logging, Agent Skills)
3. **Project Structure**: Detailed source tree showing new MCP servers (odoo/, facebook/, instagram/, twitter/), tasks (ceo_briefing, subscription_audit, bottleneck_detector), and Ralph Wiggum hooks
4. **5 Key Architectural Decisions**:
   - Odoo JSON-RPC API vs Direct Database (chose JSON-RPC)
   - Separate Facebook/Instagram MCPs vs Single Meta MCP (chose separate)
   - Ralph Wiggum Hybrid Completion Strategy (file-based + promise-based)
   - PM2 + Custom Watchdog for process management
   - CEO Briefing Pull Model for data aggregation
5. **API Contracts**: MCP tool definitions for create_invoice, create_payment, get_financial_summary, create_post, publish_media, post_tweet
6. **NFRs and Budgets**: Performance targets, reliability SLOs, security requirements, cost budgets
7. **Operational Readiness**: Observability, alerting thresholds, runbooks
8. **Risk Analysis**: 4 key risks with mitigations and kill switches

Research completed via 4 parallel subagent tasks:
- Odoo JSON-RPC API (v19+): Authentication, CRUD patterns, error handling
- Meta Business Suite API (Graph API v22+): OAuth2, posting workflows, rate limits
- Twitter API v2: OAuth 1.0a requirements, posting, media upload
- Claude Code Stop Hooks: Ralph Wiggum pattern implementation

## Outcome

- ✅ Impact: Created complete Gold Tier implementation plan enabling autonomous employee functionality
- 🧪 Tests: Constitution check passed (all 7 principles), Research tasks completed (4/4)
- 📁 Files: 2 files created (plan.md, research.md)
- 🔁 Next prompts: Generate Phase 1 artifacts (data-model.md, contracts/, quickstart.md), then `/sp.tasks`
- 🧠 Reflection: Plan builds upon Silver Tier patterns while introducing new capabilities. The 5 architectural decisions address key technical choices with clear rationale. Ralph Wiggum hybrid completion strategy provides defense-in-depth for autonomous loops.

## Evaluation notes (flywheel)

- Failure modes observed: None - plan generated cleanly from spec and research
- Graders run and results (PASS/FAIL): Constitution check PASS (7/7 principles)
- Prompt variant (if applicable): Standard /sp.plan with parallel subagent research
- Next experiment (smallest change to try): Consider adding sequence diagrams for complex workflows (Instagram two-step publishing, Ralph Wiggum loop)
