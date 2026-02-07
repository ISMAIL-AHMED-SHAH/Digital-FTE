"""Bottleneck Detection and Analysis (T035 - FR-017).

Analyzes task completion times to identify bottlenecks:
- Task duration tracking
- Overdue task detection
- Processing time analysis by stage
- Workflow bottleneck identification
- Recommendation generation

Used by CEO Briefing to highlight operational issues.
"""

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any
from collections import defaultdict
import statistics

logger = logging.getLogger(__name__)


@dataclass
class Bottleneck:
    """Identified bottleneck in the workflow.

    Attributes:
        type: Bottleneck type (approval_delay, slow_api, queue_backup, overdue_tasks)
        description: Human-readable description
        severity: low, medium, high, critical
        impact_hours: Estimated hours of delay caused
        affected_count: Number of tasks/items affected
        location: Where in the workflow (stage, service, etc.)
        recommendation: Suggested fix
    """
    type: str
    description: str
    severity: str
    impact_hours: float
    affected_count: int
    location: str
    recommendation: str


@dataclass
class TaskMetrics:
    """Task completion metrics.

    Attributes:
        total_tasks: Total tasks in period
        completed: Completed tasks
        pending: Still pending
        overdue: Past due date
        completion_rate: Percentage completed
        avg_completion_hours: Average time to complete
        median_completion_hours: Median time to complete
    """
    total_tasks: int = 0
    completed: int = 0
    pending: int = 0
    overdue: int = 0
    completion_rate: float = 0.0
    avg_completion_hours: float = 0.0
    median_completion_hours: float = 0.0


@dataclass
class StageMetrics:
    """Metrics for a workflow stage.

    Attributes:
        stage_name: Name of the stage
        avg_duration_hours: Average time in stage
        max_duration_hours: Maximum time in stage
        task_count: Tasks that passed through
        is_bottleneck: Whether this stage is a bottleneck
    """
    stage_name: str
    avg_duration_hours: float
    max_duration_hours: float
    task_count: int
    is_bottleneck: bool = False


class BottleneckDetector:
    """Detects workflow bottlenecks from task data.

    Usage:
        detector = BottleneckDetector()

        # Analyze tasks
        metrics = detector.analyze_tasks(tasks)

        # Detect bottlenecks
        bottlenecks = detector.detect_bottlenecks(tasks, approvals, api_calls)

        # Generate report
        report = detector.generate_report(bottlenecks, metrics)
    """

    # Thresholds for bottleneck detection
    APPROVAL_DELAY_THRESHOLD_HOURS = 4
    API_SLOW_THRESHOLD_MS = 1000
    QUEUE_BACKUP_THRESHOLD = 5
    OVERDUE_CRITICAL_DAYS = 7

    def __init__(self):
        """Initialize the detector."""
        pass

    def analyze_tasks(
        self,
        tasks: list[dict[str, Any]],
        today: date | None = None
    ) -> TaskMetrics:
        """Analyze task completion metrics.

        Args:
            tasks: List of task dicts with created_at, completed_at,
                   due_date, status
            today: Current date for overdue calculation

        Returns:
            TaskMetrics summary
        """
        today = today or date.today()

        total = len(tasks)
        completed = 0
        pending = 0
        overdue = 0
        completion_times = []

        for task in tasks:
            status = task.get("status", "pending")

            if status == "completed":
                completed += 1

                # Calculate completion time
                created = task.get("created_at")
                completed_at = task.get("completed_at")

                if created and completed_at:
                    if isinstance(created, str):
                        created = datetime.fromisoformat(created)
                    if isinstance(completed_at, str):
                        completed_at = datetime.fromisoformat(completed_at)

                    duration = (completed_at - created).total_seconds() / 3600
                    completion_times.append(duration)
            else:
                pending += 1

                # Check if overdue
                due_date = task.get("due_date")
                if due_date:
                    if isinstance(due_date, str):
                        due_date = date.fromisoformat(due_date)
                    if due_date < today:
                        overdue += 1

        # Calculate statistics
        avg_time = statistics.mean(completion_times) if completion_times else 0
        median_time = statistics.median(completion_times) if completion_times else 0
        completion_rate = (completed / total * 100) if total > 0 else 0

        return TaskMetrics(
            total_tasks=total,
            completed=completed,
            pending=pending,
            overdue=overdue,
            completion_rate=round(completion_rate, 1),
            avg_completion_hours=round(avg_time, 2),
            median_completion_hours=round(median_time, 2),
        )

    def analyze_stages(
        self,
        tasks: list[dict[str, Any]]
    ) -> list[StageMetrics]:
        """Analyze time spent in each workflow stage.

        Args:
            tasks: List of tasks with stage_history

        Returns:
            List of StageMetrics for each stage
        """
        stage_durations: dict[str, list[float]] = defaultdict(list)

        for task in tasks:
            history = task.get("stage_history", [])

            for i, stage in enumerate(history):
                stage_name = stage.get("stage")
                entered = stage.get("entered_at")
                exited = stage.get("exited_at")

                if entered and exited:
                    if isinstance(entered, str):
                        entered = datetime.fromisoformat(entered)
                    if isinstance(exited, str):
                        exited = datetime.fromisoformat(exited)

                    duration_hours = (exited - entered).total_seconds() / 3600
                    stage_durations[stage_name].append(duration_hours)

        # Calculate metrics per stage
        stages = []
        all_avgs = []

        for stage_name, durations in stage_durations.items():
            if durations:
                avg = statistics.mean(durations)
                all_avgs.append((stage_name, avg))

                stages.append(StageMetrics(
                    stage_name=stage_name,
                    avg_duration_hours=round(avg, 2),
                    max_duration_hours=round(max(durations), 2),
                    task_count=len(durations),
                ))

        # Mark bottleneck stages (>2x average of all stages)
        if all_avgs:
            overall_avg = statistics.mean(avg for _, avg in all_avgs)
            for stage in stages:
                if stage.avg_duration_hours > overall_avg * 2:
                    stage.is_bottleneck = True

        return stages

    def detect_bottlenecks(
        self,
        tasks: list[dict[str, Any]] | None = None,
        approvals: list[dict[str, Any]] | None = None,
        api_calls: list[dict[str, Any]] | None = None,
        today: date | None = None
    ) -> list[Bottleneck]:
        """Detect all bottlenecks from available data.

        Args:
            tasks: Task data for overdue/queue analysis
            approvals: Approval data for delay analysis
            api_calls: API call data for slow service analysis
            today: Current date

        Returns:
            List of detected Bottleneck objects
        """
        today = today or date.today()
        bottlenecks = []

        # Check approval delays
        if approvals:
            approval_bottleneck = self._check_approval_delays(approvals)
            if approval_bottleneck:
                bottlenecks.append(approval_bottleneck)

        # Check API performance
        if api_calls:
            api_bottlenecks = self._check_api_performance(api_calls)
            bottlenecks.extend(api_bottlenecks)

        # Check task queue backup
        if tasks:
            queue_bottleneck = self._check_queue_backup(tasks)
            if queue_bottleneck:
                bottlenecks.append(queue_bottleneck)

            # Check overdue tasks
            overdue_bottleneck = self._check_overdue_tasks(tasks, today)
            if overdue_bottleneck:
                bottlenecks.append(overdue_bottleneck)

        # Sort by severity
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        bottlenecks.sort(key=lambda b: severity_order.get(b.severity, 4))

        logger.info(f"Detected {len(bottlenecks)} bottlenecks")
        return bottlenecks

    def _check_approval_delays(
        self,
        approvals: list[dict[str, Any]]
    ) -> Bottleneck | None:
        """Check for approval delay bottlenecks.

        Args:
            approvals: List of approval records

        Returns:
            Bottleneck if delays detected, None otherwise
        """
        wait_times = []

        for approval in approvals:
            created = approval.get("created_at")
            resolved = approval.get("resolved_at")

            if created and resolved:
                if isinstance(created, str):
                    created = datetime.fromisoformat(created)
                if isinstance(resolved, str):
                    resolved = datetime.fromisoformat(resolved)

                wait_hours = (resolved - created).total_seconds() / 3600
                wait_times.append(wait_hours)

        if not wait_times:
            return None

        avg_wait = statistics.mean(wait_times)

        if avg_wait > self.APPROVAL_DELAY_THRESHOLD_HOURS:
            severity = "critical" if avg_wait > 24 else "high" if avg_wait > 8 else "medium"

            return Bottleneck(
                type="approval_delay",
                description=f"Average approval wait time is {avg_wait:.1f} hours",
                severity=severity,
                impact_hours=avg_wait * len(wait_times),
                affected_count=len(wait_times),
                location="approval_workflow",
                recommendation=self._get_approval_recommendation(avg_wait),
            )

        return None

    def _get_approval_recommendation(self, avg_wait: float) -> str:
        """Get recommendation for approval delays."""
        if avg_wait > 24:
            return "Consider automated approval for low-value transactions (<$500) and set up approval reminders"
        elif avg_wait > 8:
            return "Implement approval reminders after 4 hours and consider delegated approval authority"
        else:
            return "Set up mobile notifications for pending approvals"

    def _check_api_performance(
        self,
        api_calls: list[dict[str, Any]]
    ) -> list[Bottleneck]:
        """Check for slow API bottlenecks.

        Args:
            api_calls: List of API call records

        Returns:
            List of Bottleneck objects for slow services
        """
        by_service: dict[str, list[int]] = defaultdict(list)

        for call in api_calls:
            service = call.get("service", "unknown")
            response_time = call.get("response_time_ms", 0)
            by_service[service].append(response_time)

        bottlenecks = []

        for service, times in by_service.items():
            avg_time = statistics.mean(times)

            if avg_time > self.API_SLOW_THRESHOLD_MS:
                severity = "high" if avg_time > 3000 else "medium"

                bottlenecks.append(Bottleneck(
                    type="slow_api",
                    description=f"{service} API averaging {avg_time:.0f}ms response time",
                    severity=severity,
                    impact_hours=sum(times) / 1000 / 3600,  # Total time in hours
                    affected_count=len(times),
                    location=service,
                    recommendation=f"Implement request batching for {service} and add caching where appropriate",
                ))

        return bottlenecks

    def _check_queue_backup(
        self,
        tasks: list[dict[str, Any]]
    ) -> Bottleneck | None:
        """Check for task queue backup.

        Args:
            tasks: List of tasks

        Returns:
            Bottleneck if queue backed up, None otherwise
        """
        pending = [t for t in tasks if t.get("status") == "pending"]

        if len(pending) > self.QUEUE_BACKUP_THRESHOLD:
            severity = "critical" if len(pending) > 20 else "high" if len(pending) > 10 else "medium"

            return Bottleneck(
                type="queue_backup",
                description=f"{len(pending)} tasks waiting in queue",
                severity=severity,
                impact_hours=len(pending) * 0.5,  # Estimated
                affected_count=len(pending),
                location="task_queue",
                recommendation="Increase processing concurrency or review task prioritization",
            )

        return None

    def _check_overdue_tasks(
        self,
        tasks: list[dict[str, Any]],
        today: date
    ) -> Bottleneck | None:
        """Check for overdue task bottleneck.

        Args:
            tasks: List of tasks
            today: Current date

        Returns:
            Bottleneck if many overdue tasks, None otherwise
        """
        overdue = []

        for task in tasks:
            if task.get("status") != "completed":
                due_date = task.get("due_date")
                if due_date:
                    if isinstance(due_date, str):
                        due_date = date.fromisoformat(due_date)
                    if due_date < today:
                        days_overdue = (today - due_date).days
                        overdue.append(days_overdue)

        if not overdue:
            return None

        max_overdue = max(overdue)
        avg_overdue = statistics.mean(overdue)

        if max_overdue > self.OVERDUE_CRITICAL_DAYS or len(overdue) > 3:
            severity = "critical" if max_overdue > 14 else "high" if max_overdue > 7 else "medium"

            return Bottleneck(
                type="overdue_tasks",
                description=f"{len(overdue)} overdue tasks (avg {avg_overdue:.1f} days late)",
                severity=severity,
                impact_hours=sum(overdue) * 8,  # Assume 8 hours per day delayed
                affected_count=len(overdue),
                location="task_completion",
                recommendation="Review blocked tasks and escalate critical overdue items",
            )

        return None

    def generate_report(
        self,
        bottlenecks: list[Bottleneck],
        task_metrics: TaskMetrics,
        stage_metrics: list[StageMetrics] | None = None,
        period_from: date | None = None,
        period_to: date | None = None
    ) -> dict[str, Any]:
        """Generate bottleneck report for CEO briefing.

        Args:
            bottlenecks: Detected bottlenecks
            task_metrics: Task completion metrics
            stage_metrics: Optional stage analysis
            period_from: Report period start
            period_to: Report period end

        Returns:
            Report dictionary
        """
        severity_counts = defaultdict(int)
        for b in bottlenecks:
            severity_counts[b.severity] += 1

        return {
            "period": {
                "from": period_from.isoformat() if period_from else None,
                "to": period_to.isoformat() if period_to else None,
            },
            "task_summary": {
                "total": task_metrics.total_tasks,
                "completed": task_metrics.completed,
                "pending": task_metrics.pending,
                "overdue": task_metrics.overdue,
                "completion_rate": task_metrics.completion_rate,
                "avg_completion_hours": task_metrics.avg_completion_hours,
            },
            "bottleneck_summary": {
                "total": len(bottlenecks),
                "critical": severity_counts.get("critical", 0),
                "high": severity_counts.get("high", 0),
                "medium": severity_counts.get("medium", 0),
                "low": severity_counts.get("low", 0),
            },
            "bottlenecks": [
                {
                    "type": b.type,
                    "description": b.description,
                    "severity": b.severity,
                    "recommendation": b.recommendation,
                }
                for b in bottlenecks[:5]  # Top 5 bottlenecks
            ],
            "stage_bottlenecks": [
                {
                    "stage": s.stage_name,
                    "avg_hours": s.avg_duration_hours,
                }
                for s in (stage_metrics or []) if s.is_bottleneck
            ],
        }
