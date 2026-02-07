#!/usr/bin/env python3
"""Ralph Wiggum Loop Skill Entry Point (T068).

Manages autonomous loop execution:
- Start/stop loop
- Check status
- View history
- Generate summaries

Usage:
    python main_operation.py start --task-id TASK_ID
    python main_operation.py status --task-id TASK_ID
    python main_operation.py stop --task-id TASK_ID --reason "Reason"
    python main_operation.py history --task-id TASK_ID
    python main_operation.py summary --task-id TASK_ID
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))


def output_json(data: dict) -> None:
    """Output data as JSON to stdout."""
    print(json.dumps(data, indent=2, default=str))


def output_error(message: str, code: str = "SKILL_ERROR") -> None:
    """Output error as JSON."""
    output_json({
        "success": False,
        "error": {"code": code, "message": message}
    })
    sys.exit(1)


def load_config() -> dict:
    """Load Ralph Wiggum configuration."""
    config_path = PROJECT_ROOT / "config" / "gold_tier.yaml"

    default_config = {
        "max_iterations": 50,
        "timeout_minutes": 30,
        "error_threshold": 3,
        "warning_threshold": 0.8,
    }

    if config_path.exists():
        try:
            import yaml
            with open(config_path) as f:
                full_config = yaml.safe_load(f)
                ralph_config = full_config.get("ralph_wiggum", {})
                default_config.update(ralph_config)
        except ImportError:
            pass  # Use defaults if yaml not available

    return default_config


def cmd_start(args: argparse.Namespace) -> None:
    """Start autonomous loop for task."""
    try:
        from tasks.ralph_loop_tracker import RalphLoopTracker
        from tasks.ralph_completion_checker import RalphCompletionChecker
    except ImportError:
        output_error("Could not import Ralph modules. Run from project root.", "IMPORT_ERROR")
        return

    config = load_config()
    state_dir = PROJECT_ROOT / "data" / "ralph"
    vault_path = Path(os.environ.get("VAULT_PATH", PROJECT_ROOT / "vault"))

    # Initialize tracker
    max_iter = args.max_iterations or config["max_iterations"]
    tracker = RalphLoopTracker(state_dir=state_dir, max_iterations=max_iter)

    # Check if task exists
    task_file = None
    needs_action = vault_path / "Needs_Action"
    if needs_action.exists():
        for pattern in [f"{args.task_id}*", f"*{args.task_id}*"]:
            matches = list(needs_action.glob(pattern))
            if matches:
                task_file = matches[0]
                break

    if not task_file:
        # Check if already in Done
        done = vault_path / "Done"
        if done.exists():
            for pattern in [f"{args.task_id}*", f"*{args.task_id}*"]:
                if list(done.glob(pattern)):
                    output_json({
                        "success": True,
                        "status": "already_completed",
                        "message": f"Task {args.task_id} is already in Done folder",
                    })
                    return

    # Start the loop
    state = tracker.start_loop(args.task_id, max_iterations=max_iter)

    output_json({
        "success": True,
        "status": "started",
        "task_id": args.task_id,
        "max_iterations": max_iter,
        "state_file": str(state_dir / f"{args.task_id}_state.json"),
        "message": f"Loop started for task {args.task_id}",
    })


def cmd_status(args: argparse.Namespace) -> None:
    """Check loop status."""
    try:
        from tasks.ralph_loop_tracker import RalphLoopTracker
    except ImportError:
        output_error("Could not import Ralph modules.", "IMPORT_ERROR")
        return

    state_dir = PROJECT_ROOT / "data" / "ralph"
    state_file = state_dir / f"{args.task_id}_state.json"

    if not state_file.exists():
        output_json({
            "success": True,
            "status": "not_found",
            "message": f"No active loop for task {args.task_id}",
        })
        return

    with open(state_file) as f:
        state = json.load(f)

    output_json({
        "success": True,
        "task_id": args.task_id,
        "status": state.get("status", "unknown"),
        "iteration": state.get("iteration", 0),
        "max_iterations": state.get("max_iterations", 50),
        "error_count": state.get("error_count", 0),
        "started_at": state.get("started_at"),
        "last_checkpoint": state.get("last_checkpoint"),
        "completion_reason": state.get("completion_reason"),
    })


def cmd_stop(args: argparse.Namespace) -> None:
    """Stop running loop."""
    try:
        from tasks.ralph_loop_tracker import RalphLoopTracker
    except ImportError:
        output_error("Could not import Ralph modules.", "IMPORT_ERROR")
        return

    state_dir = PROJECT_ROOT / "data" / "ralph"
    tracker = RalphLoopTracker(state_dir=state_dir)

    state_file = state_dir / f"{args.task_id}_state.json"
    if not state_file.exists():
        output_error(f"No active loop for task {args.task_id}", "NOT_FOUND")
        return

    # Load and update state
    tracker._state_file = state_file
    tracker.state = tracker._load_state()

    summary = tracker.stop_loop(args.reason or "User requested stop")

    output_json({
        "success": True,
        "status": "stopped",
        "task_id": args.task_id,
        "reason": args.reason or "User requested stop",
        "summary": summary,
    })


def cmd_history(args: argparse.Namespace) -> None:
    """View loop iteration history."""
    try:
        from tasks.ralph_loop_tracker import RalphLoopTracker
    except ImportError:
        output_error("Could not import Ralph modules.", "IMPORT_ERROR")
        return

    state_dir = PROJECT_ROOT / "data" / "ralph"
    state_file = state_dir / f"{args.task_id}_state.json"

    if not state_file.exists():
        output_error(f"No state found for task {args.task_id}", "NOT_FOUND")
        return

    tracker = RalphLoopTracker(state_dir=state_dir)
    tracker._state_file = state_file
    tracker.state = tracker._load_state()

    history = tracker.get_iteration_history()

    output_json({
        "success": True,
        "task_id": args.task_id,
        "iterations": len(history),
        "history": history[-args.limit:] if args.limit else history,
    })


def cmd_summary(args: argparse.Namespace) -> None:
    """Generate execution summary."""
    try:
        from tasks.ralph_loop_tracker import RalphLoopTracker
        from tasks.ralph_summary_generator import RalphSummaryGenerator
    except ImportError:
        output_error("Could not import Ralph modules.", "IMPORT_ERROR")
        return

    state_dir = PROJECT_ROOT / "data" / "ralph"
    vault_path = Path(os.environ.get("VAULT_PATH", PROJECT_ROOT / "vault"))

    state_file = state_dir / f"{args.task_id}_state.json"
    if not state_file.exists():
        output_error(f"No state found for task {args.task_id}", "NOT_FOUND")
        return

    with open(state_file) as f:
        state = json.load(f)

    generator = RalphSummaryGenerator(vault_path=vault_path)
    summary = generator.generate(args.task_id, state)

    # Write to file if requested
    if args.output:
        filepath = generator.write_summary(
            summary,
            args.task_id,
            format=args.format or "markdown"
        )
        summary["output_file"] = str(filepath)

    output_json({
        "success": True,
        "summary": summary,
    })


def cmd_check(args: argparse.Namespace) -> None:
    """Check completion status."""
    try:
        from tasks.ralph_completion_checker import RalphCompletionChecker
    except ImportError:
        output_error("Could not import Ralph modules.", "IMPORT_ERROR")
        return

    vault_path = Path(os.environ.get("VAULT_PATH", PROJECT_ROOT / "vault"))
    checker = RalphCompletionChecker(vault_path=vault_path)

    result = checker.check(
        task_id=args.task_id,
        response=args.response,
        error_count=args.error_count or 0,
        iteration=args.iteration or 0,
        max_iterations=args.max_iterations or 50,
    )

    output_json({
        "success": True,
        "is_complete": result.is_complete,
        "should_stop": result.should_stop,
        "method": result.method,
        "reason": result.reason,
        "details": result.details,
    })


def main():
    parser = argparse.ArgumentParser(
        description="Ralph Wiggum Autonomous Loop Management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Operation to perform")

    # Start command
    start_parser = subparsers.add_parser("start", help="Start autonomous loop")
    start_parser.add_argument("--task-id", required=True, help="Task identifier")
    start_parser.add_argument("--max-iterations", type=int, help="Maximum iterations")
    start_parser.add_argument("--timeout", type=int, help="Timeout in minutes")
    start_parser.set_defaults(func=cmd_start)

    # Status command
    status_parser = subparsers.add_parser("status", help="Check loop status")
    status_parser.add_argument("--task-id", required=True, help="Task identifier")
    status_parser.set_defaults(func=cmd_status)

    # Stop command
    stop_parser = subparsers.add_parser("stop", help="Stop running loop")
    stop_parser.add_argument("--task-id", required=True, help="Task identifier")
    stop_parser.add_argument("--reason", help="Reason for stopping")
    stop_parser.set_defaults(func=cmd_stop)

    # History command
    history_parser = subparsers.add_parser("history", help="View iteration history")
    history_parser.add_argument("--task-id", required=True, help="Task identifier")
    history_parser.add_argument("--limit", type=int, help="Limit number of entries")
    history_parser.set_defaults(func=cmd_history)

    # Summary command
    summary_parser = subparsers.add_parser("summary", help="Generate execution summary")
    summary_parser.add_argument("--task-id", required=True, help="Task identifier")
    summary_parser.add_argument("--output", action="store_true", help="Write to file")
    summary_parser.add_argument("--format", choices=["markdown", "json"], help="Output format")
    summary_parser.set_defaults(func=cmd_summary)

    # Check command (for completion detection)
    check_parser = subparsers.add_parser("check", help="Check completion status")
    check_parser.add_argument("--task-id", help="Task identifier")
    check_parser.add_argument("--response", help="Response text to analyze")
    check_parser.add_argument("--error-count", type=int, help="Current error count")
    check_parser.add_argument("--iteration", type=int, help="Current iteration")
    check_parser.add_argument("--max-iterations", type=int, help="Maximum iterations")
    check_parser.set_defaults(func=cmd_check)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        args.func(args)
    except Exception as e:
        output_error(str(e), "EXECUTION_ERROR")


if __name__ == "__main__":
    main()
