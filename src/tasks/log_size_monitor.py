"""Log Size Monitor (T082 - FR-036).

Monitors log directory size and generates alerts at 80% threshold.

Can be run as:
- Scheduled task via PM2/cron
- Manual check
- Called from other modules

Environment:
    VAULT_PATH: Path to vault (default: ./vault)
    MAX_SIZE_MB: Maximum log size in MB (default: 1024)
    ALERT_THRESHOLD: Alert threshold percentage (default: 80)
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.common.audit_logger import AuditLogger

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_config() -> dict:
    """Load monitor configuration."""
    config_path = project_root / "config" / "gold_tier.yaml"

    default_config = {
        "max_size_mb": int(os.environ.get("MAX_SIZE_MB", 1024)),
        "alert_threshold_percent": int(os.environ.get("ALERT_THRESHOLD", 80)),
    }

    if config_path.exists():
        try:
            import yaml
            with open(config_path) as f:
                full_config = yaml.safe_load(f)
                audit_config = full_config.get("audit", {})
                default_config.update({
                    "max_size_mb": audit_config.get("max_size_mb", default_config["max_size_mb"]),
                    "alert_threshold_percent": audit_config.get("alert_threshold_percent", default_config["alert_threshold_percent"]),
                })
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"Error loading config: {e}")

    return default_config


def get_log_files_info(logs_dir: Path) -> list[dict]:
    """Get information about log files.

    Args:
        logs_dir: Path to logs directory

    Returns:
        List of file info dicts sorted by size (largest first)
    """
    files = []

    if not logs_dir.exists():
        return files

    for pattern in ["*.json", "*.json.gz"]:
        for path in logs_dir.glob(pattern):
            if not path.is_file():
                continue

            stat = path.stat()
            files.append({
                "name": path.name,
                "path": str(path),
                "size_bytes": stat.st_size,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "is_compressed": path.suffix == ".gz"
            })

    # Sort by size descending
    files.sort(key=lambda x: x["size_bytes"], reverse=True)
    return files


def check_log_size(
    vault_path: Path,
    max_size_mb: int = 1024,
    alert_threshold_percent: int = 80
) -> dict:
    """Check log directory size against threshold.

    Args:
        vault_path: Path to vault
        max_size_mb: Maximum allowed size in MB
        alert_threshold_percent: Percentage threshold for alerting

    Returns:
        Status dict with size info and alert if applicable
    """
    audit_logger = AuditLogger(vault_path)
    logs_dir = vault_path / "Logs"

    current_size = audit_logger.get_log_size_bytes()
    max_size_bytes = max_size_mb * 1024 * 1024
    threshold_bytes = int(max_size_bytes * (alert_threshold_percent / 100))

    usage_percent = round((current_size / max_size_bytes) * 100, 2) if max_size_bytes > 0 else 0

    status = {
        "timestamp": datetime.now().isoformat(),
        "current_size_bytes": current_size,
        "current_size_mb": round(current_size / (1024 * 1024), 2),
        "max_size_mb": max_size_mb,
        "threshold_percent": alert_threshold_percent,
        "usage_percent": usage_percent,
        "is_alert": current_size >= threshold_bytes,
        "files": get_log_files_info(logs_dir)[:10],  # Top 10 largest
    }

    # Estimate days until full
    if len(status["files"]) > 0:
        # Rough estimate based on average daily log size
        avg_daily_size = current_size / max(len(status["files"]), 1)
        remaining_bytes = max_size_bytes - current_size
        if avg_daily_size > 0 and remaining_bytes > 0:
            status["days_until_full"] = int(remaining_bytes / avg_daily_size)
        else:
            status["days_until_full"] = None
    else:
        status["days_until_full"] = None

    return status


def create_size_alert(
    status: dict,
    vault_path: Path,
    config: dict
) -> Optional[Path]:
    """Create an alert file for size threshold.

    Args:
        status: Status dict from check_log_size
        vault_path: Path to vault
        config: Configuration dict

    Returns:
        Path to alert file or None
    """
    if not status["is_alert"]:
        return None

    alert_dir = vault_path / "Alerts"
    alert_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now()
    alert_name = f"log_size_monitor_{timestamp.strftime('%Y%m%d_%H%M%S')}.md"

    # Format large files table
    files_table = "| File | Size (MB) | Modified |\n|------|-----------|----------|\n"
    for f in status["files"][:5]:
        files_table += f"| {f['name']} | {f['size_mb']} | {f['modified'][:10]} |\n"

    content = f"""---
type: alert
category: system
severity: warning
created_at: {timestamp.isoformat()}
---

# Log Size Monitor Alert

**Time:** {timestamp.strftime('%Y-%m-%d %H:%M:%S')}

## Status

Log storage has exceeded the {status['threshold_percent']}% threshold.

| Metric | Value |
|--------|-------|
| Current Size | {status['current_size_mb']} MB |
| Maximum Size | {status['max_size_mb']} MB |
| Usage | {status['usage_percent']}% |
| Days Until Full | ~{status.get('days_until_full', 'N/A')} |

## Largest Log Files

{files_table}

## Recommended Actions

1. Run log maintenance manually:
   ```bash
   python -m src.tasks.log_maintenance --compress-now
   ```

2. Archive old logs to external storage

3. Review retention settings:
   - Current retention: Check `config/gold_tier.yaml`
   - Consider reducing if not needed

4. Investigate excessive logging sources

## Configuration

- Max Size: {config['max_size_mb']} MB
- Alert Threshold: {config['alert_threshold_percent']}%
"""

    alert_path = alert_dir / alert_name
    alert_path.write_text(content)

    logger.warning(f"Created log size alert: {alert_path}")
    return alert_path


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Log Size Monitor"
    )
    parser.add_argument(
        "--vault-path",
        type=Path,
        default=Path(os.environ.get("VAULT_PATH", "./vault")),
        help="Path to vault"
    )
    parser.add_argument(
        "--output-json",
        action="store_true",
        help="Output status as JSON"
    )
    parser.add_argument(
        "--create-alert",
        action="store_true",
        help="Create alert file if threshold exceeded"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only output if alert condition"
    )

    args = parser.parse_args()

    config = load_config()

    status = check_log_size(
        args.vault_path,
        config["max_size_mb"],
        config["alert_threshold_percent"]
    )

    if args.quiet and not status["is_alert"]:
        sys.exit(0)

    if args.output_json:
        print(json.dumps(status, indent=2, default=str))
    else:
        print(f"Log Size Monitor Status")
        print(f"=======================")
        print(f"Current Size: {status['current_size_mb']} MB / {status['max_size_mb']} MB ({status['usage_percent']}%)")
        print(f"Alert Status: {'⚠️  ALERT' if status['is_alert'] else '✅ OK'}")

        if status.get("days_until_full"):
            print(f"Est. Days Until Full: {status['days_until_full']}")

        if status["files"]:
            print(f"\nTop 5 Largest Files:")
            for f in status["files"][:5]:
                print(f"  {f['name']}: {f['size_mb']} MB")

    if args.create_alert and status["is_alert"]:
        create_size_alert(status, args.vault_path, config)

    # Exit with error code if alert
    sys.exit(1 if status["is_alert"] else 0)


if __name__ == "__main__":
    main()
