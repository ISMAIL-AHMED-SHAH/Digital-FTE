#!/usr/bin/env python3
import argparse
import sys
import json
from pathlib import Path

# Config
VAULT_ROOT = Path("AI_Employee_Vault")
CONFIG_DIR = VAULT_ROOT / "Config"
SCHEDULE_FILE = CONFIG_DIR / "schedules.json"

def setup_dirs():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

def load_schedules():
    if not SCHEDULE_FILE.exists():
        return []
    try:
        with open(SCHEDULE_FILE, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []

def save_schedules(schedules):
    with open(SCHEDULE_FILE, 'w') as f:
        json.dump(schedules, f, indent=2)

def list_schedules():
    schedules = load_schedules()
    if not schedules:
        print("No scheduled tasks.")
        return

    print(f"{'Comment':<20} | {'Schedule':<15} | {'Command'}")
    print("-" * 80)
    for s in schedules:
        print(f"{s.get('comment', 'N/A'):<20} | {s.get('schedule', 'N/A'):<15} | {s.get('cmd', 'N/A')}")

def add_schedule(cmd, schedule, comment):
    schedules = load_schedules()

    # Check duplicate comment
    for s in schedules:
        if s.get('comment') == comment:
            print(f"✗ Error: Schedule with comment '{comment}' already exists. Use remove first.")
            return False

    schedules.append({
        "cmd": cmd,
        "schedule": schedule,
        "comment": comment,
        "active": True
    })

    save_schedules(schedules)
    print(f"✓ Added schedule: {comment} ({schedule})")

    # Ideally, we would also update real cron here.
    # For this implementation, we simply update the source of truth file.
    return True

def remove_schedule(comment):
    schedules = load_schedules()
    initial_len = len(schedules)

    schedules = [s for s in schedules if s.get('comment') != comment]

    if len(schedules) == initial_len:
        print(f"✗ Error: Schedule '{comment}' not found.")
        return False

    save_schedules(schedules)
    print(f"✓ Removed schedule: {comment}")
    return True

def main():
    parser = argparse.ArgumentParser(description="Scheduler operations")
    parser.add_argument("--action", required=True, choices=["list", "add", "remove"])
    parser.add_argument("--cmd", help="Command to execute")
    parser.add_argument("--schedule", help="Cron expression")
    parser.add_argument("--comment", help="Unique identifier/comment for the task")

    args = parser.parse_args()
    setup_dirs()

    if args.action == "list":
        list_schedules()

    elif args.action == "add":
        if not all([args.cmd, args.schedule, args.comment]):
            print("Error: --cmd, --schedule, and --comment required for add")
            sys.exit(1)
        if not add_schedule(args.cmd, args.schedule, args.comment):
            sys.exit(1)

    elif args.action == "remove":
        if not args.comment:
            print("Error: --comment required for remove")
            sys.exit(1)
        if not remove_schedule(args.comment):
            sys.exit(1)

if __name__ == "__main__":
    main()
