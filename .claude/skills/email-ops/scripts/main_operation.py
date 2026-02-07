#!/usr/bin/env python3
"""
Email Operations Skill - Main Operation
Integrates with Gmail MCP server for Silver Tier.

Supports:
- send: Send email via Gmail MCP server (with dry-run support)
- list-sent: List recent sent emails from idempotency database
- status: Check Gmail credentials and rate limit status
"""

import argparse
import sys
import json
import os
import subprocess
from pathlib import Path
from datetime import datetime

# Configuration
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
VAULT_ROOT = PROJECT_ROOT / "AI_Employee_Vault"
LOGS_DIR = VAULT_ROOT / "Logs"
GMAIL_MCP_DIR = PROJECT_ROOT / "src" / "mcp_servers" / "gmail"
IDEMPOTENCY_DB = PROJECT_ROOT / "data" / "idempotency.db"

# Fallback for simple operations
DRY_RUN_LOG = LOGS_DIR / "Email_Dry_Run.log"
AUDIT_LOG = LOGS_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.json"


def setup_dirs():
    """Ensure required directories exist."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)


def audit_log(action: str, target: str, status: str, details: dict = None):
    """Write audit log entry."""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "component": "email_ops_skill",
        "action_type": action,
        "target": target,
        "result": status,
        "parameters": details or {}
    }

    try:
        if AUDIT_LOG.exists():
            with open(AUDIT_LOG, 'r') as f:
                logs = json.load(f)
        else:
            logs = []

        logs.append(entry)

        with open(AUDIT_LOG, 'w') as f:
            json.dump(logs, f, indent=2)
    except Exception as e:
        print(f"Warning: Audit log failed: {e}", file=sys.stderr)


def check_mcp_server_available() -> bool:
    """Check if Gmail MCP server is available."""
    index_js = GMAIL_MCP_DIR / "dist" / "index.js"
    return index_js.exists()


def send_email_via_mcp(to: str, subject: str, body: str,
                       cc: list = None, bcc: list = None,
                       html: bool = False, dry_run: bool = False) -> dict:
    """
    Send email via Gmail MCP server.

    Args:
        to: Recipient email address
        subject: Email subject
        body: Email body content
        cc: CC recipients (optional)
        bcc: BCC recipients (optional)
        html: If True, body is treated as HTML
        dry_run: If True, simulate without sending

    Returns:
        dict with success, message_id, error, rate_limit
    """
    if not check_mcp_server_available():
        return {
            "success": False,
            "error": "Gmail MCP server not built. Run: cd src/mcp_servers/gmail && npm run build"
        }

    # Build MCP tool call payload
    tool_input = {
        "to": to,
        "subject": subject,
        "body": body,
        "dry_run": dry_run
    }
    if cc:
        tool_input["cc"] = cc
    if bcc:
        tool_input["bcc"] = bcc
    if html:
        tool_input["html"] = html

    # For now, simulate the MCP call since we can't directly invoke MCP from CLI
    # In production, Claude would call the MCP server directly

    if dry_run or os.getenv("DRY_RUN", "").lower() == "true":
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] [DRY RUN] To: {to} | Subject: {subject}\n"

        with open(DRY_RUN_LOG, 'a') as f:
            f.write(log_entry)

        return {
            "success": True,
            "message_id": "dry-run-message-id",
            "thread_id": "dry-run-thread-id",
            "rate_limit": {"remaining": 50, "limit": 50}
        }

    # Real MCP integration would happen here via Claude's tool calls
    # For skill CLI usage, we provide instructions
    return {
        "success": False,
        "error": "Direct MCP calls require Claude. Use through Claude with 'send email to X' command."
    }


def send_email(to: str, subject: str, body: str,
               attachment: str = None, dry_run: bool = False) -> bool:
    """Send email with optional attachment."""

    # Check for dry-run mode from environment
    dry_run = dry_run or os.getenv("DRY_RUN", "").lower() == "true"

    result = send_email_via_mcp(to, subject, body, dry_run=dry_run)

    if result["success"]:
        mode = "(DRY RUN)" if dry_run else ""
        print(f"✓ Email sent {mode} to {to}")
        print(f"  Message ID: {result.get('message_id', 'N/A')}")
        if result.get("rate_limit"):
            rl = result["rate_limit"]
            print(f"  Rate limit: {rl['remaining']}/{rl['limit']} remaining today")

        audit_log("send_email", to, "success", {
            "subject": subject,
            "dry_run": dry_run,
            "message_id": result.get("message_id")
        })
        return True
    else:
        print(f"✗ Failed to send email: {result.get('error', 'Unknown error')}")
        audit_log("send_email", to, "failure", {
            "subject": subject,
            "error": result.get("error")
        })
        return False


def list_sent(limit: int = 5):
    """List recent sent emails from logs."""

    # Check idempotency database first
    if IDEMPOTENCY_DB.exists():
        try:
            import sqlite3
            conn = sqlite3.connect(str(IDEMPOTENCY_DB))
            cursor = conn.cursor()
            cursor.execute("""
                SELECT action_id, recipient, sent_at, result_status
                FROM sent_actions
                WHERE action_type = 'email'
                ORDER BY sent_at DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            conn.close()

            if rows:
                print(f"Recent sent emails (from idempotency database):")
                print("-" * 70)
                for row in rows:
                    print(f"  {row[2]} | To: {row[1]} | Status: {row[3]}")
                return
        except Exception as e:
            print(f"Warning: Could not read idempotency DB: {e}", file=sys.stderr)

    # Fallback to dry-run log
    if DRY_RUN_LOG.exists():
        print(f"Recent sent emails (from {DRY_RUN_LOG}):")
        print("-" * 70)

        with open(DRY_RUN_LOG, 'r') as f:
            lines = f.readlines()

        for line in lines[-limit:]:
            print(f"  {line.strip()}")
    else:
        print("No sent emails found.")


def check_status():
    """Check Gmail MCP server status and credentials."""

    print("Gmail Email Operations Status")
    print("=" * 40)

    # Check MCP server
    if check_mcp_server_available():
        print("✓ Gmail MCP server: Built and available")
    else:
        print("✗ Gmail MCP server: Not built")
        print("  Run: cd src/mcp_servers/gmail && npm install && npm run build")

    # Check dry-run mode
    if os.getenv("DRY_RUN", "").lower() == "true":
        print("⚠ Dry-run mode: ENABLED (via DRY_RUN env var)")
    else:
        print("✓ Dry-run mode: Disabled")

    # Check idempotency database
    if IDEMPOTENCY_DB.exists():
        print(f"✓ Idempotency DB: {IDEMPOTENCY_DB}")
        try:
            import sqlite3
            conn = sqlite3.connect(str(IDEMPOTENCY_DB))
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM sent_actions WHERE action_type = 'email'")
            count = cursor.fetchone()[0]
            conn.close()
            print(f"  Emails tracked: {count}")
        except Exception:
            pass
    else:
        print("⚠ Idempotency DB: Not found (will be created on first use)")

    # Check credentials (via environment or keyring)
    cred_status = "Not configured"
    if os.getenv("GMAIL_ACCESS_TOKEN"):
        cred_status = "Found (via environment)"

    print(f"  Gmail credentials: {cred_status}")
    print("")
    print("To send real emails, configure Gmail OAuth credentials.")
    print("See: specs/002-external-connectivity/quickstart.md")


def main():
    parser = argparse.ArgumentParser(description="Email operations via Gmail MCP")
    parser.add_argument("--action", required=True,
                       choices=["send", "list-sent", "status"])
    parser.add_argument("--to", help="Recipient email address")
    parser.add_argument("--subject", help="Email subject")
    parser.add_argument("--body", help="Email body content")
    parser.add_argument("--attachment", help="Path to attachment (not yet implemented)")
    parser.add_argument("--limit", type=int, default=5, help="Limit for list-sent")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without sending")

    args = parser.parse_args()
    setup_dirs()

    if args.action == "send":
        if not all([args.to, args.subject, args.body]):
            print("Error: --to, --subject, and --body required for send")
            sys.exit(1)
        if not send_email(args.to, args.subject, args.body,
                         args.attachment, args.dry_run):
            sys.exit(1)

    elif args.action == "list-sent":
        list_sent(args.limit)

    elif args.action == "status":
        check_status()


if __name__ == "__main__":
    main()
