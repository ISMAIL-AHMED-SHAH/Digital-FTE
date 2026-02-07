#!/usr/bin/env python3
"""
Manage Approval Skill - Main Operation
Integrates with Silver Tier integrity validation for approval workflow.

Supports:
- list: List pending approval requests
- approve: Approve an action (with integrity validation)
- reject: Reject an action with reason
- verify: Verify integrity hash of an action file
"""

import argparse
import sys
import shutil
import json
import re
import yaml
from pathlib import Path
from datetime import datetime

# Configuration
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
VAULT_ROOT = PROJECT_ROOT / "AI_Employee_Vault"
PENDING_DIR = VAULT_ROOT / "Pending_Approval"
APPROVED_DIR = VAULT_ROOT / "Approved"
REJECTED_DIR = VAULT_ROOT / "Rejected"
LOGS_DIR = VAULT_ROOT / "Logs"

# Add project root to path for imports
sys.path.insert(0, str(PROJECT_ROOT))


def setup_dirs():
    """Ensure required directories exist."""
    for d in [PENDING_DIR, APPROVED_DIR, REJECTED_DIR, LOGS_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def log_action(action: str, file_name: str, result: str, details: dict = None):
    """Write audit log entry."""
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = LOGS_DIR / f"{today}.json"

    entry = {
        "timestamp": datetime.now().isoformat(),
        "component": "manage_approval_skill",
        "action_type": "approval_workflow",
        "sub_action": action,
        "target": file_name,
        "result": result,
        "actor": "human_via_skill",
        "parameters": details or {}
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


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from markdown content."""
    if not content.startswith("---"):
        return {}, content

    # Find the closing ---
    end_match = re.search(r'\n---\n', content[3:])
    if not end_match:
        return {}, content

    frontmatter_text = content[3:end_match.start() + 3]
    body = content[end_match.end() + 3:]

    try:
        frontmatter = yaml.safe_load(frontmatter_text)
        return frontmatter or {}, body
    except yaml.YAMLError:
        return {}, content


def verify_integrity(file_path: Path) -> tuple[bool, str]:
    """
    Verify integrity hash of an action file.

    Returns:
        tuple of (is_valid, message)
    """
    try:
        from src.common.integrity import verify_hash
    except ImportError:
        return True, "Integrity module not available (skipping verification)"

    content = file_path.read_text()
    frontmatter, body = parse_frontmatter(content)

    if "integrity_hash" not in frontmatter:
        return True, "No integrity hash found (legacy file)"

    stored_hash = frontmatter["integrity_hash"]
    action_type = frontmatter.get("type", "unknown")
    parameters = {
        "source": frontmatter.get("source", ""),
        "subject": frontmatter.get("subject", ""),
        "content": frontmatter.get("content", "")
    }
    created = frontmatter.get("timestamp", datetime.now().isoformat())

    try:
        is_valid = verify_hash(action_type, parameters, created, stored_hash)
        if is_valid:
            return True, "Integrity verified"
        else:
            return False, "Integrity check FAILED - file may have been tampered with"
    except Exception as e:
        return False, f"Integrity verification error: {e}"


def list_approvals():
    """List pending approval requests."""
    files = list(PENDING_DIR.glob("*.md"))
    if not files:
        print("No pending approvals.")
        return

    print(f"{'ID':<35} | {'Type':<12} | {'Priority':<8} | {'Summary'}")
    print("-" * 100)

    for f in files:
        content = f.read_text()
        frontmatter, _ = parse_frontmatter(content)

        type_str = frontmatter.get("type", "unknown")
        priority = frontmatter.get("priority", "normal")
        subject = frontmatter.get("subject", f.name)[:40]

        # Check integrity
        is_valid, _ = verify_integrity(f)
        integrity_mark = "✓" if is_valid else "⚠"

        print(f"{f.name:<35} | {type_str:<12} | {priority:<8} | {integrity_mark} {subject}")


def get_file(file_id: str) -> Path | None:
    """Find approval file by ID or partial match."""
    # Try exact match
    f = PENDING_DIR / file_id
    if f.exists():
        return f

    # Try with .md extension
    if not file_id.endswith(".md"):
        f = PENDING_DIR / f"{file_id}.md"
        if f.exists():
            return f

    # Search for partial match
    matches = list(PENDING_DIR.glob(f"*{file_id}*"))
    if len(matches) == 1:
        return matches[0]
    elif len(matches) > 1:
        print(f"Error: Ambiguous ID '{file_id}', matches multiple files:")
        for m in matches:
            print(f"  - {m.name}")
        return None

    print(f"Error: File '{file_id}' not found in {PENDING_DIR}")
    return None


def approve(file_id: str, skip_integrity: bool = False) -> bool:
    """Approve an action file."""
    f = get_file(file_id)
    if not f:
        return False

    # Verify integrity before approval
    if not skip_integrity:
        is_valid, message = verify_integrity(f)
        if not is_valid:
            print(f"✗ Cannot approve: {message}")
            print("  Use --skip-integrity to override (not recommended)")
            log_action("approve", f.name, "blocked", {"reason": message})
            return False
        print(f"✓ {message}")

    # Read content and update status
    content = f.read_text()
    frontmatter, body = parse_frontmatter(content)

    # Update frontmatter with approval info
    frontmatter["status"] = "approved"
    frontmatter["approved_at"] = datetime.now().isoformat()
    frontmatter["approved_by"] = "human_via_skill"

    # Rebuild content
    updated_content = "---\n" + yaml.dump(frontmatter, default_flow_style=False) + "---\n" + body

    # Move to Approved folder
    dest = APPROVED_DIR / f.name
    try:
        dest.write_text(updated_content)
        f.unlink()
        print(f"✓ Approved: {f.name} -> {dest}")
        log_action("approve", f.name, "success")
        return True
    except Exception as e:
        print(f"✗ Failed to approve {f.name}: {e}")
        log_action("approve", f.name, "failure", {"error": str(e)})
        return False


def reject(file_id: str, reason: str) -> bool:
    """Reject an action file with reason."""
    f = get_file(file_id)
    if not f:
        return False

    # Read content
    content = f.read_text()
    frontmatter, body = parse_frontmatter(content)

    # Update frontmatter with rejection info
    frontmatter["status"] = "rejected"
    frontmatter["rejected_at"] = datetime.now().isoformat()
    frontmatter["rejected_by"] = "human_via_skill"
    frontmatter["rejection_reason"] = reason

    # Add rejection note to body
    rejection_note = f"\n\n## Rejection Info\n\n- **Rejected At**: {datetime.now().isoformat()}\n- **Reason**: {reason}\n"

    # Rebuild content
    updated_content = "---\n" + yaml.dump(frontmatter, default_flow_style=False) + "---\n" + body + rejection_note

    dest = REJECTED_DIR / f.name
    try:
        dest.write_text(updated_content)
        f.unlink()
        print(f"✓ Rejected: {f.name} -> {dest}")
        log_action("reject", f.name, "success", {"reason": reason})
        return True
    except Exception as e:
        print(f"✗ Failed to reject {f.name}: {e}")
        log_action("reject", f.name, "failure", {"error": str(e)})
        return False


def verify_file(file_id: str) -> bool:
    """Verify integrity of a specific file."""
    f = get_file(file_id)
    if not f:
        return False

    is_valid, message = verify_integrity(f)

    if is_valid:
        print(f"✓ {f.name}: {message}")
        return True
    else:
        print(f"✗ {f.name}: {message}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Manage approval queue with integrity validation")
    parser.add_argument("--action", required=True,
                       choices=["list", "approve", "reject", "verify"])
    parser.add_argument("--id", help="File ID or name for approve/reject/verify")
    parser.add_argument("--reason", help="Reason for rejection")
    parser.add_argument("--skip-integrity", action="store_true",
                       help="Skip integrity check (not recommended)")

    args = parser.parse_args()
    setup_dirs()

    if args.action == "list":
        list_approvals()

    elif args.action == "approve":
        if not args.id:
            print("Error: --id required for approve")
            sys.exit(1)
        if not approve(args.id, args.skip_integrity):
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

    elif args.action == "verify":
        if not args.id:
            print("Error: --id required for verify")
            sys.exit(1)
        if not verify_file(args.id):
            sys.exit(1)


if __name__ == "__main__":
    main()
