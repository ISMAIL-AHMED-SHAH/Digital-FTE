---
id: 001
title: Local File Watcher Service Specification
stage: spec
date: 2026-01-19
surface: agent
model: claude-opus-4-5
feature: 001-local-file-watcher
branch: 001-local-file-watcher
user: user
command: /sp.specify
labels: ["spec", "bronze-tier", "file-watcher", "perception-layer"]
links:
  spec: specs/001-local-file-watcher/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/001-local-file-watcher/spec.md
  - specs/001-local-file-watcher/checklists/requirements.md
tests:
  - null
---

## Prompt

/sp.specify

Context:
The Project Constitution has been ratified.
We are now starting the Bronze Tier (Foundation) phase.

Scope:
Bronze Tier requirements ONLY.
Silver and Gold tier capabilities are explicitly out of scope for now.

Task:
Create a Specification for the "Local File Watcher Service".

Authoritative Inputs:
Use the Markdown (.md) documents in the GOAL folder as the authoritative source.
Derive functional and non-functional requirements strictly from those documents.

Specification Requirements:
As per mentioned in the file
  & 'c:\Code\Hackathon-0\GOAL\Personal AI Employee Hackathon 0_ Building Autonomous FTEs in 2026.md'

i.e:
* Define purpose and responsibilities of the Local File Watcher Service
* Functional requirements (Bronze Tier only)
* Explicit non-goals
* Inputs, outputs, and file system interactions
* Error handling and failure modes
* Acceptance criteria suitable for testable tasks
or what you think is better

## Response snapshot

Created comprehensive specification for Local File Watcher Service (Bronze Tier):

**Branch**: `001-local-file-watcher`

**3 User Stories**:
1. P1: Drop File for Processing - core file detection and action file creation
2. P2: View Pending Actions in Dashboard - Obsidian vault visibility
3. P3: Service Resilience - error handling and crash resistance

**12 Functional Requirements** covering:
- Single drop folder monitoring (FR-001)
- Action file creation in /Needs_Action (FR-002)
- YAML frontmatter with metadata (FR-003)
- FILE_ prefix naming pattern (FR-004)
- Special character handling (FR-005)
- Directory ignoring (FR-006)
- Crash-resistant loop (FR-007)
- --dry-run support (FR-008)
- JSON structured logging (FR-009)
- CLI configuration (FR-010, FR-011)
- Duplicate handling (FR-012)

**7 Success Criteria** - all measurable and technology-agnostic

**Explicit Non-Goals**: Gmail/WhatsApp watchers, MCP integration, process management, cloud deployment

Quality checklist passed: 16/16 items validated.

## Outcome

- Impact: Created Bronze Tier specification for first Watcher component
- Tests: N/A (specification phase)
- Files: spec.md, checklists/requirements.md
- Next prompts: /sp.plan to create implementation plan
- Reflection: Spec successfully derived from hackathon document, scoped to Bronze Tier only

## Evaluation notes (flywheel)

- Failure modes observed: None
- Graders run and results (PASS/FAIL): Quality checklist PASS (16/16)
- Prompt variant (if applicable): Standard /sp.specify invocation
- Next experiment (smallest change to try): Validate spec alignment during /sp.plan constitution check
