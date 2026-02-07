---
type: alert
category: watchdog
severity: {{ severity }}
created_at: {{ timestamp }}
process: {{ process_name }}
---

# Watchdog Alert: {{ title }}

**Process:** {{ process_name }}
**Time:** {{ timestamp }}
**Severity:** {{ severity }}

## Issue

{{ description }}

## Process Status

| Metric | Value |
|--------|-------|
| Status | {{ process_status }} |
| PID | {{ pid }} |
| Restarts | {{ restart_count }}/{{ max_restarts }} |
| Last Error | {{ last_error }} |
| Uptime Before Crash | {{ uptime_before_crash }} |

## Restart History

| Time | Reason | Success |
|------|--------|---------|
{{ #each restart_history }}
| {{ timestamp }} | {{ reason }} | {{ success }} |
{{ /each }}

## Recommended Actions

{{ #if is_max_restarts }}
### CRITICAL: Max Restarts Exceeded

1. **Immediate:** Process will NOT be auto-restarted
2. Check logs: `pm2 logs {{ process_name }}`
3. Review recent changes that may have caused instability
4. Manually restart after fixing: `pm2 restart {{ process_name }}`
5. Reset restart counter: Update watchdog state file

{{ else }}
### Process Restarted

1. Monitor process stability
2. Check logs for recurring errors
3. Review if restart pattern indicates deeper issue

{{ /if }}

## Log Locations

- **stdout:** `logs/{{ process_name }}-out.log`
- **stderr:** `logs/{{ process_name }}-error.log`
- **PM2 logs:** `pm2 logs {{ process_name }} --lines 100`

## Related Services

{{ #each dependent_services }}
- {{ name }}: {{ status }}
{{ /each }}

## Manual Commands

```bash
# Check status
pm2 status {{ process_name }}

# View logs
pm2 logs {{ process_name }} --lines 50

# Restart manually
pm2 restart {{ process_name }}

# Stop process
pm2 stop {{ process_name }}
```
