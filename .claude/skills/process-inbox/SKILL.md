---
name: process-inbox
description: "WHAT: Process pending action files in Needs_Action folder, create execution plans, update Dashboard. WHEN: User says 'process inbox', 'handle pending actions', 'create plans for tasks'. Trigger on: inbox processing, action file handling, plan generation."
---

# Process Inbox - Claude Reasoning Loop

This skill implements the **Claude Reasoning Loop** for the AI Employee system.
When invoked, Claude Code acts as the reasoning engine to process action files and create intelligent execution plans.

## Architecture
```
Watchers (perception) → Needs_Action/ (memory) → Claude Code via /process-inbox (reasoning) → Plans/ + MCP (action)
```

## Instructions

When this skill is invoked, you MUST:

### 1. Scan for Pending Actions
Read all `.md` files in `AI_Employee_Vault/Needs_Action/`

### 2. For Each Action File, Perform Intelligent Analysis
- Read the action file content
- Parse the YAML frontmatter (source, type, priority, timestamp)
- Understand the context and intent of the request
- Read `AI_Employee_Vault/Company_Handbook.md` for business rules
- Consider sensitivity (new contacts, financial, public posting)

### 3. Generate a Structured Execution Plan
Create a plan file in `AI_Employee_Vault/Plans/` with:

```markdown
---
action_id: <from original action>
created: <ISO timestamp>
status: pending
requires_approval: <true if sensitive>
sensitivity: <none|medium|high>
---

# Execution Plan: <brief title>

## Objective
<One sentence describing what needs to be done>

## Analysis
<Your reasoning about this action: what's being requested, context you understand, any concerns>

## Execution Steps
- [ ] Step 1 **[APPROVAL REQUIRED]** (if sensitive)
- [ ] Step 2
- [ ] Step 3

## Risk Assessment
<Any risks, concerns, or things to watch for>

## Recommended MCP Actions
<Which skills/MCP servers to use: email-ops, social-ops, etc.>
```

### 4. Handle Sensitive Actions
If the action involves:
- Sending email to **NEW** contact → Requires approval
- Financial transaction → Requires approval
- Public posting (LinkedIn, social) → Requires approval
- Bulk operations → Requires approval

Create approval request in `AI_Employee_Vault/Pending_Approval/`

### 5. Move Processed Files
Move action file from `Needs_Action/` to `Done/` after plan creation

### 6. Update Dashboard
Update `AI_Employee_Vault/Dashboard.md` with processing activity

## Example Processing

**Input** (Needs_Action/email_action.md):
```yaml
---
source: gmail
type: email
priority: high
---
From: client@example.com
Subject: Need invoice for January work

Hi, please send the invoice for the work completed in January.
```

**Output** (Plans/plan_invoice_request.md):
```markdown
---
action_id: email_action_1234
created: 2026-01-16T03:30:00Z
status: pending
requires_approval: true
sensitivity: medium
---

# Execution Plan: Generate and Send January Invoice

## Objective
Create and send the January invoice to the requesting client.

## Analysis
Client has requested an invoice for work completed in January. This requires:
1. Gathering work records for January
2. Calculating total based on agreed rates
3. Generating invoice document
4. Sending via email

This is a financial document being sent to an existing client (known contact).

## Execution Steps
- [ ] Review January work records in vault
- [ ] Calculate total amount based on Company_Handbook rates
- [ ] Generate invoice using standard template
- [ ] **[APPROVAL REQUIRED]** Send invoice to client@example.com via email-ops

## Risk Assessment
- Low: Existing client relationship
- Verify: January hours/rates before sending

## Recommended MCP Actions
- email-ops: Send final invoice after approval
```

## Validation Checklist
After processing, verify:
- [ ] All action files in Needs_Action/ have been processed
- [ ] Plan files created in Plans/ with proper YAML frontmatter
- [ ] Sensitive actions have approval requests in Pending_Approval/
- [ ] Processed action files moved to Done/
- [ ] Dashboard.md updated with activity summary
