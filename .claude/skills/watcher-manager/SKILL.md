---
name: watcher-manager
description: "WHAT: Manage watcher processes (start, stop, restart, status) using PM2 for AI Employee input detection. WHEN: User says 'start watcher', 'stop watcher', 'check watcher status', 'restart watcher'. Trigger on: watcher management, process control, monitoring."
---

# Watcher Manager

## Production Architecture Note

In the production deployment, all watchers (Gmail, WhatsApp, LinkedIn) run as threads inside the **ai-orchestrator** process. There are no separate watcher processes. The orchestrator manages all watchers internally.

## When to Use
- Starting the orchestrator (which starts all watchers)
- Stopping the orchestrator for maintenance
- Checking if the orchestrator and watchers are running
- Restarting the orchestrator after configuration changes

## Instructions

### Check Status
```bash
pm2 status
```
Look for `ai-orchestrator` process status (should be "online").

### Start Orchestrator (starts all watchers)
```bash
pm2 start ecosystem.config.js
```

### Stop Orchestrator (stops all watchers)
```bash
pm2 stop ai-orchestrator
```

### Restart Orchestrator (restarts all watchers)
```bash
pm2 restart ai-orchestrator
```

### View Orchestrator Logs
```bash
pm2 logs ai-orchestrator --lines 50
```

### Check Watcher Status in Dashboard
```bash
cat AI_Employee_Vault/Dashboard.md
```

## Validation
- [ ] ai-orchestrator process shows "online" in PM2
- [ ] Dashboard.md shows watchers as "running"
- [ ] No errors in orchestrator logs
- [ ] Orchestrator uptime is stable (not restarting repeatedly)

## Troubleshooting

If orchestrator is crashing:
```bash
# Check error logs
pm2 logs ai-orchestrator --err --lines 50

# Restart fresh
pm2 restart ai-orchestrator

# If still failing, see SETUP_TROUBLESHOOTING.md
```

See [REFERENCE.md](./REFERENCE.md) for PM2 configuration and detailed troubleshooting.
