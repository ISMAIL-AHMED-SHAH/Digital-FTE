---
name: view-dashboard
description: "WHAT: Display AI Employee system status, pending actions, and recent activity from Dashboard.md. WHEN: User says 'show dashboard', 'check status', 'what's pending', 'system status'. Trigger on: status check, dashboard view, system monitoring."
---

# View Dashboard

## When to Use
- Morning check-in to see overnight activity
- Quick status check before processing inbox
- Monitoring system health and pending work
- Reviewing recent activity and statistics

## Instructions
1. Execute dashboard display: `python3 scripts/main_operation.py [--vault-path AI_Employee_Vault] [--format full|summary|status]`
2. Verify dashboard readable: `python3 scripts/verify_operation.py --vault-path AI_Employee_Vault`
3. Review output for system status and pending actions.

## Validation
- [ ] Dashboard.md exists and is readable
- [ ] System status displayed correctly
- [ ] Pending actions count shown
- [ ] Recent activity visible

See [REFERENCE.md](./REFERENCE.md) for dashboard format options.
