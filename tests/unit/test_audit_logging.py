"""Unit Tests for Audit Logging System (T079).

Tests for:
- Log creation with required fields
- Log querying by date, action type, target, result
- 90-day retention
- Compression at 30 days
- Size alerting
"""

import gzip
import json
import pytest
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from common.audit_logger import (
    AuditLogger,
    AuditLogEntry,
    get_audit_logger,
)


class TestAuditLogEntry:
    """Tests for AuditLogEntry creation."""

    def test_create_entry_with_required_fields(self):
        """Test entry has all required fields."""
        entry = AuditLogEntry(
            component="test_component",
            action_type="test_action"
        )

        assert entry.timestamp is not None
        assert entry.level == "INFO"
        assert entry.component == "test_component"
        assert entry.action_type == "test_action"

    def test_entry_sanitizes_sensitive_data(self):
        """Test sensitive data is redacted."""
        entry = AuditLogEntry(
            component="test",
            action_type="test",
            parameters={
                "username": "john",
                "password": "secret123",
                "api_key": "sk-12345",
                "data": "normal"
            }
        )

        params = entry.parameters
        assert params["username"] == "john"
        assert params["password"] == "[REDACTED]"
        assert params["api_key"] == "[REDACTED]"
        assert params["data"] == "normal"

    def test_entry_truncates_long_values(self):
        """Test very long values are truncated."""
        long_value = "x" * 1000
        entry = AuditLogEntry(
            component="test",
            action_type="test",
            parameters={"long_field": long_value}
        )

        assert len(entry.parameters["long_field"]) < len(long_value)
        assert "[truncated]" in entry.parameters["long_field"]

    def test_entry_to_dict(self):
        """Test conversion to dictionary."""
        entry = AuditLogEntry(
            component="test",
            action_type="test_action",
            actor="user123",
            target="target456",
            result="success"
        )

        d = entry.to_dict()

        assert d["component"] == "test"
        assert d["action_type"] == "test_action"
        assert d["actor"] == "user123"
        assert d["target"] == "target456"
        assert d["result"] == "success"
        assert "timestamp" in d

    def test_entry_to_json(self):
        """Test JSON serialization."""
        entry = AuditLogEntry(
            component="test",
            action_type="test"
        )

        json_str = entry.to_json()
        parsed = json.loads(json_str)

        assert parsed["component"] == "test"


class TestAuditLogger:
    """Tests for AuditLogger operations."""

    def test_log_creates_daily_file(self):
        """Test logs are written to daily file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(tmpdir)
            logger.log("test", "test_action")

            # Check today's log file exists
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            log_file = Path(tmpdir) / "Logs" / f"{today}.json"

            assert log_file.exists()

    def test_log_detection(self):
        """Test logging detection events."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(tmpdir)

            entry = logger.log_detection(
                component="gmail_watcher",
                action_type="email_detected",
                target="sender@example.com",
                parameters={"subject": "Test"}
            )

            assert entry.component == "gmail_watcher"
            assert entry.action_type == "email_detected"
            assert entry.result == "action_file_created"

    def test_log_approval(self):
        """Test logging approval events."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(tmpdir)

            entry = logger.log_approval(
                component="approval_watcher",
                action_type="email_send",
                target="recipient@example.com",
                approval_status="approved"
            )

            assert entry.approval_status == "approved"
            assert entry.result == "approval_approved"

    def test_log_execution(self):
        """Test logging execution events."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(tmpdir)

            entry = logger.log_execution(
                component="odoo_mcp",
                action_type="create_invoice",
                target="customer_123",
                result="success",
                external_id="INV-001"
            )

            assert entry.result == "success"
            assert entry.extra.get("external_id") == "INV-001"

    def test_log_error(self):
        """Test logging error events."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(tmpdir)

            entry = logger.log_error(
                component="twitter_mcp",
                action_type="post_tweet",
                error=ValueError("Rate limit exceeded"),
                target="tweet_draft"
            )

            assert entry.level == "ERROR"
            assert entry.result == "error"
            assert "Rate limit" in entry.error


class TestAuditLoggerQueries:
    """Tests for log querying."""

    def setup_method(self):
        """Create test logs."""
        self.tmpdir = tempfile.mkdtemp()
        self.logger = AuditLogger(self.tmpdir)

        # Create test entries
        for i in range(5):
            self.logger.log(
                component=f"component_{i % 2}",
                action_type="action_a" if i % 2 == 0 else "action_b",
                target=f"target_{i}",
                result="success" if i % 3 != 0 else "error"
            )

    def test_query_all_logs(self):
        """Test querying without filters."""
        results = list(self.logger.query_logs())
        assert len(results) == 5

    def test_query_by_action_type(self):
        """Test filtering by action_type."""
        results = list(self.logger.query_logs(action_type="action_a"))
        assert all(r["action_type"] == "action_a" for r in results)

    def test_query_by_target(self):
        """Test filtering by target substring."""
        results = list(self.logger.query_logs(target="target_1"))
        assert len(results) >= 1
        assert all("target_1" in r["target"] for r in results)

    def test_query_by_result(self):
        """Test filtering by result."""
        results = list(self.logger.query_logs(result="error"))
        assert all(r["result"] == "error" for r in results)

    def test_query_by_component(self):
        """Test filtering by component."""
        results = list(self.logger.query_logs(component="component_0"))
        assert all(r["component"] == "component_0" for r in results)

    def test_query_with_limit(self):
        """Test query result limiting."""
        results = list(self.logger.query_logs(limit=2))
        assert len(results) == 2

    def test_query_by_date_range(self):
        """Test filtering by date range."""
        now = datetime.now(timezone.utc)
        yesterday = now - timedelta(days=1)

        results = list(self.logger.query_logs(
            date_from=yesterday,
            date_to=now
        ))
        assert len(results) >= 5  # Today's logs


class TestAuditLoggerRetention:
    """Tests for log retention and compression."""

    def test_compress_old_logs(self):
        """Test compressing logs older than threshold."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(tmpdir)
            logs_dir = Path(tmpdir) / "Logs"

            # Create an "old" log file
            old_date = (datetime.now() - timedelta(days=35)).strftime("%Y-%m-%d")
            old_file = logs_dir / f"{old_date}.json"
            old_file.write_text('{"test": "data"}\n')

            # Run compression
            compressed = logger.compress_old_logs(days_threshold=30)

            # Verify compression
            assert len(compressed) >= 1
            assert not old_file.exists()
            assert (logs_dir / f"{old_date}.json.gz").exists()

    def test_cleanup_old_logs(self):
        """Test deleting logs older than retention."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(tmpdir)
            logs_dir = Path(tmpdir) / "Logs"

            # Create a very old log file
            old_date = (datetime.now() - timedelta(days=100)).strftime("%Y-%m-%d")
            old_file = logs_dir / f"{old_date}.json"
            old_file.write_text('{"test": "data"}\n')

            # Run cleanup
            deleted = logger.cleanup_old_logs(retention_days=90)

            # Verify deletion
            assert len(deleted) >= 1
            assert not old_file.exists()

    def test_retention_keeps_recent_logs(self):
        """Test retention doesn't delete recent logs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(tmpdir)
            logs_dir = Path(tmpdir) / "Logs"

            # Create a recent log
            recent_date = datetime.now().strftime("%Y-%m-%d")
            recent_file = logs_dir / f"{recent_date}.json"
            recent_file.write_text('{"test": "data"}\n')

            # Run cleanup
            logger.cleanup_old_logs(retention_days=90)

            # Recent file should remain
            assert recent_file.exists()


class TestAuditLoggerSizeAlerting:
    """Tests for size alerting."""

    def test_get_log_size(self):
        """Test calculating total log size."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(tmpdir)
            logs_dir = Path(tmpdir) / "Logs"

            # Create some log files
            (logs_dir / "test1.json").write_text("x" * 1000)
            (logs_dir / "test2.json").write_text("x" * 500)

            size = logger.get_log_size_bytes()
            assert size >= 1500

    def test_size_alert_triggered(self):
        """Test size alert when threshold exceeded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(tmpdir)
            logs_dir = Path(tmpdir) / "Logs"

            # Create a log file
            (logs_dir / "test.json").write_text("x" * 1000)

            # Check with very small max (should trigger)
            alert = logger.check_size_alert(
                max_size_bytes=1000,  # 1KB
                alert_threshold=0.8
            )

            assert alert is not None
            assert "log_size_warning" in alert["alert_type"]

    def test_no_alert_below_threshold(self):
        """Test no alert when under threshold."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(tmpdir)
            logs_dir = Path(tmpdir) / "Logs"

            # Create a small log file
            (logs_dir / "test.json").write_text("x" * 100)

            # Check with large max (should not trigger)
            alert = logger.check_size_alert(
                max_size_bytes=1024 * 1024 * 1024,  # 1GB
                alert_threshold=0.8
            )

            assert alert is None


class TestAuditLoggerMaintenance:
    """Tests for full maintenance cycle."""

    def test_run_maintenance(self):
        """Test full maintenance cycle."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(tmpdir)
            logs_dir = Path(tmpdir) / "Logs"

            # Create old and recent logs
            old_date = (datetime.now() - timedelta(days=100)).strftime("%Y-%m-%d")
            (logs_dir / f"{old_date}.json").write_text('{"old": "data"}\n')

            compress_date = (datetime.now() - timedelta(days=35)).strftime("%Y-%m-%d")
            (logs_dir / f"{compress_date}.json").write_text('{"compress": "data"}\n')

            recent_date = datetime.now().strftime("%Y-%m-%d")
            (logs_dir / f"{recent_date}.json").write_text('{"recent": "data"}\n')

            # Run maintenance
            report = logger.run_maintenance(
                retention_days=90,
                compression_days=30
            )

            # Verify report
            assert len(report["compressed_files"]) >= 1
            assert len(report["deleted_files"]) >= 1
            assert report["final_size_bytes"] >= 0

            # Old file deleted, compressed file gzipped, recent file intact
            assert not (logs_dir / f"{old_date}.json").exists()
            assert (logs_dir / f"{compress_date}.json.gz").exists()
            assert (logs_dir / f"{recent_date}.json").exists()


class TestAuditLoggerStats:
    """Tests for log statistics."""

    def test_get_log_stats(self):
        """Test getting log statistics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(tmpdir)

            # Create various entries
            logger.log("comp_a", "action_1", result="success")
            logger.log("comp_a", "action_2", result="success")
            logger.log("comp_b", "action_1", result="error")
            logger.log_error("comp_b", "action_error", "Test error")

            stats = logger.get_log_stats()

            assert stats["total_entries"] == 4
            assert stats["by_component"]["comp_a"] == 2
            assert stats["by_component"]["comp_b"] == 2
            assert stats["errors"] >= 1


class TestCompressedLogQueries:
    """Tests for querying compressed logs."""

    def test_query_compressed_logs(self):
        """Test querying gzipped log files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(tmpdir)
            logs_dir = Path(tmpdir) / "Logs"

            # Create compressed log
            old_date = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
            compressed_path = logs_dir / f"{old_date}.json.gz"

            entry = {"timestamp": "2026-02-01", "action_type": "test", "component": "test"}
            with gzip.open(compressed_path, "wt") as f:
                f.write(json.dumps(entry) + "\n")

            # Query should find it
            results = list(logger.query_logs(
                date_from=datetime.now() - timedelta(days=10)
            ))

            assert len(results) >= 1
