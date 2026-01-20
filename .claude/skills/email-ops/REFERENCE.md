# Email Ops Reference

Detailed documentation for the email-ops skill in production deployment.

## Production Architecture

### MCP Email Server
The email operations are provided by the **mcp-email** MCP server, which runs as a separate PM2 process:
- **Process Name**: mcp-email
- **Script**: src/mcp/email_server.py
- **Framework**: FastMCP
- **Protocol**: Model Context Protocol (MCP)

The email server provides capabilities for sending emails and checking sent items via the MCP protocol.

### PM2 Configuration

The email server is configured in `ecosystem.config.js`:
```javascript
{
  name: "mcp-email",
  script: "./run-mcp-email.sh",  // Wrapper script
  interpreter: "bash",            // Uses bash to activate venv
  instances: 1,
  autorestart: true,
  max_memory_restart: "100M",
  env: {
    PYTHONUNBUFFERED: "1",
    DRY_RUN: "false"
  }
}
```

### Wrapper Script Pattern

The email server uses a wrapper script (`run-mcp-email.sh`) to activate the virtual environment:
```bash
#!/bin/bash
cd "/mnt/c/Users/kk/Desktop/Daniel's FTE"
source venv/bin/activate
export PYTHONPATH="/mnt/c/Users/kk/Desktop/Daniel's FTE"
exec python3 src/mcp/email_server.py
```

## Configuration Options

### Environment Variables (.env)
- `REQUIRE_EMAIL_APPROVAL`: Force approval for all emails (default: true)
- `DRY_RUN`: Enable dry-run mode (emails logged but not sent) (default: false)
- `GMAIL_CREDENTIALS_PATH`: Path to Gmail OAuth credentials (default: credentials.json)
- `GMAIL_TOKEN_PATH`: Path to Gmail access token (default: gmail_token.json)

### Email Server Capabilities
The MCP email server exposes these capabilities:
- `send_email(to, subject, body, attachments)`: Send email via Gmail
- `read_sent_emails(limit)`: Retrieve recent sent emails

## Advanced Usage

### Scenario 1: Sending Email with Approval
When `REQUIRE_EMAIL_APPROVAL=true`, emails require human approval:
1. Email request creates approval file in `Pending_Approval/`
2. Human reviews and moves to `Approved/`
3. Orchestrator detects approval and calls MCP server
4. Email sent and logged to audit trail

### Scenario 2: Dry-Run Mode
For testing without sending real emails:
```bash
# Edit .env
DRY_RUN=true

# Restart email server
pm2 restart mcp-email
```

All email operations will be logged but not executed.

### Scenario 3: Gmail OAuth Setup
To enable Gmail sending:
1. Create project in Google Cloud Console
2. Enable Gmail API
3. Create OAuth2 credentials (Desktop app)
4. Download as `credentials.json` to project root
5. Run authentication:
```bash
cd "/mnt/c/Users/kk/Desktop/Daniel's FTE"
source venv/bin/activate
python3 -c "
from src.watchers.gmail import GmailWatcher
w = GmailWatcher()
w._authenticate()
"
```
6. Restart email server: `pm2 restart mcp-email`

## Troubleshooting

### Issue: Email Server Keeps Restarting
**Symptoms**: PM2 shows high restart count for mcp-email
**Solution**:
```bash
# Check error logs
pm2 logs mcp-email --err --lines 50

# Common causes:
# 1. Missing fastmcp package - pip install fastmcp mcp
# 2. Missing Gmail credentials - check credentials.json exists
# 3. Import errors - check PYTHONPATH in wrapper script
```

### Issue: Emails Not Sending
**Symptoms**: Approval processed but email not sent
**Solution**:
```bash
# Check email server logs
pm2 logs mcp-email --lines 50

# Verify Gmail authentication
ls -la credentials.json gmail_token.json

# Check if dry-run mode is enabled
grep DRY_RUN .env

# Check audit logs for errors
cat AI_Employee_Vault/Logs/$(date +%Y-%m-%d).json | python3 -m json.tool | grep -i email
```

### Issue: OAuth Token Expired
**Symptoms**: "Token has been expired or revoked" error
**Solution**:
```bash
# Delete old token
rm gmail_token.json

# Re-authenticate
source venv/bin/activate
python3 -c "
from src.watchers.gmail import GmailWatcher
w = GmailWatcher()
w._authenticate()
"

# Restart email server
pm2 restart mcp-email
```

### Issue: ModuleNotFoundError for fastmcp
**Symptoms**: "ModuleNotFoundError: No module named 'fastmcp'"
**Solution**:
```bash
# Activate venv and install
source venv/bin/activate
pip install fastmcp mcp

# Restart email server
pm2 restart mcp-email
```

## Examples

### Example 1: Check Email Server Status
```bash
# Check PM2 status
pm2 status mcp-email

# Check server logs
pm2 logs mcp-email --lines 50

# Verify server is responding
# (MCP servers don't have HTTP endpoints, check logs for startup messages)
```

### Example 2: Send Email via Approval Workflow
```bash
# Create action file
cat > AI_Employee_Vault/Needs_Action/send_email.md << 'EOF'
---
id: "email_001"
type: "email"
source: "manual"
priority: "high"
timestamp: "2026-01-15T12:00:00Z"
status: "pending"
---

# Send Email

Send email to client@example.com with subject "Project Update" and body "The project is on track."
EOF

# Wait for approval request (10 seconds)
sleep 10

# Check pending approvals
ls AI_Employee_Vault/Pending_Approval/

# Approve
mv AI_Employee_Vault/Pending_Approval/*.md AI_Employee_Vault/Approved/

# Wait for execution (5 seconds)
sleep 5

# Check audit log
cat AI_Employee_Vault/Logs/$(date +%Y-%m-%d).json | python3 -m json.tool | tail -20
```

### Example 3: Test Dry-Run Mode
```bash
# Enable dry-run
echo "DRY_RUN=true" >> .env

# Restart email server
pm2 restart mcp-email

# Create test email action
# (same as Example 2)

# Check logs - email logged but not sent
pm2 logs mcp-email --lines 20
```

## Related Documentation

- **PRODUCTION_GUIDE.md**: Complete production deployment guide
- **ARCHITECTURE.md**: Technical architecture details
- **src/mcp/email_server.py**: Email server implementation
- **ecosystem.config.js**: PM2 configuration file
