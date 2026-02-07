"""Abstract Base Watcher Class for Silver Tier.

Provides common functionality for all external service watchers:
- Memory monitoring and limits
- Dry-run mode support
- Logging integration
- Lifecycle management (start/stop)
- Graceful shutdown

Implements memory budget requirements from FR-024, FR-025, FR-026.
"""

import asyncio
import logging
import os
import signal
import threading
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable

import psutil

from src.common.audit_logger import get_audit_logger

logger = logging.getLogger(__name__)


class WatcherStatus(Enum):
    """Watcher lifecycle states."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    ERROR = "error"


class WatcherPriority(Enum):
    """Watcher priority levels for graceful degradation.

    Lower number = higher priority (preserved during resource constraints).
    """
    HIGH = 1      # Gmail - critical business communication
    MEDIUM = 2    # WhatsApp - important but secondary
    LOW = 3       # LinkedIn - can be paused first


class BaseWatcher(ABC):
    """Abstract base class for all external service watchers.

    Subclasses must implement:
    - process_event(): Handle a detected event
    - _poll() or _run_server(): Main watcher logic

    Usage:
        class GmailWatcher(BaseWatcher):
            def __init__(self, config):
                super().__init__(
                    name="gmail_watcher",
                    priority=WatcherPriority.HIGH,
                    memory_limit_mb=100,
                    config=config
                )

            async def _poll(self):
                emails = await self.gmail_client.list_unread()
                for email in emails:
                    await self.process_event(email)

            async def process_event(self, event):
                # Create action file
                ...
    """

    def __init__(
        self,
        name: str,
        priority: WatcherPriority = WatcherPriority.MEDIUM,
        memory_limit_mb: int = 100,
        poll_interval_seconds: float = 120,
        config: Any = None,
        dry_run: bool = False
    ):
        """Initialize base watcher.

        Args:
            name: Unique watcher name (used in logs)
            priority: Priority for graceful degradation
            memory_limit_mb: Maximum memory budget in MB
            poll_interval_seconds: Interval between polls (for polling watchers)
            config: Watcher configuration object
            dry_run: If True, log actions without executing
        """
        self.name = name
        self.priority = priority
        self.memory_limit_mb = memory_limit_mb
        self.poll_interval_seconds = poll_interval_seconds
        self.config = config
        self.dry_run = dry_run or os.environ.get("DRY_RUN", "").lower() == "true"

        # State
        self._status = WatcherStatus.STOPPED
        self._status_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()  # Not paused by default

        # Metrics
        self._events_processed = 0
        self._errors_count = 0
        self._last_run: datetime | None = None
        self._last_error: str | None = None

        # Process handle for memory monitoring
        self._process = psutil.Process()

        # Audit logger
        self._audit = get_audit_logger()

        logger.info(
            f"Initialized {self.name} watcher "
            f"(priority={priority.name}, memory_limit={memory_limit_mb}MB, "
            f"dry_run={self.dry_run})"
        )

    @property
    def status(self) -> WatcherStatus:
        """Get current watcher status."""
        with self._status_lock:
            return self._status

    @status.setter
    def status(self, value: WatcherStatus) -> None:
        """Set watcher status."""
        with self._status_lock:
            old_status = self._status
            self._status = value
            if old_status != value:
                logger.info(f"{self.name}: {old_status.value} -> {value.value}")

    def get_memory_usage_mb(self) -> float:
        """Get current memory usage in MB."""
        try:
            mem_info = self._process.memory_info()
            return mem_info.rss / (1024 * 1024)
        except Exception as e:
            logger.warning(f"Failed to get memory usage: {e}")
            return 0.0

    def check_memory(self) -> bool:
        """Check if memory usage is within limits.

        Returns:
            True if within limits, False if exceeded
        """
        current_mb = self.get_memory_usage_mb()
        within_limit = current_mb < self.memory_limit_mb

        if not within_limit:
            logger.warning(
                f"{self.name} exceeds memory limit: "
                f"{current_mb:.1f}MB / {self.memory_limit_mb}MB"
            )

        return within_limit

    def pause(self) -> None:
        """Pause the watcher (for resource constraints)."""
        if self.status == WatcherStatus.RUNNING:
            self._pause_event.clear()
            self.status = WatcherStatus.PAUSED
            logger.info(f"{self.name} paused due to resource constraints")

    def resume(self) -> None:
        """Resume the watcher after being paused."""
        if self.status == WatcherStatus.PAUSED:
            self._pause_event.set()
            self.status = WatcherStatus.RUNNING
            logger.info(f"{self.name} resumed")

    def stop(self) -> None:
        """Request graceful shutdown."""
        if self.status in (WatcherStatus.RUNNING, WatcherStatus.PAUSED):
            self.status = WatcherStatus.STOPPING
            self._stop_event.set()
            self._pause_event.set()  # Unblock if paused
            logger.info(f"{self.name} stopping...")

    def is_running(self) -> bool:
        """Check if watcher is in running state."""
        return self.status == WatcherStatus.RUNNING

    def is_stopped(self) -> bool:
        """Check if watcher is stopped."""
        return self.status == WatcherStatus.STOPPED

    @abstractmethod
    async def process_event(self, event: Any) -> None:
        """Process a detected event.

        Args:
            event: The event to process (email, message, etc.)

        This method should:
        1. Check idempotency (skip if already processed)
        2. Create action file in vault
        3. Log the detection
        """
        pass

    async def _pre_poll(self) -> bool:
        """Called before each poll. Return False to skip this poll cycle.

        Override in subclasses for pre-poll checks.
        """
        # Check if paused
        while not self._pause_event.is_set():
            if self._stop_event.is_set():
                return False
            await asyncio.sleep(0.5)

        # Check memory
        if not self.check_memory():
            self._audit.log_error(
                component=self.name,
                action_type="memory_check",
                error=f"Memory limit exceeded: {self.get_memory_usage_mb():.1f}MB"
            )
            return False

        return True

    async def _post_poll(self) -> None:
        """Called after each poll cycle. Override for cleanup."""
        self._last_run = datetime.now(timezone.utc)

    async def _poll(self) -> None:
        """Execute one poll cycle.

        Override in subclasses that use polling (Gmail, LinkedIn).
        Default implementation does nothing.
        """
        pass

    async def _run_polling_loop(self) -> None:
        """Main polling loop for polling-based watchers."""
        while not self._stop_event.is_set():
            try:
                if await self._pre_poll():
                    await self._poll()
                    await self._post_poll()
            except Exception as e:
                self._errors_count += 1
                self._last_error = str(e)
                logger.exception(f"{self.name} poll error: {e}")
                self._audit.log_error(
                    component=self.name,
                    action_type="poll_error",
                    error=e
                )

            # Wait for next poll interval
            try:
                await asyncio.wait_for(
                    asyncio.to_thread(self._stop_event.wait),
                    timeout=self.poll_interval_seconds
                )
            except asyncio.TimeoutError:
                pass  # Normal timeout, continue polling

    async def _run_server(self) -> None:
        """Run a server-based watcher (e.g., webhook handler).

        Override in subclasses that run servers (WhatsApp webhook).
        """
        pass

    async def run(self) -> None:
        """Main entry point to run the watcher.

        This method handles lifecycle and can be overridden for custom behavior.
        """
        self.status = WatcherStatus.STARTING

        try:
            self.status = WatcherStatus.RUNNING
            await self._run_polling_loop()
        except asyncio.CancelledError:
            logger.info(f"{self.name} cancelled")
        except Exception as e:
            self.status = WatcherStatus.ERROR
            self._last_error = str(e)
            logger.exception(f"{self.name} fatal error: {e}")
            raise
        finally:
            self.status = WatcherStatus.STOPPED

    def run_sync(self) -> None:
        """Synchronous wrapper for run().

        Use this when running outside of an async context.
        """
        asyncio.run(self.run())

    def start_background(self) -> threading.Thread:
        """Start watcher in a background thread.

        Returns:
            The thread running the watcher
        """
        thread = threading.Thread(target=self.run_sync, name=self.name, daemon=True)
        thread.start()
        return thread

    def get_stats(self) -> dict[str, Any]:
        """Get watcher statistics."""
        return {
            "name": self.name,
            "status": self.status.value,
            "priority": self.priority.name,
            "memory_usage_mb": round(self.get_memory_usage_mb(), 2),
            "memory_limit_mb": self.memory_limit_mb,
            "events_processed": self._events_processed,
            "errors_count": self._errors_count,
            "last_run": self._last_run.isoformat() if self._last_run else None,
            "last_error": self._last_error,
            "dry_run": self.dry_run
        }

    def _log_action(self, action_type: str, target: str, **kwargs) -> None:
        """Log an action with dry-run prefix if applicable."""
        if self.dry_run:
            logger.info(f"[DRY-RUN] {self.name}: {action_type} -> {target}")
        else:
            logger.info(f"{self.name}: {action_type} -> {target}")


class PollingWatcher(BaseWatcher):
    """Base class for polling-based watchers (Gmail, LinkedIn)."""

    async def run(self) -> None:
        """Run the polling loop."""
        self.status = WatcherStatus.STARTING

        try:
            self.status = WatcherStatus.RUNNING
            await self._run_polling_loop()
        except asyncio.CancelledError:
            logger.info(f"{self.name} cancelled")
        finally:
            self.status = WatcherStatus.STOPPED


class ServerWatcher(BaseWatcher):
    """Base class for server-based watchers (WhatsApp webhook)."""

    def __init__(self, *args, host: str = "0.0.0.0", port: int = 8000, **kwargs):
        super().__init__(*args, **kwargs)
        self.host = host
        self.port = port

    async def run(self) -> None:
        """Run the server."""
        self.status = WatcherStatus.STARTING

        try:
            self.status = WatcherStatus.RUNNING
            await self._run_server()
        except asyncio.CancelledError:
            logger.info(f"{self.name} cancelled")
        finally:
            self.status = WatcherStatus.STOPPED
