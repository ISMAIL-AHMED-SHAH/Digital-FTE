#!/usr/bin/env python3
"""
View Dashboard - Verification
Verifies dashboard is readable and contains expected sections.
"""

import argparse
import sys
from pathlib import Path


def verify_dashboard(vault_path: Path) -> bool:
    """Verify dashboard exists and is readable."""

    dashboard = vault_path / "Dashboard.md"

    if not dashboard.exists():
        print(f"✗ Dashboard not found: {dashboard}")
        return False

    # Read dashboard content
    try:
        content = dashboard.read_text()
    except Exception as e:
        print(f"✗ Cannot read dashboard: {e}")
        return False

    # Check for required sections
    required_sections = [
        "System Status",
        "Pending Actions",
        "Recent Activity",
        "Quick Stats"
    ]

    missing_sections = []
    for section in required_sections:
        if section not in content:
            missing_sections.append(section)

    if missing_sections:
        print(f"✗ Missing sections: {', '.join(missing_sections)}")
        return False

    print("✓ Dashboard verified - all sections present")
    return True


def main():
    parser = argparse.ArgumentParser(description="Verify dashboard")
    parser.add_argument("--vault-path", default="AI_Employee_Vault")

    args = parser.parse_args()
    vault_path = Path(args.vault_path)

    if verify_dashboard(vault_path):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
