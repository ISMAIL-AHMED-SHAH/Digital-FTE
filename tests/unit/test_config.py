"""
Unit tests for file_watcher configuration and CLI argument parsing.
"""

import pytest
from pathlib import Path

from file_watcher.config import (
    WatcherConfig,
    ConfigurationError,
    ValidationError,
    create_argument_parser,
    parse_args,
    validate_config,
    load_config,
)


class TestWatcherConfig:
    """Tests for WatcherConfig dataclass."""

    def test_config_creates_needs_action_path(self, tmp_path: Path) -> None:
        """needs_action_path is derived from vault_path."""
        vault = tmp_path / "vault"
        drop = tmp_path / "drop"

        config = WatcherConfig(vault_path=vault, drop_folder=drop)

        assert config.needs_action_path == vault / "Needs_Action"

    def test_config_dry_run_default_false(self, tmp_path: Path) -> None:
        """dry_run defaults to False."""
        config = WatcherConfig(
            vault_path=tmp_path / "vault",
            drop_folder=tmp_path / "drop",
        )

        assert config.dry_run is False

    def test_config_dry_run_can_be_true(self, tmp_path: Path) -> None:
        """dry_run can be set to True."""
        config = WatcherConfig(
            vault_path=tmp_path / "vault",
            drop_folder=tmp_path / "drop",
            dry_run=True,
        )

        assert config.dry_run is True


class TestArgumentParsing:
    """Tests for CLI argument parsing."""

    def test_parse_required_args(self, tmp_path: Path) -> None:
        """Parses --vault and --drop-folder correctly."""
        vault = tmp_path / "vault"
        drop = tmp_path / "drop"

        config = parse_args([
            "--vault", str(vault),
            "--drop-folder", str(drop),
        ])

        assert config.vault_path == vault.resolve()
        assert config.drop_folder == drop.resolve()
        assert config.dry_run is False

    def test_parse_dry_run_flag(self, tmp_path: Path) -> None:
        """Parses --dry-run flag."""
        vault = tmp_path / "vault"
        drop = tmp_path / "drop"

        config = parse_args([
            "--vault", str(vault),
            "--drop-folder", str(drop),
            "--dry-run",
        ])

        assert config.dry_run is True

    def test_missing_vault_raises_system_exit(self, tmp_path: Path) -> None:
        """Missing --vault argument causes SystemExit."""
        drop = tmp_path / "drop"

        with pytest.raises(SystemExit):
            parse_args(["--drop-folder", str(drop)])

    def test_missing_drop_folder_raises_system_exit(self, tmp_path: Path) -> None:
        """Missing --drop-folder argument causes SystemExit."""
        vault = tmp_path / "vault"

        with pytest.raises(SystemExit):
            parse_args(["--vault", str(vault)])

    def test_help_flag_exits(self) -> None:
        """--help causes SystemExit with code 0."""
        with pytest.raises(SystemExit) as exc_info:
            parse_args(["--help"])

        assert exc_info.value.code == 0

    def test_version_flag_exits(self) -> None:
        """--version causes SystemExit with code 0."""
        with pytest.raises(SystemExit) as exc_info:
            parse_args(["--version"])

        assert exc_info.value.code == 0

    def test_paths_are_resolved(self, tmp_path: Path) -> None:
        """Paths are converted to absolute paths."""
        vault = tmp_path / "vault"
        drop = tmp_path / "drop"

        config = parse_args([
            "--vault", str(vault),
            "--drop-folder", str(drop),
        ])

        assert config.vault_path.is_absolute()
        assert config.drop_folder.is_absolute()


class TestPathValidation:
    """Tests for path validation logic."""

    def test_valid_config_passes(self, temp_vault: Path, temp_drop_folder: Path) -> None:
        """Valid configuration passes validation."""
        config = WatcherConfig(
            vault_path=temp_vault,
            drop_folder=temp_drop_folder,
        )

        # Should not raise
        validate_config(config)

    def test_vault_not_exists_raises(self, tmp_path: Path, temp_drop_folder: Path) -> None:
        """Non-existent vault path raises ValidationError."""
        config = WatcherConfig(
            vault_path=tmp_path / "nonexistent",
            drop_folder=temp_drop_folder,
        )

        with pytest.raises(ValidationError) as exc_info:
            validate_config(config)

        assert "Vault path does not exist" in str(exc_info.value)

    def test_drop_folder_not_exists_raises(self, temp_vault: Path, tmp_path: Path) -> None:
        """Non-existent drop folder raises ValidationError."""
        config = WatcherConfig(
            vault_path=temp_vault,
            drop_folder=tmp_path / "nonexistent",
        )

        with pytest.raises(ValidationError) as exc_info:
            validate_config(config)

        assert "Drop folder does not exist" in str(exc_info.value)

    def test_vault_is_file_raises(self, temp_drop_folder: Path, tmp_path: Path) -> None:
        """Vault path that is a file raises ValidationError."""
        vault_file = tmp_path / "vault_file"
        vault_file.write_text("not a directory")

        config = WatcherConfig(
            vault_path=vault_file,
            drop_folder=temp_drop_folder,
        )

        with pytest.raises(ValidationError) as exc_info:
            validate_config(config)

        assert "not a directory" in str(exc_info.value)

    def test_drop_folder_is_file_raises(self, temp_vault: Path, tmp_path: Path) -> None:
        """Drop folder that is a file raises ValidationError."""
        drop_file = tmp_path / "drop_file"
        drop_file.write_text("not a directory")

        config = WatcherConfig(
            vault_path=temp_vault,
            drop_folder=drop_file,
        )

        with pytest.raises(ValidationError) as exc_info:
            validate_config(config)

        assert "not a directory" in str(exc_info.value)

    def test_same_path_raises(self, temp_vault: Path) -> None:
        """Same path for vault and drop folder raises ValidationError."""
        config = WatcherConfig(
            vault_path=temp_vault,
            drop_folder=temp_vault,
        )

        with pytest.raises(ValidationError) as exc_info:
            validate_config(config)

        assert "cannot be the same path" in str(exc_info.value)

    def test_needs_action_not_exists_raises(self, tmp_path: Path, temp_drop_folder: Path) -> None:
        """Missing Needs_Action folder raises ValidationError."""
        vault = tmp_path / "vault_no_needs_action"
        vault.mkdir()  # Create vault but not Needs_Action

        config = WatcherConfig(
            vault_path=vault,
            drop_folder=temp_drop_folder,
        )

        with pytest.raises(ValidationError) as exc_info:
            validate_config(config)

        assert "Needs_Action folder not found" in str(exc_info.value)


class TestLoadConfig:
    """Tests for the combined load_config function."""

    def test_load_valid_config(self, temp_vault: Path, temp_drop_folder: Path) -> None:
        """load_config returns validated WatcherConfig."""
        config = load_config([
            "--vault", str(temp_vault),
            "--drop-folder", str(temp_drop_folder),
        ])

        assert config.vault_path == temp_vault.resolve()
        assert config.drop_folder == temp_drop_folder.resolve()

    def test_missing_args_exits_1(self, temp_vault: Path) -> None:
        """Missing required argument exits with code 1."""
        with pytest.raises(SystemExit) as exc_info:
            load_config(["--vault", str(temp_vault)])

        assert exc_info.value.code == 1

    def test_invalid_vault_exits_2(self, tmp_path: Path, temp_drop_folder: Path) -> None:
        """Invalid vault path exits with code 2."""
        with pytest.raises(SystemExit) as exc_info:
            load_config([
                "--vault", str(tmp_path / "nonexistent"),
                "--drop-folder", str(temp_drop_folder),
            ])

        assert exc_info.value.code == 2

    def test_invalid_drop_folder_exits_2(self, temp_vault: Path, tmp_path: Path) -> None:
        """Invalid drop folder exits with code 2."""
        with pytest.raises(SystemExit) as exc_info:
            load_config([
                "--vault", str(temp_vault),
                "--drop-folder", str(tmp_path / "nonexistent"),
            ])

        assert exc_info.value.code == 2

    def test_same_path_exits_2(self, temp_vault: Path) -> None:
        """Same vault and drop folder exits with code 2."""
        with pytest.raises(SystemExit) as exc_info:
            load_config([
                "--vault", str(temp_vault),
                "--drop-folder", str(temp_vault),
            ])

        assert exc_info.value.code == 2
