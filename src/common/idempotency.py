"""Idempotency Database Module for Silver Tier.

Provides SQLite-based tracking of processed messages and sent actions
to prevent duplicate processing during retries or watcher restarts.

Implements FR-014, FR-014a from spec.
"""

import logging
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Default retention period for idempotency records
DEFAULT_RETENTION_DAYS = 7


class IdempotencyError(Exception):
    """Base exception for idempotency operations."""
    pass


class IdempotencyDatabase:
    """SQLite-based idempotency tracking database.

    Thread-safe implementation for tracking:
    - Processed messages (to prevent duplicate watcher detections)
    - Sent actions (to prevent duplicate MCP executions)
    - Rate limits (to enforce daily quotas)

    Usage:
        db = IdempotencyDatabase("data/idempotency.db")

        # Check if message already processed
        if not db.is_processed("msg-123", "gmail"):
            process_message(msg)
            db.mark_processed("msg-123", "gmail")

        # Check before sending action
        if not db.is_action_sent("email-hash-123", "email_send"):
            send_email(...)
            db.mark_action_sent("email-hash-123", "email_send", "user@example.com", "success")
    """

    def __init__(
        self,
        db_path: str | Path,
        retention_days: int = DEFAULT_RETENTION_DAYS
    ):
        """Initialize idempotency database.

        Args:
            db_path: Path to SQLite database file
            retention_days: Days to retain idempotency records before cleanup
        """
        self.db_path = Path(db_path)
        self.retention_days = retention_days
        self._local = threading.local()

        # Ensure parent directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize schema if needed
        self._init_schema()

    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local, "connection") or self._local.connection is None:
            self._local.connection = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
                timeout=30.0
            )
            self._local.connection.row_factory = sqlite3.Row
            # Enable WAL mode for better concurrent access
            self._local.connection.execute("PRAGMA journal_mode=WAL")
        return self._local.connection

    @contextmanager
    def _cursor(self):
        """Context manager for database cursor with auto-commit."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    def _init_schema(self) -> None:
        """Initialize database schema if tables don't exist."""
        schema_sql = """
        CREATE TABLE IF NOT EXISTS processed_messages (
            message_id TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            processed_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            sender TEXT,
            subject TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_processed_expires_at
        ON processed_messages(expires_at);

        CREATE TABLE IF NOT EXISTS sent_actions (
            action_id TEXT PRIMARY KEY,
            action_type TEXT NOT NULL,
            recipient TEXT,
            sent_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            result_status TEXT NOT NULL,
            error_message TEXT,
            external_id TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_sent_expires_at
        ON sent_actions(expires_at);

        CREATE TABLE IF NOT EXISTS rate_limits (
            action_type TEXT NOT NULL,
            limit_date TEXT NOT NULL,
            current_count INTEGER NOT NULL DEFAULT 0,
            max_count INTEGER NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (action_type, limit_date)
        );
        """
        with self._cursor() as cursor:
            cursor.executescript(schema_sql)
        logger.debug("Idempotency database schema initialized")

    def _now_iso(self) -> str:
        """Get current UTC time in ISO format."""
        return datetime.now(timezone.utc).isoformat()

    def _expires_iso(self, days: int | None = None) -> str:
        """Get expiration time in ISO format."""
        days = days or self.retention_days
        expires = datetime.now(timezone.utc) + timedelta(days=days)
        return expires.isoformat()

    # =========================================================================
    # Processed Messages API
    # =========================================================================

    def is_processed(self, message_id: str, source: str) -> bool:
        """Check if a message has already been processed.

        Args:
            message_id: Unique message identifier (Message-ID header or content hash)
            source: Source watcher (gmail, whatsapp, file_drop)

        Returns:
            True if message was already processed, False otherwise
        """
        with self._cursor() as cursor:
            cursor.execute(
                """
                SELECT 1 FROM processed_messages
                WHERE message_id = ? AND source = ? AND expires_at > ?
                """,
                (message_id, source, self._now_iso())
            )
            return cursor.fetchone() is not None

    def mark_processed(
        self,
        message_id: str,
        source: str,
        sender: str | None = None,
        subject: str | None = None
    ) -> None:
        """Mark a message as processed.

        Args:
            message_id: Unique message identifier
            source: Source watcher
            sender: Optional sender information for debugging
            subject: Optional subject/preview for debugging
        """
        with self._cursor() as cursor:
            cursor.execute(
                """
                INSERT OR REPLACE INTO processed_messages
                (message_id, source, processed_at, expires_at, sender, subject)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (message_id, source, self._now_iso(), self._expires_iso(), sender, subject)
            )
        logger.debug(f"Marked message {message_id} from {source} as processed")

    def get_processed_count(self, source: str | None = None) -> int:
        """Get count of processed messages, optionally filtered by source."""
        with self._cursor() as cursor:
            if source:
                cursor.execute(
                    "SELECT COUNT(*) FROM processed_messages WHERE source = ? AND expires_at > ?",
                    (source, self._now_iso())
                )
            else:
                cursor.execute(
                    "SELECT COUNT(*) FROM processed_messages WHERE expires_at > ?",
                    (self._now_iso(),)
                )
            return cursor.fetchone()[0]

    # =========================================================================
    # Sent Actions API
    # =========================================================================

    def is_action_sent(self, action_id: str, action_type: str) -> bool:
        """Check if an action has already been sent successfully.

        Args:
            action_id: Unique action identifier (content hash or generated ID)
            action_type: Action type (email_send, linkedin_post, etc.)

        Returns:
            True if action was already sent successfully, False otherwise
        """
        with self._cursor() as cursor:
            cursor.execute(
                """
                SELECT 1 FROM sent_actions
                WHERE action_id = ? AND action_type = ?
                AND result_status = 'success' AND expires_at > ?
                """,
                (action_id, action_type, self._now_iso())
            )
            return cursor.fetchone() is not None

    def mark_action_sent(
        self,
        action_id: str,
        action_type: str,
        recipient: str | None,
        result_status: str,
        error_message: str | None = None,
        external_id: str | None = None
    ) -> None:
        """Record that an action was attempted.

        Args:
            action_id: Unique action identifier
            action_type: Action type
            recipient: Recipient (email address, visibility, etc.)
            result_status: 'success' or 'failed'
            error_message: Error message if failed
            external_id: External ID returned by API (e.g., Gmail Message-ID)
        """
        with self._cursor() as cursor:
            cursor.execute(
                """
                INSERT OR REPLACE INTO sent_actions
                (action_id, action_type, recipient, sent_at, expires_at, result_status, error_message, external_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (action_id, action_type, recipient, self._now_iso(), self._expires_iso(),
                 result_status, error_message, external_id)
            )
        logger.debug(f"Recorded action {action_id} ({action_type}): {result_status}")

    def get_action_result(self, action_id: str, action_type: str) -> dict[str, Any] | None:
        """Get the result of a previously sent action."""
        with self._cursor() as cursor:
            cursor.execute(
                """
                SELECT * FROM sent_actions
                WHERE action_id = ? AND action_type = ? AND expires_at > ?
                """,
                (action_id, action_type, self._now_iso())
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    # =========================================================================
    # Rate Limiting API
    # =========================================================================

    def check_rate_limit(self, action_type: str, max_count: int) -> bool:
        """Check if rate limit allows another action.

        Args:
            action_type: Action type to check
            max_count: Maximum allowed actions per day

        Returns:
            True if under limit, False if limit reached
        """
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        with self._cursor() as cursor:
            cursor.execute(
                """
                SELECT current_count FROM rate_limits
                WHERE action_type = ? AND limit_date = ?
                """,
                (action_type, today)
            )
            row = cursor.fetchone()
            current = row[0] if row else 0
            return current < max_count

    def increment_rate_limit(self, action_type: str, max_count: int) -> int:
        """Increment rate limit counter and return new count.

        Args:
            action_type: Action type
            max_count: Maximum allowed (stored for reference)

        Returns:
            New count after increment
        """
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        with self._cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO rate_limits (action_type, limit_date, current_count, max_count, updated_at)
                VALUES (?, ?, 1, ?, ?)
                ON CONFLICT(action_type, limit_date) DO UPDATE SET
                    current_count = current_count + 1,
                    updated_at = excluded.updated_at
                """,
                (action_type, today, max_count, self._now_iso())
            )
            cursor.execute(
                "SELECT current_count FROM rate_limits WHERE action_type = ? AND limit_date = ?",
                (action_type, today)
            )
            return cursor.fetchone()[0]

    def get_rate_limit_count(self, action_type: str) -> int:
        """Get current rate limit count for today."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        with self._cursor() as cursor:
            cursor.execute(
                "SELECT current_count FROM rate_limits WHERE action_type = ? AND limit_date = ?",
                (action_type, today)
            )
            row = cursor.fetchone()
            return row[0] if row else 0

    # =========================================================================
    # Cleanup API
    # =========================================================================

    def cleanup_expired(self) -> dict[str, int]:
        """Remove expired records from all tables.

        Returns:
            Dictionary with count of deleted records per table
        """
        now = self._now_iso()
        week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
        deleted = {}

        with self._cursor() as cursor:
            cursor.execute("DELETE FROM processed_messages WHERE expires_at < ?", (now,))
            deleted["processed_messages"] = cursor.rowcount

            cursor.execute("DELETE FROM sent_actions WHERE expires_at < ?", (now,))
            deleted["sent_actions"] = cursor.rowcount

            cursor.execute("DELETE FROM rate_limits WHERE limit_date < ?", (week_ago,))
            deleted["rate_limits"] = cursor.rowcount

        total = sum(deleted.values())
        if total > 0:
            logger.info(f"Cleaned up {total} expired idempotency records: {deleted}")

        return deleted

    def vacuum(self) -> None:
        """Compact the database file after cleanup."""
        conn = self._get_connection()
        conn.execute("VACUUM")
        logger.debug("Database vacuumed")

    def get_stats(self) -> dict[str, Any]:
        """Get database statistics."""
        with self._cursor() as cursor:
            stats = {}

            cursor.execute("SELECT COUNT(*) FROM processed_messages WHERE expires_at > ?", (self._now_iso(),))
            stats["active_processed_messages"] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM sent_actions WHERE expires_at > ?", (self._now_iso(),))
            stats["active_sent_actions"] = cursor.fetchone()[0]

            cursor.execute("SELECT source, COUNT(*) FROM processed_messages GROUP BY source")
            stats["messages_by_source"] = {row[0]: row[1] for row in cursor.fetchall()}

            cursor.execute("SELECT action_type, COUNT(*) FROM sent_actions GROUP BY action_type")
            stats["actions_by_type"] = {row[0]: row[1] for row in cursor.fetchall()}

            return stats

    def close(self) -> None:
        """Close database connection."""
        if hasattr(self._local, "connection") and self._local.connection:
            self._local.connection.close()
            self._local.connection = None


# Module-level convenience instance
_default_db: IdempotencyDatabase | None = None


def get_idempotency_db(db_path: str | Path | None = None) -> IdempotencyDatabase:
    """Get the default idempotency database instance."""
    global _default_db
    if _default_db is None:
        path = db_path or Path("data/idempotency.db")
        _default_db = IdempotencyDatabase(path)
    return _default_db


def is_processed(message_id: str, source: str) -> bool:
    """Convenience function to check if message is processed."""
    return get_idempotency_db().is_processed(message_id, source)


def mark_processed(message_id: str, source: str, **kwargs) -> None:
    """Convenience function to mark message as processed."""
    get_idempotency_db().mark_processed(message_id, source, **kwargs)


def is_action_sent(action_id: str, action_type: str) -> bool:
    """Convenience function to check if action was sent."""
    return get_idempotency_db().is_action_sent(action_id, action_type)


def mark_action_sent(action_id: str, action_type: str, recipient: str | None, result_status: str, **kwargs) -> None:
    """Convenience function to mark action as sent."""
    get_idempotency_db().mark_action_sent(action_id, action_type, recipient, result_status, **kwargs)
