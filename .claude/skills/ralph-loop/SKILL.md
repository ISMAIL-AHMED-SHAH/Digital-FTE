---
name: ralph-loop
description: "WHAT: Manage Ralph Wiggum autonomous loop execution (start, status, stop). WHEN: User says 'start autonomous task', 'check loop status', 'stop loop'. Trigger on: autonomous execution, multi-step tasks, loop management."
---

# Ralph Wiggum Autonomous Loop

## Overview

The Ralph Wiggum Loop enables Claude to execute multi-step tasks autonomously, continuing until the task is complete or a stopping condition is met.

## When to Use

- Executing tasks that require multiple steps
- Processing batches of similar items
- Workflows that shouldn't need human intervention at each step
- Tasks that can be monitored via the Dashboard

## Completion Detection

The loop uses hybrid completion detection (FR-019/FR-020):

1. **File-based**: Task file moved to `/Done` folder
2. **Promise-based**: Explicit completion signal emitted
3. **Semantic**: Completion phrases in responses ("all done", "task completed")
4. **Error state**: Too many errors or critical failure
5. **Approval pending**: HITL approval requested
6. **Iteration limit**: Maximum iterations reached

## Instructions

### Start Autonomous Loop

```bash
python .claude/skills/ralph-loop/scripts/main_operation.py start --task-id TASK_ID
```

Options:
- `--max-iterations N`: Maximum iterations (default: 50)
- `--timeout M`: Timeout in minutes (default: 30)

### Check Loop Status

```bash
python .claude/skills/ralph-loop/scripts/main_operation.py status --task-id TASK_ID
```

### Stop Loop

```bash
python .claude/skills/ralph-loop/scripts/main_operation.py stop --task-id TASK_ID --reason "REASON"
```

### View Loop History

```bash
python .claude/skills/ralph-loop/scripts/main_operation.py history --task-id TASK_ID
```

### Generate Summary

```bash
python .claude/skills/ralph-loop/scripts/main_operation.py summary --task-id TASK_ID
```

## Configuration

Configure in `config/gold_tier.yaml`:

```yaml
ralph_wiggum:
  enabled: true
  max_iterations: 50
  timeout_minutes: 30
  error_threshold: 3
  warning_threshold: 0.8  # Warn at 80% of max
```

## Stop Hook

The Ralph Wiggum Stop hook (`.claude/hooks/ralph-wiggum-stop.sh`) is called after each response to determine if the loop should continue. It checks:

1. File completion (task in Done folder)
2. Promise completion (signal file)
3. Error state
4. Approval pending
5. Semantic completion phrases
6. Iteration limit

Exit codes:
- `0`: Continue looping
- `1`: Stop looping

## State Tracking

Loop state is tracked in `data/ralph/{task_id}_state.json`:

- Iteration count
- Action history
- Error count
- Start/checkpoint times
- Completion status

## Example Workflow

1. User creates task in `vault/Needs_Action/task-001.md`
2. Start loop: `ralph-loop start --task-id task-001`
3. Claude processes task iteratively
4. Stop hook checks after each iteration
5. Loop completes when task moves to `/Done`
6. Summary generated in `vault/Archive/loop_summaries/`

## Safety Features

- **Max Iterations**: Prevents infinite loops
- **Error Threshold**: Stops after repeated errors
- **Timeout**: Stops after configured time
- **Approval Detection**: Pauses for HITL approval
- **State Recovery**: Can resume after crashes

## Related Skills

- `process-inbox`: For initial task processing
- `manage-approval`: For HITL approval handling
- `view-dashboard`: For monitoring loop status

## Troubleshooting

### Loop Stops Unexpectedly

1. Check `data/ralph/{task_id}_state.json` for completion reason
2. Review error logs in `logs/`
3. Check if approval file was created

### Loop Doesn't Start

1. Verify task file exists in `Needs_Action`
2. Check Claude Code permissions
3. Ensure Ralph Wiggum is enabled in settings

### Loop Hangs

1. Check for pending approval files
2. Review current iteration in state file
3. Use `stop` command with reason

## Output Locations

- **State**: `data/ralph/{task_id}_state.json`
- **Summaries**: `vault/Archive/loop_summaries/`
- **Logs**: `logs/ralph-*.log`
