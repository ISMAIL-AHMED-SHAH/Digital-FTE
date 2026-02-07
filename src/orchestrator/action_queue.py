"""Action Queue for Graceful Degradation (FR-028-029).

Provides local action queuing when external services are unavailable,
with automatic retry when services recover.

Gold Tier Implementation:
- Queue actions locally when APIs fail after retries exhaust
- Persist queue to disk for crash recovery
- Auto-process queued actions when services recover
- Priority-based processing
"""

import json
import logging
import os
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable
import threading
import time

logger = logging.getLogger(__name__)


class ActionStatus(str, Enum):
    """Status of a queued action."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class QueuedAction:
    """Represents a queued action for later processing.

    Attributes:
        id: Unique action identifier
        action_type: Type of action (e.g., "odoo.invoice.create", "social.twitter.post")
        target_service: Service to execute against (odoo, facebook, instagram, twitter, gmail)
        payload: Action payload/parameters
        priority: Priority 1-10 (1=highest, 10=lowest)
        retry_count: Number of processing attempts
        max_retries: Maximum retry attempts before marking failed
        last_error: Last error message if any
        status: Current action status
        created_at: Creation timestamp
        scheduled_at: When to process (None = ASAP)
        processed_at: When processing completed
        correlation_id: ID to link related actions
    """
    id: str
    action_type: str
    target_service: str
    payload: dict[str, Any]
    priority: int = 5
    retry_count: int = 0
    max_retries: int = 5
    last_error: str | None = None
    status: ActionStatus = ActionStatus.PENDING
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    scheduled_at: str | None = None
    processed_at: str | None = None
    correlation_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data["status"] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "QueuedAction":
        """Create from dictionary."""
        data = data.copy()
        if "status" in data:
            data["status"] = ActionStatus(data["status"])
        return cls(**data)


class ActionQueue:
    """Persistent action queue for graceful degradation.

    Usage:
        queue = ActionQueue(Path("/data/action_queue.json"))

        # Queue an action when service is unavailable
        action = queue.enqueue(
            action_type="odoo.invoice.create",
            target_service="odoo",
            payload={"partner_id": 1, "amount": 100.00}
        )

        # Register service handlers
        queue.register_handler("odoo", odoo_handler_func)

        # Start background processing
        queue.start_processing()

        # Check if service is available before dequeuing
        queue.mark_service_available("odoo")
    """

    def __init__(
        self,
        persistence_path: Path | str | None = None,
        auto_save: bool = True
    ):
        """Initialize action queue.

        Args:
            persistence_path: Path to persistence file (None = in-memory only)
            auto_save: Auto-save after each modification
        """
        self.persistence_path = Path(persistence_path) if persistence_path else None
        self.auto_save = auto_save
        self._queue: dict[str, QueuedAction] = {}
        self._handlers: dict[str, Callable] = {}
        self._service_status: dict[str, bool] = {}
        self._lock = threading.RLock()
        self._processing = False
        self._processor_thread: threading.Thread | None = None

        # Load persisted queue if exists
        if self.persistence_path and self.persistence_path.exists():
            self._load()

    def _load(self) -> None:
        """Load queue from persistence file."""
        if not self.persistence_path:
            return

        try:
            with open(self.persistence_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for action_data in data.get("actions", []):
                    action = QueuedAction.from_dict(action_data)
                    self._queue[action.id] = action
                self._service_status = data.get("service_status", {})
            logger.info(f"Loaded {len(self._queue)} actions from queue")
        except Exception as e:
            logger.error(f"Failed to load action queue: {e}")

    def _save(self) -> None:
        """Save queue to persistence file."""
        if not self.persistence_path:
            return

        try:
            self.persistence_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.persistence_path, "w", encoding="utf-8") as f:
                data = {
                    "actions": [a.to_dict() for a in self._queue.values()],
                    "service_status": self._service_status,
                    "saved_at": datetime.now(timezone.utc).isoformat()
                }
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save action queue: {e}")

    def enqueue(
        self,
        action_type: str,
        target_service: str,
        payload: dict[str, Any],
        priority: int = 5,
        max_retries: int = 5,
        scheduled_at: datetime | None = None,
        correlation_id: str | None = None
    ) -> QueuedAction:
        """Add an action to the queue.

        Args:
            action_type: Type of action
            target_service: Target service name
            payload: Action payload
            priority: Priority 1-10
            max_retries: Max retry attempts
            scheduled_at: When to process (None = ASAP)
            correlation_id: ID to link related actions

        Returns:
            The queued action
        """
        with self._lock:
            action = QueuedAction(
                id=str(uuid.uuid4()),
                action_type=action_type,
                target_service=target_service,
                payload=payload,
                priority=max(1, min(10, priority)),
                max_retries=max_retries,
                scheduled_at=scheduled_at.isoformat() if scheduled_at else None,
                correlation_id=correlation_id
            )

            self._queue[action.id] = action
            logger.info(
                f"Queued action {action.id}: {action_type} for {target_service} "
                f"(priority={priority})"
            )

            if self.auto_save:
                self._save()

            return action

    def get(self, action_id: str) -> QueuedAction | None:
        """Get an action by ID."""
        return self._queue.get(action_id)

    def update_status(
        self,
        action_id: str,
        status: ActionStatus,
        error: str | None = None
    ) -> bool:
        """Update action status.

        Args:
            action_id: Action ID
            status: New status
            error: Error message if failed

        Returns:
            True if updated, False if not found
        """
        with self._lock:
            action = self._queue.get(action_id)
            if not action:
                return False

            action.status = status
            if error:
                action.last_error = error
            if status in (ActionStatus.COMPLETED, ActionStatus.FAILED):
                action.processed_at = datetime.now(timezone.utc).isoformat()

            if self.auto_save:
                self._save()

            return True

    def cancel(self, action_id: str) -> bool:
        """Cancel a pending action."""
        return self.update_status(action_id, ActionStatus.CANCELLED)

    def remove(self, action_id: str) -> bool:
        """Remove an action from the queue."""
        with self._lock:
            if action_id in self._queue:
                del self._queue[action_id]
                if self.auto_save:
                    self._save()
                return True
            return False

    def get_pending(self, target_service: str | None = None) -> list[QueuedAction]:
        """Get pending actions, optionally filtered by service.

        Returns actions sorted by priority (1 first) then by created_at.
        """
        with self._lock:
            now = datetime.now(timezone.utc)
            pending = []

            for action in self._queue.values():
                if action.status != ActionStatus.PENDING:
                    continue
                if target_service and action.target_service != target_service:
                    continue

                # Check scheduled time
                if action.scheduled_at:
                    scheduled = datetime.fromisoformat(action.scheduled_at)
                    if scheduled > now:
                        continue

                pending.append(action)

            # Sort by priority (ascending) then created_at
            return sorted(pending, key=lambda a: (a.priority, a.created_at))

    def get_by_service(self, service: str) -> list[QueuedAction]:
        """Get all actions for a specific service."""
        with self._lock:
            return [a for a in self._queue.values() if a.target_service == service]

    def get_stats(self) -> dict[str, Any]:
        """Get queue statistics."""
        with self._lock:
            stats = {
                "total": len(self._queue),
                "by_status": {},
                "by_service": {},
                "by_priority": {}
            }

            for action in self._queue.values():
                # By status
                status = action.status.value
                stats["by_status"][status] = stats["by_status"].get(status, 0) + 1

                # By service
                service = action.target_service
                stats["by_service"][service] = stats["by_service"].get(service, 0) + 1

                # By priority
                priority = str(action.priority)
                stats["by_priority"][priority] = stats["by_priority"].get(priority, 0) + 1

            stats["service_status"] = self._service_status.copy()
            return stats

    def register_handler(
        self,
        service: str,
        handler: Callable[[QueuedAction], bool]
    ) -> None:
        """Register a handler function for a service.

        The handler should:
        - Take a QueuedAction as argument
        - Return True if action was processed successfully
        - Return False or raise exception if failed
        """
        self._handlers[service] = handler
        logger.info(f"Registered handler for service: {service}")

    def mark_service_available(self, service: str) -> None:
        """Mark a service as available (trigger queue processing)."""
        with self._lock:
            self._service_status[service] = True
            if self.auto_save:
                self._save()
        logger.info(f"Service marked available: {service}")

    def mark_service_unavailable(self, service: str) -> None:
        """Mark a service as unavailable."""
        with self._lock:
            self._service_status[service] = False
            if self.auto_save:
                self._save()
        logger.info(f"Service marked unavailable: {service}")

    def is_service_available(self, service: str) -> bool:
        """Check if a service is marked as available."""
        return self._service_status.get(service, True)  # Default to available

    def process_one(self, action: QueuedAction) -> bool:
        """Process a single action.

        Returns:
            True if successful, False if failed
        """
        handler = self._handlers.get(action.target_service)
        if not handler:
            logger.warning(f"No handler for service: {action.target_service}")
            return False

        # Mark as processing
        self.update_status(action.id, ActionStatus.PROCESSING)

        try:
            result = handler(action)
            if result:
                self.update_status(action.id, ActionStatus.COMPLETED)
                logger.info(f"Action {action.id} completed successfully")
                return True
            else:
                raise Exception("Handler returned False")
        except Exception as e:
            action.retry_count += 1
            error_msg = str(e)

            if action.retry_count >= action.max_retries:
                self.update_status(action.id, ActionStatus.FAILED, error_msg)
                logger.error(
                    f"Action {action.id} failed after {action.retry_count} attempts: {error_msg}"
                )
                return False
            else:
                # Reset to pending for retry
                self.update_status(action.id, ActionStatus.PENDING, error_msg)
                logger.warning(
                    f"Action {action.id} failed (attempt {action.retry_count}), "
                    f"will retry: {error_msg}"
                )
                return False

    def process_pending(self, service: str | None = None, max_actions: int = 10) -> int:
        """Process pending actions.

        Args:
            service: Only process actions for this service (None = all)
            max_actions: Maximum actions to process in this call

        Returns:
            Number of actions processed successfully
        """
        # Get services to process
        if service:
            services = [service]
        else:
            services = list(self._handlers.keys())

        processed = 0

        for svc in services:
            if not self.is_service_available(svc):
                continue

            pending = self.get_pending(target_service=svc)[:max_actions - processed]

            for action in pending:
                if self.process_one(action):
                    processed += 1

                if processed >= max_actions:
                    break

            if processed >= max_actions:
                break

        return processed

    def start_processing(self, interval_seconds: int = 60) -> None:
        """Start background processing thread.

        Args:
            interval_seconds: Seconds between processing cycles
        """
        if self._processing:
            return

        self._processing = True

        def processor():
            while self._processing:
                try:
                    self.process_pending()
                except Exception as e:
                    logger.error(f"Error in queue processor: {e}")
                time.sleep(interval_seconds)

        self._processor_thread = threading.Thread(target=processor, daemon=True)
        self._processor_thread.start()
        logger.info(f"Started queue processor (interval={interval_seconds}s)")

    def stop_processing(self) -> None:
        """Stop background processing thread."""
        self._processing = False
        if self._processor_thread:
            self._processor_thread.join(timeout=5)
            self._processor_thread = None
        logger.info("Stopped queue processor")

    def cleanup_completed(self, older_than_hours: int = 24) -> int:
        """Remove completed/failed actions older than threshold.

        Args:
            older_than_hours: Remove actions processed more than this many hours ago

        Returns:
            Number of actions removed
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=older_than_hours)
        removed = 0

        with self._lock:
            to_remove = []
            for action_id, action in self._queue.items():
                if action.status in (ActionStatus.COMPLETED, ActionStatus.FAILED, ActionStatus.CANCELLED):
                    if action.processed_at:
                        processed = datetime.fromisoformat(action.processed_at)
                        if processed < cutoff:
                            to_remove.append(action_id)

            for action_id in to_remove:
                del self._queue[action_id]
                removed += 1

            if removed and self.auto_save:
                self._save()

        logger.info(f"Cleaned up {removed} completed actions")
        return removed


@dataclass
class EnqueueResult:
    """Result of an enqueue operation.

    Attributes:
        success: Whether the item was enqueued
        message: Status message
        item_id: ID of queued item if successful
    """
    success: bool
    message: str
    item_id: str | None = None


class GracefulDegradationQueue:
    """Simple queue for graceful degradation scenarios.

    A lightweight wrapper around ActionQueue optimized for
    simple queueing when services are unavailable.

    Usage:
        queue = GracefulDegradationQueue(
            persistence_path=Path("./data/queue.json"),
            max_size=100
        )

        # Queue when service fails
        queue.enqueue({"type": "action", "data": payload}, reason="Service unavailable")

        # Process when service recovers
        queue.process_all(handler_function)
    """

    def __init__(
        self,
        persistence_path: Path | str,
        max_size: int = 100
    ):
        """Initialize the queue.

        Args:
            persistence_path: Path to persistence file
            max_size: Maximum queue size
        """
        self.persistence_path = Path(persistence_path)
        self.max_size = max_size
        self._items: list[dict] = []
        self._lock = threading.RLock()

        # Load existing items
        self._load()

    def _load(self) -> None:
        """Load queue from disk."""
        if self.persistence_path.exists():
            try:
                with open(self.persistence_path) as f:
                    data = json.load(f)
                    self._items = data.get("items", [])
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Error loading queue: {e}")
                self._items = []

    def _save(self) -> None:
        """Save queue to disk."""
        try:
            self.persistence_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.persistence_path, "w") as f:
                json.dump({
                    "items": self._items,
                    "saved_at": datetime.now(timezone.utc).isoformat()
                }, f, indent=2)
        except IOError as e:
            logger.error(f"Error saving queue: {e}")

    def enqueue(self, action: dict, reason: str) -> EnqueueResult:
        """Add an item to the queue.

        Args:
            action: The action to queue
            reason: Reason for queueing

        Returns:
            EnqueueResult with status
        """
        with self._lock:
            if len(self._items) >= self.max_size:
                return EnqueueResult(
                    success=False,
                    message=f"Queue full (max {self.max_size})"
                )

            item_id = str(uuid.uuid4())
            item = {
                "id": item_id,
                **action,
                "_queued_at": datetime.now(timezone.utc).isoformat(),
                "_reason": reason
            }

            self._items.append(item)
            self._save()

            return EnqueueResult(
                success=True,
                message="Item queued",
                item_id=item_id
            )

    def size(self) -> int:
        """Get queue size."""
        return len(self._items)

    def peek(self) -> dict | None:
        """Peek at the first item without removing."""
        with self._lock:
            return self._items[0] if self._items else None

    def dequeue(self) -> dict | None:
        """Remove and return the first item."""
        with self._lock:
            if not self._items:
                return None

            item = self._items.pop(0)
            self._save()
            return item

    def process_all(self, handler: Callable[[dict], bool]) -> int:
        """Process all items with a handler function.

        Args:
            handler: Function that takes an item and returns True if successful

        Returns:
            Number of successfully processed items
        """
        processed = 0
        failed_items = []

        with self._lock:
            while self._items:
                item = self._items.pop(0)
                try:
                    if handler(item):
                        processed += 1
                    else:
                        failed_items.append(item)
                except Exception as e:
                    logger.warning(f"Handler failed for item {item.get('id')}: {e}")
                    failed_items.append(item)

            # Put failed items back
            self._items.extend(failed_items)
            self._save()

        return processed

    def clear(self) -> int:
        """Clear all items from the queue.

        Returns:
            Number of items cleared
        """
        with self._lock:
            count = len(self._items)
            self._items = []
            self._save()
            return count
