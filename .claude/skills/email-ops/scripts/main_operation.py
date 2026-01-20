#!/usr/bin/env python3
import argparse
import sys
import json
import os
from pathlib import Path
from datetime import datetime

# Config
VAULT_ROOT = Path("AI_Employee_Vault")
LOGS_DIR = VAULT_ROOT / "Logs"
DRY_RUN_LOG = LOGS_DIR / "Email_Dry_Run.log"
AUDIT_LOG = LOGS_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.json"

def setup_dirs():
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

def audit_log(action, target, status, details=None):
    entry = {
        "timestamp": datetime.now().isoformat(),
        "action_type": "email_op",
        "sub_action": action,
        "target": target,
        "result": status,
        "actor": "email_ops_skill",
        "details": details or {}
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

def send_email(to, subject, body, attachment=None):
    # Check if we have credentials or force dry run
    dry_run = os.getenv("DRY_RUN", "true").lower() == "true"

    if dry_run:
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] [DRY RUN] To: {to} | Subject: {subject} | Attachment: {attachment}\n"
        with open(DRY_RUN_LOG, 'a') as f:
            f.write(log_entry)

        # Log content separately for debugging if needed
        # print(f"Body: {body}")

        print(f"✓ Email logged (DRY RUN) to {to}")
        audit_log("send", to, "success (dry_run)", {"subject": subject, "attachment": str(attachment)})
        return True

    # Real implementation would go here (using google-api-python-client)
    # For Silver Tier hackathon submission, we'll simluate real send if credentials exist,
    # otherwise fail gracefully.

    print("✗ Real email sending not configured (missing credentials). Enable DRY_RUN=true or configure Gmail API.")
    return False

def list_sent(limit):
    if not DRY_RUN_LOG.exists():
        print("No sent emails found.")
        return

    print(f"Recent sent emails (from {DRY_RUN_LOG}):")
    print("-" * 60)

    with open(DRY_RUN_LOG, 'r') as f:
        lines = f.readlines()

    for line in lines[-limit:]:
        print(line.strip())

def main():
    parser = argparse.ArgumentParser(description="Email operations")
    parser.add_argument("--action", required=True, choices=["send", "list-sent", "status"])
    parser.add_argument("--to", help="Recipient email")
    parser.add_argument("--subject", help="Email subject")
    parser.add_argument("--body", help="Email body")
    parser.add_argument("--attachment", help="Path to attachment")
    parser.add_argument("--limit", type=int, default=5, help="Limit for list-sent")

    args = parser.parse_args()
    setup_dirs()

    if args.action == "send":
        if not all([args.to, args.subject, args.body]):
            print("Error: --to, --subject, and --body required for send")
            sys.exit(1)
        if not send_email(args.to, args.subject, args.body, args.attachment):
            sys.exit(1)

    elif args.action == "list-sent":
        list_sent(args.limit)

    elif args.action == "status":
        print("✓ Email Ops ready (DRY RUN mode active)")

if __name__ == "__main__":
    main()
