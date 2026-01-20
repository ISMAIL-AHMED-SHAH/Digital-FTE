#!/usr/bin/env python3
"""
View Dashboard - Main Operation
Displays AI Employee system status from Dashboard.md.
"""

import argparse
import sys
from pathlib import Path


def display_dashboard(vault_path: Path, format_type: str) -> bool:
    """Display dashboard content in specified format."""

    dashboard = vault_path / "Dashboard.md"

    if not dashboard.exists():
        print(f"✗ Dashboard not found: {dashboard}")
        return False

    content = dashboard.read_text()

    if format_type == "full":
        # Display full dashboard
        print("=" * 60)
        print("AI EMPLOYEE DASHBOARD - BRONZE TIER")
        print("=" * 60)
        print()
        print(content)
        print()
        print("=" * 60)

    elif format_type == "summary":
        # Extract key metrics
        lines = content.split('\n')

        print("AI Employee - Quick Summary")
        print("-" * 30)

        # Extract watcher status
        for line in lines:
            if "**Watcher**:" in line:
                status = line.split("**Watcher**:")[1].strip()
                if "Running" in status:
                    print(f"✅ Watcher: {status}")
                else:
                    print(f"⚠️  Watcher: {status}")
                break

        # Extract pending count
        for line in lines:
            if "**Count**:" in line:
                count = line.split("**Count**:")[1].strip()
                print(f"📥 Pending: {count} actions")
                break

        # Extract files processed today
        for line in lines:
            if "**Files Processed Today**:" in line:
                count = line.split("**Files Processed Today**:")[1].strip()
                print(f"📁 Today: {count} files")
                break

    elif format_type == "status":
        # Minimal status check
        lines = content.split('\n')

        for line in lines:
            if "**Watcher**:" in line:
                status = line.split("**Watcher**:")[1].strip()
                if "Running" in status:
                    print("✅ System: Operational")
                else:
                    print("⚠️  System: Watcher not running")
                break

        for line in lines:
            if "**Count**:" in line:
                count = line.split("**Count**:")[1].strip()
                print(f"📥 Pending: {count}")
                break

    return True


def main():
    parser = argparse.ArgumentParser(description="View AI Employee dashboard")
    parser.add_argument("--vault-path", default="AI_Employee_Vault")
    parser.add_argument("--format", default="full", choices=["full", "summary", "status"])

    args = parser.parse_args()
    vault_path = Path(args.vault_path)

    if not vault_path.exists():
        print(f"✗ Vault not found: {vault_path}")
        sys.exit(1)

    success = display_dashboard(vault_path, args.format)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
