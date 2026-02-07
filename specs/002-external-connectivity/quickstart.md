# AI Employee Silver Tier - Quick Start Guide

This guide covers setting up and running the AI Employee Silver Tier external connectivity features.

## Prerequisites

- Python 3.10+
- Node.js 22+
- PM2 (for process management): `npm install -g pm2`
- An Obsidian vault for the file-based workflow

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd ai-employee

# Install Python dependencies
pip install -r requirements.txt

# Install Node.js dependencies for MCP servers
cd src/mcp_servers/gmail && npm install && cd ../../..
cd src/mcp_servers/linkedin && npm install && cd ../../..

# Initialize the vault structure
python -c "from src.common.vault import initialize_vault; initialize_vault('path/to/vault')"
```

## Environment Setup

Create a `.env` file in the project root:

```bash
# Vault Configuration
VAULT_PATH=/path/to/your/obsidian/vault

# Gmail OAuth (run scripts/setup_gmail_oauth.py to obtain)
GMAIL_CLIENT_ID=your_client_id
GMAIL_CLIENT_SECRET=your_client_secret

# WhatsApp Business API
WHATSAPP_VERIFY_TOKEN=your_verify_token
WHATSAPP_APP_SECRET=your_app_secret
WEBHOOK_HOST=0.0.0.0
WEBHOOK_PORT=8000

# LinkedIn OAuth
LINKEDIN_CLIENT_ID=your_client_id
LINKEDIN_CLIENT_SECRET=your_client_secret

# Optional
DRY_RUN=false
LOG_LEVEL=INFO
```

---

## Gmail Setup

### 1. Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project
3. Enable the Gmail API
4. Create OAuth 2.0 credentials (Desktop application)
5. Download the credentials JSON

### 2. Run OAuth Setup

```bash
# Using credentials file
python scripts/setup_gmail_oauth.py --credentials-file path/to/credentials.json

# Or set environment variables first
export GMAIL_CLIENT_ID=your_client_id
export GMAIL_CLIENT_SECRET=your_client_secret
python scripts/setup_gmail_oauth.py
```

### 3. Test Gmail Watcher

```bash
python -m src.watchers.gmail_watcher
```

---

## WhatsApp Setup

### 1. Configure Meta Business API

1. Go to [Meta for Developers](https://developers.facebook.com)
2. Create or select your WhatsApp Business app
3. Navigate to WhatsApp > Configuration

### 2. Generate Verification Token

```bash
python scripts/setup_whatsapp.py --generate-token
```

### 3. Configure Webhook

1. Start the webhook server:
   ```bash
   uvicorn src.watchers.whatsapp_webhook:app --host 0.0.0.0 --port 8000
   ```

2. For local development, expose via ngrok:
   ```bash
   ngrok http 8000
   ```

3. In Meta Developer Console:
   - Callback URL: `https://your-ngrok-url/webhooks/whatsapp`
   - Verify Token: (from step 2)
   - Subscribe to `messages` webhook field

### 4. Configure App Secret

Copy App Secret from Meta Developer Console > Settings > Basic, then add to `.env`:

```bash
WHATSAPP_APP_SECRET=your_app_secret
```

---

## LinkedIn Setup

### 1. Create LinkedIn App

1. Go to [LinkedIn Developers](https://www.linkedin.com/developers/apps)
2. Create a new app
3. Add your company's LinkedIn Page
4. Request access to:
   - Sign In with LinkedIn using OpenID Connect
   - Share on LinkedIn (w_member_social)

### 2. Configure OAuth

Store your LinkedIn credentials in the OS credential manager:

```bash
# The credentials will be stored when you first authenticate
# You can use keytar CLI or a simple Python script
```

### 3. Test LinkedIn MCP

```bash
npx tsx src/mcp_servers/linkedin/src/index.ts
```

---

## Scheduled Tasks

The scheduler runs automated tasks like daily briefings.

### Configure Scheduler

The scheduler configuration is in `config/scheduler_config.yaml`:

```yaml
tasks:
  daily_briefing:
    module: src.tasks.daily_briefing
    function: run
    schedule: "0 8 * * *"  # 8am daily
    description: Generate daily briefing document
    enabled: true
```

### Manual Task Execution

```bash
# List available tasks
python -m src.watchers.scheduler --list

# Run a specific task
python -m src.watchers.scheduler --task daily_briefing

# Dry-run mode
python -m src.watchers.scheduler --task daily_briefing --dry-run
```

### Set Up Automatic Scheduling

#### macOS/Linux (cron)

```bash
# Add scheduled tasks to crontab
./scripts/setup_cron.sh

# List current tasks
./scripts/setup_cron.sh --list

# Remove tasks
./scripts/setup_cron.sh --remove
```

#### Windows (Task Scheduler)

```powershell
# Add scheduled tasks (run as Administrator)
.\scripts\setup_scheduler.ps1

# List current tasks
.\scripts\setup_scheduler.ps1 -List

# Remove tasks
.\scripts\setup_scheduler.ps1 -Remove
```

### Scheduled Tasks Created

| Task | Schedule | Description |
|------|----------|-------------|
| Daily Briefing | 8:00 AM daily | Generates summary in `/Vault/Briefings/` |
| Weekly Cleanup | 2:00 AM Sundays | Removes expired idempotency records |

---

## Process Management with PM2

PM2 manages all watcher processes for reliable operation.

### Start All Watchers

```bash
# Start all configured watchers
pm2 start config/pm2.config.js

# Start specific watcher
pm2 start config/pm2.config.js --only gmail-watcher
```

### Monitor Processes

```bash
# View logs
pm2 logs

# Real-time monitoring
pm2 monit

# Process status
pm2 status
```

### Stop/Restart

```bash
# Stop all
pm2 stop all

# Restart specific process
pm2 restart gmail-watcher

# Delete all (removes from PM2)
pm2 delete all
```

### Save Configuration

```bash
# Save current process list
pm2 save

# Set up startup script (auto-start on boot)
pm2 startup
```

---

## Testing

### Run All Tests

```bash
pytest tests/ -v
```

### Test Specific Components

```bash
# Test Gmail watcher
pytest tests/unit/test_gmail_watcher.py -v

# Test WhatsApp webhook
pytest tests/unit/test_whatsapp_webhook.py -v

# Test approval workflow
pytest tests/integration/test_approval_workflow.py -v
```

### Dry-Run Mode

All components support dry-run mode for testing without side effects:

```bash
# Set environment variable
export DRY_RUN=true

# Or pass as parameter
python -m src.watchers.gmail_watcher --dry-run
python -m src.watchers.scheduler --task daily_briefing --dry-run
```

---

## Troubleshooting

### Gmail Authentication Fails

1. Verify credentials: `python scripts/setup_gmail_oauth.py --test`
2. Re-authenticate: `python scripts/setup_gmail_oauth.py --force`

### WhatsApp Webhook Not Receiving Messages

1. Check webhook is running: `curl http://localhost:8000/health`
2. Verify ngrok tunnel is active
3. Check signature validation: `python scripts/setup_whatsapp.py --test-signature`

### Scheduled Tasks Not Running

1. Check scheduler config: `python -m src.watchers.scheduler --list`
2. Run task manually: `python -m src.watchers.scheduler --task daily_briefing`
3. Check cron/Task Scheduler logs

### Memory Issues

1. Check resource monitor: `pm2 logs resource-monitor`
2. View current usage: `pm2 monit`
3. Adjust limits in `config/pm2.config.js`

---

## File Structure

```
/Vault/
├── Needs_Action/       # Incoming items from watchers
├── Pending_Approval/   # Items awaiting human approval
├── Approved/          # Approved items ready for execution
├── Rejected/          # Items rejected by user
├── Expired/           # Items that timed out
├── Done/              # Completed items (archive)
├── Logs/              # Audit logs (JSON-lines)
├── Alerts/            # System alerts
└── Briefings/         # Generated briefing documents
```

---

## Support

- Check logs: `pm2 logs` or `logs/` directory
- Review audit trail: `/Vault/Logs/YYYY-MM-DD.json`
- File issues at: [GitHub Issues](https://github.com/your-org/ai-employee/issues)
