"""Quarantine Handler (T073 - FR-030).

Manages /Quarantine folder for files that fail processing:
- Move malformed files to quarantine
- Create metadata for quarantined files
- Support restore operations
- List and manage quarantined items
"""

import json
import logging
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class QuarantineResult:
    """Result of a quarantine operation.

    Attributes:
        success: Whether operation succeeded
        message: Status message
        quarantine_path: Path to quarantined file
        metadata_path: Path to metadata file
    """
    success: bool
    message: str
    quarantine_path: Optional[Path] = None
    metadata_path: Optional[Path] = None


@dataclass
class RestoreResult:
    """Result of a restore operation.

    Attributes:
        success: Whether restore succeeded
        message: Status message
        restored_path: Path to restored file
    """
    success: bool
    message: str
    restored_path: Optional[Path] = None


class QuarantineHandler:
    """Manages quarantine operations for failed files.

    Usage:
        handler = QuarantineHandler(vault_path=Path("./vault"))

        # Quarantine a malformed file
        result = handler.quarantine(
            file_path,
            reason="Invalid YAML frontmatter",
            error_details={"line": 1, "error": "parse error"}
        )

        # List quarantined files
        files = handler.list_quarantined()

        # Restore a file
        handler.restore(quarantine_path)
    """

    def __init__(self, vault_path: Path):
        """Initialize quarantine handler.

        Args:
            vault_path: Path to vault root
        """
        self.vault_path = vault_path
        self.quarantine_dir = vault_path / "Quarantine"

    def quarantine(
        self,
        file_path: Path,
        reason: str,
        error_details: Optional[dict] = None,
        category: str = "processing_error"
    ) -> QuarantineResult:
        """Move a file to quarantine.

        Args:
            file_path: Path to file to quarantine
            reason: Human-readable reason for quarantine
            error_details: Additional error information
            category: Category of the issue

        Returns:
            QuarantineResult with operation status
        """
        if not file_path.exists():
            return QuarantineResult(
                success=False,
                message=f"File not found: {file_path}"
            )

        # Ensure quarantine directory exists
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)

        # Handle duplicate filenames
        dest_filename = file_path.name
        dest_path = self.quarantine_dir / dest_filename

        if dest_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            stem = file_path.stem
            suffix = file_path.suffix
            dest_filename = f"{stem}_{timestamp}{suffix}"
            dest_path = self.quarantine_dir / dest_filename

        try:
            # Move file to quarantine
            shutil.move(str(file_path), str(dest_path))

            # Create metadata file
            metadata = {
                "original_path": str(file_path),
                "original_filename": file_path.name,
                "quarantined_at": datetime.now().isoformat(),
                "reason": reason,
                "category": category,
            }
            if error_details:
                metadata["error_details"] = error_details

            metadata_path = dest_path.with_suffix(dest_path.suffix + ".quarantine.json")
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)

            logger.info(f"Quarantined file: {file_path} -> {dest_path}")

            return QuarantineResult(
                success=True,
                message=f"File quarantined: {dest_filename}",
                quarantine_path=dest_path,
                metadata_path=metadata_path
            )

        except Exception as e:
            logger.error(f"Error quarantining file {file_path}: {e}")
            return QuarantineResult(
                success=False,
                message=f"Error: {str(e)}"
            )

    def restore(
        self,
        quarantine_path: Path,
        restore_to: Optional[Path] = None
    ) -> RestoreResult:
        """Restore a file from quarantine.

        Args:
            quarantine_path: Path to quarantined file
            restore_to: Optional destination path (defaults to original)

        Returns:
            RestoreResult with operation status
        """
        if not quarantine_path.exists():
            return RestoreResult(
                success=False,
                message=f"Quarantined file not found: {quarantine_path}"
            )

        # Load metadata to find original path
        metadata_path = quarantine_path.with_suffix(
            quarantine_path.suffix + ".quarantine.json"
        )

        if restore_to is None:
            if metadata_path.exists():
                try:
                    with open(metadata_path) as f:
                        metadata = json.load(f)
                    restore_to = Path(metadata.get("original_path", ""))
                except (json.JSONDecodeError, IOError):
                    pass

            if not restore_to:
                # Default to Needs_Action folder
                restore_to = self.vault_path / "Needs_Action" / quarantine_path.name

        try:
            # Ensure destination directory exists
            restore_to.parent.mkdir(parents=True, exist_ok=True)

            # Move file back
            shutil.move(str(quarantine_path), str(restore_to))

            # Remove metadata file
            if metadata_path.exists():
                metadata_path.unlink()

            logger.info(f"Restored file: {quarantine_path} -> {restore_to}")

            return RestoreResult(
                success=True,
                message=f"File restored to {restore_to}",
                restored_path=restore_to
            )

        except Exception as e:
            logger.error(f"Error restoring file {quarantine_path}: {e}")
            return RestoreResult(
                success=False,
                message=f"Error: {str(e)}"
            )

    def list_quarantined(self) -> list[dict]:
        """List all quarantined files with metadata.

        Returns:
            List of quarantine info dicts
        """
        if not self.quarantine_dir.exists():
            return []

        files = []

        # Find all files (not metadata files)
        for path in self.quarantine_dir.iterdir():
            if path.suffix == ".json" and ".quarantine.json" in path.name:
                continue  # Skip metadata files

            if not path.is_file():
                continue

            info = {
                "filename": path.name,
                "path": str(path),
                "size_bytes": path.stat().st_size,
                "quarantined_at": None,
                "reason": "Unknown",
                "category": "unknown",
                "original_path": None
            }

            # Try to load metadata
            metadata_path = path.with_suffix(path.suffix + ".quarantine.json")
            if metadata_path.exists():
                try:
                    with open(metadata_path) as f:
                        metadata = json.load(f)
                    info.update({
                        "quarantined_at": metadata.get("quarantined_at"),
                        "reason": metadata.get("reason", "Unknown"),
                        "category": metadata.get("category", "unknown"),
                        "original_path": metadata.get("original_path"),
                        "error_details": metadata.get("error_details")
                    })
                except (json.JSONDecodeError, IOError):
                    pass

            files.append(info)

        # Sort by quarantine date (newest first)
        files.sort(
            key=lambda x: x.get("quarantined_at") or "",
            reverse=True
        )

        return files

    def get_quarantine_stats(self) -> dict:
        """Get statistics about quarantined files.

        Returns:
            Statistics dictionary
        """
        files = self.list_quarantined()

        if not files:
            return {
                "total_files": 0,
                "total_size_bytes": 0,
                "by_category": {},
                "oldest": None,
                "newest": None
            }

        by_category: dict[str, int] = {}
        for f in files:
            cat = f.get("category", "unknown")
            by_category[cat] = by_category.get(cat, 0) + 1

        dates = [f.get("quarantined_at") for f in files if f.get("quarantined_at")]

        return {
            "total_files": len(files),
            "total_size_bytes": sum(f.get("size_bytes", 0) for f in files),
            "by_category": by_category,
            "oldest": min(dates) if dates else None,
            "newest": max(dates) if dates else None
        }

    def cleanup_old(self, days: int = 30) -> list[str]:
        """Remove files quarantined longer than specified days.

        Args:
            days: Maximum age in days

        Returns:
            List of removed filenames
        """
        from datetime import timedelta

        cutoff = datetime.now() - timedelta(days=days)
        removed = []

        files = self.list_quarantined()

        for f in files:
            quarantined_at = f.get("quarantined_at")
            if not quarantined_at:
                continue

            try:
                dt = datetime.fromisoformat(quarantined_at)
                if dt < cutoff:
                    path = Path(f["path"])
                    metadata_path = path.with_suffix(
                        path.suffix + ".quarantine.json"
                    )

                    if path.exists():
                        path.unlink()
                    if metadata_path.exists():
                        metadata_path.unlink()

                    removed.append(f["filename"])
                    logger.info(f"Cleaned up old quarantine file: {f['filename']}")

            except (ValueError, IOError) as e:
                logger.warning(f"Error cleaning up {f['filename']}: {e}")

        return removed

    def create_quarantine_alert(
        self,
        file_path: Path,
        reason: str,
        alert_dir: Optional[Path] = None
    ) -> Optional[Path]:
        """Create an alert file for a quarantine event.

        Args:
            file_path: Quarantined file path
            reason: Quarantine reason
            alert_dir: Optional alert directory

        Returns:
            Path to alert file or None
        """
        if alert_dir is None:
            alert_dir = self.vault_path / "Alerts"

        alert_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now()
        alert_name = f"quarantine_{timestamp.strftime('%Y%m%d_%H%M%S')}.md"

        content = f"""---
type: alert
category: quarantine
severity: warning
created_at: {timestamp.isoformat()}
---

# File Quarantined

**File:** {file_path.name}
**Time:** {timestamp.strftime('%Y-%m-%d %H:%M:%S')}

## Reason

{reason}

## Location

The file has been moved to:
`{self.quarantine_dir / file_path.name}`

## Actions

1. Review the file for issues
2. Fix the problem if possible
3. Use the `manage-approval` skill to restore or delete

"""
        alert_path = alert_dir / alert_name
        alert_path.write_text(content)

        logger.info(f"Created quarantine alert: {alert_path}")
        return alert_path
