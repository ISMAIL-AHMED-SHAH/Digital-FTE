#!/usr/bin/env python3
"""
Setup Vault - Verification
Validates vault structure was created correctly.
"""

import argparse
import sys
from pathlib import Path


def verify_vault(vault_path: Path) -> bool:
    """Verify vault structure and files exist."""

    # Check vault directory exists
    if not vault_path.exists():
        print(f"✗ Vault directory not found: {vault_path}")
        return False

    # Check required folders
    required_folders = [
        "Inbox",
        "Needs_Action",
        "Done",
        "Plans",
        "Logs",
        "Pending_Approval",
        "Approved",
        "Rejected"
    ]

    missing_folders = []
    for folder in required_folders:
        if not (vault_path / folder).exists():
            missing_folders.append(folder)

    if missing_folders:
        print(f"✗ Missing folders: {', '.join(missing_folders)}")
        return False

    # Check required files
    required_files = [
        "Dashboard.md",
        "Company_Handbook.md",
        "README.md",
        ".gitignore"
    ]

    missing_files = []
    for file in required_files:
        if not (vault_path / file).exists():
            missing_files.append(file)

    if missing_files:
        print(f"✗ Missing files: {', '.join(missing_files)}")
        return False

    return True


def main():
    parser = argparse.ArgumentParser(description="Verify AI Employee Vault structure")
    parser.add_argument("--vault-path", default="AI_Employee_Vault", help="Vault path")

    args = parser.parse_args()
    vault_path = Path(args.vault_path)

    if verify_vault(vault_path):
        print("✓ Verification passed - vault structure complete")
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
