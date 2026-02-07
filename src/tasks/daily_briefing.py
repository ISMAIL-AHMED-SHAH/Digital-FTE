"""Daily Briefing Task for Silver Tier.

Generates a daily briefing document in the vault with:
- Pending tasks count
- Approval queue status
- Recent completions
- Key metrics

Implements FR-005 from spec.md and T046 from tasks.md.

Usage:
    # Run directly
    python -m src.tasks.daily_briefing

    # Run via scheduler
    python -m src.watchers.scheduler --task daily_briefing

    # Dry-run mode
    python -m src.tasks.daily_briefing --dry-run
"""

import argparse
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from src.common.audit_logger import get_audit_logger
from src.common.idempotency import get_idempotency_db
from src.common.vault import get_vault

logger = logging.getLogger(__name__)


class DailyBriefingGenerator:
    """Generates daily briefing documents for the AI Employee vault."""

    def __init__(self, dry_run: bool = False):
        """Initialize the briefing generator.

        Args:
            dry_run: If True, log output without creating files
        """
        self.dry_run = dry_run
        self.vault = get_vault()
        self.idempotency_db = get_idempotency_db()
        self._audit = get_audit_logger()

    def _get_approval_queue_status(self) -> dict[str, Any]:
        """Get current approval queue status.

        Returns:
            Dict with counts by status
        """
        status = {
            "pending": 0,
            "approved": 0,
            "rejected": 0,
            "expired": 0
        }

        # Count files in each folder
        for folder_key, status_key in [
            ("pending_approval", "pending"),
            ("approved", "approved"),
            ("rejected", "rejected"),
            ("expired", "expired")
        ]:
            try:
                files = self.vault.list_files(folder_key, "*.md")
                status[status_key] = len(files)
            except Exception as e:
                logger.warning(f"Failed to count {folder_key} files: {e}")

        return status

    def _get_needs_action_status(self) -> dict[str, Any]:
        """Get status of items needing action.

        Returns:
            Dict with counts and recent items
        """
        status = {
            "total": 0,
            "by_type": {},
            "recent": []
        }

        try:
            files = self.vault.list_files("needs_action", "*.md")
            status["total"] = len(files)

            # Count by type and get recent items
            for file_path in files[-10:]:  # Last 10
                try:
                    content = file_path.read_text(encoding="utf-8")

                    # Extract type from frontmatter
                    if "type:" in content:
                        for line in content.split("\n"):
                            if line.strip().startswith("type:"):
                                action_type = line.split(":", 1)[1].strip().strip('"')
                                status["by_type"][action_type] = status["by_type"].get(action_type, 0) + 1
                                break

                    status["recent"].append({
                        "file": file_path.name,
                        "modified": datetime.fromtimestamp(
                            file_path.stat().st_mtime,
                            tz=timezone.utc
                        ).isoformat()
                    })
                except Exception as e:
                    logger.warning(f"Failed to read {file_path}: {e}")

        except Exception as e:
            logger.warning(f"Failed to list needs_action files: {e}")

        return status

    def _get_recent_completions(self, days: int = 1) -> list[dict[str, Any]]:
        """Get recently completed actions.

        Args:
            days: Number of days to look back

        Returns:
            List of completed actions
        """
        completions = []

        try:
            files = self.vault.list_files("done", "*.md")

            cutoff = datetime.now(timezone.utc) - timedelta(days=days)

            for file_path in files:
                try:
                    modified = datetime.fromtimestamp(
                        file_path.stat().st_mtime,
                        tz=timezone.utc
                    )

                    if modified >= cutoff:
                        completions.append({
                            "file": file_path.name,
                            "completed_at": modified.isoformat()
                        })
                except Exception as e:
                    logger.warning(f"Failed to check {file_path}: {e}")

        except Exception as e:
            logger.warning(f"Failed to list done files: {e}")

        return completions

    def _get_idempotency_metrics(self) -> dict[str, Any]:
        """Get metrics from idempotency database.

        Returns:
            Dict with processed counts and rate limits
        """
        metrics = {
            "processed_messages": {},
            "sent_actions": {},
            "rate_limits": {}
        }

        try:
            stats = self.idempotency_db.get_stats()
            metrics["processed_messages"] = stats.get("messages_by_source", {})
            metrics["sent_actions"] = stats.get("actions_by_type", {})

            # Get today's rate limit usage
            for action_type in ["email", "linkedin_post"]:
                count = self.idempotency_db.get_rate_limit_count(action_type)
                if count > 0:
                    metrics["rate_limits"][action_type] = count

        except Exception as e:
            logger.warning(f"Failed to get idempotency metrics: {e}")

        return metrics

    def _get_recent_logs(self, hours: int = 24) -> list[dict[str, Any]]:
        """Get recent log entries.

        Args:
            hours: Number of hours to look back

        Returns:
            List of log entries (errors and warnings)
        """
        logs = []

        try:
            # Check today's and yesterday's log files
            today = datetime.now(timezone.utc)
            yesterday = today - timedelta(days=1)

            for date in [today, yesterday]:
                log_file = self.vault.get_folder("logs") / f"{date.strftime('%Y-%m-%d')}.json"

                if log_file.exists():
                    with open(log_file, "r", encoding="utf-8") as f:
                        for line in f:
                            try:
                                entry = json.loads(line.strip())
                                if entry.get("level") in ("ERROR", "WARNING"):
                                    logs.append(entry)
                            except json.JSONDecodeError:
                                continue

        except Exception as e:
            logger.warning(f"Failed to read logs: {e}")

        # Return most recent 10
        return logs[-10:]

    def generate_briefing(self) -> str:
        """Generate the daily briefing document content.

        Returns:
            Markdown content for the briefing
        """
        now = datetime.now(timezone.utc)
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S UTC")

        # Gather data
        approval_status = self._get_approval_queue_status()
        needs_action = self._get_needs_action_status()
        completions = self._get_recent_completions()
        metrics = self._get_idempotency_metrics()
        recent_logs = self._get_recent_logs()

        # Build briefing content
        content = f"""---
type: briefing
date: {date_str}
generated_at: {now.isoformat()}
---

# Daily Briefing - {date_str}

*Generated at {time_str}*

---

## Summary

| Metric | Value |
|--------|-------|
| Pending Actions | {needs_action['total']} |
| Pending Approvals | {approval_status['pending']} |
| Completed Today | {len(completions)} |
| Approved | {approval_status['approved']} |
| Rejected | {approval_status['rejected']} |
| Expired | {approval_status['expired']} |

---

## Approval Queue

"""

        if approval_status['pending'] > 0:
            content += f"**{approval_status['pending']} item(s) awaiting approval**\n\n"
            content += "Review pending items in `/Pending_Approval` folder.\n\n"
        else:
            content += "No items pending approval.\n\n"

        content += """---

## Needs Action

"""

        if needs_action['total'] > 0:
            content += f"**{needs_action['total']} item(s) requiring attention**\n\n"

            if needs_action['by_type']:
                content += "### By Type\n\n"
                for action_type, count in needs_action['by_type'].items():
                    content += f"- {action_type}: {count}\n"
                content += "\n"

            if needs_action['recent']:
                content += "### Recent Items\n\n"
                for item in needs_action['recent'][-5:]:
                    content += f"- `{item['file']}`\n"
                content += "\n"
        else:
            content += "No items needing action.\n\n"

        content += """---

## Recent Completions

"""

        if completions:
            content += f"**{len(completions)} item(s) completed in the last 24 hours**\n\n"
            for item in completions[-10:]:
                content += f"- `{item['file']}` at {item['completed_at']}\n"
            content += "\n"
        else:
            content += "No completions in the last 24 hours.\n\n"

        content += """---

## Metrics

### Processed Messages

"""

        if metrics['processed_messages']:
            for source, count in metrics['processed_messages'].items():
                content += f"- {source}: {count}\n"
        else:
            content += "No messages processed.\n"

        content += "\n### Rate Limit Usage (Today)\n\n"

        if metrics['rate_limits']:
            for action_type, count in metrics['rate_limits'].items():
                limit = 50 if action_type == "email" else 10
                content += f"- {action_type}: {count}/{limit}\n"
        else:
            content += "No rate-limited actions today.\n"

        content += """

---

## Recent Errors & Warnings

"""

        if recent_logs:
            content += f"**{len(recent_logs)} issue(s) in the last 24 hours**\n\n"
            for log in recent_logs[-5:]:
                content += f"- [{log.get('level', 'INFO')}] {log.get('component', 'unknown')}: {log.get('error', log.get('action_type', 'N/A'))}\n"
        else:
            content += "No errors or warnings.\n"

        content += """

---

*This briefing was automatically generated by the AI Employee scheduler.*
"""

        return content

    def save_briefing(self, content: str) -> Path | None:
        """Save the briefing to the vault.

        Args:
            content: Briefing markdown content

        Returns:
            Path to the saved file, or None if dry-run
        """
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        filename = f"{date_str}.md"

        if self.dry_run:
            logger.info(f"[DRY-RUN] Would save briefing to Briefings/{filename}")
            logger.info(f"[DRY-RUN] Content preview:\n{content[:500]}...")
            return None

        try:
            file_path = self.vault.write_file(
                folder_key="briefings",
                filename=filename,
                content=content,
                overwrite=True  # Allow updating today's briefing
            )

            logger.info(f"Saved daily briefing: {file_path}")

            # Log to audit
            self._audit.log(
                component="daily_briefing",
                action_type="briefing_generated",
                target=str(file_path),
                result="success"
            )

            return file_path

        except Exception as e:
            logger.error(f"Failed to save briefing: {e}")
            self._audit.log_error(
                component="daily_briefing",
                action_type="briefing_generation",
                error=e
            )
            raise


def run(dry_run: bool = False, **kwargs) -> dict[str, Any]:
    """Main entry point for the daily briefing task.

    This function is called by the scheduler.

    Args:
        dry_run: If True, don't create files
        **kwargs: Additional parameters (ignored)

    Returns:
        Result dictionary with status and file path
    """
    logger.info("Generating daily briefing...")

    generator = DailyBriefingGenerator(dry_run=dry_run)

    try:
        content = generator.generate_briefing()
        file_path = generator.save_briefing(content)

        return {
            "status": "success",
            "file": str(file_path) if file_path else None,
            "dry_run": dry_run
        }

    except Exception as e:
        logger.exception(f"Daily briefing failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "dry_run": dry_run
        }


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate AI Employee daily briefing"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate without creating files"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output to specific file instead of vault"
    )
    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Generate briefing
    generator = DailyBriefingGenerator(dry_run=args.dry_run)
    content = generator.generate_briefing()

    if args.output:
        # Output to specific file
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")
        print(f"Briefing saved to: {output_path}")
    elif args.dry_run:
        # Print to stdout in dry-run mode
        print(content)
    else:
        # Save to vault
        file_path = generator.save_briefing(content)
        print(f"Briefing saved to: {file_path}")


if __name__ == "__main__":
    main()
