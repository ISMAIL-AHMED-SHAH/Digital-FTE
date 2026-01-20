#!/usr/bin/env python3
"""
Setup Vault - Main Operation
Creates AI Employee Vault structure with folders and core files.
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime


def create_vault_structure(vault_path: Path, force: bool = False) -> bool:
    """Create vault folder structure and core files."""

    # Check if vault exists
    if vault_path.exists() and not force:
        print(f"✗ Failed: Vault already exists at {vault_path}")
        print("  Use --force to overwrite")
        return False

    # Create main vault directory
    vault_path.mkdir(exist_ok=True)

    # Create folder structure
    folders = [
        "Inbox",
        "Needs_Action",
        "Done",
        "Plans",
        "Logs",
        "Pending_Approval",
        "Approved",
        "Rejected"
    ]

    for folder in folders:
        (vault_path / folder).mkdir(exist_ok=True)

    # Create Dashboard.md
    dashboard_content = """# AI Employee Dashboard

**Last Updated**: Not yet started

## System Status

- **Watcher**: Not started
- **Watcher Type**: Not configured
- **Last Check**: N/A
- **Uptime**: N/A

## Pending Actions

**Count**: 0

No pending actions.

## Recent Activity

No activity yet. System is ready to start.

## Quick Stats

- **Files Processed Today**: 0
- **Files Processed This Week**: 0
- **Average Processing Time**: N/A
- **Success Rate**: N/A

## Errors

No errors.

---

*Dashboard will be automatically updated by Claude Code after each processing run.*
"""
    (vault_path / "Dashboard.md").write_text(dashboard_content)

    # Create Company_Handbook.md
    timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    handbook_content = f"""# Company Handbook

**Last Updated**: {timestamp}

## Communication Style

- Always be polite and professional
- Use clear, concise language
- Avoid jargon unless necessary
- Address people by name when known

## Approval Thresholds

### Always Require Approval
- Financial transactions (payments, transfers)
- Communications to new contacts
- Bulk operations (mass emails, social media posts)

### No Approval Needed
- Reading emails and files
- Creating plans and summaries
- Logging activities

## Priority Keywords

### High Priority
- urgent, asap, critical, emergency, invoice, payment

### Medium Priority
- important, soon, review, feedback

### Low Priority
- fyi, info, update, note

## Error Handling Preferences

- Network errors: Retry 3 times with exponential backoff
- Authentication errors: Alert human immediately, pause operations
- Parsing errors: Log warning, attempt partial processing

## Business Rules

- Generate invoices within 24 hours of request
- Acknowledge emails within 4 hours during business hours
- Process high-priority items first
- Keep logs for 90 days minimum

---

*This handbook guides AI behavior. Update it as your needs evolve.*
"""
    (vault_path / "Company_Handbook.md").write_text(handbook_content)

    # Create README.md
    readme_content = """# AI Employee Vault

This is your AI Employee's knowledge base and workspace.

## Folder Structure

- **Inbox/**: Drop files here for processing
- **Needs_Action/**: Pending action files
- **Done/**: Completed action files
- **Plans/**: Generated plan files
- **Logs/**: System logs

## Key Files

- **Dashboard.md**: Real-time system status
- **Company_Handbook.md**: AI behavior rules

---

*Bronze Tier - Personal AI Employee Foundation*
"""
    (vault_path / "README.md").write_text(readme_content)

    # Create .gitignore
    gitignore_content = """# Obsidian workspace files
.obsidian/workspace.json

# Logs
Logs/*.log
Logs/*.json

# Temporary files
*.tmp
.DS_Store

# Sensitive data
*.key
*.secret
"""
    (vault_path / ".gitignore").write_text(gitignore_content)

    return True


def main():
    parser = argparse.ArgumentParser(description="Initialize AI Employee Vault")
    parser.add_argument("--vault-path", default="AI_Employee_Vault", help="Vault path")
    parser.add_argument("--force", action="store_true", help="Overwrite existing")

    args = parser.parse_args()
    vault_path = Path(args.vault_path)

    success = create_vault_structure(vault_path, args.force)

    if success:
        print(f"✓ Vault created at {vault_path.absolute()}")
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
