#!/usr/bin/env python3
"""
Watcher Manager - Verification
Verifies watcher process status.
"""

import subprocess
import sys


def verify_watcher() -> bool:
    """Verify watcher is in expected state."""

    try:
        # Check PM2 is available
        subprocess.run(["pm2", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("✗ PM2 not available")
        return False

    # Check watcher process status
    result = subprocess.run(
        ["pm2", "list"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print("✗ Failed to query PM2")
        return False

    # Watcher can be running or stopped - both are valid states
    if "ai-watcher" in result.stdout:
        if "online" in result.stdout:
            print("✓ Watcher is running")
        else:
            print("✓ Watcher is stopped")
    else:
        print("✓ Watcher not configured")

    return True


def main():
    if verify_watcher():
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
