"""Approval Watcher for Silver Tier.

Monitors /Approved and /Rejected folders for approval decisions and
processes them accordingly:
- Approved: Validate integrity hash, execute action via MCP
- Rejected: Log rejection, do not execute
- Expired: Move to /Expired folder automatically

Implements FR-008, FR-009, FR-010, FR-020 from spec.
"""

import asyncio
import logging
import re
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

import yaml
from watchdog.events import FileCreatedEvent, FileMovedEvent, FileSystemEventHandler
from watchdog.observers import Observer

from src.common.audit_logger import get_audit_logger
from src.common.integrity import validate_hash, HashMismatchError
from src.common.vault import get_vault, Vault
from src.watchers.base_watcher import BaseWatcher, WatcherPriority, WatcherStatus
from src.watchers.config import get_config
from src.watchers.models import ApprovalRequest, ApprovalStatus, ApprovalResult

logger = logging.getLogger(__name__)


class ApprovalFileHandler(FileSystemEventHandler):
    """Watchdog handler for approval folder events."""

    def __init__(
        self,
        watcher: "ApprovalWatcher",
        folder_type: str  # "approved" or "rejected"
    ):
        self.watcher = watcher
        self.folder_type = folder_type

    def on_created(self, event):
        """Handle new file creation."""
        if event.is_directory:
            return
        if not event.src_path.endswith(".md"):
            return

        logger.debug(f"File created in {self.folder_type}: {event.src_path}")
        asyncio.run_coroutine_threadsafe(
            self.watcher._handle_file(Path(event.src_path), self.folder_type),
            self.watcher._loop
        )

    def on_moved(self, event):
        """Handle file moved into folder."""
        if event.is_directory:
            return
        if not event.dest_path.endswith(".md"):
            return

        logger.debug(f"File moved to {self.folder_type}: {event.dest_path}")
        asyncio.run_coroutine_threadsafe(
            self.watcher._handle_file(Path(event.dest_path), self.folder_type),
            self.watcher._loop
        )


class ApprovalWatcher(BaseWatcher):
    """Watcher for approval workflow folders.

    Monitors:
    - /Approved: Files moved here trigger action execution (with integrity check)
    - /Rejected: Files moved here trigger rejection logging

    Also periodically checks /Pending_Approval for expired requests.

    Usage:
        watcher = ApprovalWatcher(config, action_executor=my_executor)
        await watcher.run()
    """

    def __init__(
        self,
        config=None,
        action_executor: Callable[[ApprovalRequest], asyncio.Future] | None = None,
        vault_path: str | Path | None = None,
        dry_run: bool = False
    ):
        """Initialize approval watcher.

        Args:
            config: Watcher configuration (default: from config file)
            action_executor: Async function to execute approved actions
            vault_path: Override vault path
            dry_run: If True, don't execute actions
        """
        config = config or get_config()

        super().__init__(
            name="approval_watcher",
            priority=WatcherPriority.HIGH,
            memory_limit_mb=config.approval.memory_limit_mb,
            poll_interval_seconds=config.approval.expiration_check_interval_seconds,
            config=config,
            dry_run=dry_run
        )

        self.vault = get_vault(vault_path)
        self.action_executor = action_executor
        self.expiration_check_interval = config.approval.expiration_check_interval_seconds

        # Watchdog observers
        self._approved_observer: Observer | None = None
        self._rejected_observer: Observer | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

        # Statistics
        self._approved_count = 0
        self._rejected_count = 0
        self._expired_count = 0
        self._tampered_count = 0

        # Audit logger
        self._audit = get_audit_logger()

    def _parse_approval_file(self, file_path: Path) -> ApprovalRequest | None:
        """Parse an approval file and extract the ApprovalRequest.

        Args:
            file_path: Path to the approval file

        Returns:
            ApprovalRequest or None if parsing fails
        """
        try:
            content = file_path.read_text(encoding="utf-8")

            # Extract YAML frontmatter
            match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
            if not match:
                logger.warning(f"No YAML frontmatter in {file_path}")
                return None

            yaml_content = match.group(1)
            return ApprovalRequest.from_yaml_frontmatter(yaml_content)

        except Exception as e:
            logger.error(f"Failed to parse approval file {file_path}: {e}")
            return None

    async def _handle_approved(self, file_path: Path, request: ApprovalRequest) -> ApprovalResult:
        """Handle an approved action file.

        1. Validate integrity hash
        2. If valid, execute action via MCP
        3. Move to /Done or log error

        Args:
            file_path: Path to the approved file
            request: Parsed ApprovalRequest

        Returns:
            ApprovalResult with execution details
        """
        action_type = request.action_type if isinstance(request.action_type, str) else request.action_type.value
        target = request.parameters.get("to") or request.parameters.get("visibility") or "unknown"

        # Step 1: Validate integrity hash
        logger.info(f"Validating integrity for {file_path.name}")

        is_valid = validate_hash(
            action_type=action_type,
            parameters=request.parameters,
            created_timestamp=request.created_timestamp.isoformat(),
            expected_hash=request.integrity_hash
        )

        if not is_valid:
            # TAMPERED - move to rejected with special suffix
            logger.warning(f"INTEGRITY VIOLATION: {file_path.name} has been tampered with!")
            self._tampered_count += 1

            # Move to rejected with _TAMPERED suffix
            tampered_name = f"_TAMPERED_{file_path.name}"
            rejected_path = self.vault.get_folder("rejected") / tampered_name

            shutil.move(str(file_path), str(rejected_path))

            # Log security alert
            self._audit.log_security_event(
                component=self.name,
                action_type="integrity_violation",
                target=target,
                reason=f"Approval file {file_path.name} failed integrity check. "
                       f"Expected hash: {request.integrity_hash[:16]}..."
            )

            # Create alert file
            from src.common.alerts import create_alert
            await create_alert(
                alert_type="tampered_approval",
                title=f"Tampered Approval File Detected",
                message=f"The approval file `{file_path.name}` was modified after creation. "
                        f"The action was NOT executed. File moved to Rejected folder.",
                severity="critical",
                vault=self.vault
            )

            return ApprovalResult(
                request=request,
                status=ApprovalStatus.REJECTED,
                executed=False,
                error="Integrity hash mismatch - file tampered"
            )

        # Step 2: Check if already expired
        if request.is_expired():
            logger.warning(f"Approved file {file_path.name} has already expired")
            await self._move_to_expired(file_path, request)
            return ApprovalResult(
                request=request,
                status=ApprovalStatus.EXPIRED,
                executed=False,
                error="Request expired before execution"
            )

        # Step 3: Execute action
        self._approved_count += 1
        logger.info(f"Executing approved action: {action_type} -> {target}")

        result = ApprovalResult(
            request=request,
            status=ApprovalStatus.APPROVED,
            executed=False
        )

        if self.dry_run:
            logger.info(f"[DRY-RUN] Would execute {action_type} to {target}")
            result.result = "dry_run_skipped"
            result.executed = False
        elif self.action_executor:
            try:
                exec_result = await self.action_executor(request)
                result.executed = True
                result.result = "success"
                result.external_id = exec_result.get("external_id") if isinstance(exec_result, dict) else None
                logger.info(f"Successfully executed {action_type} to {target}")
            except Exception as e:
                logger.exception(f"Failed to execute {action_type}: {e}")
                result.executed = False
                result.error = str(e)
        else:
            # No executor configured - just log
            logger.warning(f"No action executor configured. Would execute: {action_type}")
            result.result = "no_executor"

        # Log audit
        self._audit.log_execution(
            component=self.name,
            action_type=action_type,
            target=target,
            result=result.result or "executed" if result.executed else "failed",
            parameters=request.parameters,
            external_id=result.external_id
        )

        # Move to done folder
        if result.executed or self.dry_run:
            done_path = self.vault.get_folder("done") / file_path.name
            shutil.move(str(file_path), str(done_path))
            logger.debug(f"Moved to done: {done_path}")

        return result

    async def _handle_rejected(self, file_path: Path, request: ApprovalRequest) -> ApprovalResult:
        """Handle a rejected action file.

        Just log the rejection - action is NOT executed.

        Args:
            file_path: Path to the rejected file
            request: Parsed ApprovalRequest

        Returns:
            ApprovalResult with rejection details
        """
        action_type = request.action_type if isinstance(request.action_type, str) else request.action_type.value
        target = request.parameters.get("to") or request.parameters.get("visibility") or "unknown"

        self._rejected_count += 1

        logger.info(f"Action rejected: {action_type} -> {target}")

        # Log audit
        self._audit.log_approval(
            component=self.name,
            action_type=action_type,
            target=target,
            approval_status="rejected",
            parameters=request.parameters
        )

        return ApprovalResult(
            request=request,
            status=ApprovalStatus.REJECTED,
            executed=False,
            result="rejected_by_user"
        )

    async def _move_to_expired(self, file_path: Path, request: ApprovalRequest) -> None:
        """Move an expired approval file to /Expired folder."""
        action_type = request.action_type if isinstance(request.action_type, str) else request.action_type.value
        target = request.parameters.get("to") or request.parameters.get("visibility") or "unknown"

        self._expired_count += 1

        expired_path = self.vault.get_folder("expired") / file_path.name
        shutil.move(str(file_path), str(expired_path))

        logger.info(f"Moved expired approval to: {expired_path}")

        self._audit.log_approval(
            component=self.name,
            action_type=action_type,
            target=target,
            approval_status="expired",
            parameters={"original_file": file_path.name}
        )

    async def _handle_file(self, file_path: Path, folder_type: str) -> None:
        """Handle a file detected in approved or rejected folder.

        Args:
            file_path: Path to the file
            folder_type: "approved" or "rejected"
        """
        if not file_path.exists():
            logger.debug(f"File no longer exists: {file_path}")
            return

        request = self._parse_approval_file(file_path)
        if not request:
            logger.warning(f"Could not parse approval file: {file_path}")
            return

        if folder_type == "approved":
            await self._handle_approved(file_path, request)
        elif folder_type == "rejected":
            await self._handle_rejected(file_path, request)

    async def _check_expirations(self) -> int:
        """Check for expired approval requests in /Pending_Approval.

        Returns:
            Number of expired files moved
        """
        pending_folder = self.vault.get_folder("pending_approval")
        if not pending_folder.exists():
            return 0

        expired_count = 0
        now = datetime.now(timezone.utc)

        for file_path in pending_folder.glob("*.md"):
            try:
                request = self._parse_approval_file(file_path)
                if request and request.is_expired():
                    await self._move_to_expired(file_path, request)
                    expired_count += 1
            except Exception as e:
                logger.error(f"Error checking expiration for {file_path}: {e}")

        if expired_count > 0:
            logger.info(f"Expired {expired_count} approval request(s)")

        return expired_count

    async def _poll(self) -> None:
        """Poll for expired approvals."""
        await self._check_expirations()

    async def process_event(self, event: Any) -> None:
        """Process an approval event (not used - we use watchdog handlers)."""
        pass

    def _start_observers(self) -> None:
        """Start watchdog observers for approved and rejected folders."""
        approved_folder = self.vault.get_folder("approved")
        rejected_folder = self.vault.get_folder("rejected")

        # Ensure folders exist
        approved_folder.mkdir(parents=True, exist_ok=True)
        rejected_folder.mkdir(parents=True, exist_ok=True)

        # Create observers
        self._approved_observer = Observer()
        self._rejected_observer = Observer()

        # Add handlers
        self._approved_observer.schedule(
            ApprovalFileHandler(self, "approved"),
            str(approved_folder),
            recursive=False
        )
        self._rejected_observer.schedule(
            ApprovalFileHandler(self, "rejected"),
            str(rejected_folder),
            recursive=False
        )

        # Start observers
        self._approved_observer.start()
        self._rejected_observer.start()

        logger.info(f"Watching approved folder: {approved_folder}")
        logger.info(f"Watching rejected folder: {rejected_folder}")

    def _stop_observers(self) -> None:
        """Stop watchdog observers."""
        if self._approved_observer:
            self._approved_observer.stop()
            self._approved_observer.join(timeout=5)
            self._approved_observer = None

        if self._rejected_observer:
            self._rejected_observer.stop()
            self._rejected_observer.join(timeout=5)
            self._rejected_observer = None

    async def run(self) -> None:
        """Run the approval watcher."""
        self.status = WatcherStatus.STARTING
        self._loop = asyncio.get_event_loop()

        try:
            # Start folder observers
            self._start_observers()

            # Process any existing files in approved/rejected folders
            await self._process_existing_files()

            self.status = WatcherStatus.RUNNING

            # Run polling loop for expiration checks
            while not self._stop_event.is_set():
                try:
                    if await self._pre_poll():
                        await self._poll()
                        await self._post_poll()
                except Exception as e:
                    self._errors_count += 1
                    self._last_error = str(e)
                    logger.exception(f"{self.name} poll error: {e}")

                # Wait for next poll
                try:
                    await asyncio.wait_for(
                        asyncio.to_thread(self._stop_event.wait),
                        timeout=self.poll_interval_seconds
                    )
                except asyncio.TimeoutError:
                    pass

        finally:
            self._stop_observers()
            self.status = WatcherStatus.STOPPED

    async def _process_existing_files(self) -> None:
        """Process any existing files in approved/rejected folders at startup."""
        for folder_type in ["approved", "rejected"]:
            folder = self.vault.get_folder(folder_type)
            if not folder.exists():
                continue

            for file_path in folder.glob("*.md"):
                await self._handle_file(file_path, folder_type)

    def get_stats(self) -> dict[str, Any]:
        """Get watcher statistics."""
        stats = super().get_stats()
        stats.update({
            "approved_count": self._approved_count,
            "rejected_count": self._rejected_count,
            "expired_count": self._expired_count,
            "tampered_count": self._tampered_count
        })
        return stats


async def main():
    """Run the approval watcher standalone."""
    import argparse

    parser = argparse.ArgumentParser(description="Approval Watcher")
    parser.add_argument("--vault", help="Path to Obsidian vault")
    parser.add_argument("--dry-run", action="store_true", help="Don't execute actions")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    watcher = ApprovalWatcher(vault_path=args.vault, dry_run=args.dry_run)
    await watcher.run()


if __name__ == "__main__":
    asyncio.run(main())
