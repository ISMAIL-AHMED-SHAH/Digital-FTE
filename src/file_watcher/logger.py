"""
Structured JSON logging for Local File Watcher Service.

Provides JSON-formatted log output with action_type field for all operations.
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from typing import Any

from pythonjsonlogger.json import JsonFormatter


class WatcherJsonFormatter(JsonFormatter):
    """
    Custom JSON formatter for file watcher logs.

    Adds timestamp in ISO 8601 UTC format and ensures consistent field ordering.
    """

    def add_fields(
        self,
        log_record: dict[str, Any],
        record: logging.LogRecord,
        message_dict: dict[str, Any],
    ) -> None:
        """Add custom fields to the log record."""
        super().add_fields(log_record, record, message_dict)

        # Add timestamp in ISO 8601 UTC format
        log_record["timestamp"] = datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%S.%f"
        )[:-3] + "Z"

        # Add level name
        log_record["level"] = record.levelname

        # Add logger name
        log_record["logger"] = record.name


def setup_logger(name: str = "file_watcher") -> logging.Logger:
    """
    Configure and return a JSON-formatted logger.

    Sets up logging with:
    - INFO/DEBUG to stdout
    - WARNING/ERROR to stderr
    - JSON format for all output

    Args:
        name: Logger name. Defaults to "file_watcher".

    Returns:
        Configured logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Prevent duplicate handlers if called multiple times
    if logger.handlers:
        return logger

    # JSON formatter
    formatter = WatcherJsonFormatter()

    # stdout handler for INFO and DEBUG
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.DEBUG)
    stdout_handler.setFormatter(formatter)
    stdout_handler.addFilter(lambda record: record.levelno < logging.WARNING)

    # stderr handler for WARNING and ERROR
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.WARNING)
    stderr_handler.setFormatter(formatter)

    logger.addHandler(stdout_handler)
    logger.addHandler(stderr_handler)

    # Prevent propagation to root logger
    logger.propagate = False

    return logger


def get_logger() -> logging.Logger:
    """
    Get or create the file_watcher logger.

    Returns:
        The configured logger instance.
    """
    return setup_logger("file_watcher")


# Pre-defined log functions for common action types


def log_startup(
    logger: logging.Logger,
    vault_path: str,
    drop_folder: str,
    dry_run: bool,
) -> None:
    """Log service startup."""
    logger.info(
        "File watcher started",
        extra={
            "action_type": "startup",
            "vault_path": vault_path,
            "drop_folder": drop_folder,
            "dry_run": dry_run,
        },
    )


def log_file_detected(
    logger: logging.Logger,
    source_file: str,
    size: int,
) -> None:
    """Log file detection."""
    logger.info(
        "File detected",
        extra={
            "action_type": "file_detected",
            "source_file": source_file,
            "size": size,
        },
    )


def log_action_created(
    logger: logging.Logger,
    source_file: str,
    action_file: str,
) -> None:
    """Log action file creation."""
    logger.info(
        "Action file created",
        extra={
            "action_type": "action_created",
            "source_file": source_file,
            "action_file": action_file,
        },
    )


def log_action_skipped(
    logger: logging.Logger,
    source_file: str,
    would_create: str,
) -> None:
    """Log skipped action in dry-run mode."""
    logger.info(
        "Action file skipped (dry-run)",
        extra={
            "action_type": "action_skipped",
            "source_file": source_file,
            "would_create": would_create,
        },
    )


def log_error(
    logger: logging.Logger,
    message: str,
    source_file: str | None = None,
    error: str | None = None,
    traceback: str | None = None,
) -> None:
    """Log an error."""
    extra: dict[str, Any] = {"action_type": "error"}
    if source_file:
        extra["source_file"] = source_file
    if error:
        extra["error"] = error
    if traceback:
        extra["traceback"] = traceback
    logger.error(message, extra=extra)


def log_shutdown(
    logger: logging.Logger,
    reason: str,
) -> None:
    """Log service shutdown."""
    logger.info(
        "File watcher stopped",
        extra={
            "action_type": "shutdown",
            "reason": reason,
        },
    )
