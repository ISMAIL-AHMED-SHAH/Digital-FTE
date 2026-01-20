"""
Unit tests for file_watcher logging functionality.

Tests JSON log format validation per FR-009 and data-model.md LogEntry schema.
"""

import json
import logging

import pytest

from file_watcher.logger import (
    get_logger,
    log_action_created,
    log_action_skipped,
    log_error,
    log_file_detected,
    log_shutdown,
    log_startup,
    setup_logger,
)


class TestLoggerSetup:
    """Tests for logger configuration."""

    def test_setup_logger_returns_logger(self) -> None:
        """setup_logger returns a configured Logger instance."""
        logger = setup_logger("test_logger_setup")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_logger_setup"

    def test_get_logger_returns_file_watcher_logger(self) -> None:
        """get_logger returns the file_watcher logger."""
        logger = get_logger()
        assert logger.name == "file_watcher"

    def test_logger_has_handlers(self) -> None:
        """Logger has stdout and stderr handlers configured."""
        logger = setup_logger("test_handlers")
        # Should have at least 2 handlers (stdout and stderr)
        assert len(logger.handlers) >= 2


class TestLogFormat:
    """Tests for JSON log format validation."""

    @pytest.fixture
    def logger(self) -> logging.Logger:
        """Create a logger for testing."""
        return setup_logger("test_log_format")

    @pytest.fixture
    def log_capture(self, logger: logging.Logger):
        """Capture log output for verification."""
        import io

        # Create a string buffer to capture output
        buffer = io.StringIO()
        handler = logging.StreamHandler(buffer)
        handler.setLevel(logging.DEBUG)

        # Use the same formatter as the real logger
        from file_watcher.logger import WatcherJsonFormatter

        handler.setFormatter(WatcherJsonFormatter())
        logger.addHandler(handler)

        yield buffer

        # Cleanup
        logger.removeHandler(handler)

    def test_log_output_is_valid_json(
        self, logger: logging.Logger, log_capture
    ) -> None:
        """Log output is valid JSON."""
        logger.info("Test message")
        log_capture.seek(0)
        output = log_capture.readline()

        # Should be parseable as JSON
        parsed = json.loads(output)
        assert "message" in parsed

    def test_log_contains_timestamp(
        self, logger: logging.Logger, log_capture
    ) -> None:
        """Log output contains timestamp in ISO 8601 UTC format."""
        logger.info("Test message")
        log_capture.seek(0)
        output = log_capture.readline()

        parsed = json.loads(output)
        assert "timestamp" in parsed
        # Should end with Z (UTC)
        assert parsed["timestamp"].endswith("Z")
        # Should be ISO 8601 format
        assert "T" in parsed["timestamp"]

    def test_log_contains_level(
        self, logger: logging.Logger, log_capture
    ) -> None:
        """Log output contains level field."""
        logger.info("Test message")
        log_capture.seek(0)
        output = log_capture.readline()

        parsed = json.loads(output)
        assert "level" in parsed
        assert parsed["level"] == "INFO"

    def test_log_contains_logger_name(
        self, logger: logging.Logger, log_capture
    ) -> None:
        """Log output contains logger name."""
        logger.info("Test message")
        log_capture.seek(0)
        output = log_capture.readline()

        parsed = json.loads(output)
        assert "logger" in parsed
        assert parsed["logger"] == "test_log_format"


class TestActionTypeLogging:
    """Tests for action_type field in log entries per data-model.md."""

    @pytest.fixture
    def logger(self) -> logging.Logger:
        """Create a logger for testing."""
        return setup_logger("test_action_types")

    @pytest.fixture
    def log_capture(self, logger: logging.Logger):
        """Capture log output for verification."""
        import io

        from file_watcher.logger import WatcherJsonFormatter

        buffer = io.StringIO()
        handler = logging.StreamHandler(buffer)
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(WatcherJsonFormatter())
        logger.addHandler(handler)

        yield buffer

        logger.removeHandler(handler)

    def test_startup_log_has_correct_action_type(
        self, logger: logging.Logger, log_capture
    ) -> None:
        """Startup log has action_type='startup'."""
        log_startup(logger, "/path/to/vault", "/path/to/drop", False)
        log_capture.seek(0)
        output = log_capture.readline()

        parsed = json.loads(output)
        assert parsed["action_type"] == "startup"
        assert parsed["vault_path"] == "/path/to/vault"
        assert parsed["drop_folder"] == "/path/to/drop"
        assert parsed["dry_run"] is False

    def test_file_detected_log_has_correct_action_type(
        self, logger: logging.Logger, log_capture
    ) -> None:
        """File detected log has action_type='file_detected'."""
        log_file_detected(logger, "/path/to/file.pdf", 1024)
        log_capture.seek(0)
        output = log_capture.readline()

        parsed = json.loads(output)
        assert parsed["action_type"] == "file_detected"
        assert parsed["source_file"] == "/path/to/file.pdf"
        assert parsed["size"] == 1024

    def test_action_created_log_has_correct_action_type(
        self, logger: logging.Logger, log_capture
    ) -> None:
        """Action created log has action_type='action_created'."""
        log_action_created(logger, "/path/to/source.pdf", "/vault/FILE_source.pdf.md")
        log_capture.seek(0)
        output = log_capture.readline()

        parsed = json.loads(output)
        assert parsed["action_type"] == "action_created"
        assert parsed["source_file"] == "/path/to/source.pdf"
        assert parsed["action_file"] == "/vault/FILE_source.pdf.md"

    def test_action_skipped_log_has_correct_action_type(
        self, logger: logging.Logger, log_capture
    ) -> None:
        """Action skipped log has action_type='action_skipped'."""
        log_action_skipped(logger, "/path/to/source.pdf", "/vault/FILE_source.pdf.md")
        log_capture.seek(0)
        output = log_capture.readline()

        parsed = json.loads(output)
        assert parsed["action_type"] == "action_skipped"
        assert parsed["source_file"] == "/path/to/source.pdf"
        assert parsed["would_create"] == "/vault/FILE_source.pdf.md"

    def test_error_log_has_correct_action_type(
        self, logger: logging.Logger, log_capture
    ) -> None:
        """Error log has action_type='error' with traceback."""
        log_error(
            logger,
            "Test error",
            source_file="/path/to/file.pdf",
            error="Permission denied",
            traceback="Traceback...",
        )
        log_capture.seek(0)
        output = log_capture.readline()

        parsed = json.loads(output)
        assert parsed["action_type"] == "error"
        assert parsed["source_file"] == "/path/to/file.pdf"
        assert parsed["error"] == "Permission denied"
        assert parsed["traceback"] == "Traceback..."

    def test_shutdown_log_has_correct_action_type(
        self, logger: logging.Logger, log_capture
    ) -> None:
        """Shutdown log has action_type='shutdown'."""
        log_shutdown(logger, "SIGINT received")
        log_capture.seek(0)
        output = log_capture.readline()

        parsed = json.loads(output)
        assert parsed["action_type"] == "shutdown"
        assert parsed["reason"] == "SIGINT received"


class TestLogLevelRouting:
    """Tests for log level routing to stdout/stderr."""

    def test_info_logs_to_stdout(self) -> None:
        """INFO level logs go to stdout handler."""
        import sys

        logger = setup_logger("test_routing_stdout")

        # Find stdout handler by checking stream identity
        stdout_handler = None
        for handler in logger.handlers:
            if hasattr(handler, "stream") and handler.stream is sys.stdout:
                stdout_handler = handler
                break

        assert stdout_handler is not None, "Should have stdout handler"
        # INFO should be accepted by stdout handler
        assert stdout_handler.level <= logging.INFO

    def test_error_logs_to_stderr(self) -> None:
        """ERROR level logs go to stderr handler."""
        import sys

        logger = setup_logger("test_routing_stderr")

        # Find stderr handler by checking stream identity
        stderr_handler = None
        for handler in logger.handlers:
            if hasattr(handler, "stream") and handler.stream is sys.stderr:
                stderr_handler = handler
                break

        assert stderr_handler is not None, "Should have stderr handler"
        # ERROR should be accepted by stderr handler
        assert stderr_handler.level <= logging.ERROR
