# Gold Tier Troubleshooting Guide

## Quick Diagnostics

### Check System Status

```bash
# PM2 status
pm2 status

# Check all logs
pm2 logs

# Dashboard status
python -m src.skills.view_dashboard
```

## Common Issues

### 1. Odoo Connection Failures

**Symptoms:**
- Invoice creation times out
- "Connection refused" errors
- "Invalid credentials" errors

**Diagnosis:**
```bash
# Test Odoo connection
python scripts/setup_odoo_connection.py --test

# Check Odoo MCP logs
pm2 logs odoo-mcp --lines 50

# Verify environment variables
echo $ODOO_URL
```

**Solutions:**

| Issue | Solution |
|-------|----------|
| Connection timeout | Check Odoo server status, firewall rules |
| Invalid credentials | Re-run `setup_odoo_connection.py` |
| SSL errors | Verify certificate, try HTTP if internal |
| Rate limiting | Reduce request frequency, check Odoo config |

### 2. Social Media OAuth Errors

**Symptoms:**
- "Token expired" errors
- "Invalid OAuth token" errors
- Posts fail with 401/403

**Diagnosis:**
```bash
# Check token status (Facebook)
python -c "from src.mcp_servers.facebook.src.lib.meta_oauth import *; print(debug_token())"

# Check Twitter credentials
python scripts/setup_twitter_oauth.py --verify
```

**Solutions:**

| Platform | Issue | Solution |
|----------|-------|----------|
| Facebook/Instagram | Token expired | Re-run `setup_meta_oauth.py` |
| Facebook/Instagram | Permissions revoked | Re-authorize app in Meta Business Suite |
| Twitter | Invalid token | Generate new tokens in Twitter Developer Portal |
| All | Rate limited | Wait for rate limit reset, check usage |

### 3. Ralph Wiggum Loop Issues

**Symptoms:**
- Loop stuck/not progressing
- Max iterations reached unexpectedly
- Loop doesn't complete

**Diagnosis:**
```bash
# Check loop status
python .claude/skills/ralph-loop/scripts/main_operation.py status --task-id TASK_ID

# View iteration history
python .claude/skills/ralph-loop/scripts/main_operation.py history --task-id TASK_ID

# Check stop hook logs
cat logs/ralph-wiggum-stop.log
```

**Solutions:**

| Issue | Solution |
|-------|----------|
| Loop stuck | Check for pending HITL approval files |
| Premature completion | Verify completion detection phrases |
| Max iterations | Increase limit or break into sub-tasks |
| Error threshold | Review error logs, fix root cause |

**Loop State Recovery:**
```bash
# View state file
cat data/ralph/{task_id}_state.json

# Reset iteration counter
echo "0" > .ralph-wiggum-iterations

# Generate summary
python .claude/skills/ralph-loop/scripts/main_operation.py summary --task-id TASK_ID
```

### 4. File Watcher Not Detecting Files

**Symptoms:**
- Files in Drop folder not processed
- No action files created
- Silent failures

**Diagnosis:**
```bash
# Check watcher status
pm2 status file-watcher

# View watcher logs
pm2 logs file-watcher --lines 100

# Check file permissions
ls -la vault/Drop/
```

**Solutions:**

| Issue | Solution |
|-------|----------|
| Watcher not running | `pm2 restart file-watcher` |
| Permission denied | Fix folder permissions |
| Invalid file format | Check file extension and content |
| Watchdog killed it | Check watchdog alerts |

### 5. Log Storage Full

**Symptoms:**
- Log size alerts
- Write failures
- Slow log queries

**Diagnosis:**
```bash
# Check log size
python -m src.tasks.log_size_monitor

# List large files
ls -lhS vault/Logs/ | head -20
```

**Solutions:**
```bash
# Run manual maintenance
python -m src.tasks.log_maintenance --compress-now

# Force cleanup
python -m src.tasks.log_maintenance --retention-days 60

# Archive old logs
tar -czvf logs_archive.tar.gz vault/Logs/*.json.gz
```

### 6. Quarantine Issues

**Symptoms:**
- Files moved to Quarantine
- Processing errors

**Diagnosis:**
```bash
# List quarantined files
ls -la vault/Quarantine/

# View quarantine metadata
cat vault/Quarantine/*.quarantine.json
```

**Solutions:**
```bash
# After fixing the file
# Manually move back to Needs_Action
mv vault/Quarantine/file.md vault/Needs_Action/

# Or use skill
python .claude/skills/manage-approval/scripts/main_operation.py restore --file file.md
```

### 7. Graceful Degradation Queue

**Symptoms:**
- Actions queued but not processing
- Queue growing

**Diagnosis:**
```bash
# Check queue status
cat data/action_queue.json | jq '.actions | length'

# View queue stats
python -c "
from src.orchestrator.action_queue import ActionQueue
q = ActionQueue('data/action_queue.json')
print(q.get_stats())
"
```

**Solutions:**
```bash
# Mark service available
python -c "
from src.orchestrator.action_queue import ActionQueue
q = ActionQueue('data/action_queue.json')
q.mark_service_available('odoo')
q.process_pending()
"

# Clear stuck items
python -c "
from src.orchestrator.action_queue import ActionQueue
q = ActionQueue('data/action_queue.json')
q.cleanup_completed(older_than_hours=1)
"
```

## Error Categories Reference

| Category | Retryable | Action |
|----------|-----------|--------|
| TRANSIENT | Yes | Auto-retry with backoff |
| AUTH | No | Pause + alert for re-auth |
| LOGIC | No | Human review required |
| DATA | No | File quarantined |
| SYSTEM | Yes | Watchdog restart |

## Log Locations

| Component | Log Path |
|-----------|----------|
| File Watcher | `logs/file-watcher-*.log` |
| Odoo MCP | `logs/odoo-mcp-*.log` |
| Facebook MCP | `logs/facebook-mcp-*.log` |
| Instagram MCP | `logs/instagram-mcp-*.log` |
| Twitter MCP | `logs/twitter-mcp-*.log` |
| Watchdog | `logs/watchdog-*.log` |
| Ralph Stop Hook | `logs/ralph-wiggum-stop.log` |
| Audit Logs | `vault/Logs/YYYY-MM-DD.json` |

## PM2 Commands Reference

```bash
# Start all
pm2 start ecosystem.config.js

# Restart specific
pm2 restart odoo-mcp

# Stop all
pm2 stop all

# View logs
pm2 logs [process-name]

# Monitor
pm2 monit

# Flush logs
pm2 flush

# Save/resurrect
pm2 save
pm2 resurrect
```

## Getting Help

1. Check this troubleshooting guide
2. Review audit logs in `vault/Logs/`
3. Check alerts in `vault/Alerts/`
4. Review PM2 logs: `pm2 logs`
5. Ask Claude Code with context: `/view-dashboard`
