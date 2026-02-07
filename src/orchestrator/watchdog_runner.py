"""Watchdog Runner - Entry point for PM2 managed watchdog (T077).

This module provides the main entry point for the watchdog process
when managed by PM2 via ecosystem.config.js.

Usage:
    python -m src.orchestrator.watchdog_runner

Environment:
    LOG_DIR: Directory for log files
    CONFIG_PATH: Path to gold_tier.yaml (optional)
"""

import asyncio
import logging
import os
import signal
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.orchestrator.watchdog import Watchdog, ProcessConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)

logger = logging.getLogger(__name__)


def load_config() -> dict:
    """Load watchdog configuration from gold_tier.yaml."""
    config_path = Path(os.environ.get(
        "CONFIG_PATH",
        project_root / "config" / "gold_tier.yaml"
    ))

    default_config = {
        "check_interval_seconds": 30,
        "state_dir": str(project_root / "data" / "watchdog"),
        "alert_directory": str(project_root / "vault" / "Alerts"),
        "monitored_processes": [
            {
                "name": "file-watcher",
                "command": "pm2 describe file-watcher",
                "restart_on_crash": True,
                "max_restarts": 5,
                "restart_cooldown_seconds": 60
            },
            {
                "name": "action-queue",
                "command": "pm2 describe action-queue",
                "restart_on_crash": True,
                "max_restarts": 5,
                "restart_cooldown_seconds": 60
            }
        ]
    }

    if config_path.exists():
        try:
            import yaml
            with open(config_path) as f:
                full_config = yaml.safe_load(f)
                watchdog_config = full_config.get("watchdog", {})
                default_config.update({
                    "check_interval_seconds": watchdog_config.get(
                        "check_interval_seconds",
                        default_config["check_interval_seconds"]
                    ),
                    "monitored_processes": watchdog_config.get(
                        "monitored_processes",
                        default_config["monitored_processes"]
                    )
                })
        except ImportError:
            logger.warning("PyYAML not installed, using default config")
        except Exception as e:
            logger.warning(f"Error loading config: {e}, using defaults")

    return default_config


async def main():
    """Main watchdog runner."""
    logger.info("Starting Watchdog Runner...")

    config = load_config()

    # Initialize watchdog
    watchdog = Watchdog(
        state_dir=Path(config["state_dir"]),
        check_interval=config["check_interval_seconds"],
        alert_directory=Path(config["alert_directory"]),
        use_pm2=True
    )

    # Register monitored processes
    for proc in config["monitored_processes"]:
        watchdog.register_process(ProcessConfig(
            name=proc["name"],
            command=proc.get("command", ""),
            restart_on_crash=proc.get("restart_on_crash", True),
            max_restarts=proc.get("max_restarts", 5),
            restart_cooldown=proc.get("restart_cooldown_seconds", 60)
        ))

    # Load any persisted state
    watchdog.load_state()

    # Setup signal handlers for graceful shutdown
    shutdown_event = asyncio.Event()

    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, shutting down...")
        shutdown_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info(
        f"Watchdog started. Monitoring {len(config['monitored_processes'])} processes. "
        f"Check interval: {config['check_interval_seconds']}s"
    )

    # Main monitoring loop
    try:
        while not shutdown_event.is_set():
            try:
                # Run health check
                crashed = await watchdog.check_processes()

                if crashed:
                    logger.warning(f"Detected crashed processes: {crashed}")

                # Wait for next check or shutdown
                try:
                    await asyncio.wait_for(
                        shutdown_event.wait(),
                        timeout=config["check_interval_seconds"]
                    )
                except asyncio.TimeoutError:
                    pass  # Normal timeout, continue loop

            except Exception as e:
                logger.error(f"Error in watchdog loop: {e}")
                await asyncio.sleep(5)  # Brief pause before retry

    finally:
        # Save state on shutdown
        watchdog.save_state()
        logger.info("Watchdog shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
