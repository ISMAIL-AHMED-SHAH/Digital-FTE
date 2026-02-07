# Quickstart Guide: Gold Tier - Autonomous Employee

**Branch**: `003-gold-tier-autonomous` | **Date**: 2026-02-05 | **Plan**: [plan.md](./plan.md)

This guide walks through setting up all Gold Tier integrations: Odoo ERP, Meta Business Suite (Facebook/Instagram), Twitter, and the Ralph Wiggum autonomous loop.

---

## Prerequisites

### System Requirements

- **Bronze Tier**: File Watcher service running
- **Silver Tier**: Gmail and LinkedIn MCP servers configured
- **Python**: 3.13+ with pip
- **Node.js**: 24+ LTS with npm
- **Git**: For version control
- **PM2**: For process management (installed with Silver Tier)

### External Accounts

| Service | Requirement | Sign-up URL |
|---------|-------------|-------------|
| Odoo Community | Self-hosted instance (v19+) or Odoo.sh account | https://www.odoo.com/page/download |
| Meta Business Suite | Business account with Facebook Page | https://business.facebook.com/ |
| Instagram Business | Connected to Facebook Page | Via Facebook Page Settings |
| Twitter Developer | Developer account with API access | https://developer.x.com/ |

---

## 1. Odoo Community Setup

### 1.1 Install Odoo (if self-hosting)

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install postgresql
wget https://nightly.odoo.com/19.0/nightly/deb/odoo_19.0.latest_all.deb
sudo dpkg -i odoo_19.0.latest_all.deb

# Start Odoo
sudo systemctl start odoo
```

**Or use Docker:**
```bash
docker run -d -p 8069:8069 --name odoo \
  -e HOST=db -e USER=odoo -e PASSWORD=odoo \
  --link db:db odoo:19.0
```

### 1.2 Create Odoo Database and Install Modules

1. Navigate to `http://localhost:8069`
2. Create a new database (e.g., `ai_employee`)
3. Install the **Accounting** module from Apps
4. Complete the initial setup wizard

### 1.3 Generate API Key

1. Log into Odoo as an admin user
2. Go to **Settings** → **Users & Companies** → **Users**
3. Click your user → **Preferences** tab
4. Under **Account Security**, click **New API Key**
5. Name it (e.g., "AI Employee") and copy the key

### 1.4 Store Credentials

```bash
# Store API key in OS credential manager
# Windows (PowerShell):
cmdkey /generic:odoo_api_key /user:odoo /pass:YOUR_API_KEY

# macOS:
security add-generic-password -a "odoo" -s "odoo_api_key" -w "YOUR_API_KEY"

# Linux (using secret-tool):
secret-tool store --label="Odoo API Key" service odoo_api_key user odoo
```

### 1.5 Configure Environment

Add to `.env`:
```env
# Odoo Configuration
ODOO_HOST=localhost
ODOO_PORT=8069
ODOO_DATABASE=ai_employee
ODOO_USERNAME=admin
# API key stored in OS credential manager as 'odoo_api_key'
```

### 1.6 Test Connection

```bash
python scripts/setup_odoo_connection.py --test
```

Expected output:
```
✓ Connected to Odoo 19.0
✓ Database: ai_employee
✓ User: admin
✓ Company: Your Company
✓ Latency: 45ms
```

---

## 2. Meta Business Suite Setup (Facebook & Instagram)

### 2.1 Create Meta App

1. Go to [Meta for Developers](https://developers.facebook.com/)
2. Click **My Apps** → **Create App**
3. Select **Business** app type
4. Fill in app details and create

### 2.2 Configure App Permissions

1. In App Dashboard, go to **App Settings** → **Basic**
2. Add Facebook Login product
3. Request the following permissions:
   - `pages_manage_posts`
   - `pages_read_engagement`
   - `instagram_basic`
   - `instagram_content_publishing`

### 2.3 Get Page Access Token

1. Go to [Graph API Explorer](https://developers.facebook.com/tools/explorer/)
2. Select your app
3. Click **Get Token** → **Get Page Access Token**
4. Select permissions and authorize your Facebook Page
5. Copy the resulting access token

**Convert to Long-Lived Token:**
```bash
curl -X GET "https://graph.facebook.com/v22.0/oauth/access_token?grant_type=fb_exchange_token&client_id=YOUR_APP_ID&client_secret=YOUR_APP_SECRET&fb_exchange_token=SHORT_LIVED_TOKEN"
```

### 2.4 Get Instagram Business Account ID

1. In Graph API Explorer, query:
   ```
   GET /me/accounts?fields=instagram_business_account
   ```
2. Note the `instagram_business_account.id` for your Page

### 2.5 Store Credentials

```bash
# Store Meta App Secret
# Windows:
cmdkey /generic:meta_app_secret /user:meta /pass:YOUR_APP_SECRET
cmdkey /generic:fb_page_token_PAGE_ID /user:meta /pass:YOUR_PAGE_TOKEN
cmdkey /generic:ig_access_token_IG_USER_ID /user:meta /pass:YOUR_IG_TOKEN

# macOS:
security add-generic-password -a "meta" -s "meta_app_secret" -w "YOUR_APP_SECRET"
security add-generic-password -a "meta" -s "fb_page_token_PAGE_ID" -w "YOUR_PAGE_TOKEN"
```

### 2.6 Configure Environment

Add to `.env`:
```env
# Meta Business Suite
META_APP_ID=your_app_id
FB_PAGE_ID=your_page_id
IG_USER_ID=your_instagram_business_account_id
# Secrets stored in OS credential manager
```

### 2.7 Test Connections

```bash
# Test Facebook
python scripts/setup_meta_oauth.py --platform facebook --test

# Test Instagram
python scripts/setup_meta_oauth.py --platform instagram --test
```

---

## 3. Twitter API Setup

### 3.1 Create Twitter Developer App

1. Go to [Twitter Developer Portal](https://developer.x.com/en/portal/dashboard)
2. Create a new Project and App
3. Select **Read and Write** permissions
4. Note your API credentials

### 3.2 Generate Access Tokens

1. In App Settings, go to **Keys and tokens**
2. Generate:
   - API Key and Secret
   - Access Token and Secret (with Read/Write permissions)
   - Bearer Token (for read-only operations)

### 3.3 Store Credentials

```bash
# Store Twitter credentials
# Windows:
cmdkey /generic:twitter_api_secret /user:twitter /pass:YOUR_API_SECRET
cmdkey /generic:twitter_access_token_secret /user:twitter /pass:YOUR_ACCESS_TOKEN_SECRET
cmdkey /generic:twitter_bearer_token /user:twitter /pass:YOUR_BEARER_TOKEN

# macOS:
security add-generic-password -a "twitter" -s "twitter_api_secret" -w "YOUR_API_SECRET"
security add-generic-password -a "twitter" -s "twitter_access_token_secret" -w "YOUR_ACCESS_TOKEN_SECRET"
```

### 3.4 Configure Environment

Add to `.env`:
```env
# Twitter API
TWITTER_API_KEY=your_api_key
TWITTER_ACCESS_TOKEN=your_access_token
# Secrets stored in OS credential manager
```

### 3.5 Test Connection

```bash
python scripts/setup_twitter_oauth.py --test
```

Expected output:
```
✓ Authenticated as @your_handle
✓ Rate limit: 100/100 tweets remaining
✓ Account type: Standard
```

---

## 4. Ralph Wiggum Loop Setup

### 4.1 Enable the Stop Hook

Create or update `.claude/settings.local.json`:

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": ".claude/hooks/ralph-wiggum-stop.sh"
          }
        ]
      }
    ]
  }
}
```

### 4.2 Create the Stop Hook Script

Create `.claude/hooks/ralph-wiggum-stop.sh`:

```bash
#!/bin/bash
# Ralph Wiggum Stop Hook
# Exit 0 = Task complete, allow exit
# Exit 2 = Task incomplete, continue loop

# Read hook input (JSON via stdin)
INPUT=$(cat)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id')
TRANSCRIPT=$(echo "$INPUT" | jq -r '.transcript_path')
CWD=$(echo "$INPUT" | jq -r '.cwd')
STOP_ACTIVE=$(echo "$INPUT" | jq -r '.stop_hook_active')

# Prevent recursion
if [ "$STOP_ACTIVE" = "true" ]; then
  exit 0
fi

# Check iteration count
ITER_FILE="/tmp/ralph_${SESSION_ID}_iterations"
if [ -f "$ITER_FILE" ]; then
  ITERATIONS=$(cat "$ITER_FILE")
else
  ITERATIONS=0
fi

# Max iterations guard (default 10)
MAX_ITERATIONS=${RALPH_MAX_ITERATIONS:-10}
if [ "$ITERATIONS" -ge "$MAX_ITERATIONS" ]; then
  echo "Max iterations ($MAX_ITERATIONS) reached"
  rm -f "$ITER_FILE"
  exit 0
fi

# Increment iteration
echo $((ITERATIONS + 1)) > "$ITER_FILE"

# Check for file-based completion (task moved to /Done)
VAULT_PATH="${VAULT_PATH:-$CWD/Vault}"
if [ -f "$VAULT_PATH/Done/current_task.md" ]; then
  echo "Task complete (file moved to Done)"
  rm -f "$ITER_FILE"
  exit 0
fi

# Check for promise-based completion
if grep -q "<promise>TASK_COMPLETE</promise>" "$TRANSCRIPT" 2>/dev/null; then
  echo "Task complete (promise signal)"
  rm -f "$ITER_FILE"
  exit 0
fi

# Task not complete - continue loop
echo "Iteration $((ITERATIONS + 1))/$MAX_ITERATIONS - continuing..."
exit 2
```

Make it executable:
```bash
chmod +x .claude/hooks/ralph-wiggum-stop.sh
```

### 4.3 Configure Ralph Wiggum

Add to `config/gold_tier.yaml`:

```yaml
ralph_wiggum:
  enabled: true
  max_iterations: 10
  timeout_minutes: 30
  completion_strategy: hybrid  # file_based, promise_based, or hybrid
  log_iterations: true
  generate_summary: true
```

### 4.4 Test the Loop

Start Claude Code with a multi-step task:

```bash
claude "Process all files in /Vault/Needs_Action and move completed to /Done"
```

The loop should:
1. Start processing
2. Continue until all files are processed
3. Exit when task file is moved to /Done or promise is emitted

---

## 5. CEO Briefing Setup

### 5.1 Schedule Weekly Briefing

```bash
# Add to crontab (Linux/macOS)
# Run every Sunday at 11 PM
0 23 * * 0 cd /path/to/project && python src/tasks/ceo_briefing.py

# Windows Task Scheduler (PowerShell)
$action = New-ScheduledTaskAction -Execute "python" -Argument "src/tasks/ceo_briefing.py"
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 11PM
Register-ScheduledTask -TaskName "CEO Briefing" -Action $action -Trigger $trigger
```

### 5.2 Configure Briefing

Add to `config/gold_tier.yaml`:

```yaml
ceo_briefing:
  schedule:
    day: Sunday
    time: "23:00"
  output_path: "/Vault/Briefings"
  include:
    - revenue_summary
    - completed_tasks
    - bottlenecks
    - cost_optimization
    - upcoming_deadlines
  odoo_integration: true
  monthly_target: 10000  # Revenue target for percentage calculation
```

### 5.3 Test Manual Generation

```bash
python src/tasks/ceo_briefing.py --manual --period 7d
```

---

## 6. Start Gold Tier Services

### 6.1 Install Dependencies

```bash
# Python dependencies
pip install -r requirements.txt

# Node.js MCP servers
cd src/mcp_servers/odoo && npm install
cd ../facebook && npm install
cd ../instagram && npm install
cd ../twitter && npm install
```

### 6.2 Start MCP Servers with PM2

```bash
# Start all Gold Tier MCP servers
pm2 start ecosystem.config.js --only odoo-mcp,facebook-mcp,instagram-mcp,twitter-mcp

# Verify status
pm2 status
```

### 6.3 Update Claude Settings

The MCP servers should be registered in `.claude/settings.local.json`:

```json
{
  "mcpServers": {
    "odoo": {
      "command": "node",
      "args": ["src/mcp_servers/odoo/index.js"],
      "env": {
        "ODOO_HOST": "${ODOO_HOST}",
        "ODOO_PORT": "${ODOO_PORT}",
        "ODOO_DATABASE": "${ODOO_DATABASE}",
        "ODOO_USERNAME": "${ODOO_USERNAME}"
      }
    },
    "facebook": {
      "command": "node",
      "args": ["src/mcp_servers/facebook/index.js"],
      "env": {
        "META_APP_ID": "${META_APP_ID}",
        "FB_PAGE_ID": "${FB_PAGE_ID}"
      }
    },
    "instagram": {
      "command": "node",
      "args": ["src/mcp_servers/instagram/index.js"],
      "env": {
        "META_APP_ID": "${META_APP_ID}",
        "IG_USER_ID": "${IG_USER_ID}"
      }
    },
    "twitter": {
      "command": "node",
      "args": ["src/mcp_servers/twitter/index.js"],
      "env": {
        "TWITTER_API_KEY": "${TWITTER_API_KEY}",
        "TWITTER_ACCESS_TOKEN": "${TWITTER_ACCESS_TOKEN}"
      }
    }
  }
}
```

---

## 7. End-to-End Verification

### 7.1 Test Odoo Invoice Creation

```
You: Create a draft invoice for customer "Acme Corp" for $500 consulting services

Expected: Claude uses create_invoice tool, creates draft in Odoo, generates approval file
```

### 7.2 Test Social Posting

```
You: Post "Hello from AI Employee! 🤖" to Twitter

Expected: Claude uses post_tweet tool, creates pending approval in vault
```

### 7.3 Test CEO Briefing

```
You: Generate a CEO briefing for the past 7 days

Expected: Claude queries Odoo for financials, compiles task data, generates briefing markdown
```

### 7.4 Test Ralph Wiggum Loop

```
You: Process all pending approvals in /Needs_Approval until complete

Expected: Claude starts loop, processes each file, exits when folder is empty
```

---

## Troubleshooting

### Odoo Connection Issues

| Symptom | Cause | Solution |
|---------|-------|----------|
| Connection refused | Odoo not running | `systemctl start odoo` |
| Authentication failed | Wrong API key | Regenerate key in Odoo |
| Timeout | Network/firewall | Check port 8069 access |

### Meta API Issues

| Symptom | Cause | Solution |
|---------|-------|----------|
| Token expired | >60 day token | Run `refresh_token` tool |
| Permission denied | Missing scope | Reauthorize with required permissions |
| Rate limited | Too many requests | Wait for cooldown period |

### Twitter API Issues

| Symptom | Cause | Solution |
|---------|-------|----------|
| 401 Unauthorized | Bad OAuth signature | Regenerate access tokens |
| 429 Too Many Requests | Rate limited | Check `get_rate_limit_status` |
| Duplicate status | Identical tweet | Modify tweet text |

### Ralph Wiggum Loop Issues

| Symptom | Cause | Solution |
|---------|-------|----------|
| Loop never exits | No completion signal | Check task file location |
| Exits immediately | `stop_hook_active=true` | Check hook recursion |
| Max iterations reached | Task too complex | Increase `RALPH_MAX_ITERATIONS` |

---

## Next Steps

1. **Review approval workflow**: Test the HITL approval process for invoices and posts
2. **Configure rate limits**: Adjust daily limits in `config/gold_tier.yaml`
3. **Set up monitoring**: Configure alerting thresholds for service health
4. **Schedule CEO Briefing**: Verify cron/task scheduler is running
5. **Run `/sp.tasks`**: Generate implementation tasks for remaining features

---

*Generated by AI Employee Specification System | Gold Tier v0.3*
