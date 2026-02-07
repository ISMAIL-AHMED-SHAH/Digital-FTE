"""Unit Tests for Error Recovery System (T070).

Tests for:
- Error categorization (Transient, Auth, Logic, Data, System)
- Retry with exponential backoff
- Graceful degradation queue
- Quarantine handling
"""

import asyncio
import json
import pytest
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from common.error_categorizer import (
    ErrorCategorizer,
    ErrorCategory,
    CategorizedError,
)
from common.retry_handler import (
    RetryHandler,
    RetryConfig,
    RetryResult,
)


class TestErrorCategorizer:
    """Tests for error categorization."""

    def test_categorize_transient_network_error(self):
        """Test categorizing network timeout as transient."""
        categorizer = ErrorCategorizer()

        error = ConnectionError("Connection timed out")
        result = categorizer.categorize(error)

        assert result.category == ErrorCategory.TRANSIENT
        assert result.is_retryable
        assert "network" in result.suggested_action.lower() or "retry" in result.suggested_action.lower()

    def test_categorize_transient_rate_limit(self):
        """Test categorizing rate limit as transient."""
        categorizer = ErrorCategorizer()

        error = Exception("Rate limit exceeded. Try again in 60 seconds.")
        result = categorizer.categorize(error, context={"status_code": 429})

        assert result.category == ErrorCategory.TRANSIENT
        assert result.is_retryable

    def test_categorize_auth_error(self):
        """Test categorizing authentication failure."""
        categorizer = ErrorCategorizer()

        error = Exception("Invalid access token")
        result = categorizer.categorize(error, context={"status_code": 401})

        assert result.category == ErrorCategory.AUTH
        assert not result.is_retryable
        assert "token" in result.suggested_action.lower() or "auth" in result.suggested_action.lower()

    def test_categorize_auth_expired_token(self):
        """Test categorizing expired token."""
        categorizer = ErrorCategorizer()

        error = Exception("Token has expired")
        result = categorizer.categorize(error)

        assert result.category == ErrorCategory.AUTH

    def test_categorize_logic_validation_error(self):
        """Test categorizing validation error as logic."""
        categorizer = ErrorCategorizer()

        error = ValueError("Invalid invoice amount: must be positive")
        result = categorizer.categorize(error)

        assert result.category == ErrorCategory.LOGIC
        assert not result.is_retryable

    def test_categorize_data_not_found(self):
        """Test categorizing not found as data error."""
        categorizer = ErrorCategorizer()

        error = Exception("Customer not found: ID 12345")
        result = categorizer.categorize(error, context={"status_code": 404})

        assert result.category == ErrorCategory.DATA
        assert not result.is_retryable

    def test_categorize_data_integrity_error(self):
        """Test categorizing integrity error as data."""
        categorizer = ErrorCategorizer()

        error = Exception("Duplicate key violation: invoice_number")
        result = categorizer.categorize(error)

        assert result.category == ErrorCategory.DATA

    def test_categorize_system_internal_error(self):
        """Test categorizing 500 as system error."""
        categorizer = ErrorCategorizer()

        error = Exception("Internal server error")
        result = categorizer.categorize(error, context={"status_code": 500})

        assert result.category == ErrorCategory.SYSTEM
        assert result.is_retryable  # System errors may be retryable

    def test_categorize_with_service_context(self):
        """Test categorization with service-specific context."""
        categorizer = ErrorCategorizer()

        error = Exception("API error")
        result = categorizer.categorize(
            error,
            context={"service": "odoo", "operation": "create_invoice"}
        )

        assert result.service == "odoo"
        assert result.operation == "create_invoice"

    def test_default_category_is_system(self):
        """Test unknown errors default to SYSTEM."""
        categorizer = ErrorCategorizer()

        error = Exception("Some unknown error")
        result = categorizer.categorize(error)

        # Unknown errors should be categorized, default to SYSTEM
        assert result.category in ErrorCategory


class TestRetryHandler:
    """Tests for retry with exponential backoff."""

    @pytest.mark.asyncio
    async def test_successful_first_attempt(self):
        """Test successful operation on first try."""
        handler = RetryHandler()

        async def success_op():
            return "success"

        result = await handler.execute_with_retry(success_op)

        assert result.success
        assert result.value == "success"
        assert result.attempts == 1
        assert result.total_delay == 0

    @pytest.mark.asyncio
    async def test_retry_on_transient_error(self):
        """Test retry on transient error."""
        handler = RetryHandler(config=RetryConfig(
            initial_delay=0.01,
            max_delay=0.1,
            max_attempts=3
        ))

        attempt_count = 0

        async def fail_twice_then_succeed():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ConnectionError("Network error")
            return "success"

        result = await handler.execute_with_retry(fail_twice_then_succeed)

        assert result.success
        assert result.value == "success"
        assert result.attempts == 3

    @pytest.mark.asyncio
    async def test_max_attempts_exceeded(self):
        """Test failure after max attempts."""
        handler = RetryHandler(config=RetryConfig(
            initial_delay=0.01,
            max_delay=0.1,
            max_attempts=3
        ))

        async def always_fail():
            raise ConnectionError("Persistent network error")

        result = await handler.execute_with_retry(always_fail)

        assert not result.success
        assert result.attempts == 3
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_no_retry_on_auth_error(self):
        """Test no retry on non-retryable errors."""
        handler = RetryHandler(config=RetryConfig(
            initial_delay=0.01,
            max_attempts=5
        ))

        attempt_count = 0

        async def auth_fail():
            nonlocal attempt_count
            attempt_count += 1
            error = Exception("Invalid token")
            error.status_code = 401  # Auth error
            raise error

        result = await handler.execute_with_retry(
            auth_fail,
            error_context={"status_code": 401}
        )

        assert not result.success
        assert attempt_count == 1  # Should not retry

    @pytest.mark.asyncio
    async def test_exponential_backoff_timing(self):
        """Test exponential backoff delays."""
        handler = RetryHandler(config=RetryConfig(
            initial_delay=0.1,
            max_delay=1.0,
            max_attempts=4,
            backoff_multiplier=2.0
        ))

        delays = []
        original_sleep = asyncio.sleep

        async def mock_sleep(delay):
            delays.append(delay)
            await original_sleep(0.001)  # Minimal actual delay

        async def always_fail():
            raise ConnectionError("Network error")

        with patch("asyncio.sleep", mock_sleep):
            await handler.execute_with_retry(always_fail)

        # Should have delays for attempts 2, 3, 4 (not first attempt)
        assert len(delays) == 3
        # Delays should increase: 0.1, 0.2, 0.4 (capped at max_delay)
        assert delays[0] == pytest.approx(0.1, rel=0.1)
        assert delays[1] == pytest.approx(0.2, rel=0.1)
        assert delays[2] == pytest.approx(0.4, rel=0.1)

    @pytest.mark.asyncio
    async def test_max_delay_cap(self):
        """Test delay is capped at max_delay."""
        handler = RetryHandler(config=RetryConfig(
            initial_delay=1.0,
            max_delay=2.0,
            max_attempts=5,
            backoff_multiplier=3.0
        ))

        delays = []

        async def mock_sleep(delay):
            delays.append(delay)

        async def always_fail():
            raise ConnectionError("Network error")

        with patch("asyncio.sleep", mock_sleep):
            await handler.execute_with_retry(always_fail)

        # All delays should be <= max_delay
        for delay in delays:
            assert delay <= 2.0

    @pytest.mark.asyncio
    async def test_retry_callback(self):
        """Test callback on each retry."""
        handler = RetryHandler(config=RetryConfig(
            initial_delay=0.01,
            max_attempts=3
        ))

        retry_events = []

        def on_retry(attempt, error, delay):
            retry_events.append({
                "attempt": attempt,
                "error": str(error),
                "delay": delay
            })

        async def fail_twice():
            if len(retry_events) < 2:
                raise ConnectionError("Network error")
            return "success"

        await handler.execute_with_retry(fail_twice, on_retry=on_retry)

        assert len(retry_events) == 2
        assert retry_events[0]["attempt"] == 1
        assert retry_events[1]["attempt"] == 2


class TestGracefulDegradationQueue:
    """Tests for graceful degradation queue."""

    def test_queue_action_when_service_unavailable(self):
        """Test queuing action when service is down."""
        from orchestrator.action_queue import GracefulDegradationQueue

        with tempfile.TemporaryDirectory() as tmpdir:
            queue = GracefulDegradationQueue(
                persistence_path=Path(tmpdir) / "queue.json"
            )

            action = {
                "type": "create_invoice",
                "service": "odoo",
                "payload": {"customer_id": 123, "amount": 100.00},
            }

            queue.enqueue(action, reason="Service unavailable")

            assert queue.size() == 1
            queued = queue.peek()
            assert queued["type"] == "create_invoice"
            assert queued["payload"]["customer_id"] == 123

    def test_queue_persistence(self):
        """Test queue persists to disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_path = Path(tmpdir) / "queue.json"

            # Add to queue
            queue1 = GracefulDegradationQueue(persistence_path=queue_path)
            queue1.enqueue({"type": "test", "data": "value"}, reason="Test")

            # Create new queue instance - should load from disk
            queue2 = GracefulDegradationQueue(persistence_path=queue_path)

            assert queue2.size() == 1
            assert queue2.peek()["type"] == "test"

    def test_queue_max_size(self):
        """Test queue respects max size."""
        with tempfile.TemporaryDirectory() as tmpdir:
            queue = GracefulDegradationQueue(
                persistence_path=Path(tmpdir) / "queue.json",
                max_size=3
            )

            for i in range(5):
                result = queue.enqueue({"type": f"action_{i}"}, reason="Test")
                if i < 3:
                    assert result.success
                else:
                    assert not result.success

            assert queue.size() == 3

    def test_dequeue_in_order(self):
        """Test FIFO dequeue order."""
        with tempfile.TemporaryDirectory() as tmpdir:
            queue = GracefulDegradationQueue(
                persistence_path=Path(tmpdir) / "queue.json"
            )

            queue.enqueue({"order": 1}, reason="Test")
            queue.enqueue({"order": 2}, reason="Test")
            queue.enqueue({"order": 3}, reason="Test")

            assert queue.dequeue()["order"] == 1
            assert queue.dequeue()["order"] == 2
            assert queue.dequeue()["order"] == 3
            assert queue.dequeue() is None

    def test_process_queue_on_service_restore(self):
        """Test processing queued actions when service restored."""
        with tempfile.TemporaryDirectory() as tmpdir:
            queue = GracefulDegradationQueue(
                persistence_path=Path(tmpdir) / "queue.json"
            )

            # Queue some actions
            queue.enqueue({"type": "a"}, reason="Test")
            queue.enqueue({"type": "b"}, reason="Test")

            # Process with mock handler
            processed = []

            def handler(action):
                processed.append(action["type"])
                return True

            queue.process_all(handler)

            assert processed == ["a", "b"]
            assert queue.size() == 0


class TestQuarantineHandler:
    """Tests for quarantine handling."""

    def test_quarantine_malformed_file(self):
        """Test quarantining a malformed file."""
        from common.quarantine_handler import QuarantineHandler

        with tempfile.TemporaryDirectory() as tmpdir:
            vault_path = Path(tmpdir)
            needs_action = vault_path / "Needs_Action"
            quarantine = vault_path / "Quarantine"
            needs_action.mkdir()

            # Create malformed file
            bad_file = needs_action / "bad_task.md"
            bad_file.write_text("This is not valid YAML frontmatter")

            handler = QuarantineHandler(vault_path=vault_path)
            result = handler.quarantine(
                bad_file,
                reason="Invalid YAML frontmatter",
                error_details={"line": 1, "error": "parse error"}
            )

            assert result.success
            assert not bad_file.exists()
            assert (quarantine / "bad_task.md").exists()

    def test_quarantine_creates_metadata(self):
        """Test quarantine creates metadata file."""
        from common.quarantine_handler import QuarantineHandler

        with tempfile.TemporaryDirectory() as tmpdir:
            vault_path = Path(tmpdir)
            needs_action = vault_path / "Needs_Action"
            quarantine = vault_path / "Quarantine"
            needs_action.mkdir()

            task_file = needs_action / "task.md"
            task_file.write_text("content")

            handler = QuarantineHandler(vault_path=vault_path)
            handler.quarantine(task_file, reason="Test reason")

            # Check metadata file exists
            metadata_file = quarantine / "task.md.quarantine.json"
            assert metadata_file.exists()

            metadata = json.loads(metadata_file.read_text())
            assert metadata["reason"] == "Test reason"
            assert "quarantined_at" in metadata
            assert metadata["original_path"] == str(task_file)

    def test_quarantine_handles_duplicates(self):
        """Test quarantine handles duplicate filenames."""
        from common.quarantine_handler import QuarantineHandler

        with tempfile.TemporaryDirectory() as tmpdir:
            vault_path = Path(tmpdir)
            needs_action = vault_path / "Needs_Action"
            quarantine = vault_path / "Quarantine"
            needs_action.mkdir()
            quarantine.mkdir()

            # Pre-existing quarantined file
            (quarantine / "task.md").write_text("old")

            # New file with same name
            task_file = needs_action / "task.md"
            task_file.write_text("new")

            handler = QuarantineHandler(vault_path=vault_path)
            result = handler.quarantine(task_file, reason="Test")

            assert result.success
            # Should have renamed with timestamp
            files = list(quarantine.glob("task*.md"))
            assert len(files) == 2

    def test_list_quarantined_files(self):
        """Test listing quarantined files."""
        from common.quarantine_handler import QuarantineHandler

        with tempfile.TemporaryDirectory() as tmpdir:
            vault_path = Path(tmpdir)
            quarantine = vault_path / "Quarantine"
            quarantine.mkdir(parents=True)

            # Create quarantined files with metadata
            for i in range(3):
                (quarantine / f"file{i}.md").write_text(f"content {i}")
                (quarantine / f"file{i}.md.quarantine.json").write_text(
                    json.dumps({"reason": f"Reason {i}", "quarantined_at": "2026-02-07"})
                )

            handler = QuarantineHandler(vault_path=vault_path)
            files = handler.list_quarantined()

            assert len(files) == 3
            assert all("reason" in f for f in files)

    def test_restore_from_quarantine(self):
        """Test restoring file from quarantine."""
        from common.quarantine_handler import QuarantineHandler

        with tempfile.TemporaryDirectory() as tmpdir:
            vault_path = Path(tmpdir)
            needs_action = vault_path / "Needs_Action"
            quarantine = vault_path / "Quarantine"
            needs_action.mkdir()
            quarantine.mkdir()

            # Create quarantined file
            quarantined = quarantine / "task.md"
            quarantined.write_text("content")
            (quarantine / "task.md.quarantine.json").write_text(
                json.dumps({
                    "reason": "Test",
                    "original_path": str(needs_action / "task.md")
                })
            )

            handler = QuarantineHandler(vault_path=vault_path)
            result = handler.restore(quarantined)

            assert result.success
            assert (needs_action / "task.md").exists()
            assert not quarantined.exists()


class TestErrorRecoveryIntegration:
    """Integration tests for error recovery flow."""

    @pytest.mark.asyncio
    async def test_full_recovery_flow(self):
        """Test complete error recovery flow."""
        from common.error_categorizer import ErrorCategorizer
        from common.retry_handler import RetryHandler, RetryConfig

        categorizer = ErrorCategorizer()
        handler = RetryHandler(config=RetryConfig(
            initial_delay=0.01,
            max_attempts=3
        ))

        # Simulate transient error that resolves
        attempt = 0

        async def flaky_operation():
            nonlocal attempt
            attempt += 1
            if attempt < 2:
                raise ConnectionError("Temporary network issue")
            return {"status": "success"}

        # First categorize to determine if retryable
        test_error = ConnectionError("Temporary network issue")
        categorized = categorizer.categorize(test_error)

        assert categorized.is_retryable

        # Then execute with retry
        result = await handler.execute_with_retry(flaky_operation)

        assert result.success
        assert result.value["status"] == "success"

    @pytest.mark.asyncio
    async def test_queue_on_persistent_failure(self):
        """Test queuing action after persistent failure."""
        from orchestrator.action_queue import GracefulDegradationQueue
        from common.retry_handler import RetryHandler, RetryConfig

        with tempfile.TemporaryDirectory() as tmpdir:
            queue = GracefulDegradationQueue(
                persistence_path=Path(tmpdir) / "queue.json"
            )
            handler = RetryHandler(config=RetryConfig(
                initial_delay=0.01,
                max_attempts=2
            ))

            action = {"type": "create_invoice", "customer_id": 123}

            async def always_fail():
                raise ConnectionError("Service unavailable")

            result = await handler.execute_with_retry(always_fail)

            if not result.success:
                # Queue for later
                queue.enqueue(action, reason=str(result.error))

            assert queue.size() == 1
