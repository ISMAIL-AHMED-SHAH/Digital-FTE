"""Audit Logger Module for Silver and Gold Tier.

Provides structured JSON-lines logging for all watcher detections
and MCP executions to /Vault/Logs/YYYY-MM-DD.json.

Gold Tier Extensions (FR-031-036):
- 90-day log retention with automatic cleanup
- Compression of logs older than 30 days (gzip)
- Size alerting at 80% of configured limit (default 1GB)
- Log query support by date range, action type, target, and result

Implements FR-012, FR-015 (Silver), FR-031-036 (Gold) from spec.
"""

import gzip
import json
import logging
import os
import shutil
import traceback
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Generator, Iterator

logger = logging.getLogger(__name__)


class AuditLogEntry:
    """Structured audit log entry.

    All entries contain these standard fields:
    - timestamp: ISO 8601 UTC timestamp
    - level: Log level (INFO, WARNING, ERROR, etc.)
    - component: Source component (gmail_watcher, approval_watcher, etc.)
    - action_type: Type of action being logged
    - actor: Who/what performed the action
    - target: What the action was performed on
    - parameters: Action parameters (sanitized)
    - approval_status: null, pending, approved, rejected, expired
    - result: Outcome of the action
    - error: Error message if any
    """

    def __init__(
        self,
        component: str,
        action_type: str,
        *,
        level: str = "INFO",
        actor: str | None = None,
        target: str | None = None,
        parameters: dict[str, Any] | None = None,
        approval_status: str | None = None,
        result: str | None = None,
        error: str | None = None,
        traceback_str: str | None = None,
        **extra_fields
    ):
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.level = level
        self.component = component
        self.action_type = action_type
        self.actor = actor
        self.target = target
        self.parameters = self._sanitize_parameters(parameters) if parameters else None
        self.approval_status = approval_status
        self.result = result
        self.error = error
        self.traceback = traceback_str
        self.extra = extra_fields

    @staticmethod
    def _sanitize_parameters(params: dict[str, Any]) -> dict[str, Any]:
        """Remove sensitive data from parameters before logging."""
        sanitized = {}
        sensitive_keys = {
            "password", "secret", "token", "key", "credential",
            "access_token", "refresh_token", "api_key", "auth"
        }

        for key, value in params.items():
            key_lower = key.lower()
            if any(s in key_lower for s in sensitive_keys):
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, str) and len(value) > 500:
                # Truncate very long values (like email bodies)
                sanitized[key] = value[:500] + "...[truncated]"
            elif isinstance(value, dict):
                sanitized[key] = AuditLogEntry._sanitize_parameters(value)
            else:
                sanitized[key] = value

        return sanitized

    def to_dict(self) -> dict[str, Any]:
        """Convert entry to dictionary for JSON serialization."""
        entry = {
            "timestamp": self.timestamp,
            "level": self.level,
            "component": self.component,
            "action_type": self.action_type,
            "actor": self.actor,
            "target": self.target,
            "parameters": self.parameters,
            "approval_status": self.approval_status,
            "result": self.result,
            "error": self.error,
        }

        # Include traceback only for errors
        if self.traceback and self.level in ("ERROR", "CRITICAL"):
            entry["traceback"] = self.traceback

        # Include any extra fields
        entry.update(self.extra)

        return entry

    def to_json(self) -> str:
        """Convert entry to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False)


class AuditLogger:
    """Audit logger that writes JSON-lines to daily log files.

    Usage:
        audit = AuditLogger("/path/to/vault")

        # Log a watcher detection
        audit.log_detection(
            component="gmail_watcher",
            action_type="email_detected",
            target="sender@example.com",
            parameters={"subject": "Invoice #123"}
        )

        # Log an approval
        audit.log_approval(
            component="approval_watcher",
            action_type="email_send",
            target="recipient@example.com",
            approval_status="approved"
        )

        # Log an MCP execution
        audit.log_execution(
            component="gmail_mcp",
            action_type="email_send",
            target="recipient@example.com",
            result="success",
            external_id="msg-12345"
        )
    """

    def __init__(self, vault_path: str | Path):
        """Initialize audit logger.

        Args:
            vault_path: Path to Obsidian vault root
        """
        self.vault_path = Path(vault_path)
        self.logs_dir = self.vault_path / "Logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def _get_log_file(self) -> Path:
        """Get today's log file path."""
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return self.logs_dir / f"{date_str}.json"

    def _write_entry(self, entry: AuditLogEntry) -> None:
        """Write an entry to the log file."""
        log_file = self._get_log_file()

        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(entry.to_json() + "\n")
        except Exception as e:
            # Fall back to standard logging if file write fails
            logger.error(f"Failed to write audit log: {e}")
            logger.info(f"Audit entry: {entry.to_json()}")

    def log(
        self,
        component: str,
        action_type: str,
        **kwargs
    ) -> AuditLogEntry:
        """Write a generic audit log entry.

        Args:
            component: Source component name
            action_type: Type of action
            **kwargs: Additional fields (level, actor, target, parameters, etc.)

        Returns:
            The created AuditLogEntry
        """
        entry = AuditLogEntry(component, action_type, **kwargs)
        self._write_entry(entry)
        return entry

    def log_detection(
        self,
        component: str,
        action_type: str,
        target: str,
        parameters: dict[str, Any] | None = None,
        **kwargs
    ) -> AuditLogEntry:
        """Log a watcher detection event.

        Args:
            component: Watcher component (gmail_watcher, whatsapp_webhook, etc.)
            action_type: Detection type (email_detected, message_received, etc.)
            target: Source of the detection (sender email, phone number)
            parameters: Detection details (subject, preview, etc.)
        """
        return self.log(
            component=component,
            action_type=action_type,
            target=target,
            parameters=parameters,
            result="action_file_created",
            **kwargs
        )

    def log_approval(
        self,
        component: str,
        action_type: str,
        target: str,
        approval_status: str,
        parameters: dict[str, Any] | None = None,
        **kwargs
    ) -> AuditLogEntry:
        """Log an approval workflow event.

        Args:
            component: Component (approval_watcher)
            action_type: Action type being approved
            target: Target of the action
            approval_status: pending, approved, rejected, expired
            parameters: Action parameters
        """
        return self.log(
            component=component,
            action_type=action_type,
            target=target,
            approval_status=approval_status,
            parameters=parameters,
            result=f"approval_{approval_status}",
            **kwargs
        )

    def log_execution(
        self,
        component: str,
        action_type: str,
        target: str,
        result: str,
        parameters: dict[str, Any] | None = None,
        external_id: str | None = None,
        **kwargs
    ) -> AuditLogEntry:
        """Log an MCP execution event.

        Args:
            component: MCP component (gmail_mcp, linkedin_mcp)
            action_type: Action executed (email_send, create_post)
            target: Target of the action
            result: Execution result (success, failed)
            parameters: Action parameters
            external_id: External ID returned by API
        """
        extra = {}
        if external_id:
            extra["external_id"] = external_id

        return self.log(
            component=component,
            action_type=action_type,
            target=target,
            parameters=parameters,
            result=result,
            approval_status="approved",  # Only executed if approved
            **extra,
            **kwargs
        )

    def log_error(
        self,
        component: str,
        action_type: str,
        error: str | Exception,
        target: str | None = None,
        include_traceback: bool = True,
        **kwargs
    ) -> AuditLogEntry:
        """Log an error event.

        Args:
            component: Component where error occurred
            action_type: Action that failed
            error: Error message or exception
            target: Target if applicable
            include_traceback: Whether to include stack trace
        """
        error_msg = str(error)
        tb = None
        if include_traceback and isinstance(error, Exception):
            tb = traceback.format_exc()

        return self.log(
            component=component,
            action_type=action_type,
            target=target,
            error=error_msg,
            traceback_str=tb,
            level="ERROR",
            result="error",
            **kwargs
        )

    def log_security_event(
        self,
        component: str,
        action_type: str,
        target: str,
        reason: str,
        **kwargs
    ) -> AuditLogEntry:
        """Log a security-related event (tampering, invalid signature, etc.).

        Args:
            component: Component detecting the security issue
            action_type: Type of security event
            target: Affected target
            reason: Reason for security alert
        """
        return self.log(
            component=component,
            action_type=action_type,
            target=target,
            level="WARNING",
            result="security_alert",
            error=reason,
            **kwargs
        )

    # =========================================================================
    # Gold Tier Extensions (FR-031-036)
    # =========================================================================

    def get_log_size_bytes(self) -> int:
        """Get total size of all log files in bytes."""
        total_size = 0
        for log_file in self.logs_dir.glob("*.json"):
            total_size += log_file.stat().st_size
        for log_file in self.logs_dir.glob("*.json.gz"):
            total_size += log_file.stat().st_size
        return total_size

    def check_size_alert(
        self,
        max_size_bytes: int = 1024 * 1024 * 1024,  # 1GB default
        alert_threshold: float = 0.8
    ) -> dict[str, Any] | None:
        """Check if log directory size exceeds alert threshold.

        Args:
            max_size_bytes: Maximum allowed size in bytes (default 1GB)
            alert_threshold: Percentage threshold for alerting (default 0.8 = 80%)

        Returns:
            Alert info dict if threshold exceeded, None otherwise
        """
        current_size = self.get_log_size_bytes()
        threshold_bytes = int(max_size_bytes * alert_threshold)

        if current_size >= threshold_bytes:
            return {
                "alert_type": "log_size_warning",
                "current_size_bytes": current_size,
                "current_size_mb": round(current_size / (1024 * 1024), 2),
                "max_size_bytes": max_size_bytes,
                "max_size_mb": round(max_size_bytes / (1024 * 1024), 2),
                "threshold_percent": int(alert_threshold * 100),
                "usage_percent": round((current_size / max_size_bytes) * 100, 2),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        return None

    def compress_old_logs(self, days_threshold: int = 30) -> list[str]:
        """Compress log files older than threshold.

        Args:
            days_threshold: Compress logs older than this many days (default 30)

        Returns:
            List of compressed file paths
        """
        compressed = []
        cutoff_date = datetime.now(timezone.utc).date() - timedelta(days=days_threshold)

        for log_file in self.logs_dir.glob("*.json"):
            # Skip already compressed files
            if log_file.suffix == ".gz":
                continue

            # Parse date from filename (YYYY-MM-DD.json)
            try:
                file_date_str = log_file.stem
                file_date = datetime.strptime(file_date_str, "%Y-%m-%d").date()
            except ValueError:
                continue

            if file_date < cutoff_date:
                compressed_path = log_file.with_suffix(".json.gz")
                try:
                    with open(log_file, "rb") as f_in:
                        with gzip.open(compressed_path, "wb", compresslevel=6) as f_out:
                            shutil.copyfileobj(f_in, f_out)
                    # Remove original after successful compression
                    log_file.unlink()
                    compressed.append(str(compressed_path))
                    logger.info(f"Compressed log file: {log_file} -> {compressed_path}")
                except Exception as e:
                    logger.error(f"Failed to compress {log_file}: {e}")

        return compressed

    def cleanup_old_logs(self, retention_days: int = 90) -> list[str]:
        """Delete log files older than retention period.

        Args:
            retention_days: Delete logs older than this many days (default 90)

        Returns:
            List of deleted file paths
        """
        deleted = []
        cutoff_date = datetime.now(timezone.utc).date() - timedelta(days=retention_days)

        for pattern in ["*.json", "*.json.gz"]:
            for log_file in self.logs_dir.glob(pattern):
                # Parse date from filename
                try:
                    # Handle both .json and .json.gz
                    file_date_str = log_file.stem.replace(".json", "")
                    file_date = datetime.strptime(file_date_str, "%Y-%m-%d").date()
                except ValueError:
                    continue

                if file_date < cutoff_date:
                    try:
                        log_file.unlink()
                        deleted.append(str(log_file))
                        logger.info(f"Deleted old log file: {log_file}")
                    except Exception as e:
                        logger.error(f"Failed to delete {log_file}: {e}")

        return deleted

    def run_maintenance(
        self,
        retention_days: int = 90,
        compression_days: int = 30,
        max_size_bytes: int = 1024 * 1024 * 1024,
        alert_threshold: float = 0.8
    ) -> dict[str, Any]:
        """Run full maintenance cycle: compress, cleanup, check size.

        Args:
            retention_days: Delete logs older than this (default 90)
            compression_days: Compress logs older than this (default 30)
            max_size_bytes: Max log directory size (default 1GB)
            alert_threshold: Alert at this percentage of max (default 0.8)

        Returns:
            Maintenance report dict
        """
        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "compressed_files": [],
            "deleted_files": [],
            "size_alert": None,
            "final_size_bytes": 0,
            "final_size_mb": 0
        }

        # Step 1: Compress old logs
        report["compressed_files"] = self.compress_old_logs(compression_days)

        # Step 2: Delete very old logs
        report["deleted_files"] = self.cleanup_old_logs(retention_days)

        # Step 3: Check size
        report["size_alert"] = self.check_size_alert(max_size_bytes, alert_threshold)

        # Final size
        final_size = self.get_log_size_bytes()
        report["final_size_bytes"] = final_size
        report["final_size_mb"] = round(final_size / (1024 * 1024), 2)

        return report

    def query_logs(
        self,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        action_type: str | None = None,
        target: str | None = None,
        result: str | None = None,
        component: str | None = None,
        level: str | None = None,
        limit: int | None = None
    ) -> Generator[dict[str, Any], None, None]:
        """Query log entries with filters.

        Args:
            date_from: Start date (inclusive)
            date_to: End date (inclusive)
            action_type: Filter by action_type
            target: Filter by target (substring match)
            result: Filter by result
            component: Filter by component
            level: Filter by log level
            limit: Maximum entries to return

        Yields:
            Matching log entries as dicts
        """
        if date_from is None:
            date_from = datetime.now(timezone.utc) - timedelta(days=90)
        if date_to is None:
            date_to = datetime.now(timezone.utc)

        # Normalize to dates
        start_date = date_from.date() if isinstance(date_from, datetime) else date_from
        end_date = date_to.date() if isinstance(date_to, datetime) else date_to

        count = 0
        current_date = start_date

        while current_date <= end_date:
            date_str = current_date.strftime("%Y-%m-%d")

            # Try regular file first, then compressed
            log_file = self.logs_dir / f"{date_str}.json"
            compressed_file = self.logs_dir / f"{date_str}.json.gz"

            file_to_read = None
            is_compressed = False

            if log_file.exists():
                file_to_read = log_file
            elif compressed_file.exists():
                file_to_read = compressed_file
                is_compressed = True

            if file_to_read:
                try:
                    if is_compressed:
                        with gzip.open(file_to_read, "rt", encoding="utf-8") as f:
                            for entry in self._read_and_filter_entries(
                                f, action_type, target, result, component, level
                            ):
                                yield entry
                                count += 1
                                if limit and count >= limit:
                                    return
                    else:
                        with open(file_to_read, "r", encoding="utf-8") as f:
                            for entry in self._read_and_filter_entries(
                                f, action_type, target, result, component, level
                            ):
                                yield entry
                                count += 1
                                if limit and count >= limit:
                                    return
                except Exception as e:
                    logger.error(f"Error reading log file {file_to_read}: {e}")

            current_date += timedelta(days=1)

    def _read_and_filter_entries(
        self,
        file_handle,
        action_type: str | None,
        target: str | None,
        result: str | None,
        component: str | None,
        level: str | None
    ) -> Iterator[dict[str, Any]]:
        """Read and filter log entries from a file handle."""
        for line in file_handle:
            line = line.strip()
            if not line:
                continue

            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            # Apply filters
            if action_type and entry.get("action_type") != action_type:
                continue
            if target and target not in str(entry.get("target", "")):
                continue
            if result and entry.get("result") != result:
                continue
            if component and entry.get("component") != component:
                continue
            if level and entry.get("level") != level:
                continue

            yield entry

    def get_log_stats(
        self,
        date_from: datetime | None = None,
        date_to: datetime | None = None
    ) -> dict[str, Any]:
        """Get statistics about log entries.

        Args:
            date_from: Start date
            date_to: End date

        Returns:
            Statistics dict with counts by action_type, component, result, etc.
        """
        stats = {
            "total_entries": 0,
            "by_action_type": {},
            "by_component": {},
            "by_result": {},
            "by_level": {},
            "errors": 0,
            "period": {
                "from": date_from.isoformat() if date_from else None,
                "to": date_to.isoformat() if date_to else None
            }
        }

        for entry in self.query_logs(date_from=date_from, date_to=date_to):
            stats["total_entries"] += 1

            action_type = entry.get("action_type", "unknown")
            stats["by_action_type"][action_type] = stats["by_action_type"].get(action_type, 0) + 1

            component = entry.get("component", "unknown")
            stats["by_component"][component] = stats["by_component"].get(component, 0) + 1

            result = entry.get("result", "unknown")
            stats["by_result"][result] = stats["by_result"].get(result, 0) + 1

            level = entry.get("level", "INFO")
            stats["by_level"][level] = stats["by_level"].get(level, 0) + 1

            if entry.get("error"):
                stats["errors"] += 1

        return stats


# Module-level convenience instance
_default_logger: AuditLogger | None = None


def get_audit_logger(vault_path: str | Path | None = None) -> AuditLogger:
    """Get the default audit logger instance."""
    global _default_logger
    if _default_logger is None:
        if vault_path is None:
            vault_path = os.environ.get("VAULT_PATH", ".")
        _default_logger = AuditLogger(vault_path)
    return _default_logger


def log_detection(component: str, action_type: str, target: str, **kwargs) -> AuditLogEntry:
    """Convenience function to log a detection."""
    return get_audit_logger().log_detection(component, action_type, target, **kwargs)


def log_approval(component: str, action_type: str, target: str, approval_status: str, **kwargs) -> AuditLogEntry:
    """Convenience function to log an approval."""
    return get_audit_logger().log_approval(component, action_type, target, approval_status, **kwargs)


def log_execution(component: str, action_type: str, target: str, result: str, **kwargs) -> AuditLogEntry:
    """Convenience function to log an execution."""
    return get_audit_logger().log_execution(component, action_type, target, result, **kwargs)


def log_error(component: str, action_type: str, error: str | Exception, **kwargs) -> AuditLogEntry:
    """Convenience function to log an error."""
    return get_audit_logger().log_error(component, action_type, error, **kwargs)
