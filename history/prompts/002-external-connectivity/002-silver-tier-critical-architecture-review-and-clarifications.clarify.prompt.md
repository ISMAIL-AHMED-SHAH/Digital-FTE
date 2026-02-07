---
id: 002
title: Silver Tier Critical Architecture Review and Clarifications
stage: clarify
date: 2026-01-23
surface: agent
model: claude-sonnet-4-5
feature: 002-external-connectivity
branch: 002-external-connectivity
user: user
command: /sp.clarify
labels: ["security", "architecture", "clarification", "silver-tier", "authentication", "whatsapp", "hitl", "resource-management"]
links:
  spec: specs/002-external-connectivity/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/002-external-connectivity/spec.md
tests:
  - None (clarification phase, no tests executed)
---

## Prompt

As an expert AI Architect, critically review the Silver Tier specification for any ambiguities, security loopholes, or potential 'scope leaks'.

Please focus on:

Authentication: Is the Gmail OAuth flow clearly defined for a local-first app?

WhatsApp Reliability: How do we handle message polling without getting blocked or missing data?

HITL (Human-in-the-Loop): Is the 'Approval' vs 'Rejection' logic solid enough to prevent accidental external posts?

Resource Management: Will running multiple watchers (Gmail + WhatsApp + File) slow down the Windows machine?

Identify any [NEEDS CLARIFICATION] points yourself and present them to me.

## Response snapshot

Conducted comprehensive architectural review identifying 5 critical ambiguities requiring clarification:

1. **WhatsApp Integration Approach**: CRITICAL - Playwright automation violates WhatsApp TOS
   - **Decision**: Switch to WhatsApp Business API with webhook-based message detection
   - **Impact**: Eliminates legal liability, account suspension risk, improves reliability

2. **OAuth Token Storage**: CRITICAL - No secure storage mechanism specified
   - **Decision**: Use OS credential manager (Windows Credential Manager / macOS Keychain) with automatic refresh
   - **Impact**: Prevents credential exposure, enables long-running watchers without manual intervention

3. **Approval File Integrity**: HIGH - Tampering prevention undefined
   - **Decision**: SHA-256 hash of critical fields embedded in YAML frontmatter
   - **Impact**: Prevents accidental/malicious parameter modification before execution

4. **Resource Management**: MEDIUM - No memory budgets or degradation strategy
   - **Decision**: 100MB per-process limit, 500MB total budget, priority-based graceful degradation
   - **Impact**: Prevents system slowdown, ensures Gmail (highest priority) keeps running

5. **Idempotency Implementation**: MEDIUM - Duplicate prevention mechanism unspecified
   - **Decision**: SQLite database with Message-ID/content hash, 7-day deduplication window
   - **Impact**: Prevents duplicate emails/posts during retry scenarios

**Specification Updates**:
- Added 10 new functional requirements (FR-002a, FR-014a, FR-021 through FR-027)
- Updated 5 existing requirements with specific implementation details
- Added IdempotencyRecord entity to data model
- Added 9 new edge cases with detailed resolution strategies
- Added 7 new success criteria with measurable targets
- Updated 4 assumptions with concrete technical requirements
- Created Clarifications section documenting all Q&A pairs

## Outcome

- ✅ Impact: CRITICAL - Eliminated 2 critical risks (WhatsApp TOS violation, credential exposure), mitigated 3 high/medium risks (tampering, resource exhaustion, duplicate actions). Specification now production-ready for planning phase.
- 🧪 Tests: No tests executed (clarification phase focused on specification refinement)
- 📁 Files: Modified specs/002-external-connectivity/spec.md with 50+ changes across 7 major sections
- 🔁 Next prompts: Run `/sp.plan` to generate architectural implementation plan based on clarified specification; planning phase will design OAuth flows, webhook architecture, SQLite schema, resource monitoring strategy
- 🧠 Reflection: Interactive clarification workflow successfully identified and resolved ambiguities that would have caused implementation delays, security vulnerabilities, and platform violations. All 5 questions addressed highest-impact concerns from user's focus areas (authentication, WhatsApp, HITL, resources).

## Evaluation notes (flywheel)

- Failure modes observed: None. All 5 clarifications accepted immediately (4 with "recommended", 1 with option letter). User had spec open in IDE, indicating active review during session.
- Graders run and results (PASS/FAIL): N/A (clarification workflow, no automated grading applicable)
- Prompt variant (if applicable): Standard /sp.clarify workflow with user-specified focus areas (authentication, WhatsApp, HITL, resource management)
- Next experiment (smallest change to try): Consider adding risk severity matrix to clarification output for easier prioritization when question count exceeds limit; consider suggesting ADR creation for architecturally significant clarifications (WhatsApp API switch, OAuth storage strategy qualify)
