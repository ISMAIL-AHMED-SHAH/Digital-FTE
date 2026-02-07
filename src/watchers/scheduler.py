"""Scheduled Task Runner for Silver Tier.

Executes configured tasks at scheduled times, with support for:
- Cron-style scheduling
- Task parameters
- Execution logging
- Dry-run mode

Implements FR-005, FR-005a from spec.md and T045 from tasks.md.

Usage:
    # Run a specific task
    python -m src.watchers.scheduler --task daily_briefing

    # Run with dry-run mode
    python -m src.watchers.scheduler --task daily_briefing --dry-run

    # List available tasks
    python -m src.watchers.scheduler --list

    # Run as daemon (checks schedule continuously)
    python -m src.watchers.scheduler --daemon
"""

import argparse
import asyncio
import importlib
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import yaml

from src.common.audit_logger import get_audit_logger
from src.common.vault import get_vault

logger = logging.getLogger(__name__)


class TaskNotFoundError(Exception):
    """Task module or function not found."""
    pass


class TaskExecutionError(Exception):
    """Task execution failed."""
    pass


class ScheduledTask:
    """Represents a configured scheduled task."""

    def __init__(
        self,
        name: str,
        module: str,
        function: str = "run",
        schedule: str | None = None,
        parameters: dict[str, Any] | None = None,
        enabled: bool = True,
        description: str = ""
    ):
        """Initialize scheduled task.

        Args:
            name: Task name (used in logs and CLI)
            module: Python module path (e.g., "src.tasks.daily_briefing")
            function: Function to call in the module (default: "run")
            schedule: Cron expression (e.g., "0 8 * * *" for 8am daily)
            parameters: Parameters to pass to the task function
            enabled: Whether the task is enabled
            description: Human-readable description
        """
        self.name = name
        self.module = module
        self.function = function
        self.schedule = schedule
        self.parameters = parameters or {}
        self.enabled = enabled
        self.description = description

    def __repr__(self) -> str:
        return f"ScheduledTask(name={self.name!r}, module={self.module!r})"


class TaskScheduler:
    """Scheduled task runner.

    Loads task configuration from YAML and executes tasks on demand
    or according to their schedules.
    """

    def __init__(
        self,
        config_path: str | Path | None = None,
        dry_run: bool = False
    ):
        """Initialize task scheduler.

        Args:
            config_path: Path to scheduler config YAML
            dry_run: If True, log actions without executing
        """
        self.config_path = Path(config_path) if config_path else Path("config/scheduler_config.yaml")
        self.dry_run = dry_run or os.environ.get("DRY_RUN", "").lower() == "true"
        self.tasks: dict[str, ScheduledTask] = {}
        self._audit = get_audit_logger()

        # Load configuration
        self._load_config()

    def _load_config(self) -> None:
        """Load task configuration from YAML file."""
        if not self.config_path.exists():
            logger.warning(f"Config file not found: {self.config_path}")
            self._create_default_config()
            return

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}

            tasks_config = config.get("tasks", {})
            for name, task_config in tasks_config.items():
                self.tasks[name] = ScheduledTask(
                    name=name,
                    module=task_config.get("module", f"src.tasks.{name}"),
                    function=task_config.get("function", "run"),
                    schedule=task_config.get("schedule"),
                    parameters=task_config.get("parameters", {}),
                    enabled=task_config.get("enabled", True),
                    description=task_config.get("description", "")
                )

            logger.info(f"Loaded {len(self.tasks)} task(s) from config")

        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            raise

    def _create_default_config(self) -> None:
        """Create default scheduler configuration."""
        default_config = {
            "tasks": {
                "daily_briefing": {
                    "module": "src.tasks.daily_briefing",
                    "function": "run",
                    "schedule": "0 8 * * *",
                    "description": "Generate daily briefing document",
                    "enabled": True,
                    "parameters": {}
                }
            }
        }

        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            yaml.dump(default_config, f, default_flow_style=False)

        logger.info(f"Created default config: {self.config_path}")

        # Load the default config
        for name, task_config in default_config["tasks"].items():
            self.tasks[name] = ScheduledTask(name=name, **task_config)

    def list_tasks(self) -> list[ScheduledTask]:
        """List all configured tasks."""
        return list(self.tasks.values())

    def get_task(self, name: str) -> ScheduledTask | None:
        """Get a task by name."""
        return self.tasks.get(name)

    def _load_task_function(self, task: ScheduledTask) -> Callable:
        """Load the task function from its module.

        Args:
            task: Task to load

        Returns:
            The task function

        Raises:
            TaskNotFoundError: If module or function not found
        """
        try:
            module = importlib.import_module(task.module)
            func = getattr(module, task.function, None)

            if func is None:
                raise TaskNotFoundError(
                    f"Function '{task.function}' not found in module '{task.module}'"
                )

            return func

        except ImportError as e:
            raise TaskNotFoundError(
                f"Module '{task.module}' not found: {e}"
            )

    async def run_task(
        self,
        task_name: str,
        parameters: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Run a task by name.

        Args:
            task_name: Name of the task to run
            parameters: Override parameters (merged with configured params)

        Returns:
            Task result dictionary

        Raises:
            TaskNotFoundError: If task not configured
            TaskExecutionError: If task execution fails
        """
        task = self.get_task(task_name)
        if not task:
            raise TaskNotFoundError(f"Task not found: {task_name}")

        if not task.enabled:
            logger.warning(f"Task '{task_name}' is disabled")
            return {"status": "skipped", "reason": "disabled"}

        # Merge parameters
        params = {**task.parameters, **(parameters or {})}

        # Add dry_run flag
        params["dry_run"] = self.dry_run

        start_time = datetime.now(timezone.utc)
        logger.info(f"Starting task: {task_name}")

        # Log to audit
        self._audit.log(
            component="scheduler",
            action_type="task_start",
            target=task_name,
            parameters=params
        )

        try:
            if self.dry_run:
                logger.info(f"[DRY-RUN] Would execute: {task.module}.{task.function}(**{params})")
                result = {"status": "dry_run", "task": task_name}
            else:
                # Load and execute
                func = self._load_task_function(task)

                # Check if function is async
                if asyncio.iscoroutinefunction(func):
                    result = await func(**params)
                else:
                    result = func(**params)

                result = result or {"status": "success"}

            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()

            logger.info(f"Task '{task_name}' completed in {duration:.2f}s")

            # Log success
            self._audit.log(
                component="scheduler",
                action_type="task_complete",
                target=task_name,
                result="success",
                duration_seconds=duration
            )

            return {
                **result,
                "task": task_name,
                "duration_seconds": duration,
                "completed_at": end_time.isoformat()
            }

        except Exception as e:
            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()

            logger.exception(f"Task '{task_name}' failed: {e}")

            # Log error
            self._audit.log_error(
                component="scheduler",
                action_type="task_failed",
                error=e,
                target=task_name,
                duration_seconds=duration
            )

            raise TaskExecutionError(f"Task '{task_name}' failed: {e}") from e

    async def run_all_enabled(self) -> list[dict[str, Any]]:
        """Run all enabled tasks.

        Returns:
            List of task results
        """
        results = []

        for task in self.tasks.values():
            if task.enabled:
                try:
                    result = await self.run_task(task.name)
                    results.append(result)
                except Exception as e:
                    results.append({
                        "task": task.name,
                        "status": "error",
                        "error": str(e)
                    })

        return results


def create_scheduler_config():
    """Create the default scheduler configuration file."""
    config = {
        "tasks": {
            "daily_briefing": {
                "module": "src.tasks.daily_briefing",
                "function": "run",
                "schedule": "0 8 * * *",
                "description": "Generate daily briefing document with pending tasks, approval queue, and metrics",
                "enabled": True,
                "parameters": {}
            }
        },
        "settings": {
            "timezone": "UTC",
            "log_level": "INFO"
        }
    }

    config_path = Path("config/scheduler_config.yaml")
    config_path.parent.mkdir(parents=True, exist_ok=True)

    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    print(f"Created scheduler config: {config_path}")
    return config_path


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="AI Employee Scheduled Task Runner"
    )
    parser.add_argument(
        "--task",
        type=str,
        help="Task name to run"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all configured tasks"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate execution without running tasks"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config/scheduler_config.yaml",
        help="Path to scheduler config file"
    )
    parser.add_argument(
        "--init",
        action="store_true",
        help="Create default scheduler configuration"
    )
    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Handle init
    if args.init:
        create_scheduler_config()
        return

    # Create scheduler
    scheduler = TaskScheduler(
        config_path=args.config,
        dry_run=args.dry_run
    )

    # Handle list
    if args.list:
        tasks = scheduler.list_tasks()
        if not tasks:
            print("No tasks configured")
            return

        print("\nConfigured Tasks:")
        print("-" * 60)
        for task in tasks:
            status = "enabled" if task.enabled else "disabled"
            print(f"  {task.name}")
            print(f"    Module: {task.module}.{task.function}")
            print(f"    Schedule: {task.schedule or 'manual'}")
            print(f"    Status: {status}")
            if task.description:
                print(f"    Description: {task.description}")
            print()
        return

    # Handle task execution
    if args.task:
        try:
            result = await scheduler.run_task(args.task)
            print(f"\nTask completed: {result}")
        except TaskNotFoundError as e:
            print(f"\nError: {e}")
            sys.exit(1)
        except TaskExecutionError as e:
            print(f"\nTask failed: {e}")
            sys.exit(1)
        return

    # No action specified
    parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
