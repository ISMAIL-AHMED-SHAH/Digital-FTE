# Social Ops Reference

Detailed documentation for the social-ops skill in production deployment.

## Production Architecture

### MCP Social Server
The social media operations are provided by the **mcp-social** MCP server, which runs as a separate PM2 process:
- **Process Name**: mcp-social
- **Script**: src/mcp/social_server.py
- **Framework**: FastMCP
- **Protocol**: Model Context Protocol (MCP)

The social server provides capabilities for posting to LinkedIn and checking post status via the MCP protocol.

### PM2 Configuration

The social server is configured in `ecosystem.config.js`:
```javascript
{
  name: "mcp-social",
  script: "./run-mcp-social.sh",  // Wrapper script
  interpreter: "bash",             // Uses bash to activate venv
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

The social server uses a wrapper script (`run-mcp-social.sh`) to activate the virtual environment:
```bash
#!/bin/bash
cd "/mnt/c/Users/kk/Desktop/Daniel's FTE"
source venv/bin/activate
export PYTHONPATH="/mnt/c/Users/kk/Desktop/Daniel's FTE"
exec python3 src/mcp/social_server.py
```

## Configuration Options

### Environment Variables (.env)
- `REQUIRE_SOCIAL_APPROVAL`: Force approval for all social posts (default: true)
- `DRY_RUN`: Enable dry-run mode (posts logged but not published) (default: false)
- `LINKEDIN_ACCESS_TOKEN`: LinkedIn API access token (optional, for future integration)

### Social Server Capabilities
The MCP social server exposes these capabilities:
- `post_to_linkedin(content, schedule)`: Post content to LinkedIn
- `check_post_status(post_id)`: Check status of a scheduled post

## Advanced Usage

### Scenario 1: Posting to LinkedIn with Approval
When `REQUIRE_SOCIAL_APPROVAL=true`, posts require human approval:
1. Post request creates approval file in `Pending_Approval/`
2. Human reviews and moves to `Approved/`
3. Orchestrator detects approval and calls MCP server
4. Post published and logged to audit trail

### Scenario 2: Dry-Run Mode
For testing without publishing real posts:
```bash
# Edit .env
DRY_RUN=true

# Restart social server
pm2 restart mcp-social
```

All social media operations will be logged but not executed.

### Scenario 3: Scheduled Posting
Posts can be scheduled for future publication:
```bash
# Create action file with schedule
cat > AI_Employee_Vault/Needs_Action/linkedin_post.md << 'EOF'
---
id: "social_001"
type: "social"
source: "manual"
priority: "normal"
timestamp: "2026-01-15T12:00:00Z"
status: "pending"
metadata:
  platform: "linkedin"
  schedule: "2026-01-16T09:00:00Z"
---

# LinkedIn Post

Post this content: "Excited to share our latest project update! #AI #Automation"
EOF
```

## Troubleshooting

### Issue: Social Server Keeps Restarting
**Symptoms**: PM2 shows high restart count for mcp-social
**Solution**:
```bash
# Check error logs
pm2 logs mcp-social --err --lines 50

# Common causes:
# 1. Missing fastmcp package - pip install fastmcp mcp
# 2. Import errors - check PYTHONPATH in wrapper script
# 3. Configuration errors - check .env file
```

### Issue: Posts Not Publishing
**Symptoms**: Approval processed but post not published
**Solution**:
```bash
# Check social server logs
pm2 logs mcp-social --lines 50

# Check if dry-run mode is enabled
grep DRY_RUN .env

# Check audit logs for errors
cat AI_Employee_Vault/Logs/$(date +%Y-%m-%d).json | python3 -m json.tool | grep -i social
```

### Issue: LinkedIn API Authentication
**Symptoms**: "Authentication failed" or "Invalid token" errors
**Solution**:
```bash
# LinkedIn API integration is optional in Silver Tier
# For now, the social server operates in simulation mode
# Full LinkedIn API integration planned for Gold Tier

# Check if LINKEDIN_ACCESS_TOKEN is set
grep LINKEDIN_ACCESS_TOKEN .env

# If not set, posts will be logged but not published
```

### Issue: ModuleNotFoundError for fastmcp
**Symptoms**: "ModuleNotFoundError: No module named 'fastmcp'"
**Solution**:
```bash
# Activate venv and install
source venv/bin/activate
pip install fastmcp mcp

# Restart social server
pm2 restart mcp-social
```

### Issue: Duplicate Content Detection
**Symptoms**: "Duplicate content detected" warning
**Solution**:
The social server includes duplicate content detection to prevent accidental double-posting. If you need to post similar content:
```bash
# Modify the content slightly
# Or wait 24 hours before posting similar content
# Or disable duplicate detection (not recommended)
```

## Examples

### Example 1: Check Social Server Status
```bash
# Check PM2 status
pm2 status mcp-social

# Check server logs
pm2 logs mcp-social --lines 50

# Verify server is responding
# (MCP servers don't have HTTP endpoints, check logs for startup messages)
```

### Example 2: Post to LinkedIn via Approval Workflow
```bash
# Create action file
cat > AI_Employee_Vault/Needs_Action/linkedin_post.md << 'EOF'
---
id: "social_001"
type: "social"
source: "manual"
priority: "normal"
timestamp: "2026-01-15T12:00:00Z"
status: "pending"
metadata:
  platform: "linkedin"
---

# LinkedIn Post

Post this content: "Excited to announce our new AI Employee system is live! 🚀 #AI #Automation"
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

# Restart social server
pm2 restart mcp-social

# Create test post action
# (same as Example 2)

# Check logs - post logged but not published
pm2 logs mcp-social --lines 20
```

### Example 4: Schedule Post for Future
```bash
# Create scheduled post
cat > AI_Employee_Vault/Needs_Action/scheduled_post.md << 'EOF'
---
id: "social_002"
type: "social"
source: "manual"
priority: "normal"
timestamp: "2026-01-15T12:00:00Z"
status: "pending"
metadata:
  platform: "linkedin"
  schedule: "2026-01-16T09:00:00Z"
---

# Scheduled LinkedIn Post

Post tomorrow at 9am: "Weekly update: Our AI Employee processed 50 tasks this week!"
EOF

# Follow approval workflow
# Post will be scheduled for future publication
```

## Related Documentation

- **PRODUCTION_GUIDE.md**: Complete production deployment guide
- **ARCHITECTURE.md**: Technical architecture details
- **src/mcp/social_server.py**: Social server implementation
- **ecosystem.config.js**: PM2 configuration file
