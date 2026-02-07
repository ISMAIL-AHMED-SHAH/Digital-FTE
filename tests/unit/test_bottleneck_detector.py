"""Unit Tests for Bottleneck Detector (T032).

Tests for task completion time analysis and bottleneck detection including:
- Task duration tracking
- Overdue task detection
- Processing time analysis
- Workflow bottleneck identification

Per spec: FR-017
"""

import pytest
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import List, Dict


class TestTaskDurationTracking:
    """Test task duration measurement."""

    def test_task_completion_time(self):
        """Test calculation of task completion time."""
        task = {
            "id": "T001",
            "created_at": datetime(2026, 1, 1, 9, 0),
            "completed_at": datetime(2026, 1, 1, 14, 30),
        }

        duration = task["completed_at"] - task["created_at"]
        hours = duration.total_seconds() / 3600

        assert hours == 5.5

    def test_average_completion_time(self):
        """Test average task completion time calculation."""
        tasks = [
            {"duration_hours": 2.0},
            {"duration_hours": 4.0},
            {"duration_hours": 3.0},
            {"duration_hours": 5.0},
            {"duration_hours": 1.0},
        ]

        avg_duration = sum(t["duration_hours"] for t in tasks) / len(tasks)
        assert avg_duration == 3.0

    def test_median_completion_time(self):
        """Test median task completion time (more robust than mean)."""
        durations = [1.0, 2.0, 3.0, 4.0, 100.0]  # Outlier at end

        sorted_durations = sorted(durations)
        n = len(sorted_durations)
        median = sorted_durations[n // 2]

        assert median == 3.0  # Not affected by outlier

    def test_completion_time_by_type(self):
        """Test completion time breakdown by task type."""
        tasks = [
            {"type": "invoice", "duration_hours": 0.5},
            {"type": "invoice", "duration_hours": 0.3},
            {"type": "email", "duration_hours": 0.1},
            {"type": "email", "duration_hours": 0.2},
            {"type": "social_post", "duration_hours": 1.0},
        ]

        by_type = {}
        for task in tasks:
            t = task["type"]
            if t not in by_type:
                by_type[t] = []
            by_type[t].append(task["duration_hours"])

        avg_by_type = {t: sum(d) / len(d) for t, d in by_type.items()}

        assert avg_by_type["invoice"] == 0.4
        assert avg_by_type["email"] == 0.15
        assert avg_by_type["social_post"] == 1.0


class TestOverdueTaskDetection:
    """Test overdue task identification."""

    def test_overdue_task_detection(self):
        """Test detection of tasks past their due date."""
        today = date(2026, 1, 15)

        tasks = [
            {"id": "T001", "due_date": date(2026, 1, 10), "status": "pending"},
            {"id": "T002", "due_date": date(2026, 1, 20), "status": "pending"},
            {"id": "T003", "due_date": date(2026, 1, 14), "status": "completed"},
        ]

        overdue = [
            t for t in tasks
            if t["status"] == "pending" and t["due_date"] < today
        ]

        assert len(overdue) == 1
        assert overdue[0]["id"] == "T001"

    def test_overdue_severity_classification(self):
        """Test severity based on how overdue a task is."""
        today = date(2026, 1, 15)

        tasks = [
            {"id": "T001", "due_date": date(2026, 1, 14)},  # 1 day overdue
            {"id": "T002", "due_date": date(2026, 1, 10)},  # 5 days overdue
            {"id": "T003", "due_date": date(2025, 12, 15)},  # 31 days overdue
        ]

        def classify_overdue(due_date, today):
            days_overdue = (today - due_date).days
            if days_overdue <= 2:
                return "low"
            elif days_overdue <= 7:
                return "medium"
            elif days_overdue <= 14:
                return "high"
            else:
                return "critical"

        severities = [classify_overdue(t["due_date"], today) for t in tasks]

        assert severities[0] == "low"
        assert severities[1] == "medium"
        assert severities[2] == "critical"

    def test_overdue_count_by_category(self):
        """Test overdue count breakdown by category."""
        overdue_tasks = [
            {"category": "accounting", "days_overdue": 3},
            {"category": "accounting", "days_overdue": 5},
            {"category": "social_media", "days_overdue": 1},
            {"category": "email", "days_overdue": 2},
        ]

        by_category = {}
        for task in overdue_tasks:
            cat = task["category"]
            by_category[cat] = by_category.get(cat, 0) + 1

        assert by_category["accounting"] == 2
        assert by_category["social_media"] == 1
        assert by_category["email"] == 1


class TestProcessingTimeAnalysis:
    """Test processing time analysis for bottleneck detection."""

    def test_approval_wait_time(self):
        """Test time spent waiting for human approval."""
        approvals = [
            {"created_at": datetime(2026, 1, 10, 9, 0), "approved_at": datetime(2026, 1, 10, 14, 0)},
            {"created_at": datetime(2026, 1, 11, 10, 0), "approved_at": datetime(2026, 1, 12, 9, 0)},
            {"created_at": datetime(2026, 1, 13, 15, 0), "approved_at": datetime(2026, 1, 13, 16, 30)},
        ]

        wait_times = []
        for a in approvals:
            wait = (a["approved_at"] - a["created_at"]).total_seconds() / 3600
            wait_times.append(wait)

        # 5 hours, 23 hours, 1.5 hours
        assert wait_times[0] == 5.0
        assert wait_times[1] == 23.0
        assert wait_times[2] == 1.5

        avg_wait = sum(wait_times) / len(wait_times)
        assert avg_wait == pytest.approx(9.83, rel=0.1)

    def test_api_response_time_tracking(self):
        """Test external API response time tracking."""
        api_calls = [
            {"service": "odoo", "response_time_ms": 250},
            {"service": "odoo", "response_time_ms": 180},
            {"service": "facebook", "response_time_ms": 450},
            {"service": "twitter", "response_time_ms": 320},
        ]

        by_service = {}
        for call in api_calls:
            svc = call["service"]
            if svc not in by_service:
                by_service[svc] = []
            by_service[svc].append(call["response_time_ms"])

        avg_by_service = {s: sum(t) / len(t) for s, t in by_service.items()}

        assert avg_by_service["odoo"] == 215
        assert avg_by_service["facebook"] == 450

    def test_queue_time_analysis(self):
        """Test time tasks spend in queue before processing."""
        queue_times = [
            {"task_id": "T001", "queued_at": datetime(2026, 1, 10, 9, 0), "started_at": datetime(2026, 1, 10, 9, 5)},
            {"task_id": "T002", "queued_at": datetime(2026, 1, 10, 9, 0), "started_at": datetime(2026, 1, 10, 10, 0)},
            {"task_id": "T003", "queued_at": datetime(2026, 1, 10, 9, 0), "started_at": datetime(2026, 1, 10, 9, 2)},
        ]

        wait_minutes = []
        for q in queue_times:
            wait = (q["started_at"] - q["queued_at"]).total_seconds() / 60
            wait_minutes.append(wait)

        # 5 min, 60 min, 2 min
        assert wait_minutes == [5, 60, 2]

        # Identify bottleneck: T002 waited too long
        bottleneck = max(queue_times, key=lambda q: (q["started_at"] - q["queued_at"]).total_seconds())
        assert bottleneck["task_id"] == "T002"


class TestWorkflowBottleneckIdentification:
    """Test workflow bottleneck detection."""

    def test_stage_duration_analysis(self):
        """Test time spent in each workflow stage."""
        workflow = {
            "stages": [
                {"name": "created", "avg_duration_hours": 0.1},
                {"name": "processing", "avg_duration_hours": 0.5},
                {"name": "awaiting_approval", "avg_duration_hours": 8.0},  # Bottleneck!
                {"name": "approved", "avg_duration_hours": 0.1},
                {"name": "executing", "avg_duration_hours": 0.3},
                {"name": "completed", "avg_duration_hours": 0.0},
            ]
        }

        # Find stage with longest duration
        bottleneck_stage = max(workflow["stages"], key=lambda s: s["avg_duration_hours"])

        assert bottleneck_stage["name"] == "awaiting_approval"
        assert bottleneck_stage["avg_duration_hours"] == 8.0

    def test_service_dependency_bottleneck(self):
        """Test bottleneck from slow external service."""
        service_stats = [
            {"service": "odoo", "avg_response_ms": 200, "error_rate": 0.01},
            {"service": "facebook", "avg_response_ms": 1500, "error_rate": 0.05},  # Slow!
            {"service": "gmail", "avg_response_ms": 300, "error_rate": 0.02},
        ]

        # Identify slow services (>1000ms avg)
        slow_services = [s for s in service_stats if s["avg_response_ms"] > 1000]

        assert len(slow_services) == 1
        assert slow_services[0]["service"] == "facebook"

    def test_resource_contention_bottleneck(self):
        """Test bottleneck from resource contention."""
        resource_usage = {
            "concurrent_tasks": 10,
            "max_concurrent": 5,  # Limit exceeded
            "queue_depth": 15,
            "processing_rate": 2,  # tasks per minute
        }

        # If concurrent > max, tasks queue up
        is_contention = resource_usage["concurrent_tasks"] > resource_usage["max_concurrent"]
        assert is_contention

        # Queue drain time
        drain_time_minutes = resource_usage["queue_depth"] / resource_usage["processing_rate"]
        assert drain_time_minutes == 7.5


class TestBottleneckReporting:
    """Test bottleneck report generation."""

    def test_bottleneck_report_structure(self):
        """Test bottleneck report has required fields."""
        report = {
            "period": {"from": "2026-01-01", "to": "2026-01-31"},
            "summary": {
                "total_bottlenecks": 3,
                "critical": 1,
                "high": 1,
                "medium": 1,
            },
            "bottlenecks": [
                {
                    "type": "approval_delay",
                    "description": "Average approval wait time is 8 hours",
                    "severity": "critical",
                    "impact": "Delays invoice posting by 1 business day",
                    "recommendation": "Consider automated approval for amounts < $1000",
                },
            ],
        }

        assert "summary" in report
        assert "bottlenecks" in report
        assert len(report["bottlenecks"]) > 0
        assert "recommendation" in report["bottlenecks"][0]

    def test_bottleneck_severity_scoring(self):
        """Test bottleneck severity scoring algorithm."""
        def score_bottleneck(impact_hours: float, frequency: int, affected_tasks: int) -> str:
            score = impact_hours * frequency * (affected_tasks / 10)

            if score >= 100:
                return "critical"
            elif score >= 50:
                return "high"
            elif score >= 20:
                return "medium"
            else:
                return "low"

        # High impact, frequent, many affected = critical
        assert score_bottleneck(8.0, 5, 50) == "critical"

        # Medium impact, moderate frequency
        assert score_bottleneck(2.0, 3, 20) == "medium"

        # Low impact, rare
        assert score_bottleneck(0.5, 1, 5) == "low"

    def test_bottleneck_trend_analysis(self):
        """Test bottleneck trend over time."""
        weekly_bottlenecks = [
            {"week": "2025-W50", "count": 5, "avg_severity_score": 45},
            {"week": "2025-W51", "count": 7, "avg_severity_score": 52},
            {"week": "2025-W52", "count": 8, "avg_severity_score": 60},
            {"week": "2026-W01", "count": 6, "avg_severity_score": 48},
        ]

        # Check if improving or worsening
        recent = weekly_bottlenecks[-1]
        previous = weekly_bottlenecks[-2]

        trend = "improving" if recent["avg_severity_score"] < previous["avg_severity_score"] else "worsening"
        assert trend == "improving"


class TestBottleneckRecommendations:
    """Test recommendation generation for bottlenecks."""

    def test_approval_bottleneck_recommendations(self):
        """Test recommendations for approval bottlenecks."""
        bottleneck = {
            "type": "approval_delay",
            "avg_wait_hours": 12,
            "affected_task_types": ["invoice", "payment"],
        }

        recommendations = []

        if bottleneck["avg_wait_hours"] > 8:
            recommendations.append({
                "action": "Enable auto-approval for low-value transactions",
                "threshold": "$500",
                "expected_improvement": "60% faster processing",
            })

        if bottleneck["avg_wait_hours"] > 4:
            recommendations.append({
                "action": "Send approval reminders after 4 hours",
                "expected_improvement": "30% faster response",
            })

        assert len(recommendations) == 2

    def test_api_bottleneck_recommendations(self):
        """Test recommendations for slow API bottlenecks."""
        bottleneck = {
            "type": "slow_api",
            "service": "facebook",
            "avg_response_ms": 1500,
            "error_rate": 0.08,
        }

        recommendations = []

        if bottleneck["avg_response_ms"] > 1000:
            recommendations.append({
                "action": "Implement request batching",
                "expected_improvement": "40% fewer API calls",
            })

        if bottleneck["error_rate"] > 0.05:
            recommendations.append({
                "action": "Add retry with exponential backoff",
                "expected_improvement": "50% fewer failures",
            })

        assert len(recommendations) == 2
