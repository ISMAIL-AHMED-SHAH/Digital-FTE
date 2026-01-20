# Silver Tier Agent Skills Catalog

**Version**: 2.0.0
**Date**: 2026-01-15
**Category**: Personal AI Employee - Silver Tier Functional Assistant

## Overview

This directory contains Claude Code Agent Skills for the Silver Tier Personal AI Employee system. These skills provide reusable, documented capabilities for managing your AI Employee's vault, orchestrator, MCP servers, approval workflows, and automated operations.

**Production Status**: ✅ All services running with PM2 process management

**Architecture**:
- **ai-orchestrator**: Main coordinator with threaded watchers (Gmail, WhatsApp, LinkedIn)
- **mcp-email**: Email sending capabilities via FastMCP
- **mcp-social**: LinkedIn posting capabilities via FastMCP

## Available Skills

### 1. setup-vault
**Purpose**: Initialize AI Employee Vault structure
**Status**: ✅ Ready
**File**: `setup-vault.md`

Creates the complete folder structure and initial files for the AI Employee Vault.

**Usage**:
```
User: "Run the setup-vault skill"
```

**Inputs**:
- `vault_path` (optional): Custom vault location
- `force` (optional): Overwrite existing vault

**Outputs**:
- Creates 8 folders (Inbox, Needs_Action, Done, Plans, Logs, etc.)
- Creates Dashboard.md, Company_Handbook.md, README.md
- Creates .gitignore for Obsidian compatibility

---

### 2. watcher-manager
**Purpose**: Manage orchestrator and watchers
**Status**: ✅ Ready (Silver Tier)
**File**: `watcher-manager/SKILL.md`

Manages the ai-orchestrator process which runs all watchers (Gmail, WhatsApp, LinkedIn) as internal threads.

**Usage**:
```
User: "Check watcher status"
User: "Restart the orchestrator"
User: "Start the watchers"
```

**Key Commands**:
- `pm2 status` - Check orchestrator status
- `pm2 restart ai-orchestrator` - Restart orchestrator and all watchers
- `pm2 logs ai-orchestrator` - View orchestrator logs

**Outputs**:
- Shows orchestrator process status
- Displays watcher health in Dashboard.md
- Shows uptime and resource usage

---

### 3. process-inbox
**Purpose**: Process pending action files and create plans
**Status**: ✅ Ready
**File**: `process-inbox.md`

The "brain" of the AI Employee - reads action files, creates execution plans, updates dashboard.

**Usage**:
```
User: "Run process-inbox skill"
User: "Run process-inbox with priority_filter=high"
User: "Run process-inbox with dry_run=true"
```

**Inputs**:
- `vault_path` (optional): Custom vault location
- `priority_filter` (optional): "high", "medium", "low", or "all"
- `max_files` (optional): Maximum files to process
- `dry_run` (optional): Preview without changes

**Outputs**:
- Creates Plan.md files in Plans folder
- Moves processed files to Done folder
- Updates Dashboard.md with activity
- Generates processing summary

---

### 4. view-dashboard
**Purpose**: Display current system status and activity
**Status**: ✅ Ready
**File**: `view-dashboard.md`

Shows a formatted view of the AI Employee Dashboard with status, pending actions, and statistics.

**Usage**:
```
User: "Run view-dashboard skill"
User: "Run view-dashboard with format=summary"
User: "Run view-dashboard with format=status"
```

**Inputs**:
- `vault_path` (optional): Custom vault location
- `format` (optional): "full", "summary", or "status"
- `lines` (optional): Number of activity lines to show

**Outputs**:
- Formatted dashboard display
- System status indicators
- Pending actions summary
- Recent activity log
- Quick action suggestions

---

### 5. manage-approval
**Purpose**: Manage human-in-the-loop approval workflow
**Status**: ✅ Ready (Silver Tier)
**File**: `manage-approval/SKILL.md`

Manages approval requests for sensitive actions (emails, social posts, payments).

**Usage**:
```
User: "Check pending approvals"
User: "Approve action AR-2026-01-15-001"
User: "Reject email request"
```

**Inputs**:
- `action` (required): "list", "approve", or "reject"
- `id` (optional): Approval request ID
- `reason` (optional): Rejection reason

**Outputs**:
- Lists pending approval requests
- Moves approved files to Approved/
- Moves rejected files to Rejected/
- Logs approval decisions to audit trail

---

### 6. email-ops
**Purpose**: Send emails via MCP email server
**Status**: ✅ Ready (Silver Tier)
**File**: `email-ops/SKILL.md`

Sends emails through the mcp-email MCP server with approval workflow.

**Usage**:
```
User: "Send email to client@example.com"
User: "Check sent emails"
User: "Check email server status"
```

**Inputs**:
- `action` (required): "send", "list-sent", or "status"
- `to` (optional): Recipient email
- `subject` (optional): Email subject
- `body` (optional): Email body
- `attachment` (optional): File path to attach

**Outputs**:
- Creates approval request for email
- Sends email after approval
- Logs to audit trail
- Returns sent email status

---

### 7. social-ops
**Purpose**: Post to LinkedIn via MCP social server
**Status**: ✅ Ready (Silver Tier)
**File**: `social-ops/SKILL.md`

Posts content to LinkedIn through the mcp-social MCP server with approval workflow.

**Usage**:
```
User: "Post to LinkedIn"
User: "Schedule LinkedIn post"
User: "Check social server status"
```

**Inputs**:
- `action` (required): "post", "schedule", or "status"
- `content` (optional): Post content
- `schedule` (optional): Schedule time (ISO 8601)

**Outputs**:
- Creates approval request for post
- Publishes post after approval
- Logs to audit trail
- Returns post status

---

### 8. scheduler
**Purpose**: Manage scheduled tasks using cron
**Status**: ✅ Ready (Silver Tier)
**File**: `scheduler/SKILL.md`

Manages scheduled tasks for recurring operations (daily briefings, cleanup, etc.).

**Usage**:
```
User: "List scheduled tasks"
User: "Schedule daily briefing at 8am"
User: "Remove scheduled task"
```

**Inputs**:
- `action` (required): "list", "add", or "remove"
- `cmd` (optional): Command to schedule
- `schedule` (optional): Cron expression
- `comment` (optional): Task name/description

**Outputs**:
- Lists current scheduled tasks
- Adds task to crontab
- Removes task from crontab
- Validates cron syntax

---

### 9. create-claude-skill
**Purpose**: Create new AI skills using MCP Code Execution pattern
**Status**: ✅ Ready (Silver Tier)
**File**: `create-claude-skill/SKILL.md`

Creates new reusable skills for the AI Employee system.

**Usage**:
```
User: "Create a new skill for data analysis"
User: "Create skill for report generation"
```

**Inputs**:
- `skill_name` (required): Name of new skill
- `description` (required): What the skill does
- `capabilities` (optional): List of capabilities

**Outputs**:
- Creates skill directory structure
- Generates SKILL.md and REFERENCE.md
- Creates script templates
- Adds skill to catalog

---

## Quick Start Workflow

### Initial Setup (First Time)

1. **Verify System is Running**
   ```bash
   pm2 status
   ```
   All three services (ai-orchestrator, mcp-email, mcp-social) should show "online".

2. **Check Dashboard**
   ```
   User: "Show me the dashboard"
   ```

3. **Customize Company Handbook**
   - Edit `AI_Employee_Vault/Company_Handbook.md`
   - Add your rules, priorities, and preferences

4. **Configure Optional Watchers**
   - Gmail: See PRODUCTION_GUIDE.md for OAuth setup
   - WhatsApp: See PRODUCTION_GUIDE.md for QR code setup

5. **Test the System**
   ```bash
   # Create test action file
   cat > AI_Employee_Vault/Needs_Action/test.md << 'EOF'
   ---
   id: "test_001"
   type: "email"
   source: "manual"
   priority: "high"
   timestamp: "2026-01-15T12:00:00Z"
   status: "pending"
   ---

   # Test Task

   Send test email to test@example.com
   EOF

   # Wait 10 seconds for processing
   sleep 10

   # Check results
   ls AI_Employee_Vault/Plans/
   ls AI_Employee_Vault/Pending_Approval/
   ```

### Daily Usage

**Morning Check-In**:
```bash
# Check system status
pm2 status

# View dashboard
cat AI_Employee_Vault/Dashboard.md

# Check pending approvals
ls AI_Employee_Vault/Pending_Approval/
```

**Give AI a Task**:
```bash
# Create action file
cat > AI_Employee_Vault/Needs_Action/my_task.md << 'EOF'
---
id: "task_$(date +%s)"
type: "email"
source: "manual"
priority: "high"
timestamp: "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
status: "pending"
---

# Your Task Here

Describe what you want the AI to do.
EOF

# Wait for processing (10 seconds)
sleep 10

# Check for approval request
ls AI_Employee_Vault/Pending_Approval/
```

**Approve Actions**:
```bash
# Check pending approvals
ls AI_Employee_Vault/Pending_Approval/

# Read approval request
cat AI_Employee_Vault/Pending_Approval/[filename].md

# Approve
mv AI_Employee_Vault/Pending_Approval/[filename].md AI_Employee_Vault/Approved/

# Or reject
mv AI_Employee_Vault/Pending_Approval/[filename].md AI_Employee_Vault/Rejected/
```

**Monitor System**:
```bash
# Check PM2 status
pm2 status

# View orchestrator logs
pm2 logs ai-orchestrator --lines 50

# View audit logs
cat AI_Employee_Vault/Logs/$(date +%Y-%m-%d).json | python3 -m json.tool
```

### Troubleshooting

**Watcher Not Running**:
```
User: "Run watcher-manager with action=status"
User: "Run watcher-manager with action=start"
```

**Check for Errors**:
```
User: "Show me the dashboard"
Claude: [Displays errors section]

User: "Show me the watcher logs"
Claude: [Reads AI_Employee_Vault/Logs/watcher-*.log]
```

**Reset System**:
```
User: "Run watcher-manager with action=stop"
User: "Run setup-vault with force=true"
User: "Run watcher-manager with action=start"
```

## Skill Invocation Patterns

### Direct Invocation
```
User: "Run [skill-name] skill"
User: "Run [skill-name] with [param]=[value]"
User: "Run [skill-name] with [param1]=[value1] and [param2]=[value2]"
```

### Natural Language
```
User: "Set up the vault"
Claude: [Interprets as setup-vault skill]

User: "Start the watcher"
Claude: [Interprets as watcher-manager with action=start]

User: "Process my inbox"
Claude: [Interprets as process-inbox skill]

User: "Show me the dashboard"
Claude: [Interprets as view-dashboard skill]
```

### Chained Operations
```
User: "Set up the vault, then start the watcher, then show me the dashboard"
Claude: [Executes skills in sequence]
```

## Skill Development Guidelines

### Creating New Skills

When creating new skills for Bronze Tier, follow these guidelines:

1. **File Format**: Markdown (.md) in `.claude/skills/` directory
2. **Required Sections**:
   - Name, Version, Description, Category
   - Purpose
   - Inputs (with types and defaults)
   - Outputs
   - Prerequisites
   - Execution Steps
   - Example Usage
   - Error Handling
   - Testing
   - Version History

3. **Naming Convention**: Use kebab-case (e.g., `setup-vault`, `process-inbox`)

4. **Documentation**: Include clear examples and error messages

5. **Testing**: Provide test cases and validation steps

### Skill Template

```markdown
# [Skill Name] Skill

**Name**: skill-name
**Version**: 1.0.0
**Description**: Brief description
**Category**: Bronze Tier - Foundation

## Purpose
[What this skill does and why it's needed]

## Inputs
- `param1` (required): Description
- `param2` (optional): Description. Default: value

## Outputs
[What the skill produces]

## Prerequisites
[What must exist before running]

## Execution Steps
[Detailed steps with code/commands]

## Example Usage
[Real examples with expected results]

## Error Handling
[Common errors and solutions]

## Testing
[How to test the skill]

## Version History
- **1.0.0** (YYYY-MM-DD): Initial implementation
```

## Integration with Claude Code

These skills are designed to work seamlessly with Claude Code:

1. **Automatic Discovery**: Claude Code can discover skills in `.claude/skills/`
2. **Natural Language**: Users can invoke skills conversationally
3. **Parameter Passing**: Skills accept parameters via natural language
4. **Error Handling**: Skills provide clear error messages
5. **Chaining**: Skills can be chained together in workflows

## Skill Dependencies

```
setup-vault (no dependencies)
    ↓
watcher-manager (requires vault)
    ↓
process-inbox (requires vault + watcher)
    ↓
view-dashboard (requires vault)
```

## Performance Characteristics

| Skill | Execution Time | Memory Usage | Disk I/O |
|-------|---------------|--------------|----------|
| setup-vault | < 5 seconds | Minimal | Low (creates files) |
| watcher-manager | < 2 seconds | Minimal | None |
| process-inbox | 30-60s per file | Low | Medium (reads/writes) |
| view-dashboard | < 1 second | Minimal | Low (reads only) |

## Security Considerations

- **Credentials**: Never store credentials in skill files
- **Permissions**: Skills require write access to vault directory
- **Validation**: All inputs are validated before execution
- **Dry Run**: process-inbox supports dry-run mode for safety
- **Logging**: All actions are logged for audit trail

## Troubleshooting

### Skill Not Found

**Problem**: Claude says it can't find the skill

**Solutions**:
- Verify skill file exists in `.claude/skills/`
- Check file has `.md` extension
- Ensure skill name matches filename

### Skill Fails to Execute

**Problem**: Skill starts but fails during execution

**Solutions**:
- Check prerequisites are met
- Verify vault path is correct
- Review error messages in output
- Check logs in `AI_Employee_Vault/Logs/`

### Permission Denied

**Problem**: Cannot create files or folders

**Solutions**:
- Check write permissions on vault directory
- Verify disk space is available
- Run with appropriate user permissions

## Future Skills (Silver/Gold Tier)

Skills planned for future tiers:

**Silver Tier**:
- `send-email`: Send emails via MCP server
- `approve-action`: Approve pending actions
- `schedule-task`: Schedule recurring tasks
- `manage-contacts`: Manage contact list

**Gold Tier**:
- `generate-briefing`: Create CEO briefing
- `audit-accounting`: Run accounting audit
- `post-social`: Post to social media
- `analyze-metrics`: Analyze business metrics

## Contributing

To add new skills:

1. Create skill file in `.claude/skills/`
2. Follow skill template format
3. Test thoroughly
4. Update this catalog
5. Document in quickstart guide

## Support

- **Documentation**: See individual skill files for detailed docs
- **Issues**: Check logs in `AI_Employee_Vault/Logs/`
- **Community**: Join Wednesday research meetings

## Version History

- **1.0.0** (2026-01-14): Initial Bronze Tier skills
  - setup-vault
  - watcher-manager
  - process-inbox
  - view-dashboard

---

**Bronze Tier - Personal AI Employee Foundation**
*Building autonomous AI employees, one skill at a time.*
