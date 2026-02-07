"""Watcher Configuration Module for Silver Tier.

Extends Bronze Tier configuration pattern with settings for
external service watchers, rate limits, and memory budgets.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()


@dataclass
class GlobalConfig:
    """Global configuration for all watchers."""
    total_memory_budget_mb: int = 500
    memory_alert_threshold_percent: int = 80
    memory_recovery_threshold_percent: int = 70
    resource_check_interval_seconds: int = 60
    idempotency_retention_days: int = 7
    approval_expiration_hours: int = 24


@dataclass
class GmailConfig:
    """Gmail watcher configuration."""
    enabled: bool = True
    priority: int = 1
    memory_limit_mb: int = 100
    poll_interval_seconds: int = 120
    keywords: list[str] = field(default_factory=lambda: [
        "urgent", "important", "invoice", "payment", "deadline"
    ])
    labels: list[str] = field(default_factory=lambda: ["INBOX", "IMPORTANT"])
    max_emails_per_poll: int = 10
    send_rate_limit_per_day: int = 50


@dataclass
class WhatsAppConfig:
    """WhatsApp watcher configuration."""
    enabled: bool = True
    priority: int = 2
    memory_limit_mb: int = 100
    keywords: list[str] = field(default_factory=lambda: [
        "invoice", "pricing", "quote", "order", "support"
    ])
    webhook_rate_limit_per_minute: int = 100
    webhook_response_timeout_ms: int = 500


@dataclass
class LinkedInConfig:
    """LinkedIn watcher/MCP configuration."""
    enabled: bool = True
    priority: int = 3
    memory_limit_mb: int = 100
    post_rate_limit_per_day: int = 10
    max_post_length: int = 3000
    default_visibility: str = "PUBLIC"


@dataclass
class ApprovalConfig:
    """Approval watcher configuration."""
    enabled: bool = True
    priority: int = 1
    memory_limit_mb: int = 50
    expiration_check_interval_seconds: int = 300
    folders: dict[str, str] = field(default_factory=lambda: {
        "needs_action": "Needs_Action",
        "pending_approval": "Pending_Approval",
        "approved": "Approved",
        "rejected": "Rejected",
        "expired": "Expired",
        "done": "Done",
        "logs": "Logs",
        "alerts": "Alerts"
    })


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = "INFO"
    format: str = "json"
    retention_days: int = 90
    include_traceback: bool = True


@dataclass
class RetryConfig:
    """Retry configuration."""
    initial_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    max_retries: int = 5
    backoff_multiplier: float = 2.0


@dataclass
class WatcherConfig:
    """Complete watcher configuration."""
    vault_path: Path
    dry_run: bool = False
    dev_mode: bool = False
    idempotency_db_path: Path = field(default_factory=lambda: Path("data/idempotency.db"))

    # Component configs
    global_config: GlobalConfig = field(default_factory=GlobalConfig)
    gmail: GmailConfig = field(default_factory=GmailConfig)
    whatsapp: WhatsAppConfig = field(default_factory=WhatsAppConfig)
    linkedin: LinkedInConfig = field(default_factory=LinkedInConfig)
    approval: ApprovalConfig = field(default_factory=ApprovalConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    retry: RetryConfig = field(default_factory=RetryConfig)

    def get_vault_folder(self, folder_key: str) -> Path:
        """Get absolute path to a vault folder.

        Args:
            folder_key: Key from approval.folders (e.g., "needs_action")

        Returns:
            Absolute path to the folder
        """
        folder_name = self.approval.folders.get(folder_key, folder_key)
        return self.vault_path / folder_name


def _merge_dict(base: dict, override: dict) -> dict:
    """Deep merge two dictionaries."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _merge_dict(result[key], value)
        else:
            result[key] = value
    return result


def _dataclass_from_dict(cls, data: dict):
    """Create a dataclass instance from a dictionary."""
    if data is None:
        return cls()

    # Get field names and their types
    import dataclasses
    field_names = {f.name for f in dataclasses.fields(cls)}

    # Filter to only known fields
    filtered_data = {k: v for k, v in data.items() if k in field_names}

    return cls(**filtered_data)


def load_config(
    config_path: str | Path | None = None,
    vault_path: str | Path | None = None
) -> WatcherConfig:
    """Load watcher configuration from YAML file and environment.

    Priority (highest to lowest):
    1. Environment variables (VAULT_PATH, DRY_RUN, etc.)
    2. Config file values
    3. Default values

    Args:
        config_path: Path to watcher_config.yaml (default: config/watcher_config.yaml)
        vault_path: Override vault path (default: from env or config)

    Returns:
        Complete WatcherConfig object
    """
    # Determine config file path
    if config_path is None:
        config_path = Path("config/watcher_config.yaml")
    else:
        config_path = Path(config_path)

    # Load YAML config if exists
    yaml_config: dict[str, Any] = {}
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            yaml_config = yaml.safe_load(f) or {}

    # Determine vault path (env > arg > config > default)
    if vault_path is None:
        vault_path = os.environ.get("VAULT_PATH")
    if vault_path is None:
        vault_path = yaml_config.get("vault_path", ".")
    vault_path = Path(vault_path).expanduser().resolve()

    # Determine dry_run mode
    dry_run = os.environ.get("DRY_RUN", "").lower() == "true"
    if not dry_run:
        dry_run = yaml_config.get("dry_run", False)

    # Determine dev_mode
    dev_mode = os.environ.get("DEV_MODE", "").lower() == "true"
    if not dev_mode:
        dev_mode = yaml_config.get("dev_mode", False)

    # Idempotency DB path
    db_path = os.environ.get("IDEMPOTENCY_DB_PATH", yaml_config.get("idempotency_db_path", "data/idempotency.db"))

    # Build config object
    config = WatcherConfig(
        vault_path=vault_path,
        dry_run=dry_run,
        dev_mode=dev_mode,
        idempotency_db_path=Path(db_path),
        global_config=_dataclass_from_dict(GlobalConfig, yaml_config.get("global")),
        gmail=_dataclass_from_dict(GmailConfig, yaml_config.get("gmail")),
        whatsapp=_dataclass_from_dict(WhatsAppConfig, yaml_config.get("whatsapp")),
        linkedin=_dataclass_from_dict(LinkedInConfig, yaml_config.get("linkedin")),
        approval=_dataclass_from_dict(ApprovalConfig, yaml_config.get("approval")),
        logging=_dataclass_from_dict(LoggingConfig, yaml_config.get("logging")),
        retry=_dataclass_from_dict(RetryConfig, yaml_config.get("retry"))
    )

    # Apply dev mode overrides
    if dev_mode:
        config.gmail.poll_interval_seconds = 30  # Faster polling in dev
        config.logging.level = "DEBUG"

    return config


# Module-level default config (lazy loaded)
_default_config: WatcherConfig | None = None


def get_config() -> WatcherConfig:
    """Get the default configuration instance."""
    global _default_config
    if _default_config is None:
        _default_config = load_config()
    return _default_config


def reset_config() -> None:
    """Reset the default configuration (for testing)."""
    global _default_config
    _default_config = None
