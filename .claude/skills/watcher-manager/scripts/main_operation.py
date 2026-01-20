#!/usr/bin/env python3
"""
Watcher Manager - Main Operation
Manages watcher processes using PM2.
"""

import argparse
import subprocess
import sys
from pathlib import Path


def manage_watcher(action: str, watcher_type: str, vault_path: Path) -> bool:
    """Manage watcher process with PM2."""

    # Check if PM2 is installed
    try:
        subprocess.run(["pm2", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("✗ PM2 not installed. Install with: npm install -g pm2")
        return False

    # Determine watcher script path
    if watcher_type == "filesystem":
        script = "src/watchers/filesystem_watcher.py"
    elif watcher_type == "gmail":
        script = "src/watchers/gmail_watcher.py"
    else:
        print(f"✗ Invalid watcher type: {watcher_type}")
        return False

    # Check if script exists
    if not Path(script).exists():
        print(f"✗ Watcher script not found: {script}")
        print("  Watcher implementation needed")
        return False

    # Execute action
    if action == "start":
        # Check if already running
        result = subprocess.run(
            ["pm2", "list"],
            capture_output=True,
            text=True
        )
        if "ai-watcher" in result.stdout and "online" in result.stdout:
            print("⚠️  Watcher already running")
            return True

        # Start watcher
        result = subprocess.run([
            "pm2", "start", script,
            "--name", "ai-watcher",
            "--interpreter", "python3",
            "--max-memory-restart", "50M"
        ], capture_output=True, text=True)

        if result.returncode == 0:
            subprocess.run(["pm2", "save"], capture_output=True)
            print("✓ Watcher started")
            return True
        else:
            print(f"✗ Failed to start watcher: {result.stderr}")
            return False

    elif action == "stop":
        result = subprocess.run(
            ["pm2", "stop", "ai-watcher"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            subprocess.run(["pm2", "delete", "ai-watcher"], capture_output=True)
            subprocess.run(["pm2", "save"], capture_output=True)
            print("✓ Watcher stopped")
            return True
        else:
            print("⚠️  Watcher not running")
            return True

    elif action == "restart":
        result = subprocess.run(
            ["pm2", "restart", "ai-watcher"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print("✓ Watcher restarted")
            return True
        else:
            print("✗ Failed to restart watcher")
            return False

    elif action == "status":
        result = subprocess.run(
            ["pm2", "list"],
            capture_output=True,
            text=True
        )
        if "ai-watcher" in result.stdout:
            if "online" in result.stdout:
                print("✓ Watcher is running")
            else:
                print("⚠️  Watcher is stopped")
            return True
        else:
            print("⚠️  Watcher not found")
            return True

    return False


def main():
    parser = argparse.ArgumentParser(description="Manage AI Employee watcher")
    parser.add_argument("--action", required=True, choices=["start", "stop", "restart", "status"])
    parser.add_argument("--watcher-type", default="filesystem", choices=["filesystem", "gmail"])
    parser.add_argument("--vault-path", default="AI_Employee_Vault")

    args = parser.parse_args()
    vault_path = Path(args.vault_path)

    success = manage_watcher(args.action, args.watcher_type, vault_path)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
