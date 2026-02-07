---
type: alert
category: ralph_wiggum
severity: {{ severity }}
created_at: {{ timestamp }}
task_id: {{ task_id }}
---

# Ralph Wiggum Loop Alert: {{ title }}

**Task:** {{ task_id }}
**Time:** {{ timestamp }}
**Severity:** {{ severity }}

## Issue

{{ description }}

## Loop Status

| Metric | Value |
|--------|-------|
| Iterations | {{ iteration }}/{{ max_iterations }} |
| Status | {{ loop_status }} |
| Error Count | {{ error_count }} |
| Duration | {{ duration_minutes }} min |

## Completion Detection

- **Method:** {{ completion_method }}
- **Signal Received:** {{ completion_signal }}
- **Reason:** {{ completion_reason }}

## Recent Actions

{{ #each recent_actions }}
| {{ iteration }} | {{ action }} | {{ result }} | {{ timestamp }} |
{{ /each }}

## Recommended Actions

{{ #if is_stalled }}
1. Check if task file exists in `Needs_Action`
2. Review task requirements for blockers
3. Consider splitting into smaller tasks
{{ /if }}

{{ #if max_iterations_reached }}
1. Review task complexity
2. Consider increasing `max_iterations` in config
3. Break task into sub-tasks
{{ /if }}

{{ #if error_threshold_exceeded }}
1. Review error logs for patterns
2. Check service availability
3. Consider quarantining problematic file
{{ /if }}

## Task File Location

Original: `{{ original_path }}`
Current: `{{ current_path }}`

## Recovery Options

- **Resume:** `/ralph-loop start --task-id {{ task_id }}`
- **Stop:** `/ralph-loop stop --task-id {{ task_id }} --reason "Manual stop"`
- **Summary:** `/ralph-loop summary --task-id {{ task_id }}`
