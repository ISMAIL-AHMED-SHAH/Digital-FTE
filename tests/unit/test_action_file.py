"""
Unit tests for file_watcher action file generation.
"""

import pytest
from pathlib import Path

from file_watcher.action_file import (
    ActionFile,
    generate_action_content,
    generate_action_filename,
    get_action_file_path,
)


class TestActionFile:
    """Tests for ActionFile dataclass."""

    def test_action_file_has_correct_defaults(self) -> None:
        """ActionFile has type='file_drop' and status='pending' by default."""
        action = ActionFile(
            original_name="test.pdf",
            size=1024,
            timestamp="2026-01-19T10:30:00Z",
            source_path="/path/to/test.pdf",
        )

        assert action.type == "file_drop"
        assert action.status == "pending"

    def test_action_file_stores_provided_values(self) -> None:
        """ActionFile stores provided values correctly."""
        action = ActionFile(
            original_name="report.docx",
            size=2048,
            timestamp="2026-01-19T15:45:30Z",
            source_path="C:/Users/test/report.docx",
        )

        assert action.original_name == "report.docx"
        assert action.size == 2048
        assert action.timestamp == "2026-01-19T15:45:30Z"
        assert action.source_path == "C:/Users/test/report.docx"

    def test_from_path_creates_action_file(self, sample_file: Path) -> None:
        """from_path creates ActionFile with correct metadata."""
        action = ActionFile.from_path(sample_file)

        assert action.original_name == sample_file.name
        assert action.size == sample_file.stat().st_size
        assert action.source_path == str(sample_file.resolve())
        assert action.type == "file_drop"
        assert action.status == "pending"
        # Timestamp should be ISO format
        assert "T" in action.timestamp
        assert action.timestamp.endswith("Z")

    def test_from_path_handles_empty_file(self, temp_drop_folder: Path) -> None:
        """from_path handles empty files (size=0)."""
        empty_file = temp_drop_folder / "empty.txt"
        empty_file.write_bytes(b"")

        action = ActionFile.from_path(empty_file)

        assert action.size == 0


class TestGenerateActionContent:
    """Tests for generate_action_content function."""

    def test_generates_yaml_frontmatter(self) -> None:
        """Generated content has YAML frontmatter."""
        action = ActionFile(
            original_name="test.pdf",
            size=1024,
            timestamp="2026-01-19T10:30:00Z",
            source_path="/path/to/test.pdf",
        )

        content = generate_action_content(action)

        assert content.startswith("---\n")
        assert "\n---\n" in content

    def test_contains_all_required_fields(self) -> None:
        """Generated content contains all required frontmatter fields."""
        action = ActionFile(
            original_name="test.pdf",
            size=1024,
            timestamp="2026-01-19T10:30:00Z",
            source_path="/path/to/test.pdf",
        )

        content = generate_action_content(action)

        assert "type: file_drop" in content
        assert "original_name: test.pdf" in content
        assert "size: 1024" in content
        assert "timestamp: '2026-01-19T10:30:00Z'" in content or "timestamp: 2026-01-19T10:30:00Z" in content
        assert "status: pending" in content
        assert "source_path:" in content

    def test_contains_markdown_body(self) -> None:
        """Generated content contains markdown body."""
        action = ActionFile(
            original_name="test.pdf",
            size=1024,
            timestamp="2026-01-19T10:30:00Z",
            source_path="/path/to/test.pdf",
        )

        content = generate_action_content(action)

        assert "## New File Dropped" in content
        assert "**File**: test.pdf" in content
        assert "New file dropped for processing." in content

    def test_handles_special_characters_in_filename(self) -> None:
        """Generated content handles special characters in filename."""
        action = ActionFile(
            original_name="My Report (Final) [v2].pdf",
            size=1024,
            timestamp="2026-01-19T10:30:00Z",
            source_path="/path/to/My Report (Final) [v2].pdf",
        )

        content = generate_action_content(action)

        # YAML should quote strings with special characters
        assert "My Report (Final) [v2].pdf" in content

    def test_handles_unicode_in_filename(self) -> None:
        """Generated content handles unicode in filename."""
        action = ActionFile(
            original_name="日本語ファイル.txt",
            size=512,
            timestamp="2026-01-19T10:30:00Z",
            source_path="/path/to/日本語ファイル.txt",
        )

        content = generate_action_content(action)

        assert "日本語ファイル.txt" in content

    def test_yaml_quotes_colon_in_filename(self) -> None:
        """YAML properly quotes filenames containing colons (FR-005)."""
        import yaml

        action = ActionFile(
            original_name="file: with colon.txt",
            size=1024,
            timestamp="2026-01-19T10:30:00Z",
            source_path="/path/to/file: with colon.txt",
        )

        content = generate_action_content(action)

        # Extract and parse YAML frontmatter
        parts = content.split("---")
        yaml_content = parts[1]
        parsed = yaml.safe_load(yaml_content)

        # Verify the colon is preserved correctly
        assert parsed["original_name"] == "file: with colon.txt"
        assert parsed["source_path"] == "/path/to/file: with colon.txt"

    def test_yaml_handles_backslash_in_path(self) -> None:
        """YAML properly handles Windows-style backslash paths (FR-005)."""
        import yaml

        action = ActionFile(
            original_name="report.pdf",
            size=1024,
            timestamp="2026-01-19T10:30:00Z",
            source_path="C:\\Users\\test\\Documents\\report.pdf",
        )

        content = generate_action_content(action)

        # Extract and parse YAML frontmatter
        parts = content.split("---")
        yaml_content = parts[1]
        parsed = yaml.safe_load(yaml_content)

        # Verify backslashes are preserved
        assert parsed["source_path"] == "C:\\Users\\test\\Documents\\report.pdf"

    def test_yaml_handles_quotes_in_filename(self) -> None:
        """YAML properly handles quotes in filenames (FR-005)."""
        import yaml

        action = ActionFile(
            original_name='Report "Final".pdf',
            size=1024,
            timestamp="2026-01-19T10:30:00Z",
            source_path='/path/to/Report "Final".pdf',
        )

        content = generate_action_content(action)

        # Extract and parse YAML frontmatter
        parts = content.split("---")
        yaml_content = parts[1]
        parsed = yaml.safe_load(yaml_content)

        # Verify quotes are preserved
        assert parsed["original_name"] == 'Report "Final".pdf'


class TestGenerateActionFilename:
    """Tests for generate_action_filename function."""

    def test_generates_file_prefix_pattern(self, temp_vault: Path) -> None:
        """Generated filename uses FILE_ prefix pattern."""
        filename = generate_action_filename(
            "test.pdf",
            temp_vault / "Needs_Action",
        )

        assert filename == "FILE_test.pdf.md"

    def test_preserves_original_extension(self, temp_vault: Path) -> None:
        """Generated filename preserves original file extension."""
        filename = generate_action_filename(
            "document.docx",
            temp_vault / "Needs_Action",
        )

        assert filename == "FILE_document.docx.md"

    def test_adds_timestamp_for_duplicate(self, temp_vault: Path) -> None:
        """Adds timestamp suffix when file already exists."""
        needs_action = temp_vault / "Needs_Action"
        # Create existing file
        existing = needs_action / "FILE_test.pdf.md"
        existing.write_text("existing content")

        filename = generate_action_filename(
            "test.pdf",
            needs_action,
            timestamp="2026-01-19T10:30:05Z",
        )

        assert filename == "FILE_test.pdf_20260119T103005.md"

    def test_no_timestamp_when_not_duplicate(self, temp_vault: Path) -> None:
        """No timestamp suffix when file doesn't exist."""
        filename = generate_action_filename(
            "unique.pdf",
            temp_vault / "Needs_Action",
        )

        assert "_202" not in filename  # No timestamp
        assert filename == "FILE_unique.pdf.md"

    def test_handles_spaces_in_filename(self, temp_vault: Path) -> None:
        """Handles spaces in original filename."""
        filename = generate_action_filename(
            "my report.pdf",
            temp_vault / "Needs_Action",
        )

        assert filename == "FILE_my report.pdf.md"

    def test_handles_special_chars_in_filename(self, temp_vault: Path) -> None:
        """Handles special characters in original filename."""
        filename = generate_action_filename(
            "Report (Final).pdf",
            temp_vault / "Needs_Action",
        )

        assert filename == "FILE_Report (Final).pdf.md"

    def test_multiple_consecutive_duplicates(self, temp_vault: Path) -> None:
        """Handles multiple consecutive duplicate files (FR-012)."""
        needs_action = temp_vault / "Needs_Action"

        # First file - no suffix
        filename1 = generate_action_filename("report.pdf", needs_action)
        assert filename1 == "FILE_report.pdf.md"
        (needs_action / filename1).write_text("content1")

        # Second file - timestamp suffix
        filename2 = generate_action_filename(
            "report.pdf", needs_action, timestamp="2026-01-19T10:30:01Z"
        )
        assert filename2 == "FILE_report.pdf_20260119T103001.md"
        (needs_action / filename2).write_text("content2")

        # Third file - different timestamp suffix
        filename3 = generate_action_filename(
            "report.pdf", needs_action, timestamp="2026-01-19T10:30:02Z"
        )
        assert filename3 == "FILE_report.pdf_20260119T103002.md"

        # Verify all files are unique
        assert len({filename1, filename2, filename3}) == 3

    def test_generates_timestamp_automatically_for_duplicate(
        self, temp_vault: Path
    ) -> None:
        """Generates timestamp automatically when duplicate exists and no timestamp provided (FR-012)."""
        needs_action = temp_vault / "Needs_Action"

        # Create existing file
        (needs_action / "FILE_auto.pdf.md").write_text("existing")

        # Request filename without timestamp - should auto-generate one
        filename = generate_action_filename("auto.pdf", needs_action)

        assert filename.startswith("FILE_auto.pdf_")
        assert filename.endswith(".md")
        # Should have timestamp in format YYYYMMDDTHHMMSS
        assert "T" in filename  # ISO timestamp separator

    def test_handles_unicode_in_filename(self, temp_vault: Path) -> None:
        """Handles unicode characters in filenames (FR-005)."""
        filename = generate_action_filename(
            "日本語ファイル.txt",
            temp_vault / "Needs_Action",
        )

        assert filename == "FILE_日本語ファイル.txt.md"


class TestGetActionFilePath:
    """Tests for get_action_file_path function."""

    def test_returns_full_path(self, temp_vault: Path) -> None:
        """Returns full path to action file."""
        action = ActionFile(
            original_name="test.pdf",
            size=1024,
            timestamp="2026-01-19T10:30:00Z",
            source_path="/path/to/test.pdf",
        )
        needs_action = temp_vault / "Needs_Action"

        path = get_action_file_path(action, needs_action)

        assert path.parent == needs_action
        assert path.name == "FILE_test.pdf.md"

    def test_handles_duplicate_path(self, temp_vault: Path) -> None:
        """Returns unique path when duplicate exists."""
        needs_action = temp_vault / "Needs_Action"
        # Create existing file
        existing = needs_action / "FILE_test.pdf.md"
        existing.write_text("existing content")

        action = ActionFile(
            original_name="test.pdf",
            size=1024,
            timestamp="2026-01-19T10:30:05Z",
            source_path="/path/to/test.pdf",
        )

        path = get_action_file_path(action, needs_action)

        assert path.parent == needs_action
        assert "20260119T103005" in path.name
