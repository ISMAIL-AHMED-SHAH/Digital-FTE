"""
File system watcher for Local File Watcher Service.

Monitors drop folder for new files and creates action items in Obsidian vault.
"""

from __future__ import annotations

import logging
import traceback
from pathlib import Path
from typing import TYPE_CHECKING

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from .action_file import (
    ActionFile,
    generate_action_content,
    get_action_file_path,
)
from .logger import (
    log_action_created,
    log_action_skipped,
    log_error,
    log_file_detected,
)

if TYPE_CHECKING:
    from .config import WatcherConfig


class DropFolderHandler(FileSystemEventHandler):
    """
    Handles file system events for the drop folder.

    Creates action files in the Obsidian vault when new files are detected.
    """

    def __init__(
        self,
        config: "WatcherConfig",
        logger: logging.Logger,
    ) -> None:
        """
        Initialize the handler.

        Args:
            config: Watcher configuration with paths and options.
            logger: Logger instance for structured logging.
        """
        super().__init__()
        self.config = config
        self.logger = logger

    def on_created(self, event: FileSystemEvent) -> None:
        """
        Handle file creation events.

        Creates an action file for each new file detected.
        Ignores directories per FR-006.

        Args:
            event: The file system event.
        """
        # Ignore directories (FR-006)
        if event.is_directory:
            return

        try:
            self._process_file(Path(event.src_path))
        except Exception as e:
            # Log error but continue running (FR-007 - resilience)
            log_error(
                self.logger,
                f"Failed to process file: {e}",
                source_file=event.src_path,
                error=str(e),
                traceback=traceback.format_exc(),
            )

    def _process_file(self, file_path: Path) -> None:
        """
        Process a newly detected file.

        Args:
            file_path: Path to the detected file.
        """
        # Log file detection
        size = file_path.stat().st_size
        log_file_detected(self.logger, str(file_path), size)

        # Create action file metadata
        action = ActionFile.from_path(file_path)

        # Get target path for action file
        action_file_path = get_action_file_path(
            action, self.config.needs_action_path
        )

        # Check dry-run mode (FR-008)
        if self.config.dry_run:
            log_action_skipped(
                self.logger,
                str(file_path),
                str(action_file_path),
            )
            return

        # Write action file
        write_action_file(action, action_file_path)

        # Log success
        log_action_created(
            self.logger,
            str(file_path),
            str(action_file_path),
        )


def write_action_file(action: ActionFile, target_path: Path) -> None:
    """
    Write an action file to the specified path.

    Args:
        action: The ActionFile with metadata.
        target_path: Path where the action file should be written.

    Raises:
        OSError: If the file cannot be written.
    """
    content = generate_action_content(action)
    target_path.write_text(content, encoding="utf-8")


def start_watching(
    config: "WatcherConfig",
    logger: logging.Logger,
) -> Observer:
    """
    Start watching the drop folder for new files.

    Args:
        config: Watcher configuration with paths and options.
        logger: Logger instance for structured logging.

    Returns:
        The started Observer instance.
    """
    handler = DropFolderHandler(config, logger)
    observer = Observer()

    observer.schedule(
        handler,
        str(config.drop_folder),
        recursive=False,  # Only watch top-level of drop folder
    )

    observer.start()
    return observer


def stop_watching(observer: Observer) -> None:
    """
    Stop the file watcher gracefully.

    Args:
        observer: The Observer instance to stop.
    """
    observer.stop()
    observer.join()
