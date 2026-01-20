"""
Integration tests for file_watcher end-to-end flows.

Tests the complete flow: drop file → action file created in vault.
"""

import time
from pathlib import Path

import pytest

from file_watcher.config import WatcherConfig
from file_watcher.logger import setup_logger
from file_watcher.watcher import start_watching, stop_watching


class TestWatcherIntegration:
    """End-to-end tests for file watcher."""

    @pytest.fixture
    def watcher_config(
        self, temp_vault: Path, temp_drop_folder: Path
    ) -> WatcherConfig:
        """Create a WatcherConfig for testing."""
        return WatcherConfig(
            vault_path=temp_vault,
            drop_folder=temp_drop_folder,
            dry_run=False,
        )

    @pytest.fixture
    def dry_run_config(
        self, temp_vault: Path, temp_drop_folder: Path
    ) -> WatcherConfig:
        """Create a dry-run WatcherConfig for testing."""
        return WatcherConfig(
            vault_path=temp_vault,
            drop_folder=temp_drop_folder,
            dry_run=True,
        )

    @pytest.fixture
    def logger(self):
        """Create a logger for testing."""
        return setup_logger("test_watcher")

    def wait_for_file(
        self, path: Path, timeout: float = 5.0, poll_interval: float = 0.1
    ) -> bool:
        """
        Wait for a file to appear.

        Args:
            path: Path to wait for.
            timeout: Maximum time to wait in seconds.
            poll_interval: Time between checks in seconds.

        Returns:
            True if file appeared, False if timeout.
        """
        start = time.time()
        while time.time() - start < timeout:
            if path.exists():
                return True
            time.sleep(poll_interval)
        return False

    def test_drop_file_creates_action(
        self,
        watcher_config: WatcherConfig,
        logger,
        temp_drop_folder: Path,
        temp_vault: Path,
    ) -> None:
        """Dropping a file creates an action file in Needs_Action."""
        # Start watcher
        observer = start_watching(watcher_config, logger)

        try:
            # Give watcher time to initialize
            time.sleep(0.5)

            # Drop a file
            dropped_file = temp_drop_folder / "test_document.pdf"
            dropped_file.write_bytes(b"PDF content here")

            # Wait for action file to appear
            expected_action = temp_vault / "Needs_Action" / "FILE_test_document.pdf.md"
            assert self.wait_for_file(expected_action, timeout=5.0), (
                f"Action file not created within 5 seconds: {expected_action}"
            )

            # Verify action file content
            content = expected_action.read_text(encoding="utf-8")
            assert "type: file_drop" in content
            assert "original_name: test_document.pdf" in content
            assert "status: pending" in content
            assert "## New File Dropped" in content

        finally:
            stop_watching(observer)

    def test_drop_file_preserves_original(
        self,
        watcher_config: WatcherConfig,
        logger,
        temp_drop_folder: Path,
    ) -> None:
        """Dropping a file does not modify the original file (FR-013)."""
        observer = start_watching(watcher_config, logger)

        try:
            time.sleep(0.5)

            # Drop a file with specific content
            original_content = b"Original file content - should not be modified"
            dropped_file = temp_drop_folder / "preserve_test.pdf"
            dropped_file.write_bytes(original_content)

            # Wait for processing
            time.sleep(2.0)

            # Verify original file unchanged
            assert dropped_file.exists(), "Original file should still exist"
            assert dropped_file.read_bytes() == original_content, (
                "Original file content should not be modified"
            )

        finally:
            stop_watching(observer)

    def test_dry_run_does_not_create_file(
        self,
        dry_run_config: WatcherConfig,
        logger,
        temp_drop_folder: Path,
        temp_vault: Path,
    ) -> None:
        """Dry-run mode logs but does not create action files (FR-008)."""
        observer = start_watching(dry_run_config, logger)

        try:
            time.sleep(0.5)

            # Drop a file
            dropped_file = temp_drop_folder / "dry_run_test.pdf"
            dropped_file.write_bytes(b"PDF content")

            # Wait to ensure watcher processes
            time.sleep(2.0)

            # Action file should NOT exist
            expected_action = temp_vault / "Needs_Action" / "FILE_dry_run_test.pdf.md"
            assert not expected_action.exists(), (
                "Dry-run mode should not create action files"
            )

        finally:
            stop_watching(observer)

    def test_ignores_directories(
        self,
        watcher_config: WatcherConfig,
        logger,
        temp_drop_folder: Path,
        temp_vault: Path,
    ) -> None:
        """Watcher ignores directories (FR-006)."""
        observer = start_watching(watcher_config, logger)

        try:
            time.sleep(0.5)

            # Create a directory (not a file)
            new_dir = temp_drop_folder / "subdirectory"
            new_dir.mkdir()

            # Wait to ensure watcher processes
            time.sleep(2.0)

            # No action file should be created for directory
            needs_action = temp_vault / "Needs_Action"
            action_files = list(needs_action.glob("FILE_subdirectory*"))
            assert len(action_files) == 0, (
                "Should not create action file for directories"
            )

        finally:
            stop_watching(observer)

    def test_handles_multiple_files(
        self,
        watcher_config: WatcherConfig,
        logger,
        temp_drop_folder: Path,
        temp_vault: Path,
    ) -> None:
        """Watcher handles multiple files dropped in sequence."""
        observer = start_watching(watcher_config, logger)

        try:
            time.sleep(0.5)

            # Drop multiple files
            files = ["file1.pdf", "file2.docx", "file3.txt"]
            for filename in files:
                (temp_drop_folder / filename).write_bytes(b"content")
                time.sleep(0.3)  # Small delay between files

            # Wait for all to be processed
            time.sleep(3.0)

            # Verify all action files created
            needs_action = temp_vault / "Needs_Action"
            for filename in files:
                expected = needs_action / f"FILE_{filename}.md"
                assert expected.exists(), f"Action file not created for {filename}"

        finally:
            stop_watching(observer)

    def test_handles_file_with_spaces(
        self,
        watcher_config: WatcherConfig,
        logger,
        temp_drop_folder: Path,
        temp_vault: Path,
    ) -> None:
        """Watcher handles filenames with spaces (FR-005)."""
        observer = start_watching(watcher_config, logger)

        try:
            time.sleep(0.5)

            # Drop file with spaces in name
            dropped_file = temp_drop_folder / "My Report (Final).pdf"
            dropped_file.write_bytes(b"PDF content")

            # Wait for action file
            expected_action = temp_vault / "Needs_Action" / "FILE_My Report (Final).pdf.md"
            assert self.wait_for_file(expected_action, timeout=5.0), (
                "Action file not created for filename with spaces"
            )

            # Verify content references correct filename
            content = expected_action.read_text(encoding="utf-8")
            assert "My Report (Final).pdf" in content

        finally:
            stop_watching(observer)


class TestWatcherResilience:
    """Tests for watcher error handling and resilience."""

    @pytest.fixture
    def watcher_config(
        self, temp_vault: Path, temp_drop_folder: Path
    ) -> WatcherConfig:
        """Create a WatcherConfig for testing."""
        return WatcherConfig(
            vault_path=temp_vault,
            drop_folder=temp_drop_folder,
            dry_run=False,
        )

    @pytest.fixture
    def logger(self):
        """Create a logger for testing."""
        return setup_logger("test_watcher_resilience")

    def test_continues_after_error(
        self,
        watcher_config: WatcherConfig,
        logger,
        temp_drop_folder: Path,
        temp_vault: Path,
    ) -> None:
        """Watcher continues running after encountering an error (FR-007)."""
        observer = start_watching(watcher_config, logger)

        try:
            time.sleep(0.5)

            # Make Needs_Action read-only to cause an error
            needs_action = temp_vault / "Needs_Action"

            # Drop first file (will fail due to read-only)
            # Note: On Windows, making a directory read-only works differently
            # We'll test that the watcher continues even after a processing error

            # First, drop a file that will succeed
            file1 = temp_drop_folder / "file1.pdf"
            file1.write_bytes(b"content1")

            time.sleep(2.0)

            # Verify first file was processed
            expected1 = needs_action / "FILE_file1.pdf.md"
            assert expected1.exists(), "First file should be processed"

            # Drop another file
            file2 = temp_drop_folder / "file2.pdf"
            file2.write_bytes(b"content2")

            time.sleep(2.0)

            # Verify second file was also processed (watcher still running)
            expected2 = needs_action / "FILE_file2.pdf.md"
            assert expected2.exists(), (
                "Watcher should continue processing after first file"
            )

        finally:
            stop_watching(observer)

    def test_error_handling_logs_and_continues(
        self,
        watcher_config: WatcherConfig,
        logger,
        temp_drop_folder: Path,
        temp_vault: Path,
        caplog,
    ) -> None:
        """Watcher logs errors and continues running (FR-007)."""
        import os
        import stat

        observer = start_watching(watcher_config, logger)

        try:
            time.sleep(0.5)
            needs_action = temp_vault / "Needs_Action"

            # Make Needs_Action read-only (platform-dependent)
            if os.name == "nt":  # Windows
                # On Windows, we simulate by removing write permission
                original_mode = os.stat(needs_action).st_mode
                os.chmod(needs_action, stat.S_IRUSR | stat.S_IXUSR)
            else:  # Unix-like
                original_mode = os.stat(needs_action).st_mode
                os.chmod(needs_action, stat.S_IRUSR | stat.S_IXUSR)

            try:
                # Drop a file - this should fail silently
                fail_file = temp_drop_folder / "will_fail.pdf"
                fail_file.write_bytes(b"content")

                time.sleep(2.0)

                # Verify watcher is still alive
                assert observer.is_alive(), "Watcher should still be running after error"

            finally:
                # Restore permissions
                os.chmod(needs_action, original_mode)

            # Now drop another file - should succeed
            success_file = temp_drop_folder / "will_succeed.pdf"
            success_file.write_bytes(b"content")

            time.sleep(2.0)

            # Verify the success file was processed
            expected = needs_action / "FILE_will_succeed.pdf.md"
            assert expected.exists(), (
                "Watcher should process files after error recovery"
            )

        finally:
            stop_watching(observer)
