---
id: 001
title: Bona-Papa Constitution Creation
stage: constitution
date: 2026-01-19
surface: agent
model: claude-opus-4-5
feature: none
branch: master
user: user
command: /sp.constitution
labels: ["constitution", "hackathon-0", "bona-papa", "digital-fte"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - .specify/memory/constitution.md
  - history/prompts/constitution/001-bona-papa-constitution-creation.constitution.prompt.md
tests:
  - null
---

## Prompt

/sp.constitution

You are acting as a Senior AI Systems Architect and Autonomous Agent Designer.

Context:
I am starting "Hackathon-0: Building Autonomous Digital FTEs in 2026."
i want to name My Digital Employee as "Bona-Papa."

Task:
Create the Project Constitution for Bona-Papa using the Spec-Kit-Plus methodology.

Inputs:
Use the Markdown (.md) files located in the GOAL folder as authoritative.

& 'c:\Code\Hackathon-0\GOAL\Personal AI Employee Hackathon 0_ Building Autonomous FTEs in 2026.md'

## Response snapshot

Created the Bona-Papa Constitution v1.0.0 with 7 core principles derived from the hackathon document:

1. **Local-First Architecture** - Obsidian vault as single source of truth, privacy-centric
2. **Perception-Reasoning-Action (PRA) Loop** - Watchers → Claude Code → MCP Servers
3. **Human-in-the-Loop (HITL) Safety** - File-based approval workflow for sensitive actions
4. **Autonomous Persistence (Ralph Wiggum)** - Stop hook pattern for multi-step task completion
5. **Security & Credential Management** - Environment variables, keychains, no secrets in vault
6. **Comprehensive Audit Logging** - JSON logs with 90-day retention
7. **Agent Skills Architecture** - All functionality as reusable Claude Code Agent Skills

Additional sections: Security & Privacy Requirements, Development Workflow (Bronze/Silver/Gold/Platinum tiers), Governance with amendment process and compliance review schedule.

## Outcome

- Impact: Created foundational constitution establishing all governance principles for the Bona-Papa Digital FTE project
- Tests: N/A (constitution document, no code)
- Files: .specify/memory/constitution.md created
- Next prompts: /sp.spec to create first feature specification, or implement Bronze tier deliverables
- Reflection: Constitution successfully derived from hackathon authoritative document, capturing all key architectural decisions

## Evaluation notes (flywheel)

- Failure modes observed: None
- Graders run and results (PASS/FAIL): N/A
- Prompt variant (if applicable): Standard /sp.constitution invocation
- Next experiment (smallest change to try): Validate constitution alignment during first /sp.plan execution
