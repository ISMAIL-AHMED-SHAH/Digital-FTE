#!/usr/bin/env python3
import argparse
import sys
import json
import os
from pathlib import Path
from datetime import datetime
import difflib

# Config
VAULT_ROOT = Path("AI_Employee_Vault")
LOGS_DIR = VAULT_ROOT / "Logs"
DRY_RUN_LOG = LOGS_DIR / "LinkedIn_Dry_Run.log"
AUDIT_LOG = LOGS_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.json"

def setup_dirs():
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

def audit_log(action, result, details=None):
    entry = {
        "timestamp": datetime.now().isoformat(),
        "action_type": "social_op",
        "sub_action": action,
        "target": "linkedin",
        "result": result,
        "actor": "social_ops_skill",
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

def check_duplicates(content):
    if not DRY_RUN_LOG.exists():
        return False

    with open(DRY_RUN_LOG, 'r') as f:
        posts = [line.split('| Content: ')[1].strip() for line in f if '| Content: ' in line]

    for post in posts:
        # Simple simulation of 80% similarity check
        ratio = difflib.SequenceMatcher(None, content, post).ratio()
        if ratio > 0.8:
            return True
    return False

def post_update(content):
    if check_duplicates(content):
        print("✗ Duplicate content detected (>80% similar to recent post). Post rejected.")
        audit_log("post", "rejected_duplicate", {"content_preview": content[:50]})
        return False

    dry_run = os.getenv("DRY_RUN", "true").lower() == "true"

    if dry_run:
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] [DRY RUN] Status: Posted | Content: {content}\n"
        with open(DRY_RUN_LOG, 'a') as f:
            f.write(log_entry)

        print("✓ Post logged (DRY RUN)")
        audit_log("post", "success (dry_run)", {"content_preview": content[:50]})
        return True

    print("✗ Real LinkedIn posting not configured. Enable DRY_RUN=true")
    return False

def schedule_post(content, time_str):
    dry_run = os.getenv("DRY_RUN", "true").lower() == "true"

    if dry_run:
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] [DRY RUN] Status: Scheduled ({time_str}) | Content: {content}\n"
        with open(DRY_RUN_LOG, 'a') as f:
            f.write(log_entry)

        print(f"✓ Post scheduled for {time_str} (DRY RUN)")
        audit_log("schedule", "success (dry_run)", {"time": time_str})
        return True

    print("✗ Real LinkedIn scheduling not configured")
    return False

def list_recent(limit):
    if not DRY_RUN_LOG.exists():
        print("No recent posts found.")
        return

    print(f"Recent LinkedIn activity (from {DRY_RUN_LOG}):")
    print("-" * 60)

    with open(DRY_RUN_LOG, 'r') as f:
        lines = f.readlines()

    for line in lines[-limit:]:
        print(line.strip())

def main():
    parser = argparse.ArgumentParser(description="Social operations")
    parser.add_argument("--action", required=True, choices=["post", "schedule", "list-recent"])
    parser.add_argument("--content", help="Post content")
    parser.add_argument("--time", help="Schedule time (ISO8601)")
    parser.add_argument("--limit", type=int, default=5)

    args = parser.parse_args()
    setup_dirs()

    if args.action == "post":
        if not args.content:
            print("Error: --content required for post")
            sys.exit(1)
        if not post_update(args.content):
            sys.exit(1)

    elif args.action == "schedule":
        if not args.content or not args.time:
            print("Error: --content and --time required for schedule")
            sys.exit(1)
        if not schedule_post(args.content, args.time):
            sys.exit(1)

    elif args.action == "list-recent":
        list_recent(args.limit)

if __name__ == "__main__":
    main()
