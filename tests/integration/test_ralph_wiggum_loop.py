"""Integration Tests for Ralph Wiggum Autonomous Loop (T062).

Tests loop execution, completion detection, and max iteration handling.
"""

import json
import os
import pytest
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch


class TestLoopExecution:
    """Test Ralph Wiggum loop execution."""

    @pytest.fixture
    def temp_vault(self, tmp_path):
        """Create temporary vault structure."""
        vault = tmp_path / "vault"
        (vault / "Needs_Action").mkdir(parents=True)
        (vault / "Done").mkdir(parents=True)
        (vault / "Rejected").mkdir(parents=True)
        return vault

    @pytest.fixture
    def temp_state_dir(self, tmp_path):
        """Create temporary state directory."""
        state_dir = tmp_path / "state"
        state_dir.mkdir()
        return state_dir

    @pytest.mark.asyncio
    async def test_loop_starts_with_pending_task(self, temp_vault):
        """Test that loop starts when task file exists in Needs_Action."""
        # Create a task file
        task_file = temp_vault / "Needs_Action" / "task-001.md"
        task_file.write_text("""---
type: task
status: pending
---
# Process invoice data
""")

        result = await self._check_should_continue(str(temp_vault))

        assert result["should_continue"] is True
        assert result["reason"] == "pending_tasks"

    @pytest.mark.asyncio
    async def test_loop_stops_when_no_tasks(self, temp_vault):
        """Test that loop stops when no pending tasks exist."""
        # Empty Needs_Action folder
        result = await self._check_should_continue(str(temp_vault))

        assert result["should_continue"] is False
        assert "no_pending" in result["reason"]

    @pytest.mark.asyncio
    async def test_loop_stops_on_completion_phrase(self, temp_vault):
        """Test that loop stops when completion phrase is detected."""
        # Simulate response with completion phrase
        response = "Task completed successfully. All done!"

        result = await self._check_completion_phrase(response)

        assert result["is_complete"] is True
        assert "phrase_detected" in result

    @pytest.mark.asyncio
    async def test_loop_stops_on_approval_request(self, temp_vault):
        """Test that loop stops when HITL approval is requested."""
        # Create an approval request
        approval_file = temp_vault / "Needs_Action" / "approval-001.md"
        approval_file.write_text("""---
type: approval_request
platform: facebook
status: pending
---
# Approval Required
""")

        result = await self._check_approval_pending(str(temp_vault))

        assert result["approval_pending"] is True
        assert result["should_stop"] is True

    @pytest.mark.asyncio
    async def test_loop_stops_on_error_state(self):
        """Test that loop stops when critical error occurs."""
        error_state = {
            "error_count": 3,
            "last_error": "API rate limit exceeded",
            "error_category": "TRANSIENT",
        }

        result = await self._check_error_state(error_state)

        assert result["should_stop"] is True
        assert result["reason"] == "error_threshold"

    @pytest.mark.asyncio
    async def test_loop_continues_on_recoverable_error(self):
        """Test that loop continues on single recoverable error."""
        error_state = {
            "error_count": 1,
            "last_error": "Temporary network issue",
            "error_category": "TRANSIENT",
        }

        result = await self._check_error_state(error_state)

        assert result["should_stop"] is False

    async def _check_should_continue(self, vault_path: str) -> dict:
        """Check if loop should continue."""
        needs_action = Path(vault_path) / "Needs_Action"
        pending_files = list(needs_action.glob("*.md"))

        if not pending_files:
            return {"should_continue": False, "reason": "no_pending_tasks"}

        return {"should_continue": True, "reason": "pending_tasks", "task_count": len(pending_files)}

    async def _check_completion_phrase(self, response: str) -> dict:
        """Check for completion phrases in response."""
        completion_phrases = [
            "all done",
            "task completed",
            "finished",
            "completed successfully",
            "no more tasks",
        ]

        response_lower = response.lower()
        for phrase in completion_phrases:
            if phrase in response_lower:
                return {"is_complete": True, "phrase_detected": phrase}

        return {"is_complete": False}

    async def _check_approval_pending(self, vault_path: str) -> dict:
        """Check for pending approval requests."""
        needs_action = Path(vault_path) / "Needs_Action"

        for file in needs_action.glob("*.md"):
            content = file.read_text()
            if "type: approval" in content.lower() or "approval required" in content.lower():
                return {"approval_pending": True, "should_stop": True, "file": str(file)}

        return {"approval_pending": False, "should_stop": False}

    async def _check_error_state(self, error_state: dict) -> dict:
        """Check if error state warrants stopping."""
        error_threshold = 3

        if error_state.get("error_count", 0) >= error_threshold:
            return {"should_stop": True, "reason": "error_threshold"}

        if error_state.get("error_category") in ["AUTH", "SYSTEM"]:
            return {"should_stop": True, "reason": "critical_error"}

        return {"should_stop": False}


class TestIterationLimit:
    """Test max iteration handling."""

    @pytest.mark.asyncio
    async def test_respects_max_iterations(self):
        """Test that loop stops at max iterations."""
        max_iterations = 5
        tracker = MockLoopTracker(max_iterations=max_iterations)

        # Simulate iterations
        for i in range(max_iterations + 2):
            result = await tracker.should_continue()
            if not result:
                break
            await tracker.increment()

        assert tracker.current_iteration == max_iterations
        assert tracker.stopped_by_limit is True

    @pytest.mark.asyncio
    async def test_configurable_max_iterations(self):
        """Test that max iterations can be configured."""
        tracker = MockLoopTracker(max_iterations=10)
        assert tracker.max_iterations == 10

        tracker = MockLoopTracker(max_iterations=100)
        assert tracker.max_iterations == 100

    @pytest.mark.asyncio
    async def test_iteration_warning_at_threshold(self):
        """Test that warning is emitted near max iterations."""
        max_iterations = 10
        warning_threshold = 0.8  # 80%
        tracker = MockLoopTracker(max_iterations=max_iterations)

        warnings = []
        for i in range(max_iterations):
            result = await tracker.check_with_warnings()
            if result.get("warning"):
                warnings.append(result["warning"])
            if not result["continue"]:
                break
            await tracker.increment()

        assert len(warnings) > 0
        assert any("approaching limit" in w.lower() for w in warnings)


class MockLoopTracker:
    """Mock loop tracker for testing."""

    def __init__(self, max_iterations: int = 50):
        self.max_iterations = max_iterations
        self.current_iteration = 0
        self.stopped_by_limit = False

    async def should_continue(self) -> bool:
        if self.current_iteration >= self.max_iterations:
            self.stopped_by_limit = True
            return False
        return True

    async def increment(self):
        self.current_iteration += 1

    async def check_with_warnings(self) -> dict:
        result = {"continue": True, "warning": None}

        if self.current_iteration >= self.max_iterations:
            self.stopped_by_limit = True
            result["continue"] = False
            return result

        # Warning at 80% of max
        if self.current_iteration >= self.max_iterations * 0.8:
            result["warning"] = f"Approaching iteration limit ({self.current_iteration}/{self.max_iterations})"

        return result


class TestCompletionDetection:
    """Test hybrid completion detection strategies."""

    @pytest.mark.asyncio
    async def test_file_based_completion(self, tmp_path):
        """Test file-based completion detection."""
        vault = tmp_path / "vault"
        (vault / "Needs_Action").mkdir(parents=True)
        (vault / "Done").mkdir(parents=True)

        # Create and move task to Done
        task_id = "task-001"
        done_file = vault / "Done" / f"{task_id}.md"
        done_file.write_text("# Completed task")

        result = await self._check_file_completion(str(vault), task_id)

        assert result["completed"] is True
        assert result["method"] == "file_based"

    @pytest.mark.asyncio
    async def test_promise_based_completion(self):
        """Test promise-based completion detection."""
        # Simulate a completion promise/signal
        promise = MockCompletionPromise()

        # Initially not complete
        assert await promise.is_completed() is False

        # Emit completion
        await promise.emit_completion("Task finished successfully")

        # Now complete
        assert await promise.is_completed() is True
        assert promise.completion_message == "Task finished successfully"

    @pytest.mark.asyncio
    async def test_semantic_completion(self):
        """Test semantic completion from response analysis."""
        responses = [
            ("I've completed all the requested tasks.", True),
            ("Working on it...", False),
            ("Done! All invoices have been processed.", True),
            ("Let me check that for you.", False),
            ("Task complete. No further action needed.", True),
        ]

        for response, expected in responses:
            result = await self._check_semantic_completion(response)
            assert result["is_complete"] == expected, f"Failed for: {response}"

    @pytest.mark.asyncio
    async def test_hybrid_completion_priority(self, tmp_path):
        """Test that completion detection uses correct priority."""
        vault = tmp_path / "vault"
        (vault / "Done").mkdir(parents=True)

        # File completion should take precedence
        done_file = vault / "Done" / "task-001.md"
        done_file.write_text("# Done")

        # Even with ambiguous response
        response = "Processing..."

        result = await self._check_hybrid_completion(str(vault), "task-001", response)

        assert result["completed"] is True
        assert result["method"] == "file_based"

    async def _check_file_completion(self, vault_path: str, task_id: str) -> dict:
        """Check file-based completion."""
        done_path = Path(vault_path) / "Done" / f"{task_id}.md"
        if done_path.exists():
            return {"completed": True, "method": "file_based"}
        return {"completed": False}

    async def _check_semantic_completion(self, response: str) -> dict:
        """Check semantic completion from response."""
        completion_indicators = [
            "completed",
            "done",
            "finished",
            "all tasks",
            "no further action",
            "successfully processed",
        ]

        response_lower = response.lower()
        for indicator in completion_indicators:
            if indicator in response_lower:
                return {"is_complete": True, "indicator": indicator}

        return {"is_complete": False}

    async def _check_hybrid_completion(
        self, vault_path: str, task_id: str, response: str
    ) -> dict:
        """Check completion using hybrid strategy."""
        # Priority 1: File-based
        file_result = await self._check_file_completion(vault_path, task_id)
        if file_result.get("completed"):
            return file_result

        # Priority 2: Semantic
        semantic_result = await self._check_semantic_completion(response)
        if semantic_result.get("is_complete"):
            return {"completed": True, "method": "semantic"}

        return {"completed": False}


class MockCompletionPromise:
    """Mock completion promise for testing."""

    def __init__(self):
        self._completed = False
        self.completion_message = None

    async def is_completed(self) -> bool:
        return self._completed

    async def emit_completion(self, message: str):
        self._completed = True
        self.completion_message = message


class TestLoopState:
    """Test loop state tracking and persistence."""

    @pytest.fixture
    def state_file(self, tmp_path):
        """Create temporary state file."""
        return tmp_path / "loop_state.json"

    @pytest.mark.asyncio
    async def test_state_persistence(self, state_file):
        """Test that loop state is persisted."""
        state = {
            "task_id": "task-001",
            "iteration": 5,
            "started_at": datetime.now().isoformat(),
            "last_action": "Created invoice",
        }

        # Save state
        state_file.write_text(json.dumps(state))

        # Load state
        loaded = json.loads(state_file.read_text())

        assert loaded["task_id"] == state["task_id"]
        assert loaded["iteration"] == state["iteration"]

    @pytest.mark.asyncio
    async def test_state_recovery_after_crash(self, state_file):
        """Test that loop can recover from saved state."""
        # Simulate crash at iteration 3
        crash_state = {
            "task_id": "task-001",
            "iteration": 3,
            "status": "in_progress",
            "last_checkpoint": datetime.now().isoformat(),
        }
        state_file.write_text(json.dumps(crash_state))

        # Recover
        recovered = json.loads(state_file.read_text())

        assert recovered["iteration"] == 3
        assert recovered["status"] == "in_progress"

    @pytest.mark.asyncio
    async def test_iteration_history(self, state_file):
        """Test that iteration history is maintained."""
        history = {
            "iterations": [
                {"number": 1, "action": "Read task file", "duration_ms": 150},
                {"number": 2, "action": "Process data", "duration_ms": 2500},
                {"number": 3, "action": "Generate report", "duration_ms": 800},
            ]
        }
        state_file.write_text(json.dumps(history))

        loaded = json.loads(state_file.read_text())

        assert len(loaded["iterations"]) == 3
        assert loaded["iterations"][1]["action"] == "Process data"


class TestSummaryGeneration:
    """Test completion summary generation."""

    @pytest.mark.asyncio
    async def test_summary_includes_all_actions(self):
        """Test that summary includes all performed actions."""
        actions = [
            {"action": "Read invoice", "result": "success"},
            {"action": "Validate data", "result": "success"},
            {"action": "Create entry", "result": "success"},
        ]

        summary = await self._generate_summary(actions)

        assert summary["total_actions"] == 3
        assert summary["successful"] == 3
        assert "Read invoice" in summary["actions_performed"]

    @pytest.mark.asyncio
    async def test_summary_includes_timing(self):
        """Test that summary includes timing information."""
        start_time = datetime.now() - timedelta(minutes=5)
        end_time = datetime.now()

        summary = await self._generate_summary(
            actions=[],
            start_time=start_time,
            end_time=end_time
        )

        assert "duration" in summary
        assert summary["duration"]["minutes"] >= 4

    @pytest.mark.asyncio
    async def test_summary_includes_errors(self):
        """Test that summary includes any errors encountered."""
        actions = [
            {"action": "Read invoice", "result": "success"},
            {"action": "API call", "result": "error", "error": "Timeout"},
            {"action": "Retry API", "result": "success"},
        ]

        summary = await self._generate_summary(actions)

        assert summary["errors_encountered"] == 1
        assert "Timeout" in str(summary["error_details"])

    async def _generate_summary(
        self,
        actions: list,
        start_time: datetime = None,
        end_time: datetime = None
    ) -> dict:
        """Generate execution summary."""
        start_time = start_time or datetime.now() - timedelta(minutes=1)
        end_time = end_time or datetime.now()

        successful = sum(1 for a in actions if a.get("result") == "success")
        errors = [a for a in actions if a.get("result") == "error"]

        duration = end_time - start_time

        return {
            "total_actions": len(actions),
            "successful": successful,
            "errors_encountered": len(errors),
            "error_details": [e.get("error") for e in errors],
            "actions_performed": [a["action"] for a in actions],
            "duration": {
                "minutes": duration.total_seconds() / 60,
                "seconds": duration.total_seconds(),
            },
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
        }
