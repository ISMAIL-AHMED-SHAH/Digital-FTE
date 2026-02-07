"""Watchdog Process Monitor (FR-027).

Monitors and manages long-running processes, providing:
- Auto-restart on crash
- Health check monitoring
- Process lifecycle management

Full implementation will be completed in Phase 8 (User Story 6).
This stub provides the interface needed for Gold Tier initialization.
"""

import logging
import subprocess
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)


class ProcessStatus(str, Enum):
    """Status of a monitored process."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    CRASHED = "crashed"
    RESTARTING = "restarting"


@dataclass
class ProcessConfig:
    """Configuration for a monitored process.

    Attributes:
        name: Unique process identifier
        command: Command to execute
        args: Command arguments
        working_dir: Working directory for the process
        env: Environment variables
        restart_on_crash: Auto-restart if process crashes
        max_restarts: Maximum restart attempts before giving up
        restart_delay: Seconds to wait before restart
        health_check: Optional health check function
        health_check_interval: Seconds between health checks
    """
    name: str
    command: str
    args: list[str] = field(default_factory=list)
    working_dir: Path | str | None = None
    env: dict[str, str] | None = None
    restart_on_crash: bool = True
    max_restarts: int = 5
    restart_delay: float = 5.0
    health_check: Callable[[], bool] | None = None
    health_check_interval: float = 30.0


@dataclass
class ProcessState:
    """Current state of a monitored process.

    Attributes:
        config: Process configuration
        status: Current status
        pid: Process ID if running
        start_time: When process was started
        restart_count: Number of restarts since last manual start
        last_error: Last error message if any
        last_health_check: Last health check timestamp
        healthy: Whether last health check passed
    """
    config: ProcessConfig
    status: ProcessStatus = ProcessStatus.STOPPED
    pid: int | None = None
    start_time: datetime | None = None
    restart_count: int = 0
    last_error: str | None = None
    last_health_check: datetime | None = None
    healthy: bool = True


class Watchdog:
    """Process watchdog for monitoring and auto-restart.

    Usage:
        watchdog = Watchdog()

        # Register a process
        watchdog.register(ProcessConfig(
            name="odoo-mcp",
            command="node",
            args=["src/mcp_servers/odoo/dist/index.js"],
            restart_on_crash=True
        ))

        # Start monitoring
        watchdog.start("odoo-mcp")

        # Check status
        status = watchdog.get_status("odoo-mcp")

        # Stop monitoring
        watchdog.stop_all()
    """

    def __init__(self, log_dir: Path | str | None = None):
        """Initialize watchdog.

        Args:
            log_dir: Directory for process logs
        """
        self.log_dir = Path(log_dir) if log_dir else None
        self._processes: dict[str, ProcessState] = {}
        self._subprocess_handles: dict[str, subprocess.Popen] = {}
        self._monitoring = False
        self._monitor_thread: threading.Thread | None = None
        self._lock = threading.RLock()

        if self.log_dir:
            self.log_dir.mkdir(parents=True, exist_ok=True)

    def register(self, config: ProcessConfig) -> None:
        """Register a process for monitoring.

        Args:
            config: Process configuration
        """
        with self._lock:
            if config.name in self._processes:
                logger.warning(f"Process {config.name} already registered, updating config")

            self._processes[config.name] = ProcessState(config=config)
            logger.info(f"Registered process: {config.name}")

    def unregister(self, name: str) -> bool:
        """Unregister a process.

        Args:
            name: Process name

        Returns:
            True if unregistered, False if not found
        """
        with self._lock:
            if name not in self._processes:
                return False

            state = self._processes[name]
            if state.status == ProcessStatus.RUNNING:
                self.stop(name)

            del self._processes[name]
            logger.info(f"Unregistered process: {name}")
            return True

    def start(self, name: str) -> bool:
        """Start a registered process.

        Args:
            name: Process name

        Returns:
            True if started, False if failed
        """
        with self._lock:
            if name not in self._processes:
                logger.error(f"Process not registered: {name}")
                return False

            state = self._processes[name]
            if state.status == ProcessStatus.RUNNING:
                logger.warning(f"Process already running: {name}")
                return True

            return self._start_process(state)

    def _start_process(self, state: ProcessState) -> bool:
        """Internal: Start a process.

        Args:
            state: Process state

        Returns:
            True if started successfully
        """
        config = state.config
        state.status = ProcessStatus.STARTING

        try:
            cmd = [config.command] + config.args

            # Prepare environment
            env = None
            if config.env:
                import os
                env = os.environ.copy()
                env.update(config.env)

            # Prepare working directory
            cwd = Path(config.working_dir) if config.working_dir else None

            # Start process
            proc = subprocess.Popen(
                cmd,
                cwd=cwd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            self._subprocess_handles[config.name] = proc
            state.pid = proc.pid
            state.status = ProcessStatus.RUNNING
            state.start_time = datetime.now(timezone.utc)
            state.last_error = None

            logger.info(f"Started process {config.name} (PID: {proc.pid})")
            return True

        except Exception as e:
            state.status = ProcessStatus.CRASHED
            state.last_error = str(e)
            logger.error(f"Failed to start {config.name}: {e}")
            return False

    def stop(self, name: str, timeout: float = 10.0) -> bool:
        """Stop a running process.

        Args:
            name: Process name
            timeout: Seconds to wait for graceful shutdown

        Returns:
            True if stopped, False if failed
        """
        with self._lock:
            if name not in self._processes:
                return False

            state = self._processes[name]
            if state.status != ProcessStatus.RUNNING:
                return True

            state.status = ProcessStatus.STOPPING
            proc = self._subprocess_handles.get(name)

            if proc:
                try:
                    proc.terminate()
                    proc.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    proc.kill()
                except Exception as e:
                    logger.error(f"Error stopping {name}: {e}")

                del self._subprocess_handles[name]

            state.status = ProcessStatus.STOPPED
            state.pid = None
            state.restart_count = 0
            logger.info(f"Stopped process: {name}")
            return True

    def restart(self, name: str) -> bool:
        """Restart a process.

        Args:
            name: Process name

        Returns:
            True if restarted
        """
        self.stop(name)
        time.sleep(0.5)
        return self.start(name)

    def get_status(self, name: str) -> ProcessState | None:
        """Get status of a process.

        Args:
            name: Process name

        Returns:
            ProcessState or None if not found
        """
        return self._processes.get(name)

    def get_all_status(self) -> dict[str, ProcessState]:
        """Get status of all registered processes."""
        return self._processes.copy()

    def start_monitoring(self, interval: float = 5.0) -> None:
        """Start background monitoring thread.

        Args:
            interval: Seconds between checks
        """
        if self._monitoring:
            return

        self._monitoring = True

        def monitor_loop():
            while self._monitoring:
                self._check_processes()
                time.sleep(interval)

        self._monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info("Started process monitoring")

    def stop_monitoring(self) -> None:
        """Stop background monitoring."""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
            self._monitor_thread = None
        logger.info("Stopped process monitoring")

    def stop_all(self) -> None:
        """Stop all processes and monitoring."""
        self.stop_monitoring()

        with self._lock:
            for name in list(self._processes.keys()):
                self.stop(name)

    def _check_processes(self) -> None:
        """Internal: Check all processes and handle crashes."""
        with self._lock:
            for name, state in self._processes.items():
                if state.status != ProcessStatus.RUNNING:
                    continue

                proc = self._subprocess_handles.get(name)
                if not proc:
                    continue

                # Check if process is still running
                poll_result = proc.poll()
                if poll_result is not None:
                    # Process has exited
                    state.status = ProcessStatus.CRASHED
                    state.last_error = f"Process exited with code {poll_result}"
                    logger.warning(f"Process {name} crashed (exit code: {poll_result})")

                    # Handle auto-restart
                    config = state.config
                    if config.restart_on_crash and state.restart_count < config.max_restarts:
                        state.restart_count += 1
                        state.status = ProcessStatus.RESTARTING
                        logger.info(
                            f"Auto-restarting {name} (attempt {state.restart_count}/{config.max_restarts})"
                        )
                        time.sleep(config.restart_delay)
                        self._start_process(state)

                # Run health check if configured
                if state.config.health_check:
                    if state.last_health_check:
                        elapsed = (datetime.now(timezone.utc) - state.last_health_check).total_seconds()
                        if elapsed < state.config.health_check_interval:
                            continue

                    try:
                        state.healthy = state.config.health_check()
                        state.last_health_check = datetime.now(timezone.utc)
                        if not state.healthy:
                            logger.warning(f"Health check failed for {name}")
                    except Exception as e:
                        state.healthy = False
                        logger.error(f"Health check error for {name}: {e}")

    def get_metrics(self) -> dict[str, Any]:
        """Get monitoring metrics.

        Returns:
            Dict with process counts by status
        """
        with self._lock:
            metrics = {
                "total": len(self._processes),
                "running": 0,
                "stopped": 0,
                "crashed": 0,
                "unhealthy": 0
            }

            for state in self._processes.values():
                if state.status == ProcessStatus.RUNNING:
                    metrics["running"] += 1
                elif state.status == ProcessStatus.STOPPED:
                    metrics["stopped"] += 1
                elif state.status == ProcessStatus.CRASHED:
                    metrics["crashed"] += 1

                if not state.healthy:
                    metrics["unhealthy"] += 1

            return metrics
