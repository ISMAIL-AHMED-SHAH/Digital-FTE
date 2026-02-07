"""Vault Initialization Utility for Silver Tier.

Verifies and creates required folder structure in the Obsidian vault
for the AI Employee file-based workflow.

Required folders:
- Needs_Action: Incoming action files from watchers
- Pending_Approval: Actions awaiting human approval
- Approved: Actions approved for execution
- Rejected: Actions rejected by user
- Expired: Actions that timed out without approval
- Done: Completed actions (archived)
- Logs: Audit logs (JSON-lines)
- Alerts: System alerts for user attention
- Briefings: Generated briefing documents
"""

import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Default folder structure
DEFAULT_FOLDERS = {
    "needs_action": "Needs_Action",
    "pending_approval": "Pending_Approval",
    "approved": "Approved",
    "rejected": "Rejected",
    "expired": "Expired",
    "done": "Done",
    "logs": "Logs",
    "alerts": "Alerts",
    "briefings": "Briefings"
}


class VaultError(Exception):
    """Error related to vault operations."""
    pass


class VaultNotFoundError(VaultError):
    """Vault directory does not exist."""
    pass


class Vault:
    """Vault management utility.

    Usage:
        vault = Vault("/path/to/obsidian/vault")

        # Verify/create folder structure
        vault.initialize()

        # Get paths
        needs_action = vault.get_folder("needs_action")
        logs = vault.get_folder("logs")

        # Write files
        vault.write_action_file("needs_action", "email-123.md", content)
        vault.write_log_entry({"action": "email_detected", ...})
    """

    def __init__(
        self,
        vault_path: str | Path,
        folders: dict[str, str] | None = None,
        create_if_missing: bool = True
    ):
        """Initialize vault utility.

        Args:
            vault_path: Path to Obsidian vault root
            folders: Custom folder mapping (key -> folder name)
            create_if_missing: Create vault directory if it doesn't exist
        """
        self.vault_path = Path(vault_path).expanduser().resolve()
        self.folders = {**DEFAULT_FOLDERS, **(folders or {})}
        self._create_if_missing = create_if_missing

        # Validate vault path
        if not self.vault_path.exists():
            if create_if_missing:
                logger.warning(f"Creating vault directory: {self.vault_path}")
                self.vault_path.mkdir(parents=True, exist_ok=True)
            else:
                raise VaultNotFoundError(f"Vault not found: {self.vault_path}")

    def get_folder(self, key: str) -> Path:
        """Get the absolute path to a vault folder.

        Args:
            key: Folder key (e.g., "needs_action", "logs")

        Returns:
            Absolute path to the folder

        Raises:
            KeyError: If folder key is not recognized
        """
        if key not in self.folders:
            raise KeyError(f"Unknown folder key: {key}. Valid keys: {list(self.folders.keys())}")

        return self.vault_path / self.folders[key]

    def folder_exists(self, key: str) -> bool:
        """Check if a folder exists."""
        return self.get_folder(key).exists()

    def create_folder(self, key: str) -> Path:
        """Create a folder if it doesn't exist.

        Args:
            key: Folder key

        Returns:
            Path to the folder
        """
        folder_path = self.get_folder(key)
        if not folder_path.exists():
            folder_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created vault folder: {folder_path}")
        return folder_path

    def initialize(self, skip_existing: bool = True) -> dict[str, bool]:
        """Initialize all required vault folders.

        Args:
            skip_existing: If True, don't recreate existing folders

        Returns:
            Dictionary mapping folder key to whether it was created
        """
        results = {}

        for key in self.folders:
            folder_path = self.get_folder(key)
            exists = folder_path.exists()

            if not exists:
                folder_path.mkdir(parents=True, exist_ok=True)
                results[key] = True
                logger.info(f"Created: {folder_path}")
            else:
                results[key] = False
                if not skip_existing:
                    logger.debug(f"Exists: {folder_path}")

        created_count = sum(1 for v in results.values() if v)
        if created_count > 0:
            logger.info(f"Initialized {created_count} vault folders")
        else:
            logger.debug("All vault folders already exist")

        return results

    def verify(self) -> tuple[bool, list[str]]:
        """Verify that all required folders exist.

        Returns:
            Tuple of (all_valid, list_of_missing_folders)
        """
        missing = []

        for key in self.folders:
            if not self.folder_exists(key):
                missing.append(key)

        return len(missing) == 0, missing

    def list_files(self, folder_key: str, pattern: str = "*.md") -> list[Path]:
        """List files in a vault folder.

        Args:
            folder_key: Folder key
            pattern: Glob pattern (default: *.md)

        Returns:
            List of file paths
        """
        folder = self.get_folder(folder_key)
        if not folder.exists():
            return []
        return sorted(folder.glob(pattern))

    def read_file(self, folder_key: str, filename: str) -> str | None:
        """Read a file from a vault folder.

        Args:
            folder_key: Folder key
            filename: File name

        Returns:
            File contents or None if not found
        """
        file_path = self.get_folder(folder_key) / filename
        if not file_path.exists():
            return None

        return file_path.read_text(encoding="utf-8")

    def write_file(
        self,
        folder_key: str,
        filename: str,
        content: str,
        overwrite: bool = False
    ) -> Path:
        """Write a file to a vault folder.

        Args:
            folder_key: Folder key
            filename: File name
            content: File content
            overwrite: If False, raise error if file exists

        Returns:
            Path to the written file

        Raises:
            FileExistsError: If file exists and overwrite=False
        """
        folder = self.create_folder(folder_key)
        file_path = folder / filename

        if file_path.exists() and not overwrite:
            raise FileExistsError(f"File already exists: {file_path}")

        file_path.write_text(content, encoding="utf-8")
        logger.debug(f"Wrote: {file_path}")

        return file_path

    def move_file(
        self,
        from_folder: str,
        to_folder: str,
        filename: str,
        new_filename: str | None = None
    ) -> Path:
        """Move a file between vault folders.

        Args:
            from_folder: Source folder key
            to_folder: Destination folder key
            filename: File name to move
            new_filename: Optional new filename

        Returns:
            Path to the moved file

        Raises:
            FileNotFoundError: If source file doesn't exist
        """
        source = self.get_folder(from_folder) / filename
        if not source.exists():
            raise FileNotFoundError(f"Source file not found: {source}")

        dest_folder = self.create_folder(to_folder)
        dest_filename = new_filename or filename
        dest = dest_folder / dest_filename

        source.rename(dest)
        logger.info(f"Moved: {source} -> {dest}")

        return dest

    def delete_file(self, folder_key: str, filename: str) -> bool:
        """Delete a file from a vault folder.

        Args:
            folder_key: Folder key
            filename: File name

        Returns:
            True if deleted, False if not found
        """
        file_path = self.get_folder(folder_key) / filename

        if file_path.exists():
            file_path.unlink()
            logger.debug(f"Deleted: {file_path}")
            return True

        return False

    def get_stats(self) -> dict[str, Any]:
        """Get vault statistics."""
        stats = {
            "vault_path": str(self.vault_path),
            "folders": {}
        }

        for key in self.folders:
            folder = self.get_folder(key)
            if folder.exists():
                files = list(folder.glob("*.md"))
                stats["folders"][key] = {
                    "path": str(folder),
                    "exists": True,
                    "file_count": len(files)
                }
            else:
                stats["folders"][key] = {
                    "path": str(folder),
                    "exists": False,
                    "file_count": 0
                }

        return stats


# Module-level convenience functions
_default_vault: Vault | None = None


def get_vault(vault_path: str | Path | None = None) -> Vault:
    """Get the default vault instance."""
    global _default_vault

    if _default_vault is None:
        if vault_path is None:
            vault_path = os.environ.get("VAULT_PATH", ".")
        _default_vault = Vault(vault_path)

    return _default_vault


def initialize_vault(vault_path: str | Path | None = None) -> dict[str, bool]:
    """Initialize vault folder structure."""
    return get_vault(vault_path).initialize()


def verify_vault(vault_path: str | Path | None = None) -> tuple[bool, list[str]]:
    """Verify vault folder structure exists."""
    return get_vault(vault_path).verify()


def get_folder(key: str) -> Path:
    """Get path to a vault folder."""
    return get_vault().get_folder(key)
