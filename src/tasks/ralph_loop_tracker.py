"""Ralph Wiggum Loop State Tracker (T063 - FR-023).

Tracks autonomous loop execution state:
- Iteration counting and limits
- State persistence for crash recovery
- Action history logging
- Performance metrics

Used by the Ralph Wiggum Stop hook for completion detection.
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class LoopAction:
    """Record of a single loop action.

    Attributes:
        iteration: Iteration number when action occurred
        action: Description of the action taken
        result: success, error, or skipped
        duration_ms: Time taken in milliseconds
        timestamp: When the action occurred
        details: Additional action-specific details
    """
    iteration: int
    action: str
    result: str
    duration_ms: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    details: dict = field(default_factory=dict)


@dataclass
class LoopState:
    """Current state of the autonomous loop.

    Attributes:
        task_id: Identifier for the current task
        status: running, completed, stopped, error
        iteration: Current iteration number
        max_iterations: Maximum allowed iterations
        started_at: When the loop started
        last_checkpoint: Last state save timestamp
        actions: History of actions taken
        error_count: Number of errors encountered
        last_error: Most recent error message
        completion_reason: Why the loop completed (if applicable)
    """
    task_id: str
    status: str = "idle"
    iteration: int = 0
    max_iterations: int = 50
    started_at: str | None = None
    last_checkpoint: str | None = None
    actions: list[dict] = field(default_factory=list)
    error_count: int = 0
    last_error: str | None = None
    completion_reason: str | None = None


class RalphLoopTracker:
    """Tracks and persists Ralph Wiggum loop state.

    Usage:
        tracker = RalphLoopTracker(state_dir="./data/ralph")

        # Start new loop
        tracker.start_loop("task-001", max_iterations=50)

        # Record actions
        tracker.record_action("Read invoice file", "success", duration_ms=150)
        tracker.increment_iteration()

        # Check limits
        if tracker.should_stop():
            reason = tracker.get_stop_reason()

        # Complete loop
        tracker.complete_loop("all_tasks_done")
    """

    # Warning threshold (percentage of max iterations)
    WARNING_THRESHOLD = 0.8

    # Error threshold before stopping
    ERROR_THRESHOLD = 3

    def __init__(
        self,
        state_dir: str | Path = "./data/ralph",
        max_iterations: int = 50
    ):
        """Initialize the tracker.

        Args:
            state_dir: Directory to store state files
            max_iterations: Default max iterations
        """
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)

        self.default_max_iterations = max_iterations
        self.state: LoopState | None = None
        self._state_file: Path | None = None

    def start_loop(
        self,
        task_id: str,
        max_iterations: int | None = None
    ) -> LoopState:
        """Start a new loop or resume existing one.

        Args:
            task_id: Identifier for the task
            max_iterations: Maximum iterations (uses default if not specified)

        Returns:
            Current loop state
        """
        self._state_file = self.state_dir / f"{task_id}_state.json"

        # Check for existing state (crash recovery)
        if self._state_file.exists():
            logger.info(f"Recovering state for task {task_id}")
            self.state = self._load_state()
            self.state.status = "running"
        else:
            logger.info(f"Starting new loop for task {task_id}")
            self.state = LoopState(
                task_id=task_id,
                status="running",
                iteration=0,
                max_iterations=max_iterations or self.default_max_iterations,
                started_at=datetime.now().isoformat(),
            )

        self._save_state()
        return self.state

    def increment_iteration(self) -> int:
        """Increment the iteration counter.

        Returns:
            New iteration number
        """
        if not self.state:
            raise ValueError("No active loop. Call start_loop first.")

        self.state.iteration += 1
        self._save_state()

        logger.debug(f"Iteration {self.state.iteration}/{self.state.max_iterations}")
        return self.state.iteration

    def record_action(
        self,
        action: str,
        result: str,
        duration_ms: int = 0,
        details: dict | None = None
    ) -> LoopAction:
        """Record an action taken during the loop.

        Args:
            action: Description of the action
            result: success, error, or skipped
            duration_ms: Time taken in milliseconds
            details: Additional details

        Returns:
            The recorded action
        """
        if not self.state:
            raise ValueError("No active loop. Call start_loop first.")

        loop_action = LoopAction(
            iteration=self.state.iteration,
            action=action,
            result=result,
            duration_ms=duration_ms,
            details=details or {},
        )

        self.state.actions.append(asdict(loop_action))

        if result == "error":
            self.state.error_count += 1
            self.state.last_error = details.get("error") if details else action

        self._save_state()
        return loop_action

    def record_error(self, error: str, recoverable: bool = True) -> None:
        """Record an error during the loop.

        Args:
            error: Error message
            recoverable: Whether the error is recoverable
        """
        if not self.state:
            raise ValueError("No active loop. Call start_loop first.")

        self.state.error_count += 1
        self.state.last_error = error

        if not recoverable:
            self.state.status = "error"
            self.state.completion_reason = f"unrecoverable_error: {error}"

        self._save_state()

    def should_stop(self) -> bool:
        """Check if the loop should stop.

        Returns:
            True if loop should stop
        """
        if not self.state:
            return True

        # Already stopped
        if self.state.status in ["completed", "stopped", "error"]:
            return True

        # Max iterations reached
        if self.state.iteration >= self.state.max_iterations:
            self.state.completion_reason = "max_iterations_reached"
            return True

        # Too many errors
        if self.state.error_count >= self.ERROR_THRESHOLD:
            self.state.completion_reason = "error_threshold_exceeded"
            return True

        return False

    def get_stop_reason(self) -> str | None:
        """Get the reason the loop should stop.

        Returns:
            Stop reason or None if should continue
        """
        if not self.state:
            return "no_active_loop"

        return self.state.completion_reason

    def should_warn(self) -> tuple[bool, str | None]:
        """Check if approaching limits that warrant a warning.

        Returns:
            Tuple of (should_warn, warning_message)
        """
        if not self.state:
            return False, None

        # Near max iterations
        threshold = int(self.state.max_iterations * self.WARNING_THRESHOLD)
        if self.state.iteration >= threshold:
            remaining = self.state.max_iterations - self.state.iteration
            return True, f"Approaching iteration limit ({remaining} remaining)"

        # Accumulating errors
        if self.state.error_count >= self.ERROR_THRESHOLD - 1:
            return True, f"Error threshold nearly reached ({self.state.error_count}/{self.ERROR_THRESHOLD})"

        return False, None

    def complete_loop(self, reason: str) -> dict:
        """Mark the loop as completed.

        Args:
            reason: Why the loop completed

        Returns:
            Summary of the loop execution
        """
        if not self.state:
            raise ValueError("No active loop.")

        self.state.status = "completed"
        self.state.completion_reason = reason
        self.state.last_checkpoint = datetime.now().isoformat()

        summary = self.get_summary()
        self._save_state()

        logger.info(f"Loop completed: {reason}")
        return summary

    def stop_loop(self, reason: str) -> dict:
        """Stop the loop (externally triggered).

        Args:
            reason: Why the loop was stopped

        Returns:
            Summary of the loop execution
        """
        if not self.state:
            raise ValueError("No active loop.")

        self.state.status = "stopped"
        self.state.completion_reason = reason
        self.state.last_checkpoint = datetime.now().isoformat()

        summary = self.get_summary()
        self._save_state()

        logger.info(f"Loop stopped: {reason}")
        return summary

    def get_summary(self) -> dict:
        """Get execution summary.

        Returns:
            Summary dictionary
        """
        if not self.state:
            return {"error": "No active loop"}

        # Calculate metrics
        successful_actions = sum(
            1 for a in self.state.actions if a.get("result") == "success"
        )
        failed_actions = sum(
            1 for a in self.state.actions if a.get("result") == "error"
        )
        total_duration_ms = sum(
            a.get("duration_ms", 0) for a in self.state.actions
        )

        # Calculate time spent
        started = datetime.fromisoformat(self.state.started_at) if self.state.started_at else None
        ended = datetime.now()
        duration_seconds = (ended - started).total_seconds() if started else 0

        return {
            "task_id": self.state.task_id,
            "status": self.state.status,
            "iterations": self.state.iteration,
            "max_iterations": self.state.max_iterations,
            "total_actions": len(self.state.actions),
            "successful_actions": successful_actions,
            "failed_actions": failed_actions,
            "error_count": self.state.error_count,
            "last_error": self.state.last_error,
            "completion_reason": self.state.completion_reason,
            "duration_seconds": round(duration_seconds, 2),
            "action_duration_ms": total_duration_ms,
            "started_at": self.state.started_at,
            "ended_at": ended.isoformat(),
        }

    def get_state(self) -> LoopState | None:
        """Get current state.

        Returns:
            Current loop state or None
        """
        return self.state

    def get_iteration_history(self) -> list[dict]:
        """Get action history grouped by iteration.

        Returns:
            List of iterations with their actions
        """
        if not self.state:
            return []

        iterations: dict[int, list] = {}
        for action in self.state.actions:
            iter_num = action.get("iteration", 0)
            if iter_num not in iterations:
                iterations[iter_num] = []
            iterations[iter_num].append(action)

        return [
            {"iteration": k, "actions": v}
            for k, v in sorted(iterations.items())
        ]

    def _save_state(self) -> None:
        """Save state to file."""
        if not self._state_file or not self.state:
            return

        self.state.last_checkpoint = datetime.now().isoformat()

        with open(self._state_file, "w") as f:
            json.dump(asdict(self.state), f, indent=2)

    def _load_state(self) -> LoopState:
        """Load state from file."""
        if not self._state_file or not self._state_file.exists():
            raise FileNotFoundError("State file not found")

        with open(self._state_file) as f:
            data = json.load(f)

        return LoopState(**data)

    def clear_state(self) -> None:
        """Clear current state (for cleanup)."""
        if self._state_file and self._state_file.exists():
            self._state_file.unlink()
        self.state = None
        self._state_file = None
