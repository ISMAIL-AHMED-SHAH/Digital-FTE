"""
Entry point for running file_watcher as a module.

Usage: python -m file_watcher [OPTIONS]
"""

from __future__ import annotations

import signal
import sys
import time
from typing import NoReturn

from .config import load_config
from .logger import get_logger, log_shutdown, log_startup
from .watcher import start_watching, stop_watching


def main() -> int:
    """
    Main entry point for the file watcher service.

    Returns:
        Exit code: 0 for clean shutdown, 1 for config error, 2 for validation error.
    """
    # Parse and validate configuration (exits on error)
    config = load_config()

    # Set up logging
    logger = get_logger()

    # Log startup
    log_startup(
        logger,
        str(config.vault_path),
        str(config.drop_folder),
        config.dry_run,
    )

    # Start watching
    observer = start_watching(config, logger)

    # Track shutdown reason
    shutdown_reason = "unknown"

    def handle_signal(signum: int, frame: object) -> NoReturn:
        """Handle shutdown signals."""
        nonlocal shutdown_reason
        sig_name = signal.Signals(signum).name
        shutdown_reason = f"{sig_name} received"
        raise SystemExit(0)

    # Set up signal handlers
    signal.signal(signal.SIGINT, handle_signal)
    # SIGTERM not available on Windows, but we handle it where possible
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, handle_signal)

    try:
        # Run until interrupted
        while observer.is_alive():
            time.sleep(1)
    except SystemExit:
        pass
    except KeyboardInterrupt:
        shutdown_reason = "keyboard interrupt"
    finally:
        # Stop watcher gracefully
        stop_watching(observer)

        # Log shutdown
        log_shutdown(logger, shutdown_reason)

    return 0


if __name__ == "__main__":
    sys.exit(main())
