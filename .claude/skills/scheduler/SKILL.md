---
name: scheduler
description: "WHAT: Manage scheduled tasks using system cron. WHEN: User says 'schedule daily briefing', 'run script every hour', 'list schedules'. Trigger on: automation scheduling, periodic tasks."
---

# Scheduler

## When to Use
- Scheduling daily briefings or reports
- Setting up periodic cleanup tasks
- Automating recurring workflows

## Instructions
1. **List Schedules**:
   ```bash
   python3 .claude/skills/scheduler/scripts/main_operation.py --action list
   ```

2. **Add Schedule**:
   ```bash
   python3 .claude/skills/scheduler/scripts/main_operation.py --action add --cmd "COMMAND" --schedule "CRON_EXPRESSION" --comment "TASK_NAME"
   ```
   *Example cron: "0 8 * * *" (Daily at 8am)*

3. **Remove Schedule**:
   ```bash
   python3 .claude/skills/scheduler/scripts/main_operation.py --action remove --comment "TASK_NAME"
   ```

## Validation
- [ ] Schedule successfully added to crontab
- [ ] Task appears in list output
- [ ] Syntax valid (cron expression checked)

See [REFERENCE.md](./REFERENCE.md) for cron syntax.
