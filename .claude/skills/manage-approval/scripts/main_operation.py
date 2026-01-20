#!/usr/bin/env python3
import argparse
import sys
import shutil
import json
from pathlib import Path
from datetime import datetime

# Configuration
VAULT_ROOT = Path("AI_Employee_Vault")
PENDING_DIR = VAULT_ROOT / "Pending_Approval"
APPROVED_DIR = VAULT_ROOT / "Approved"
REJECTED_DIR = VAULT_ROOT / "Rejected"
LOGS_DIR = VAULT_ROOT / "Logs"

def setup_dirs():
    for d in [PENDING_DIR, APPROVED_DIR, REJECTED_DIR, LOGS_DIR]:
        d.mkdir(parents=True, exist_ok=True)

def log_action(action, file_name, result, details=None):
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = LOGS_DIR / f"{today}.json"

    entry = {
        "timestamp": datetime.now().isoformat(),
        "action_type": "approval_workflow",
        "sub_action": action,
        "target": file_name,
        "result": result,
        "actor": "human_via_skill",
        "details": details or {}
    }

    try:
        if log_file.exists():
            with open(log_file, 'r') as f:
                logs = json.load(f)
        else:
            logs = []

        logs.append(entry)

        with open(log_file, 'w') as f:
            json.dump(logs, f, indent=2)

    except Exception as e:
        print(f"Warning: Failed to write log: {e}", file=sys.stderr)

def list_approvals():
    files = list(PENDING_DIR.glob("*.md"))
    if not files:
        print("No pending approvals.")
        return

    print(f"{'ID':<30} | {'Type':<15} | {'Created':<20} | {'Summary'}")
    print("-" * 100)

    for f in files:
        # Simple parsing of frontmatter
        content = f.read_text()
        lines = content.split('\n')
        type_str = "unknown"
        created = "unknown"
        summary = f.name

        in_frontmatter = False
        for line in lines:
            if line.strip() == "---":
                if in_frontmatter: break
                in_frontmatter = True
                continue
            if in_frontmatter:
                if line.startswith("type:"): type_str = line.split(":", 1)[1].strip()
                if line.startswith("created:"): created = line.split(":", 1)[1].strip()
                if line.startswith("action:"): summary = line.split(":", 1)[1].strip()

        print(f"{f.name:<30} | {type_str:<15} | {created:<20} | {summary}")

def get_file(file_id):
    # Try exact match
    f = PENDING_DIR / file_id
    if f.exists(): return f

    # Try fuzzy match (e.g., just the name without .md, or part of name)
    # If file_id doesn't end with .md, append it
    if not file_id.endswith(".md"):
        f = PENDING_DIR / f"{file_id}.md"
        if f.exists(): return f

    # Search for containing string
    matches = list(PENDING_DIR.glob(f"*{file_id}*"))
    if len(matches) == 1:
        return matches[0]
    elif len(matches) > 1:
        print(f"Error: Ambiguous ID '{file_id}', matches multiple files:")
        for m in matches: print(f"  - {m.name}")
        return None

    print(f"Error: File '{file_id}' not found in {PENDING_DIR}")
    return None

def approve(file_id):
    f = get_file(file_id)
    if not f: return False

    dest = APPROVED_DIR / f.name
    try:
        shutil.move(str(f), str(dest))
        print(f"✓ Approved: {f.name} -> {dest}")
        log_action("approve", f.name, "success")
        return True
    except Exception as e:
        print(f"✗ Failed to approve {f.name}: {e}")
        log_action("approve", f.name, "failure", {"error": str(e)})
        return False

def reject(file_id, reason):
    f = get_file(file_id)
    if not f: return False

    dest = REJECTED_DIR / f.name
    try:
        # Append rejection reason to file content
        content = f.read_text()
        rejection_note = f"\n\n## Rejection Info\n- **Rejected At**: {datetime.now().isoformat()}\n- **Reason**: {reason}\n"
        dest.write_text(content + rejection_note)
        f.unlink() # Remove original

        print(f"✓ Rejected: {f.name} -> {dest}")
        log_action("reject", f.name, "success", {"reason": reason})
        return True
    except Exception as e:
        print(f"✗ Failed to reject {f.name}: {e}")
        log_action("reject", f.name, "failure", {"error": str(e)})
        return False

def main():
    parser = argparse.ArgumentParser(description="Manage approval queue")
    parser.add_argument("--action", required=True, choices=["list", "approve", "reject"])
    parser.add_argument("--id", help="File ID or name for approve/reject")
    parser.add_argument("--reason", help="Reason for rejection")

    args = parser.parse_args()

    setup_dirs()

    if args.action == "list":
        list_approvals()
    elif args.action == "approve":
        if not args.id:
            print("Error: --id required for approve")
            sys.exit(1)
        if not approve(args.id):
            sys.exit(1)
    elif args.action == "reject":
        if not args.id:
            print("Error: --id required for reject")
            sys.exit(1)
        if not args.reason:
            print("Error: --reason required for reject")
            sys.exit(1)
        if not reject(args.id, args.reason):
            sys.exit(1)

if __name__ == "__main__":
    main()
