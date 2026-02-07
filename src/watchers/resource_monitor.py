"""Resource Monitor for Silver Tier.

Monitors memory usage across all watcher processes and implements
graceful degradation when resource budgets are exceeded.

Features:
- Memory monitoring every 60 seconds
- Alert at 80% budget (400MB default)
- Graceful degradation at 100% budget (500MB)
- Automatic recovery when usage drops
- Metrics logging to vault

Implements FR-024, FR-025, FR-026, FR-027 from spec.md
and T051-T054 from tasks.md.

Usage:
    python -m src.watchers.resource_monitor

    # With custom budget
    MEMORY_BUDGET_MB=600 python -m src.watchers.resource_monitor

    # Dry-run mode (log only, don't pause watchers)
    DRY_RUN=true python -m src.watchers.resource_monitor
"""

import argparse
import asyncio
import json
import logging
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

import psutil
import yaml

from src.common.audit_logger import get_audit_logger
from src.common.vault import get_vault

logger = logging.getLogger(__name__)


class ResourceState(Enum):
    """Resource monitor states."""
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"
    DEGRADED = "degraded"


class WatcherInfo:
    """Information about a managed watcher process."""

    def __init__(
        self,
        name: str,
        priority: int,
        process_name: str,
        pm2_name: str | None = None
    ):
        """Initialize watcher info.

        Args:
            name: Watcher identifier
            priority: Priority (1=highest, 3=lowest)
            process_name: Process name to search for
            pm2_name: PM2 process name (if managed by PM2)
        """
        self.name = name
        self.priority = priority
        self.process_name = process_name
        self.pm2_name = pm2_name or name
        self.paused = False
        self.pid: int | None = None
        self.memory_mb: float = 0.0

    def __repr__(self) -> str:
        return f"WatcherInfo(name={self.name!r}, priority={self.priority}, paused={self.paused})"


class ResourceMonitor:
    """Resource monitor with graceful degradation.

    Monitors memory usage and pauses/resumes watchers based on
    resource constraints, following priority order.
    """

    # Default thresholds
    DEFAULT_BUDGET_MB = 500
    DEFAULT_ALERT_PERCENT = 80
    DEFAULT_RECOVERY_PERCENT = 70
    DEFAULT_CHECK_INTERVAL = 60

    def __init__(
        self,
        budget_mb: int | None = None,
        alert_threshold_percent: int | None = None,
        recovery_threshold_percent: int | None = None,
        check_interval_seconds: int | None = None,
        dry_run: bool = False,
        config_path: str | Path | None = None
    ):
        """Initialize resource monitor.

        Args:
            budget_mb: Total memory budget in MB
            alert_threshold_percent: Percentage at which to alert
            recovery_threshold_percent: Percentage at which to recover
            check_interval_seconds: Seconds between checks
            dry_run: If True, log actions without executing
            config_path: Path to watcher_config.yaml
        """
        # Load config
        self._load_config(config_path)

        # Override with parameters or environment
        self.budget_mb = budget_mb or int(
            os.environ.get("MEMORY_BUDGET_MB", self.DEFAULT_BUDGET_MB)
        )
        self.alert_threshold_percent = alert_threshold_percent or int(
            os.environ.get("MEMORY_ALERT_THRESHOLD_PERCENT", self.DEFAULT_ALERT_PERCENT)
        )
        self.recovery_threshold_percent = recovery_threshold_percent or int(
            os.environ.get("MEMORY_RECOVERY_THRESHOLD_PERCENT", self.DEFAULT_RECOVERY_PERCENT)
        )
        self.check_interval = check_interval_seconds or self.DEFAULT_CHECK_INTERVAL
        self.dry_run = dry_run or os.environ.get("DRY_RUN", "").lower() == "true"

        # Calculate thresholds in MB
        self.alert_threshold_mb = self.budget_mb * self.alert_threshold_percent / 100
        self.recovery_threshold_mb = self.budget_mb * self.recovery_threshold_percent / 100

        # State
        self._state = ResourceState.NORMAL
        self._running = False
        self._stop_event = asyncio.Event()

        # Managed watchers (ordered by priority - lowest priority first for pausing)
        self._watchers: list[WatcherInfo] = [
            WatcherInfo("linkedin-mcp", priority=3, process_name="linkedin", pm2_name="linkedin-mcp"),
            WatcherInfo("whatsapp-webhook", priority=2, process_name="whatsapp", pm2_name="whatsapp-webhook"),
            WatcherInfo("gmail-watcher", priority=1, process_name="gmail", pm2_name="gmail-watcher"),
            WatcherInfo("approval-watcher", priority=1, process_name="approval", pm2_name="approval-watcher"),
        ]

        # Audit logger and vault
        self._audit = get_audit_logger()
        self._vault = get_vault()

        logger.info(
            f"Resource monitor initialized: budget={self.budget_mb}MB, "
            f"alert={self.alert_threshold_mb:.0f}MB, "
            f"recovery={self.recovery_threshold_mb:.0f}MB, "
            f"dry_run={self.dry_run}"
        )

    def _load_config(self, config_path: str | Path | None) -> None:
        """Load configuration from YAML file."""
        path = Path(config_path) if config_path else Path("config/watcher_config.yaml")

        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    config = yaml.safe_load(f) or {}

                global_config = config.get("global", {})
                self.DEFAULT_BUDGET_MB = global_config.get("total_memory_budget_mb", 500)
                self.DEFAULT_ALERT_PERCENT = global_config.get("memory_alert_threshold_percent", 80)
                self.DEFAULT_RECOVERY_PERCENT = global_config.get("memory_recovery_threshold_percent", 70)
                self.DEFAULT_CHECK_INTERVAL = global_config.get("resource_check_interval_seconds", 60)

            except Exception as e:
                logger.warning(f"Failed to load config: {e}")

    @property
    def state(self) -> ResourceState:
        """Get current resource state."""
        return self._state

    @state.setter
    def state(self, value: ResourceState) -> None:
        """Set resource state and log transitions."""
        if self._state != value:
            old_state = self._state
            self._state = value
            logger.info(f"Resource state: {old_state.value} -> {value.value}")

            self._audit.log(
                component="resource_monitor",
                action_type="state_change",
                target=value.value,
                parameters={"from": old_state.value, "to": value.value}
            )

    def get_process_memory(self, pid: int) -> float:
        """Get memory usage of a specific process in MB.

        Args:
            pid: Process ID

        Returns:
            Memory usage in MB, or 0 if process not found
        """
        try:
            process = psutil.Process(pid)
            mem_info = process.memory_info()
            return mem_info.rss / (1024 * 1024)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return 0.0

    def find_watcher_processes(self) -> dict[str, list[psutil.Process]]:
        """Find all watcher processes by name pattern.

        Returns:
            Dict mapping watcher name to list of matching processes
        """
        results: dict[str, list[psutil.Process]] = {w.name: [] for w in self._watchers}

        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = proc.info.get('cmdline') or []
                    cmdline_str = ' '.join(cmdline).lower()

                    for watcher in self._watchers:
                        if watcher.process_name.lower() in cmdline_str:
                            results[watcher.name].append(proc)

                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

        except Exception as e:
            logger.warning(f"Error finding processes: {e}")

        return results

    def memory_usage_by_process(self) -> dict[str, float]:
        """Get memory usage for each watcher process.

        Returns:
            Dict mapping watcher name to memory usage in MB
        """
        usage: dict[str, float] = {}
        processes = self.find_watcher_processes()

        for watcher in self._watchers:
            total_mb = 0.0
            for proc in processes.get(watcher.name, []):
                try:
                    mem_info = proc.memory_info()
                    total_mb += mem_info.rss / (1024 * 1024)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            usage[watcher.name] = round(total_mb, 2)
            watcher.memory_mb = total_mb

        return usage

    def total_memory_usage(self) -> float:
        """Get total memory usage across all watchers.

        Returns:
            Total memory usage in MB
        """
        usage = self.memory_usage_by_process()
        return sum(usage.values())

    def exceeds_budget(self) -> bool:
        """Check if total memory exceeds the budget.

        Returns:
            True if over budget
        """
        return self.total_memory_usage() > self.budget_mb

    def exceeds_alert_threshold(self) -> bool:
        """Check if total memory exceeds alert threshold.

        Returns:
            True if over alert threshold
        """
        return self.total_memory_usage() > self.alert_threshold_mb

    def below_recovery_threshold(self) -> bool:
        """Check if total memory is below recovery threshold.

        Returns:
            True if below recovery threshold
        """
        return self.total_memory_usage() < self.recovery_threshold_mb

    def _pm2_command(self, action: str, process_name: str) -> bool:
        """Execute a PM2 command.

        Args:
            action: PM2 action (stop, start, restart)
            process_name: PM2 process name

        Returns:
            True if successful
        """
        if self.dry_run:
            logger.info(f"[DRY-RUN] Would execute: pm2 {action} {process_name}")
            return True

        try:
            result = subprocess.run(
                ["pm2", action, process_name],
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.returncode == 0

        except FileNotFoundError:
            logger.warning("PM2 not found - falling back to process signals")
            return False
        except subprocess.TimeoutExpired:
            logger.error(f"PM2 {action} {process_name} timed out")
            return False
        except Exception as e:
            logger.error(f"PM2 command failed: {e}")
            return False

    def pause_watcher(self, watcher: WatcherInfo) -> bool:
        """Pause a watcher process.

        Args:
            watcher: Watcher to pause

        Returns:
            True if successful
        """
        if watcher.paused:
            logger.debug(f"{watcher.name} already paused")
            return True

        logger.warning(f"Pausing watcher: {watcher.name} (priority={watcher.priority})")

        if self.dry_run:
            logger.info(f"[DRY-RUN] Would pause: {watcher.name}")
            watcher.paused = True
            return True

        # Try PM2 first
        if self._pm2_command("stop", watcher.pm2_name):
            watcher.paused = True

            self._audit.log(
                component="resource_monitor",
                action_type="watcher_paused",
                target=watcher.name,
                parameters={"reason": "memory_budget_exceeded"}
            )
            return True

        # Fall back to direct process control
        processes = self.find_watcher_processes()
        for proc in processes.get(watcher.name, []):
            try:
                proc.suspend()
                watcher.paused = True
                logger.info(f"Suspended process {proc.pid} for {watcher.name}")
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                logger.warning(f"Could not suspend {proc.pid}: {e}")

        return watcher.paused

    def resume_watcher(self, watcher: WatcherInfo) -> bool:
        """Resume a paused watcher.

        Args:
            watcher: Watcher to resume

        Returns:
            True if successful
        """
        if not watcher.paused:
            logger.debug(f"{watcher.name} not paused")
            return True

        logger.info(f"Resuming watcher: {watcher.name}")

        if self.dry_run:
            logger.info(f"[DRY-RUN] Would resume: {watcher.name}")
            watcher.paused = False
            return True

        # Try PM2 first
        if self._pm2_command("start", watcher.pm2_name):
            watcher.paused = False

            self._audit.log(
                component="resource_monitor",
                action_type="watcher_resumed",
                target=watcher.name,
                parameters={"reason": "memory_recovered"}
            )
            return True

        # Fall back to direct process control
        processes = self.find_watcher_processes()
        for proc in processes.get(watcher.name, []):
            try:
                proc.resume()
                watcher.paused = False
                logger.info(f"Resumed process {proc.pid} for {watcher.name}")
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                logger.warning(f"Could not resume {proc.pid}: {e}")

        return not watcher.paused

    def apply_graceful_degradation(self) -> list[str]:
        """Apply graceful degradation by pausing watchers in priority order.

        Pauses watchers from lowest priority (3) to highest (1).

        Returns:
            List of paused watcher names
        """
        paused = []

        # Sort by priority descending (pause lowest priority first)
        watchers_by_priority = sorted(self._watchers, key=lambda w: -w.priority)

        for watcher in watchers_by_priority:
            if not watcher.paused and self.exceeds_budget():
                if self.pause_watcher(watcher):
                    paused.append(watcher.name)

                # Re-check after each pause
                if not self.exceeds_budget():
                    break

        if paused:
            logger.warning(f"Graceful degradation: paused {paused}")
            self.state = ResourceState.DEGRADED

        return paused

    def apply_recovery(self) -> list[str]:
        """Resume paused watchers when resources recover.

        Resumes watchers from highest priority (1) to lowest (3).

        Returns:
            List of resumed watcher names
        """
        resumed = []

        # Sort by priority ascending (resume highest priority first)
        watchers_by_priority = sorted(self._watchers, key=lambda w: w.priority)

        for watcher in watchers_by_priority:
            if watcher.paused and self.below_recovery_threshold():
                if self.resume_watcher(watcher):
                    resumed.append(watcher.name)

        if resumed:
            logger.info(f"Recovery: resumed {resumed}")

            # Check if all watchers are running
            if not any(w.paused for w in self._watchers):
                self.state = ResourceState.NORMAL

        return resumed

    def get_metrics(self) -> dict[str, Any]:
        """Get current metrics snapshot.

        Returns:
            Metrics dictionary
        """
        usage = self.memory_usage_by_process()
        total = sum(usage.values())

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "state": self.state.value,
            "memory": {
                "total_mb": round(total, 2),
                "budget_mb": self.budget_mb,
                "usage_percent": round(total / self.budget_mb * 100, 1) if self.budget_mb > 0 else 0,
                "alert_threshold_mb": round(self.alert_threshold_mb, 2),
                "recovery_threshold_mb": round(self.recovery_threshold_mb, 2),
                "by_process": usage
            },
            "watchers": {
                w.name: {
                    "priority": w.priority,
                    "paused": w.paused,
                    "memory_mb": round(w.memory_mb, 2)
                }
                for w in self._watchers
            }
        }

    def log_metrics(self) -> Path | None:
        """Write metrics to daily JSON file in vault.

        Returns:
            Path to metrics file, or None if failed
        """
        metrics = self.get_metrics()

        try:
            logs_dir = self._vault.get_folder("logs")
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            metrics_file = logs_dir / f"metrics-{date_str}.json"

            # Append to JSON-lines file
            with open(metrics_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(metrics) + "\n")

            logger.debug(f"Logged metrics to {metrics_file}")
            return metrics_file

        except Exception as e:
            logger.error(f"Failed to log metrics: {e}")
            return None

    async def check_resources(self) -> None:
        """Perform a single resource check cycle."""
        total = self.total_memory_usage()

        logger.debug(
            f"Resource check: {total:.1f}MB / {self.budget_mb}MB "
            f"({total/self.budget_mb*100:.1f}%)"
        )

        # Log metrics
        self.log_metrics()

        # Check thresholds and take action
        if self.exceeds_budget():
            # Critical - apply graceful degradation
            if self.state != ResourceState.DEGRADED:
                logger.warning(
                    f"Memory budget exceeded: {total:.1f}MB > {self.budget_mb}MB"
                )
                self.state = ResourceState.CRITICAL

            self.apply_graceful_degradation()

        elif self.exceeds_alert_threshold():
            # Warning - log alert
            if self.state == ResourceState.NORMAL:
                logger.warning(
                    f"Memory alert threshold exceeded: {total:.1f}MB > {self.alert_threshold_mb:.1f}MB"
                )
                self.state = ResourceState.WARNING

                self._audit.log(
                    component="resource_monitor",
                    action_type="memory_alert",
                    target="system",
                    level="WARNING",
                    parameters={
                        "total_mb": round(total, 2),
                        "threshold_mb": round(self.alert_threshold_mb, 2)
                    }
                )

                # Create alert file in vault
                self._create_alert_file(total)

        elif self.below_recovery_threshold():
            # Recovery - resume paused watchers
            if self.state in (ResourceState.DEGRADED, ResourceState.CRITICAL, ResourceState.WARNING):
                self.apply_recovery()

    def _create_alert_file(self, current_usage_mb: float) -> None:
        """Create an alert file in the vault.

        Args:
            current_usage_mb: Current memory usage
        """
        try:
            now = datetime.now(timezone.utc)
            filename = f"memory-alert-{now.strftime('%Y%m%d-%H%M%S')}.md"

            content = f"""---
type: alert
category: resource
severity: warning
timestamp: "{now.isoformat()}"
---

# Memory Alert

**Time**: {now.strftime("%Y-%m-%d %H:%M:%S UTC")}

## Status

- **Current Usage**: {current_usage_mb:.1f} MB
- **Budget**: {self.budget_mb} MB
- **Usage**: {current_usage_mb/self.budget_mb*100:.1f}%
- **Alert Threshold**: {self.alert_threshold_mb:.1f} MB ({self.alert_threshold_percent}%)

## Action Required

Memory usage is approaching the budget limit. If usage continues to increase,
the resource monitor will begin pausing watchers to prevent system instability.

### Watcher Status

"""
            for watcher in self._watchers:
                status = "PAUSED" if watcher.paused else "Running"
                content += f"- {watcher.name}: {watcher.memory_mb:.1f} MB ({status})\n"

            content += """

---

*This alert was automatically generated by the resource monitor.*
"""

            self._vault.write_file(
                folder_key="alerts",
                filename=filename,
                content=content,
                overwrite=False
            )

            logger.info(f"Created alert file: {filename}")

        except Exception as e:
            logger.error(f"Failed to create alert file: {e}")

    async def run(self) -> None:
        """Main monitoring loop."""
        logger.info("Starting resource monitor...")
        self._running = True

        try:
            while not self._stop_event.is_set():
                await self.check_resources()

                # Wait for next check interval
                try:
                    await asyncio.wait_for(
                        self._stop_event.wait(),
                        timeout=self.check_interval
                    )
                except asyncio.TimeoutError:
                    pass  # Normal timeout, continue monitoring

        except asyncio.CancelledError:
            logger.info("Resource monitor cancelled")
        finally:
            self._running = False
            logger.info("Resource monitor stopped")

    def stop(self) -> None:
        """Request graceful shutdown."""
        logger.info("Stopping resource monitor...")
        self._stop_event.set()

    def get_stats(self) -> dict[str, Any]:
        """Get monitor statistics."""
        return {
            "state": self.state.value,
            "running": self._running,
            "budget_mb": self.budget_mb,
            "alert_threshold_mb": self.alert_threshold_mb,
            "recovery_threshold_mb": self.recovery_threshold_mb,
            "check_interval_seconds": self.check_interval,
            "dry_run": self.dry_run,
            "watchers": [
                {
                    "name": w.name,
                    "priority": w.priority,
                    "paused": w.paused,
                    "memory_mb": w.memory_mb
                }
                for w in self._watchers
            ]
        }


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="AI Employee Resource Monitor"
    )
    parser.add_argument(
        "--budget",
        type=int,
        default=None,
        help="Memory budget in MB"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="Check interval in seconds"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Log actions without executing"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run single check and exit"
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Print current stats and exit"
    )
    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Create monitor
    monitor = ResourceMonitor(
        budget_mb=args.budget,
        check_interval_seconds=args.interval,
        dry_run=args.dry_run
    )

    # Handle stats mode
    if args.stats:
        import pprint
        pprint.pprint(monitor.get_metrics())
        return

    # Handle single check mode
    if args.once:
        await monitor.check_resources()
        print(json.dumps(monitor.get_metrics(), indent=2))
        return

    # Set up signal handlers
    loop = asyncio.get_event_loop()

    def signal_handler():
        monitor.stop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, signal_handler)
        except NotImplementedError:
            # Windows doesn't support add_signal_handler
            signal.signal(sig, lambda s, f: monitor.stop())

    # Run monitor
    await monitor.run()


if __name__ == "__main__":
    asyncio.run(main())
