"""Gmail Watcher for Silver Tier.

Polls Gmail API for unread important emails and creates action files
in /Needs_Action for processing by Claude.

Features:
- 2-minute poll interval (configurable)
- Keyword filtering (urgent, invoice, important, etc.)
- Idempotency via message_id tracking
- OAuth token auto-refresh with retry logic
- Memory monitoring and dry-run support

Implements FR-001 from spec.
"""

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.common.alerts import alert_oauth_failure
from src.common.audit_logger import get_audit_logger
from src.common.idempotency import get_idempotency_db
from src.common.vault import get_vault
from src.watchers.base_watcher import PollingWatcher, WatcherPriority, WatcherStatus
from src.watchers.config import get_config
from src.watchers.gmail_client import GmailClient, GmailAuthError, GmailAPIError

logger = logging.getLogger(__name__)


class GmailWatcher(PollingWatcher):
    """Gmail watcher that polls for important emails.

    Monitors Gmail for unread emails matching configured keywords
    and creates action files in /Needs_Action for processing.

    Usage:
        watcher = GmailWatcher(config)
        await watcher.run()

    Or run standalone:
        python -m src.watchers.gmail_watcher --vault /path/to/vault
    """

    def __init__(
        self,
        config=None,
        vault_path: str | Path | None = None,
        dry_run: bool = False
    ):
        """Initialize Gmail watcher.

        Args:
            config: Watcher configuration (default: from config file)
            vault_path: Override vault path
            dry_run: If True, don't create action files
        """
        config = config or get_config()

        super().__init__(
            name="gmail_watcher",
            priority=WatcherPriority.HIGH,
            memory_limit_mb=config.gmail.memory_limit_mb,
            poll_interval_seconds=config.gmail.poll_interval_seconds,
            config=config,
            dry_run=dry_run
        )

        self.vault = get_vault(vault_path)
        self.gmail = GmailClient()
        self.idempotency = get_idempotency_db()

        # Gmail-specific config
        self.keywords = config.gmail.keywords
        self.labels = config.gmail.labels
        self.max_emails_per_poll = config.gmail.max_emails_per_poll

        # State
        self._auth_failures = 0
        self._max_auth_failures = 3
        self._authenticated = False

        # Audit logger
        self._audit = get_audit_logger()

    async def _authenticate(self) -> bool:
        """Authenticate with Gmail API.

        Returns:
            True if authentication succeeded
        """
        try:
            # Run in thread to avoid blocking
            await asyncio.to_thread(self.gmail.authenticate)
            self._authenticated = True
            self._auth_failures = 0
            logger.info("Gmail authentication successful")
            return True

        except GmailAuthError as e:
            self._auth_failures += 1
            logger.error(f"Gmail authentication failed ({self._auth_failures}/{self._max_auth_failures}): {e}")

            if self._auth_failures >= self._max_auth_failures:
                logger.error("Max authentication failures reached, pausing watcher")
                await alert_oauth_failure(
                    service="gmail",
                    error=str(e),
                    retry_count=self._auth_failures,
                    vault=self.vault
                )
                self.pause()

            return False

    async def _pre_poll(self) -> bool:
        """Pre-poll checks including authentication."""
        if not await super()._pre_poll():
            return False

        # Ensure authenticated
        if not self._authenticated:
            if not await self._authenticate():
                return False

        return True

    async def _poll(self) -> None:
        """Execute one poll cycle - fetch and process emails."""
        try:
            # Fetch emails with keywords
            emails = await asyncio.to_thread(
                self.gmail.list_unread_with_keywords,
                self.keywords,
                self.max_emails_per_poll
            )

            if not emails:
                logger.debug("No new emails matching keywords")
                return

            logger.info(f"Found {len(emails)} emails to process")

            # Process each email
            for email_meta in emails:
                await self.process_event(email_meta)

        except GmailAuthError as e:
            # Token may have expired
            logger.warning(f"Auth error during poll: {e}")
            self._authenticated = False
            self._auth_failures += 1

            if self._auth_failures >= self._max_auth_failures:
                await alert_oauth_failure(
                    service="gmail",
                    error=str(e),
                    retry_count=self._auth_failures,
                    vault=self.vault
                )
                self.pause()

        except GmailAPIError as e:
            logger.error(f"Gmail API error: {e}")
            self._errors_count += 1

    async def process_event(self, event: dict[str, Any]) -> None:
        """Process a detected email event.

        Args:
            event: Email metadata from list_unread_with_keywords
        """
        message_id = event.get("id")
        if not message_id:
            return

        # Check idempotency
        if self.idempotency.is_processed(message_id, "gmail"):
            logger.debug(f"Email {message_id} already processed, skipping")
            return

        try:
            # Get full message content
            content = await asyncio.to_thread(
                self.gmail.get_message_content,
                message_id
            )

            sender = content.get("from_email", content.get("from", "unknown"))
            subject = content.get("subject", "(no subject)")

            logger.info(f"Processing email from {sender}: {subject}")

            # Create action file
            if self.dry_run:
                logger.info(f"[DRY-RUN] Would create action file for email from {sender}")
            else:
                await self._create_action_file(content)

            # Mark as processed
            self.idempotency.mark_processed(
                message_id=message_id,
                source="gmail",
                sender=sender,
                subject=subject[:100]
            )

            self._events_processed += 1

            # Log detection
            self._audit.log_detection(
                component=self.name,
                action_type="email_detected",
                target=sender,
                parameters={
                    "subject": subject,
                    "message_id": message_id,
                    "has_attachments": "ATTACHMENT" in content.get("labels", [])
                }
            )

        except Exception as e:
            logger.exception(f"Failed to process email {message_id}: {e}")
            self._errors_count += 1
            self._audit.log_error(
                component=self.name,
                action_type="email_processing",
                error=e,
                target=message_id
            )

    async def _create_action_file(self, email_content: dict[str, Any]) -> Path:
        """Create an action file for the email in /Needs_Action.

        Args:
            email_content: Full email content from get_message_content

        Returns:
            Path to created action file
        """
        # Generate filename
        timestamp = datetime.now(timezone.utc)
        date_str = timestamp.strftime("%Y-%m-%d_%H%M%S")
        sender = email_content.get("from_email", "unknown").split("@")[0][:20]
        subject_slug = self._slugify(email_content.get("subject", "no-subject")[:30])
        filename = f"{date_str}_email_{sender}_{subject_slug}.md"

        # Determine priority based on keywords
        priority = self._determine_priority(email_content)

        # Build YAML frontmatter
        frontmatter = f"""---
type: email
source: {email_content.get('from', 'unknown')}
subject: "{email_content.get('subject', '').replace('"', '\\"')}"
priority: {priority}
timestamp: {timestamp.isoformat()}
status: pending
message_id: {email_content.get('message_id', email_content.get('id', 'unknown'))}
thread_id: {email_content.get('thread_id', '')}
labels: {email_content.get('labels', [])}
---
"""

        # Build markdown body
        body = f"""## Email from {email_content.get('from', 'Unknown')}

**Subject**: {email_content.get('subject', '(no subject)')}
**Date**: {email_content.get('date', 'Unknown')}
**To**: {email_content.get('to', '')}
{f"**CC**: {email_content.get('cc')}" if email_content.get('cc') else ""}

---

### Message Content

{email_content.get('body', email_content.get('snippet', '(no content)'))}

---

### Suggested Actions

- [ ] Review email content
- [ ] Draft response if needed
- [ ] Mark as done when processed

*Action file created by Gmail Watcher at {timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")}*
"""

        content = frontmatter + "\n" + body

        # Write to vault
        file_path = self.vault.write_file("needs_action", filename, content)
        logger.info(f"Created action file: {file_path}")

        return file_path

    def _slugify(self, text: str) -> str:
        """Convert text to filename-safe slug."""
        import re
        text = text.lower()
        text = re.sub(r'[^\w\s-]', '', text)
        text = re.sub(r'[\s_-]+', '-', text)
        return text.strip('-')[:30]

    def _determine_priority(self, email_content: dict[str, Any]) -> str:
        """Determine email priority based on content and labels.

        Args:
            email_content: Email content dict

        Returns:
            Priority string: high, normal, or low
        """
        subject = email_content.get("subject", "").lower()
        body = email_content.get("body", "").lower()
        labels = email_content.get("labels", [])
        text = subject + " " + body

        # High priority indicators
        high_priority_keywords = ["urgent", "asap", "immediately", "critical", "emergency"]
        if any(kw in text for kw in high_priority_keywords):
            return "high"

        if "IMPORTANT" in labels:
            return "high"

        # Low priority indicators
        low_priority_keywords = ["newsletter", "unsubscribe", "marketing", "promotion"]
        if any(kw in text for kw in low_priority_keywords):
            return "low"

        return "normal"

    def get_stats(self) -> dict[str, Any]:
        """Get watcher statistics."""
        stats = super().get_stats()
        stats.update({
            "authenticated": self._authenticated,
            "auth_failures": self._auth_failures,
            "keywords": self.keywords
        })
        return stats


async def main():
    """Run the Gmail watcher standalone."""
    import argparse

    parser = argparse.ArgumentParser(description="Gmail Watcher")
    parser.add_argument("--vault", help="Path to Obsidian vault")
    parser.add_argument("--dry-run", action="store_true", help="Don't create action files")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    watcher = GmailWatcher(vault_path=args.vault, dry_run=args.dry_run)
    await watcher.run()


if __name__ == "__main__":
    asyncio.run(main())
