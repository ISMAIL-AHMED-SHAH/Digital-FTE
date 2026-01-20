# Watcher Manager Reference

Detailed documentation for the watcher-manager skill in production deployment.

## Production Architecture

### Orchestrator Process
The **ai-orchestrator** is a single PM2 process that manages all watchers as internal threads:
- **GmailWatcher**: Monitors Gmail for important/urgent emails
- **WhatsAppWatcher**: Monitors WhatsApp Web for new messages
- **LinkedInWatcher**: Monitors LinkedIn for messages/notifications

All watchers run concurrently within the orchestrator process. There are no separate watcher processes.

### PM2 Configuration

The orchestrator is configured in `ecosystem.config.js`:
```javascript
{
  name: "ai-orchestrator",
  script: "./run-orchestrator.sh",  // Wrapper script
  interpreter: "bash",               // Uses bash to activate venv
  instances: 1,
  autorestart: true,
  max_memory_restart: "200M",
  env: {
    PYTHONUNBUFFERED: "1",
    DRY_RUN: "false"
  }
}
```

### Wrapper Script Pattern

The orchestrator uses a wrapper script (`run-orchestrator.sh`) to activate the virtual environment:
```bash
#!/bin/bash
cd "/mnt/c/Users/kk/Desktop/Daniel's FTE"
source venv/bin/activate
export PYTHONPATH="/mnt/c/Users/kk/Desktop/Daniel's FTE"
exec python3 src/orchestration/orchestrator.py
```

This pattern ensures PM2 uses the virtual environment's Python packages instead of system Python.

## Configuration Options

### Environment Variables (.env)
- `GMAIL_INTERVAL`: Gmail check frequency in seconds (default: 60)
- `WHATSAPP_INTERVAL`: WhatsApp check frequency in seconds (default: 60)
- `LINKEDIN_INTERVAL`: LinkedIn check frequency in seconds (default: 300)
- `ORCHESTRATOR_POLL_INTERVAL`: Action file polling frequency (default: 5)
- `HEALTH_CHECK_INTERVAL`: Health check frequency (default: 60)
- `DASHBOARD_UPDATE_INTERVAL`: Dashboard update frequency (default: 30)
- `DRY_RUN`: Enable dry-run mode (default: false)

### Watcher Configuration

Each watcher can be configured via environment variables or by modifying the orchestrator initialization code in `src/orchestration/orchestrator.py`.

## Advanced Usage

### Scenario 1: Adjusting Watcher Intervals

Edit `.env` file:
```bash
# Check Gmail more frequently
GMAIL_INTERVAL=30

# Check WhatsApp less frequently
WHATSAPP_INTERVAL=120
```

Then restart orchestrator:
```bash
pm2 restart ai-orchestrator
```

### Scenario 2: Disabling Specific Watchers

To disable a watcher, modify `src/orchestration/orchestrator.py` to comment out the watcher initialization, then restart.

### Scenario 3: Monitoring Watcher Health

Check Dashboard.md for watcher status:
```bash
cat AI_Employee_Vault/Dashboard.md
```

Check orchestrator logs for watcher activity:
```bash
pm2 logs ai-orchestrator --lines 100 | grep -i watcher
```

## Troubleshooting

### Issue: Orchestrator Keeps Restarting
**Symptoms**: PM2 shows high restart count, orchestrator status flips between online/stopped
**Solution**:
```bash
# Check error logs
pm2 logs ai-orchestrator --err --lines 50

# Common causes:
# 1. Missing dependencies - reinstall in venv
# 2. Code errors - check logs for Python tracebacks
# 3. Missing credentials - check for credentials.json, token files
# 4. Path issues - verify PYTHONPATH in wrapper script
```

### Issue: Watchers Not Detecting New Items
**Symptoms**: New emails/messages not creating action files
**Solution**:
```bash
# Check if watcher is running
cat AI_Employee_Vault/Dashboard.md

# Check watcher logs
pm2 logs ai-orchestrator --lines 100 | grep -i "check_for_updates"

# Verify credentials
# Gmail: Check credentials.json and gmail_token.json exist
# WhatsApp: Check whatsapp_session/ directory exists
```

### Issue: ModuleNotFoundError
**Symptoms**: Orchestrator crashes with "ModuleNotFoundError: No module named 'X'"
**Solution**:
```bash
# Activate venv and install missing dependency
source venv/bin/activate
pip install [missing-package]

# Restart orchestrator
pm2 restart ai-orchestrator
```

### Issue: High Memory Usage
**Symptoms**: Orchestrator using >200MB RAM, PM2 auto-restarting
**Solution**:
```bash
# Increase memory limit in ecosystem.config.js
# Change max_memory_restart to "300M" or higher

# Restart with new config
pm2 delete ai-orchestrator
pm2 start ecosystem.config.js
```

## Examples

### Example 1: Check System Status
```bash
# Check PM2 status
pm2 status

# Check orchestrator logs
pm2 logs ai-orchestrator --lines 50

# Check dashboard
cat AI_Employee_Vault/Dashboard.md
```

### Example 2: Restart After Configuration Change
```bash
# Edit configuration
nano .env

# Restart orchestrator
pm2 restart ai-orchestrator

# Verify restart successful
pm2 status
pm2 logs ai-orchestrator --lines 20
```

### Example 3: Debug Watcher Issues
```bash
# Check watcher initialization
pm2 logs ai-orchestrator --lines 200 | grep -i "watcher"

# Check for errors
pm2 logs ai-orchestrator --err --lines 50

# Check audit logs
cat AI_Employee_Vault/Logs/$(date +%Y-%m-%d).json | python3 -m json.tool | grep -i watcher
```

## Related Documentation

- **PRODUCTION_GUIDE.md**: Complete production deployment guide
- **SETUP_TROUBLESHOOTING.md**: Common issues and solutions
- **ARCHITECTURE.md**: Technical architecture details
- **ecosystem.config.js**: PM2 configuration file
