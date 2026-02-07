# AI Employee - Silver Tier

An intelligent automation system that monitors external communication channels (Gmail, WhatsApp), creates action files for human-in-the-loop approval, and executes approved actions via MCP servers.

## Features

### Bronze Tier (Completed)
- Local file watcher for vault folder monitoring
- Basic approval workflow structure

### Silver Tier (Current)
- **Gmail Integration**: Monitor inbox for keyword-filtered emails, create action files
- **WhatsApp Webhook**: Receive WhatsApp Business API messages via webhook
- **LinkedIn MCP Server**: Post approved content to LinkedIn
- **Human-in-the-Loop Approval**: Integrity-verified approval workflow
- **Scheduled Tasks**: Daily briefings and automated maintenance
- **Resource Monitoring**: Graceful degradation under memory pressure

## Architecture

```
                    ┌─────────────────────────────────────────┐
                    │           External Services             │
                    │  Gmail API  │  WhatsApp  │  LinkedIn    │
                    └──────┬──────────┬───────────┬───────────┘
                           │          │           │
                           ▼          ▼           ▼
┌──────────────────────────────────────────────────────────────┐
│                      Watchers Layer                          │
│  ┌─────────────┐  ┌────────────────┐  ┌──────────────────┐  │
│  │Gmail Watcher│  │WhatsApp Webhook│  │ Resource Monitor │  │
│  │  (Polling)  │  │   (HTTP/8000)  │  │  (60s interval)  │  │
│  └──────┬──────┘  └───────┬────────┘  └────────┬─────────┘  │
└─────────┼─────────────────┼────────────────────┼────────────┘
          │                 │                    │
          ▼                 ▼                    ▼
┌──────────────────────────────────────────────────────────────┐
│                    Vault (File-Based)                        │
│  /Needs_Action  →  /Pending_Approval  →  /Approved  →  /Done │
└──────────────────────────────────────────────────────────────┘
          │
          ▼
┌──────────────────────────────────────────────────────────────┐
│                      MCP Servers                             │
│  ┌─────────────┐           ┌──────────────┐                 │
│  │ Gmail MCP   │           │ LinkedIn MCP │                 │
│  │ send_email  │           │ create_post  │                 │
│  └─────────────┘           └──────────────┘                 │
└──────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- PM2 (`npm install -g pm2`)
- SQLite3

### Installation

```bash
# Clone repository
git clone <repository-url>
cd Hackathon-0

# Install Python dependencies
pip install -r requirements.txt

# Build MCP servers
cd src/mcp_servers/gmail && npm install && npm run build
cd ../linkedin && npm install && npm run build
```

### Configuration

1. **Copy environment template**:
   ```bash
   cp .env.example .env
   ```

2. **Configure Gmail OAuth** (optional for testing):
   ```bash
   python scripts/setup_gmail_oauth.py
   ```

3. **Configure WhatsApp** (optional):
   ```bash
   python scripts/setup_whatsapp.py
   ```

4. **Start watchers**:
   ```bash
   pm2 start config/pm2.config.js
   ```

For detailed setup, see [Quick Start Guide](specs/002-external-connectivity/quickstart.md).

## Usage

### Claude Skills

Use these skills via Claude to interact with the system:

| Skill | Command | Description |
|-------|---------|-------------|
| email-ops | `/email-ops --action send` | Send emails via Gmail |
| social-ops | `/social-ops --action post` | Post to LinkedIn |
| manage-approval | `/manage-approval --action list` | Manage approval queue |
| watcher-manager | `/watcher-manager --action status` | Monitor watcher processes |

### CLI Scripts

```bash
# Check watcher status
python .claude/skills/watcher-manager/scripts/main_operation.py --action status

# List pending approvals
python .claude/skills/manage-approval/scripts/main_operation.py --action list

# Run E2E tests (dry-run)
DRY_RUN=true ./scripts/test_e2e.sh
```

## Project Structure

```
Hackathon-0/
├── src/
│   ├── common/             # Shared utilities
│   │   ├── vault.py        # Vault file operations
│   │   ├── idempotency.py  # SQLite idempotency DB
│   │   ├── integrity.py    # SHA-256 hash validation
│   │   └── audit_logger.py # JSON-lines audit logs
│   ├── watchers/           # External service monitors
│   │   ├── base_watcher.py # Abstract watcher base
│   │   ├── gmail_watcher.py
│   │   ├── whatsapp_webhook.py
│   │   ├── resource_monitor.py
│   │   └── scheduler.py
│   ├── mcp_servers/        # MCP tool servers
│   │   ├── gmail/          # Gmail send_email tool
│   │   └── linkedin/       # LinkedIn create_post tool
│   └── tasks/              # Scheduled task implementations
│       └── daily_briefing.py
├── config/
│   ├── pm2.config.js       # PM2 ecosystem config
│   └── watcher_config.yaml # Watcher settings
├── specs/
│   └── 002-external-connectivity/
│       ├── spec.md         # Feature specification
│       ├── plan.md         # Architecture decisions
│       ├── tasks.md        # Implementation tasks
│       ├── quickstart.md   # Setup guide
│       ├── research.md     # Technical research
│       └── data-model.md   # Pydantic models
├── scripts/
│   ├── setup_gmail_oauth.py
│   ├── setup_whatsapp.py
│   ├── test_e2e.sh
│   └── test_e2e.ps1
└── .claude/skills/         # Claude skills
```

## Configuration Reference

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `VAULT_PATH` | Path to Obsidian vault | `./AI_Employee_Vault` |
| `DRY_RUN` | Enable dry-run mode | `false` |
| `GMAIL_ACCESS_TOKEN` | Gmail OAuth access token | - |
| `LINKEDIN_ACCESS_TOKEN` | LinkedIn OAuth access token | - |
| `WHATSAPP_VERIFY_TOKEN` | WhatsApp webhook verify token | - |
| `WHATSAPP_APP_SECRET` | WhatsApp app secret for HMAC | - |

### Rate Limits

| Service | Limit | Period |
|---------|-------|--------|
| Gmail (send) | 50 emails | per day |
| LinkedIn (post) | 10 posts | per day |
| WhatsApp (webhook) | 100 requests | per minute |

### Memory Budgets

| Process | Budget | Priority |
|---------|--------|----------|
| Gmail Watcher | 100 MB | 1 (High) |
| WhatsApp Webhook | 100 MB | 2 (Medium) |
| LinkedIn MCP | 100 MB | 3 (Low) |
| Resource Monitor | 50 MB | 0 (Critical) |
| **Total** | **500 MB** | - |

## Runbooks

### Watcher Not Starting

```bash
# Check PM2 status
pm2 status

# View error logs
pm2 logs gmail-watcher --err --lines 50

# Restart specific watcher
pm2 restart gmail-watcher
```

### Memory Pressure

The resource monitor automatically pauses watchers when memory exceeds 500MB:
1. LinkedIn (priority 3) paused first
2. WhatsApp (priority 2) paused second
3. Gmail (priority 1) paused last

Recovery occurs automatically when usage drops below 350MB.

### Approval Stuck

```bash
# List pending approvals
python .claude/skills/manage-approval/scripts/main_operation.py --action list

# Verify integrity of specific file
python .claude/skills/manage-approval/scripts/main_operation.py --action verify --id <file-id>
```

## Testing

```bash
# Run E2E tests in dry-run mode
DRY_RUN=true ./scripts/test_e2e.sh

# Windows PowerShell
$env:DRY_RUN="true"; .\scripts\test_e2e.ps1

# Run Python unit tests
pytest tests/
```

## Documentation

- [Quick Start Guide](specs/002-external-connectivity/quickstart.md)
- [Feature Specification](specs/002-external-connectivity/spec.md)
- [Architecture Plan](specs/002-external-connectivity/plan.md)
- [Technical Research](specs/002-external-connectivity/research.md)
- [Data Models](specs/002-external-connectivity/data-model.md)

## License

MIT License - See LICENSE file for details.
