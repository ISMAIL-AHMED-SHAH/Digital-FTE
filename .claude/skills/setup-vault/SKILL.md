---
name: setup-vault
description: "WHAT: Initialize AI Employee Vault structure with folders and core files for Bronze Tier. WHEN: User says 'set up vault', 'initialize vault', 'create AI Employee structure', or mentions starting Bronze Tier setup. Trigger on: vault setup, initialization, first-time setup."
---

# Setup Vault

## When to Use
- First-time setup of AI Employee system (Bronze Tier)
- User wants to create vault structure at project root
- Reinitializing vault after deletion (with force=true)

## Instructions
1. Execute vault creation: `python3 scripts/main_operation.py --vault-path AI_Employee_Vault [--force]`
2. Verify structure: `python3 scripts/verify_operation.py --vault-path AI_Employee_Vault`
3. Confirm success message before proceeding.

## Validation
- [ ] All 8 folders created (Inbox, Needs_Action, Done, Plans, Logs, Pending_Approval, Approved, Rejected)
- [ ] Core files created (Dashboard.md, Company_Handbook.md, README.md, .gitignore)
- [ ] No errors in verification output

See [REFERENCE.md](./REFERENCE.md) for detailed folder structure and file templates.
