"""
Configuration management for Local File Watcher Service.

Provides WatcherConfig dataclass and CLI argument parsing with validation.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import NoReturn

from . import __version__


@dataclass
class WatcherConfig:
    """
    Runtime configuration for the file watcher service.

    Attributes:
        vault_path: Absolute path to Obsidian vault root.
        drop_folder: Absolute path to monitored folder.
        dry_run: If True, log only without creating files.
        needs_action_path: Derived path to {vault_path}/Needs_Action.
    """

    vault_path: Path
    drop_folder: Path
    dry_run: bool = False
    needs_action_path: Path = field(init=False)

    def __post_init__(self) -> None:
        """Derive needs_action_path from vault_path."""
        self.needs_action_path = self.vault_path / "Needs_Action"


class ConfigurationError(Exception):
    """Raised when CLI arguments are invalid."""

    pass


class ValidationError(Exception):
    """Raised when path validation fails."""

    pass


def create_argument_parser() -> argparse.ArgumentParser:
    """
    Create and configure the argument parser for the file watcher CLI.

    Returns:
        Configured ArgumentParser instance.
    """
    parser = argparse.ArgumentParser(
        prog="file-watcher",
        description="Local File Watcher Service for Bona-Papa AI Employee. "
        "Monitors a drop folder and creates action items in Obsidian vault.",
    )

    parser.add_argument(
        "--vault",
        type=Path,
        required=True,
        metavar="PATH",
        help="Absolute path to Obsidian vault root directory",
    )

    parser.add_argument(
        "--drop-folder",
        type=Path,
        required=True,
        metavar="PATH",
        help="Absolute path to folder to monitor for new files",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Log intended actions without creating files",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    return parser


def parse_args(args: list[str] | None = None) -> WatcherConfig:
    """
    Parse command-line arguments and return a WatcherConfig.

    Args:
        args: Command-line arguments. If None, uses sys.argv[1:].

    Returns:
        WatcherConfig with parsed values.

    Raises:
        SystemExit: If required arguments are missing (exit code 1).
    """
    parser = create_argument_parser()
    namespace = parser.parse_args(args)

    return WatcherConfig(
        vault_path=namespace.vault.resolve(),
        drop_folder=namespace.drop_folder.resolve(),
        dry_run=namespace.dry_run,
    )


def validate_config(config: WatcherConfig) -> None:
    """
    Validate that all paths exist and meet requirements.

    Args:
        config: The WatcherConfig to validate.

    Raises:
        ValidationError: If any validation check fails.
    """
    # Check vault_path exists and is a directory
    if not config.vault_path.exists():
        raise ValidationError(
            f"Vault path does not exist: {config.vault_path}"
        )
    if not config.vault_path.is_dir():
        raise ValidationError(
            f"Vault path is not a directory: {config.vault_path}"
        )

    # Check drop_folder exists and is a directory
    if not config.drop_folder.exists():
        raise ValidationError(
            f"Drop folder does not exist: {config.drop_folder}"
        )
    if not config.drop_folder.is_dir():
        raise ValidationError(
            f"Drop folder is not a directory: {config.drop_folder}"
        )

    # Check paths are different
    if config.vault_path == config.drop_folder:
        raise ValidationError(
            f"Vault and drop folder cannot be the same path: {config.vault_path}"
        )

    # Check Needs_Action folder exists
    if not config.needs_action_path.exists():
        raise ValidationError(
            f"Needs_Action folder not found in vault: {config.needs_action_path}"
        )
    if not config.needs_action_path.is_dir():
        raise ValidationError(
            f"Needs_Action path is not a directory: {config.needs_action_path}"
        )


def load_config(args: list[str] | None = None) -> WatcherConfig:
    """
    Parse arguments and validate configuration.

    This is the main entry point for configuration loading.

    Args:
        args: Command-line arguments. If None, uses sys.argv[1:].

    Returns:
        Validated WatcherConfig.

    Raises:
        SystemExit: Exit code 1 for argument errors, 2 for validation errors.
    """
    try:
        config = parse_args(args)
    except SystemExit as e:
        # Let --help and --version exit cleanly with code 0
        if e.code == 0:
            raise
        # Convert argparse errors (code 2) to code 1 per CLI contract
        raise SystemExit(1)

    try:
        validate_config(config)
    except ValidationError as e:
        # Validation errors get exit code 2
        print(f"Error: {e}", file=sys.stderr)
        raise SystemExit(2)

    return config
