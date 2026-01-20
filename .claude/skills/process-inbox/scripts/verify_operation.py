#!/usr/bin/env python3
"""
Process Inbox - Verification
Verifies inbox processing results.
"""

import argparse
import sys
from pathlib import Path


def verify_processing(vault_path: Path) -> bool:
    """Verify inbox processing completed successfully."""

    needs_action = vault_path / "Needs_Action"
    done = vault_path / "Done"
    plans = vault_path / "Plans"
    dashboard = vault_path / "Dashboard.md"

    # Check folders exist
    if not needs_action.exists() or not done.exists() or not plans.exists():
        print("✗ Required folders missing")
        return False

    # Check dashboard exists
    if not dashboard.exists():
        print("✗ Dashboard.md not found")
        return False

    # Count files
    pending_count = len(list(needs_action.glob("*.md")))
    done_count = len(list(done.glob("*.md")))
    plans_count = len(list(plans.glob("*.md")))

    print(f"✓ Verification passed")
    print(f"  Pending: {pending_count} files")
    print(f"  Done: {done_count} files")
    print(f"  Plans: {plans_count} files")

    return True


def main():
    parser = argparse.ArgumentParser(description="Verify inbox processing")
    parser.add_argument("--vault-path", default="AI_Employee_Vault")

    args = parser.parse_args()
    vault_path = Path(args.vault_path)

    if verify_processing(vault_path):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
