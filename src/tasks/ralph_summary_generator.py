"""Ralph Wiggum Summary Generator (T066 - FR-024).

Generates completion summaries for autonomous loop execution:
- Execution overview
- Actions performed
- Results and errors
- Timing and performance
- Recommendations

Outputs to vault for human review.
"""

import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class LoopMetrics:
    """Metrics from loop execution.

    Attributes:
        total_iterations: Number of iterations completed
        total_actions: Total actions performed
        successful_actions: Actions that succeeded
        failed_actions: Actions that failed
        duration_seconds: Total time in seconds
        avg_iteration_ms: Average milliseconds per iteration
    """
    total_iterations: int
    total_actions: int
    successful_actions: int
    failed_actions: int
    duration_seconds: float
    avg_iteration_ms: float


@dataclass
class ActionSummary:
    """Summary of an action type.

    Attributes:
        action_type: Type/name of action
        count: Number of times performed
        success_rate: Percentage successful
        avg_duration_ms: Average duration
    """
    action_type: str
    count: int
    success_rate: float
    avg_duration_ms: float


class RalphSummaryGenerator:
    """Generates summaries for Ralph Wiggum loop execution.

    Usage:
        generator = RalphSummaryGenerator(vault_path="./vault")

        # Generate summary from loop state
        summary = generator.generate(
            task_id="task-001",
            state=loop_state_dict,
        )

        # Write to vault
        generator.write_summary(summary, "task-001")
    """

    def __init__(self, vault_path: str | Path = "./vault"):
        """Initialize the generator.

        Args:
            vault_path: Path to vault directory
        """
        self.vault_path = Path(vault_path)

    def generate(
        self,
        task_id: str,
        state: dict,
        additional_context: dict | None = None
    ) -> dict:
        """Generate execution summary.

        Args:
            task_id: Task identifier
            state: Loop state dictionary
            additional_context: Extra context to include

        Returns:
            Summary dictionary
        """
        # Calculate metrics
        metrics = self._calculate_metrics(state)

        # Summarize actions by type
        action_summary = self._summarize_actions(state.get("actions", []))

        # Generate recommendations
        recommendations = self._generate_recommendations(metrics, state)

        # Build summary
        summary = {
            "task_id": task_id,
            "generated_at": datetime.now().isoformat(),
            "status": state.get("status", "unknown"),
            "completion_reason": state.get("completion_reason"),

            "overview": {
                "started_at": state.get("started_at"),
                "ended_at": datetime.now().isoformat(),
                "iterations": metrics.total_iterations,
                "max_iterations": state.get("max_iterations", 50),
                "duration_seconds": round(metrics.duration_seconds, 2),
            },

            "metrics": asdict(metrics),

            "actions": {
                "total": metrics.total_actions,
                "by_type": [asdict(a) for a in action_summary],
            },

            "errors": {
                "count": state.get("error_count", 0),
                "last_error": state.get("last_error"),
                "error_actions": self._extract_errors(state.get("actions", [])),
            },

            "recommendations": recommendations,
        }

        if additional_context:
            summary["context"] = additional_context

        return summary

    def _calculate_metrics(self, state: dict) -> LoopMetrics:
        """Calculate execution metrics."""
        actions = state.get("actions", [])

        total_iterations = state.get("iteration", 0)
        total_actions = len(actions)
        successful = sum(1 for a in actions if a.get("result") == "success")
        failed = sum(1 for a in actions if a.get("result") == "error")

        # Calculate duration
        started_at = state.get("started_at")
        if started_at:
            try:
                start = datetime.fromisoformat(started_at)
                duration = (datetime.now() - start).total_seconds()
            except ValueError:
                duration = 0
        else:
            duration = 0

        # Calculate average iteration time
        total_duration_ms = sum(a.get("duration_ms", 0) for a in actions)
        avg_iteration_ms = (
            total_duration_ms / total_iterations if total_iterations > 0 else 0
        )

        return LoopMetrics(
            total_iterations=total_iterations,
            total_actions=total_actions,
            successful_actions=successful,
            failed_actions=failed,
            duration_seconds=duration,
            avg_iteration_ms=round(avg_iteration_ms, 2),
        )

    def _summarize_actions(self, actions: list[dict]) -> list[ActionSummary]:
        """Summarize actions by type."""
        by_type: dict[str, dict] = {}

        for action in actions:
            action_name = action.get("action", "unknown")
            if action_name not in by_type:
                by_type[action_name] = {
                    "count": 0,
                    "success": 0,
                    "total_duration": 0,
                }

            by_type[action_name]["count"] += 1
            if action.get("result") == "success":
                by_type[action_name]["success"] += 1
            by_type[action_name]["total_duration"] += action.get("duration_ms", 0)

        summaries = []
        for action_type, data in by_type.items():
            count = data["count"]
            summaries.append(ActionSummary(
                action_type=action_type,
                count=count,
                success_rate=round(data["success"] / count * 100, 1) if count > 0 else 0,
                avg_duration_ms=round(data["total_duration"] / count, 2) if count > 0 else 0,
            ))

        # Sort by count descending
        summaries.sort(key=lambda x: x.count, reverse=True)
        return summaries

    def _extract_errors(self, actions: list[dict]) -> list[dict]:
        """Extract error information from actions."""
        errors = []
        for action in actions:
            if action.get("result") == "error":
                errors.append({
                    "iteration": action.get("iteration"),
                    "action": action.get("action"),
                    "error": action.get("details", {}).get("error", "Unknown error"),
                    "timestamp": action.get("timestamp"),
                })
        return errors

    def _generate_recommendations(
        self,
        metrics: LoopMetrics,
        state: dict
    ) -> list[str]:
        """Generate recommendations based on execution."""
        recommendations = []

        # High error rate
        if metrics.total_actions > 0:
            error_rate = metrics.failed_actions / metrics.total_actions
            if error_rate > 0.2:
                recommendations.append(
                    f"High error rate ({error_rate:.1%}). Review error logs and consider adding more error handling."
                )

        # Hit max iterations
        if state.get("completion_reason") == "max_iterations_reached":
            recommendations.append(
                "Maximum iterations reached before completion. Consider increasing max_iterations or breaking task into smaller subtasks."
            )

        # Slow iterations
        if metrics.avg_iteration_ms > 5000:
            recommendations.append(
                f"Average iteration time is high ({metrics.avg_iteration_ms:.0f}ms). Consider optimizing slow operations."
            )

        # No actions performed
        if metrics.total_actions == 0:
            recommendations.append(
                "No actions were performed. Verify task setup and initial conditions."
            )

        # Error threshold exceeded
        if state.get("completion_reason") == "error_threshold_exceeded":
            recommendations.append(
                "Loop stopped due to too many errors. Review error patterns and address root cause."
            )

        # Success message
        if (state.get("status") == "completed" and
            metrics.failed_actions == 0 and
            state.get("completion_reason") not in [
                "max_iterations_reached",
                "error_threshold_exceeded"
            ]):
            recommendations.append(
                "Task completed successfully with no errors. Great job!"
            )

        return recommendations if recommendations else ["No specific recommendations."]

    def write_summary(
        self,
        summary: dict,
        task_id: str,
        format: str = "markdown"
    ) -> Path:
        """Write summary to vault.

        Args:
            summary: Summary dictionary
            task_id: Task identifier
            format: Output format (markdown or json)

        Returns:
            Path to written file
        """
        archive_dir = self.vault_path / "Archive" / "loop_summaries"
        archive_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

        if format == "json":
            filename = f"{task_id}-{timestamp}.json"
            filepath = archive_dir / filename
            with open(filepath, "w") as f:
                json.dump(summary, f, indent=2)
        else:
            filename = f"{task_id}-{timestamp}.md"
            filepath = archive_dir / filename
            markdown = self._to_markdown(summary)
            with open(filepath, "w") as f:
                f.write(markdown)

        logger.info(f"Summary written to {filepath}")
        return filepath

    def _to_markdown(self, summary: dict) -> str:
        """Convert summary to markdown format."""
        lines = [
            f"# Loop Execution Summary: {summary['task_id']}",
            "",
            f"**Generated:** {summary['generated_at']}",
            f"**Status:** {summary['status']}",
            f"**Completion Reason:** {summary.get('completion_reason', 'N/A')}",
            "",
            "## Overview",
            "",
            f"- **Started:** {summary['overview']['started_at']}",
            f"- **Ended:** {summary['overview']['ended_at']}",
            f"- **Iterations:** {summary['overview']['iterations']}/{summary['overview']['max_iterations']}",
            f"- **Duration:** {summary['overview']['duration_seconds']} seconds",
            "",
            "## Metrics",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total Actions | {summary['metrics']['total_actions']} |",
            f"| Successful | {summary['metrics']['successful_actions']} |",
            f"| Failed | {summary['metrics']['failed_actions']} |",
            f"| Avg Iteration | {summary['metrics']['avg_iteration_ms']}ms |",
            "",
        ]

        # Actions by type
        if summary['actions']['by_type']:
            lines.extend([
                "## Actions by Type",
                "",
                "| Action | Count | Success Rate | Avg Duration |",
                "|--------|-------|--------------|--------------|",
            ])
            for action in summary['actions']['by_type']:
                lines.append(
                    f"| {action['action_type']} | {action['count']} | {action['success_rate']}% | {action['avg_duration_ms']}ms |"
                )
            lines.append("")

        # Errors
        if summary['errors']['count'] > 0:
            lines.extend([
                "## Errors",
                "",
                f"**Total Errors:** {summary['errors']['count']}",
                "",
            ])
            if summary['errors']['error_actions']:
                lines.append("### Error Details")
                lines.append("")
                for error in summary['errors']['error_actions'][:5]:
                    lines.append(f"- **Iteration {error['iteration']}**: {error['action']}")
                    lines.append(f"  - Error: {error['error']}")
                if len(summary['errors']['error_actions']) > 5:
                    lines.append(f"  - ... and {len(summary['errors']['error_actions']) - 5} more")
            lines.append("")

        # Recommendations
        lines.extend([
            "## Recommendations",
            "",
        ])
        for rec in summary['recommendations']:
            lines.append(f"- {rec}")

        return "\n".join(lines)

    def create_dashboard_entry(self, summary: dict) -> dict:
        """Create a dashboard entry from summary.

        Args:
            summary: Summary dictionary

        Returns:
            Dashboard entry for display
        """
        metrics = summary.get("metrics", {})
        overview = summary.get("overview", {})

        return {
            "task_id": summary["task_id"],
            "status": summary["status"],
            "iterations": f"{overview.get('iterations', 0)}/{overview.get('max_iterations', 50)}",
            "actions": metrics.get("total_actions", 0),
            "errors": summary.get("errors", {}).get("count", 0),
            "duration": f"{overview.get('duration_seconds', 0)}s",
            "completed_at": summary.get("generated_at"),
        }
