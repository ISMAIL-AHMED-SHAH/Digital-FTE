"""Ralph Wiggum Completion Checker (T065 - FR-019/FR-020).

Implements hybrid completion detection strategy:
1. File-based: Task moved to /Done folder
2. Promise-based: Explicit completion signal
3. Semantic: Completion phrases in response
4. Error state: Too many errors or critical failure
5. Approval pending: HITL approval requested

Priority order: File > Promise > Error > Approval > Semantic
"""

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class CompletionResult:
    """Result of completion check.

    Attributes:
        is_complete: Whether task is complete
        should_stop: Whether loop should stop (may stop without completing)
        method: Detection method used
        reason: Human-readable reason
        details: Additional details
    """
    is_complete: bool
    should_stop: bool
    method: str
    reason: str
    details: dict | None = None


# Semantic completion phrases (case-insensitive)
COMPLETION_PHRASES = [
    "all done",
    "task completed",
    "task complete",
    "completed successfully",
    "finished processing",
    "no more tasks",
    "all tasks completed",
    "nothing left to do",
    "work is complete",
    "job done",
]

# Stop phrases (should stop but may not be "complete")
STOP_PHRASES = [
    "waiting for approval",
    "needs review",
    "requires human input",
    "cannot proceed",
    "blocked",
    "need clarification",
    "approval required",
]

# Error phrases
ERROR_PHRASES = [
    "critical error",
    "fatal error",
    "cannot recover",
    "authentication failed",
    "access denied",
]


class RalphCompletionChecker:
    """Checks for task completion using multiple strategies.

    Usage:
        checker = RalphCompletionChecker(vault_path="./vault")

        # Check completion
        result = checker.check(
            task_id="task-001",
            response="I've completed all the requested tasks.",
        )

        if result.should_stop:
            print(f"Stop reason: {result.reason}")
    """

    def __init__(
        self,
        vault_path: str | Path = "./vault",
        promise_file: str | Path | None = None
    ):
        """Initialize the checker.

        Args:
            vault_path: Path to vault directory
            promise_file: Path to completion promise file (optional)
        """
        self.vault_path = Path(vault_path)
        self.promise_file = Path(promise_file) if promise_file else None

        # Compile regex patterns
        self._completion_pattern = re.compile(
            "|".join(re.escape(phrase) for phrase in COMPLETION_PHRASES),
            re.IGNORECASE
        )
        self._stop_pattern = re.compile(
            "|".join(re.escape(phrase) for phrase in STOP_PHRASES),
            re.IGNORECASE
        )
        self._error_pattern = re.compile(
            "|".join(re.escape(phrase) for phrase in ERROR_PHRASES),
            re.IGNORECASE
        )

    def check(
        self,
        task_id: str | None = None,
        response: str | None = None,
        error_count: int = 0,
        max_errors: int = 3,
        iteration: int = 0,
        max_iterations: int = 50,
    ) -> CompletionResult:
        """Check for completion using all strategies.

        Args:
            task_id: Task identifier for file-based check
            response: Response text for semantic check
            error_count: Current error count
            max_errors: Maximum allowed errors
            iteration: Current iteration number
            max_iterations: Maximum allowed iterations

        Returns:
            CompletionResult with detection details
        """
        # Priority 1: Check iteration limit
        if iteration >= max_iterations:
            return CompletionResult(
                is_complete=False,
                should_stop=True,
                method="iteration_limit",
                reason=f"Maximum iterations reached ({max_iterations})",
                details={"iteration": iteration, "max": max_iterations},
            )

        # Priority 2: Check file-based completion
        if task_id:
            file_result = self.check_file_completion(task_id)
            if file_result.should_stop:
                return file_result

        # Priority 3: Check promise-based completion
        promise_result = self.check_promise_completion()
        if promise_result.should_stop:
            return promise_result

        # Priority 4: Check error state
        error_result = self.check_error_state(error_count, max_errors, response)
        if error_result.should_stop:
            return error_result

        # Priority 5: Check for pending approvals
        approval_result = self.check_approval_pending()
        if approval_result.should_stop:
            return approval_result

        # Priority 6: Check semantic completion
        if response:
            semantic_result = self.check_semantic_completion(response)
            if semantic_result.should_stop:
                return semantic_result

        # Not complete, continue
        return CompletionResult(
            is_complete=False,
            should_stop=False,
            method="none",
            reason="Continue processing",
        )

    def check_file_completion(self, task_id: str) -> CompletionResult:
        """Check if task file has been moved to Done.

        Args:
            task_id: Task identifier

        Returns:
            CompletionResult
        """
        done_folder = self.vault_path / "Done"

        # Check for task file in Done folder
        for pattern in [f"{task_id}*", f"*{task_id}*"]:
            matches = list(done_folder.glob(pattern)) if done_folder.exists() else []
            if matches:
                return CompletionResult(
                    is_complete=True,
                    should_stop=True,
                    method="file_based",
                    reason="Task file moved to Done folder",
                    details={"file": str(matches[0])},
                )

        # Check if Needs_Action is empty
        needs_action = self.vault_path / "Needs_Action"
        if needs_action.exists():
            pending = list(needs_action.glob("*.md"))
            if not pending:
                return CompletionResult(
                    is_complete=True,
                    should_stop=True,
                    method="file_based",
                    reason="No pending tasks in Needs_Action",
                )

        return CompletionResult(
            is_complete=False,
            should_stop=False,
            method="file_based",
            reason="Task still pending",
        )

    def check_promise_completion(self) -> CompletionResult:
        """Check for promise-based completion signal.

        Returns:
            CompletionResult
        """
        if not self.promise_file or not self.promise_file.exists():
            return CompletionResult(
                is_complete=False,
                should_stop=False,
                method="promise_based",
                reason="No promise file",
            )

        try:
            with open(self.promise_file) as f:
                data = json.load(f)

            if data.get("completed"):
                return CompletionResult(
                    is_complete=True,
                    should_stop=True,
                    method="promise_based",
                    reason=data.get("message", "Completion promise fulfilled"),
                    details=data,
                )

            if data.get("stop"):
                return CompletionResult(
                    is_complete=False,
                    should_stop=True,
                    method="promise_based",
                    reason=data.get("message", "Stop signal received"),
                    details=data,
                )

        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Error reading promise file: {e}")

        return CompletionResult(
            is_complete=False,
            should_stop=False,
            method="promise_based",
            reason="Promise not fulfilled",
        )

    def check_error_state(
        self,
        error_count: int,
        max_errors: int = 3,
        response: str | None = None
    ) -> CompletionResult:
        """Check if error state warrants stopping.

        Args:
            error_count: Number of errors encountered
            max_errors: Maximum allowed errors
            response: Response to check for critical errors

        Returns:
            CompletionResult
        """
        # Check error count threshold
        if error_count >= max_errors:
            return CompletionResult(
                is_complete=False,
                should_stop=True,
                method="error_state",
                reason=f"Error threshold exceeded ({error_count}/{max_errors})",
                details={"error_count": error_count, "max": max_errors},
            )

        # Check for critical error phrases
        if response and self._error_pattern.search(response):
            match = self._error_pattern.search(response)
            return CompletionResult(
                is_complete=False,
                should_stop=True,
                method="error_state",
                reason=f"Critical error detected: {match.group() if match else 'unknown'}",
                details={"phrase": match.group() if match else None},
            )

        return CompletionResult(
            is_complete=False,
            should_stop=False,
            method="error_state",
            reason="No critical errors",
        )

    def check_approval_pending(self) -> CompletionResult:
        """Check if HITL approval is pending.

        Returns:
            CompletionResult
        """
        needs_action = self.vault_path / "Needs_Action"

        if not needs_action.exists():
            return CompletionResult(
                is_complete=False,
                should_stop=False,
                method="approval_check",
                reason="No Needs_Action folder",
            )

        # Look for approval request files
        approval_patterns = ["approval-*", "*-approval-*", "*approval*.md"]
        for pattern in approval_patterns:
            for file in needs_action.glob(pattern):
                try:
                    content = file.read_text()
                    if any(phrase in content.lower() for phrase in [
                        "approval required",
                        "type: approval",
                        "waiting for approval",
                        "requires human review",
                    ]):
                        return CompletionResult(
                            is_complete=False,
                            should_stop=True,
                            method="approval_pending",
                            reason="HITL approval required",
                            details={"file": str(file)},
                        )
                except IOError:
                    continue

        return CompletionResult(
            is_complete=False,
            should_stop=False,
            method="approval_check",
            reason="No pending approvals",
        )

    def check_semantic_completion(self, response: str) -> CompletionResult:
        """Check for completion phrases in response.

        Args:
            response: Response text to analyze

        Returns:
            CompletionResult
        """
        # Check for stop phrases first (they take priority)
        stop_match = self._stop_pattern.search(response)
        if stop_match:
            return CompletionResult(
                is_complete=False,
                should_stop=True,
                method="semantic",
                reason=f"Stop phrase detected: {stop_match.group()}",
                details={"phrase": stop_match.group()},
            )

        # Check for completion phrases
        completion_match = self._completion_pattern.search(response)
        if completion_match:
            return CompletionResult(
                is_complete=True,
                should_stop=True,
                method="semantic",
                reason=f"Completion phrase detected: {completion_match.group()}",
                details={"phrase": completion_match.group()},
            )

        return CompletionResult(
            is_complete=False,
            should_stop=False,
            method="semantic",
            reason="No completion phrases detected",
        )

    def emit_completion(self, message: str = "Task completed") -> None:
        """Emit a completion promise.

        Args:
            message: Completion message
        """
        if not self.promise_file:
            self.promise_file = self.vault_path / ".ralph_completion_promise.json"

        self.promise_file.parent.mkdir(parents=True, exist_ok=True)

        with open(self.promise_file, "w") as f:
            json.dump({
                "completed": True,
                "message": message,
                "timestamp": datetime.now().isoformat(),
            }, f)

    def emit_stop(self, reason: str) -> None:
        """Emit a stop signal (not completion, but should stop).

        Args:
            reason: Reason for stopping
        """
        if not self.promise_file:
            self.promise_file = self.vault_path / ".ralph_completion_promise.json"

        self.promise_file.parent.mkdir(parents=True, exist_ok=True)

        with open(self.promise_file, "w") as f:
            json.dump({
                "completed": False,
                "stop": True,
                "message": reason,
                "timestamp": datetime.now().isoformat(),
            }, f)

    def clear_promise(self) -> None:
        """Clear the completion promise file."""
        if self.promise_file and self.promise_file.exists():
            self.promise_file.unlink()
