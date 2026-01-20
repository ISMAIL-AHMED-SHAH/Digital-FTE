"""
Action file generation for Local File Watcher Service.

Creates Markdown action files with YAML frontmatter for the Obsidian vault.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import yaml


@dataclass
class ActionFile:
    """
    Represents an action item created when a file is dropped.

    Attributes:
        original_name: Original filename with extension.
        size: File size in bytes.
        timestamp: Creation time in ISO 8601 UTC format.
        source_path: Absolute path to the original file.
        type: Always "file_drop" for this watcher.
        status: Always "pending" on creation.
    """

    original_name: str
    size: int
    timestamp: str
    source_path: str
    type: str = field(default="file_drop", init=False)
    status: str = field(default="pending", init=False)

    @classmethod
    def from_path(cls, file_path: Path) -> "ActionFile":
        """
        Create an ActionFile from a file path.

        Args:
            file_path: Path to the dropped file.

        Returns:
            ActionFile with metadata populated from the file.
        """
        stat = file_path.stat()
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        return cls(
            original_name=file_path.name,
            size=stat.st_size,
            timestamp=timestamp,
            source_path=str(file_path.resolve()),
        )


def generate_action_content(action: ActionFile) -> str:
    """
    Generate the full content for an action file.

    Creates YAML frontmatter followed by Markdown body.

    Args:
        action: The ActionFile to generate content for.

    Returns:
        Complete file content as a string.
    """
    # Build frontmatter dict in the specified order
    frontmatter = {
        "type": action.type,
        "original_name": action.original_name,
        "size": action.size,
        "timestamp": action.timestamp,
        "status": action.status,
        "source_path": action.source_path,
    }

    # Use safe_dump with proper quoting for special characters
    yaml_content = yaml.safe_dump(
        frontmatter,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    )

    # Build the markdown body
    body = f"""## New File Dropped

**File**: {action.original_name}

New file dropped for processing."""

    # Combine frontmatter and body
    return f"---\n{yaml_content}---\n\n{body}\n"


def generate_action_filename(
    original_name: str,
    needs_action_path: Path,
    timestamp: str | None = None,
) -> str:
    """
    Generate a unique filename for the action file.

    Pattern: FILE_{original_filename}.md
    If duplicate exists: FILE_{original_filename}_{timestamp}.md

    Args:
        original_name: Original filename to include in action filename.
        needs_action_path: Path to the Needs_Action folder for duplicate checking.
        timestamp: Optional timestamp for duplicate handling. If None and needed,
                   uses current time in YYYYMMDDTHHMMSS format.

    Returns:
        Unique filename for the action file (without path).
    """
    base_filename = f"FILE_{original_name}.md"
    target_path = needs_action_path / base_filename

    if not target_path.exists():
        return base_filename

    # Handle duplicate - add timestamp suffix
    if timestamp is None:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    else:
        # Convert ISO format to file-safe format if needed
        # From: 2026-01-19T10:30:00Z To: 20260119T103000
        timestamp = timestamp.replace("-", "").replace(":", "").replace("Z", "")

    return f"FILE_{original_name}_{timestamp}.md"


def get_action_file_path(
    action: ActionFile,
    needs_action_path: Path,
) -> Path:
    """
    Get the full path for an action file.

    Args:
        action: The ActionFile to get path for.
        needs_action_path: Path to the Needs_Action folder.

    Returns:
        Full path where the action file should be written.
    """
    filename = generate_action_filename(
        action.original_name,
        needs_action_path,
        action.timestamp,
    )
    return needs_action_path / filename
