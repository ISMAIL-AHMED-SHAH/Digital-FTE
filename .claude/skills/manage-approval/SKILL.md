---
name: manage-approval
description: "WHAT: Manage human-in-the-loop approval requests (list, approve, reject). WHEN: User says 'check approvals', 'approve payment', 'reject email', 'show pending'. Trigger on: approval workflow, HITL tasks, reviewing pending actions."
---

# Manage Approval

## When to Use
- Reviewing pending actions in the approval queue
- Approving specific sensitive actions (payments, emails to new contacts)
- Rejecting unsafe or incorrect actions
- Cleaning up expired approval requests

## Instructions
1. **List Pending**:
   ```bash
   python3 .claude/skills/manage-approval/scripts/main_operation.py --action list
   ```

2. **Approve Action**:
   ```bash
   python3 .claude/skills/manage-approval/scripts/main_operation.py --action approve --id "FILE_ID"
   ```

3. **Reject Action**:
   ```bash
   python3 .claude/skills/manage-approval/scripts/main_operation.py --action reject --id "FILE_ID" --reason "REJECTION_REASON"
   ```

## Validation
- [ ] Action file exists and is moved to correct folder (Approved/ or Rejected/)
- [ ] Audit log entry created
- [ ] Dashboard updated (via separate skill or automatically)

See [REFERENCE.md](./REFERENCE.md) for detailed configuration options.
