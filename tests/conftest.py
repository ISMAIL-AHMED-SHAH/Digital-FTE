"""
Shared pytest fixtures for file_watcher tests.

Provides temporary vault and drop folder fixtures for isolated testing.
"""

import tempfile
from pathlib import Path
from typing import Generator

import pytest


@pytest.fixture
def temp_vault() -> Generator[Path, None, None]:
    """
    Create a temporary Obsidian vault structure for testing.

    Yields:
        Path to the temporary vault root with /Needs_Action folder created.
    """
    with tempfile.TemporaryDirectory(prefix="test_vault_") as tmpdir:
        vault_path = Path(tmpdir)
        needs_action = vault_path / "Needs_Action"
        needs_action.mkdir(parents=True, exist_ok=True)
        yield vault_path


@pytest.fixture
def temp_drop_folder() -> Generator[Path, None, None]:
    """
    Create a temporary drop folder for testing file watching.

    Yields:
        Path to the temporary drop folder.
    """
    with tempfile.TemporaryDirectory(prefix="test_drop_") as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_file(temp_drop_folder: Path) -> Path:
    """
    Create a sample file in the drop folder for testing.

    Args:
        temp_drop_folder: The temporary drop folder fixture.

    Returns:
        Path to the created sample file.
    """
    sample_path = temp_drop_folder / "test_document.pdf"
    sample_path.write_bytes(b"Sample PDF content for testing")
    return sample_path


@pytest.fixture
def sample_file_with_spaces(temp_drop_folder: Path) -> Path:
    """
    Create a sample file with spaces and special characters in name.

    Args:
        temp_drop_folder: The temporary drop folder fixture.

    Returns:
        Path to the created sample file.
    """
    sample_path = temp_drop_folder / "My Report (Final).pdf"
    sample_path.write_bytes(b"Sample content with special filename")
    return sample_path
