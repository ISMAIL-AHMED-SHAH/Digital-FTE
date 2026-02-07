#!/usr/bin/env python3
"""
Watcher Manager Skill - Main Operation
Manages Silver Tier watcher processes using PM2.

Supports:
- start: Start all watchers or specific watcher
- stop: Stop all watchers or specific watcher
- restart: Restart watchers
- status: Show status of all watchers
- logs: View watcher logs

Watchers managed:
- gmail-watcher: Gmail email detection (polling)
- whatsapp-webhook: WhatsApp message webhook (HTTP server)
- resource-monitor: Memory monitoring and graceful degradation
- scheduler: Task scheduler for daily briefings
"""

import argparse
import subprocess
import sys
import json
from pathlib import Path
from datetime import datetime

# Configuration
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
PM2_CONFIG = PROJECT_ROOT / "config" / "pm2.config.js"

# Watcher definitions with their PM2 names and scripts
WATCHERS = {
    "gmail": {
        "pm2_name": "gmail-watcher",
        "script": "src/watchers/gmail_watcher.py",
        "interpreter": "python3",
        "priority": 1,
        "memory_limit": "100M"
    },
    "whatsapp": {
        "pm2_name": "whatsapp-webhook",
        "script": "src/watchers/whatsapp_webhook.py",
        "interpreter": "python3",
        "priority": 2,
        "memory_limit": "100M"
    },
    "resource-monitor": {
        "pm2_name": "resource-monitor",
        "script": "src/watchers/resource_monitor.py",
        "interpreter": "python3",
        "priority": 0,  # Highest - must always run
        "memory_limit": "50M"
    },
    "scheduler": {
        "pm2_name": "task-scheduler",
        "script": "src/watchers/scheduler.py",
        "interpreter": "python3",
        "priority": 3,
        "memory_limit": "50M"
    }
}


def check_pm2_installed() -> bool:
    """Check if PM2 is installed."""
    try:
        result = subprocess.run(
            ["pm2", "--version"],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def get_pm2_status() -> dict:
    """Get status of all PM2 processes."""
    try:
        result = subprocess.run(
            ["pm2", "jlist"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            processes = json.loads(result.stdout)
            return {p["name"]: p for p in processes}
        return {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def start_watcher(watcher_name: str = None) -> bool:
    """Start watcher(s) using PM2."""
    if not check_pm2_installed():
        print("✗ PM2 not installed. Install with: npm install -g pm2")
        return False

    if watcher_name:
        # Start specific watcher
        if watcher_name not in WATCHERS:
            print(f"✗ Unknown watcher: {watcher_name}")
            print(f"  Available: {', '.join(WATCHERS.keys())}")
            return False

        watcher = WATCHERS[watcher_name]
        script_path = PROJECT_ROOT / watcher["script"]

        if not script_path.exists():
            print(f"✗ Watcher script not found: {watcher['script']}")
            return False

        # Check if already running
        status = get_pm2_status()
        if watcher["pm2_name"] in status:
            proc = status[watcher["pm2_name"]]
            if proc.get("pm2_env", {}).get("status") == "online":
                print(f"⚠ {watcher_name} already running")
                return True

        # Start the watcher
        result = subprocess.run([
            "pm2", "start", str(script_path),
            "--name", watcher["pm2_name"],
            "--interpreter", watcher["interpreter"],
            "--max-memory-restart", watcher["memory_limit"],
            "--cwd", str(PROJECT_ROOT)
        ], capture_output=True, text=True)

        if result.returncode == 0:
            subprocess.run(["pm2", "save"], capture_output=True)
            print(f"✓ Started {watcher_name}")
            return True
        else:
            print(f"✗ Failed to start {watcher_name}: {result.stderr}")
            return False
    else:
        # Start all watchers using PM2 ecosystem file
        if PM2_CONFIG.exists():
            result = subprocess.run(
                ["pm2", "start", str(PM2_CONFIG)],
                capture_output=True,
                text=True,
                cwd=str(PROJECT_ROOT)
            )
            if result.returncode == 0:
                subprocess.run(["pm2", "save"], capture_output=True)
                print("✓ Started all watchers via ecosystem config")
                return True
            else:
                print(f"✗ Failed to start watchers: {result.stderr}")
                return False
        else:
            # Start each watcher individually
            success = True
            for name in WATCHERS:
                if not start_watcher(name):
                    success = False
            return success


def stop_watcher(watcher_name: str = None) -> bool:
    """Stop watcher(s) using PM2."""
    if not check_pm2_installed():
        print("✗ PM2 not installed")
        return False

    if watcher_name:
        if watcher_name not in WATCHERS:
            print(f"✗ Unknown watcher: {watcher_name}")
            return False

        pm2_name = WATCHERS[watcher_name]["pm2_name"]
        result = subprocess.run(
            ["pm2", "stop", pm2_name],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print(f"✓ Stopped {watcher_name}")
            return True
        else:
            print(f"⚠ {watcher_name} not running or already stopped")
            return True
    else:
        # Stop all watchers
        for name in WATCHERS:
            stop_watcher(name)
        subprocess.run(["pm2", "save"], capture_output=True)
        print("✓ Stopped all watchers")
        return True


def restart_watcher(watcher_name: str = None) -> bool:
    """Restart watcher(s)."""
    if watcher_name:
        if watcher_name not in WATCHERS:
            print(f"✗ Unknown watcher: {watcher_name}")
            return False

        pm2_name = WATCHERS[watcher_name]["pm2_name"]
        result = subprocess.run(
            ["pm2", "restart", pm2_name],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print(f"✓ Restarted {watcher_name}")
            return True
        else:
            # Try starting if not already running
            return start_watcher(watcher_name)
    else:
        # Restart all
        result = subprocess.run(
            ["pm2", "restart", "all"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print("✓ Restarted all watchers")
            return True
        else:
            print("⚠ Some watchers may not be running, starting them...")
            return start_watcher()


def show_status() -> bool:
    """Show status of all watchers."""
    if not check_pm2_installed():
        print("✗ PM2 not installed. Install with: npm install -g pm2")
        return False

    status = get_pm2_status()

    print("Silver Tier Watcher Status")
    print("=" * 70)
    print(f"{'Watcher':<20} | {'PM2 Name':<18} | {'Status':<10} | {'Memory':<10} | {'Uptime'}")
    print("-" * 70)

    for name, config in WATCHERS.items():
        pm2_name = config["pm2_name"]

        if pm2_name in status:
            proc = status[pm2_name]
            env = proc.get("pm2_env", {})

            proc_status = env.get("status", "unknown")
            memory_mb = proc.get("monit", {}).get("memory", 0) / (1024 * 1024)
            uptime_ms = env.get("pm_uptime", 0)

            if uptime_ms:
                uptime_sec = (datetime.now().timestamp() * 1000 - uptime_ms) / 1000
                if uptime_sec > 3600:
                    uptime_str = f"{uptime_sec / 3600:.1f}h"
                elif uptime_sec > 60:
                    uptime_str = f"{uptime_sec / 60:.1f}m"
                else:
                    uptime_str = f"{uptime_sec:.0f}s"
            else:
                uptime_str = "-"

            status_icon = "✓" if proc_status == "online" else "✗"
            print(f"{name:<20} | {pm2_name:<18} | {status_icon} {proc_status:<8} | {memory_mb:>6.1f} MB | {uptime_str}")
        else:
            print(f"{name:<20} | {pm2_name:<18} | ✗ not found | {'N/A':>9} | -")

    print("-" * 70)

    # Show PM2 ecosystem config status
    if PM2_CONFIG.exists():
        print(f"✓ PM2 ecosystem config: {PM2_CONFIG}")
    else:
        print(f"⚠ PM2 ecosystem config not found: {PM2_CONFIG}")

    return True


def show_logs(watcher_name: str = None, lines: int = 50) -> bool:
    """Show watcher logs."""
    if not check_pm2_installed():
        print("✗ PM2 not installed")
        return False

    if watcher_name:
        if watcher_name not in WATCHERS:
            print(f"✗ Unknown watcher: {watcher_name}")
            return False
        pm2_name = WATCHERS[watcher_name]["pm2_name"]
    else:
        pm2_name = "all"

    subprocess.run(["pm2", "logs", pm2_name, "--lines", str(lines)])
    return True


def main():
    parser = argparse.ArgumentParser(description="Manage Silver Tier watchers via PM2")
    parser.add_argument("--action", required=True,
                       choices=["start", "stop", "restart", "status", "logs"])
    parser.add_argument("--watcher", "-w",
                       choices=list(WATCHERS.keys()),
                       help="Specific watcher to manage (default: all)")
    parser.add_argument("--lines", "-n", type=int, default=50,
                       help="Number of log lines to show (default: 50)")

    args = parser.parse_args()

    if args.action == "start":
        if not start_watcher(args.watcher):
            sys.exit(1)

    elif args.action == "stop":
        if not stop_watcher(args.watcher):
            sys.exit(1)

    elif args.action == "restart":
        if not restart_watcher(args.watcher):
            sys.exit(1)

    elif args.action == "status":
        if not show_status():
            sys.exit(1)

    elif args.action == "logs":
        if not show_logs(args.watcher, args.lines):
            sys.exit(1)


if __name__ == "__main__":
    main()
