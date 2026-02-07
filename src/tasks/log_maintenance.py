"""Log Maintenance Task (T081 - FR-033, FR-035).

Scheduled task for log management:
- Compress logs older than 30 days
- Delete logs older than 90 days
- Generate maintenance report

Run via PM2 cron or manually:
    python -m src.tasks.log_maintenance

Environment:
    VAULT_PATH: Path to vault (default: ./vault)
    LOG_DIR: Log directory (default: ./logs)
    RETENTION_DAYS: Days to retain logs (default: 90)
    COMPRESSION_DAYS: Days before compression (default: 30)
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.common.audit_logger import AuditLogger

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_config() -> dict:
    """Load maintenance configuration from gold_tier.yaml."""
    config_path = project_root / "config" / "gold_tier.yaml"

    default_config = {
        "retention_days": int(os.environ.get("RETENTION_DAYS", 90)),
        "compression_after_days": int(os.environ.get("COMPRESSION_DAYS", 30)),
        "max_size_mb": 1024,
        "alert_threshold_percent": 80,
        "log_directory": os.environ.get("LOG_DIR", "Logs"),
    }

    if config_path.exists():
        try:
            import yaml
            with open(config_path) as f:
                full_config = yaml.safe_load(f)
                audit_config = full_config.get("audit", {})
                default_config.update({
                    "retention_days": audit_config.get("retention_days", default_config["retention_days"]),
                    "compression_after_days": audit_config.get("compression_after_days", default_config["compression_after_days"]),
                    "max_size_mb": audit_config.get("max_size_mb", default_config["max_size_mb"]),
                    "alert_threshold_percent": audit_config.get("alert_threshold_percent", default_config["alert_threshold_percent"]),
                })
        except ImportError:
            logger.warning("PyYAML not installed, using environment/defaults")
        except Exception as e:
            logger.warning(f"Error loading config: {e}")

    return default_config


def run_maintenance(
    vault_path: Path,
    config: dict,
    compress_now: bool = False
) -> dict:
    """Run log maintenance.

    Args:
        vault_path: Path to vault
        config: Configuration dict
        compress_now: Force compression regardless of age

    Returns:
        Maintenance report dict
    """
    audit_logger = AuditLogger(vault_path)

    logger.info("Starting log maintenance...")
    logger.info(f"  Retention: {config['retention_days']} days")
    logger.info(f"  Compression: {config['compression_after_days']} days")

    # Run maintenance
    compression_days = 0 if compress_now else config["compression_after_days"]

    report = audit_logger.run_maintenance(
        retention_days=config["retention_days"],
        compression_days=compression_days,
        max_size_bytes=config["max_size_mb"] * 1024 * 1024,
        alert_threshold=config["alert_threshold_percent"] / 100
    )

    # Log results
    logger.info(f"Maintenance complete:")
    logger.info(f"  Compressed: {len(report['compressed_files'])} files")
    logger.info(f"  Deleted: {len(report['deleted_files'])} files")
    logger.info(f"  Final size: {report['final_size_mb']} MB")

    if report["size_alert"]:
        logger.warning(f"SIZE ALERT: {report['size_alert']['usage_percent']}% of max")

    # Log the maintenance run itself
    audit_logger.log(
        component="log_maintenance",
        action_type="maintenance_run",
        parameters={
            "compressed_count": len(report["compressed_files"]),
            "deleted_count": len(report["deleted_files"]),
            "final_size_mb": report["final_size_mb"],
            "had_alert": report["size_alert"] is not None
        },
        result="success"
    )

    return report


def create_alert_if_needed(
    report: dict,
    vault_path: Path,
    config: dict
) -> Path | None:
    """Create alert file if size threshold exceeded.

    Args:
        report: Maintenance report
        vault_path: Path to vault
        config: Configuration dict

    Returns:
        Path to alert file or None
    """
    if not report["size_alert"]:
        return None

    alert_dir = vault_path / "Alerts"
    alert_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now()
    alert_name = f"log_size_{timestamp.strftime('%Y%m%d_%H%M%S')}.md"

    alert = report["size_alert"]

    content = f"""---
type: alert
category: system
severity: warning
created_at: {timestamp.isoformat()}
---

# Log Size Alert: Storage Threshold Exceeded

**Time:** {timestamp.strftime('%Y-%m-%d %H:%M:%S')}
**Severity:** Warning

## Issue

Log storage has exceeded {alert['threshold_percent']}% of the configured maximum size.

## Current Usage

| Metric | Value |
|--------|-------|
| Current Size | {alert['current_size_mb']} MB |
| Maximum Size | {alert['max_size_mb']} MB |
| Usage | {alert['usage_percent']}% |

## Maintenance Results

- **Compressed:** {len(report['compressed_files'])} files
- **Deleted:** {len(report['deleted_files'])} files
- **Final Size:** {report['final_size_mb']} MB

## Recommended Actions

1. Review log retention settings in `config/gold_tier.yaml`
2. Consider archiving old logs to external storage
3. Investigate if excessive logging is occurring

## Configuration

```yaml
audit:
  retention_days: {config['retention_days']}
  compression_after_days: {config['compression_after_days']}
  max_size_mb: {config['max_size_mb']}
  alert_threshold_percent: {config['alert_threshold_percent']}
```
"""

    alert_path = alert_dir / alert_name
    alert_path.write_text(content)

    logger.warning(f"Created size alert: {alert_path}")
    return alert_path


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Log Maintenance Task"
    )
    parser.add_argument(
        "--vault-path",
        type=Path,
        default=Path(os.environ.get("VAULT_PATH", "./vault")),
        help="Path to vault"
    )
    parser.add_argument(
        "--compress-now",
        action="store_true",
        help="Force compression of all logs"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without doing it"
    )
    parser.add_argument(
        "--output-json",
        action="store_true",
        help="Output report as JSON"
    )

    args = parser.parse_args()

    config = load_config()

    if args.dry_run:
        logger.info("DRY RUN - No changes will be made")
        audit_logger = AuditLogger(args.vault_path)

        # Just report current state
        size = audit_logger.get_log_size_bytes()
        alert = audit_logger.check_size_alert(
            config["max_size_mb"] * 1024 * 1024,
            config["alert_threshold_percent"] / 100
        )

        report = {
            "dry_run": True,
            "current_size_mb": round(size / (1024 * 1024), 2),
            "would_compress": [],
            "would_delete": [],
            "size_alert": alert
        }
    else:
        report = run_maintenance(args.vault_path, config, args.compress_now)
        create_alert_if_needed(report, args.vault_path, config)

    if args.output_json:
        print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
