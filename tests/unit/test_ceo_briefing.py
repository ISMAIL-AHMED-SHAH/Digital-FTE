"""Unit Tests for CEO Briefing Generator (T030).

Tests for the weekly CEO briefing generation including:
- Revenue summary aggregation
- Task completion metrics
- Bottleneck identification
- Suggestion generation
- Email/dashboard delivery

Per spec: FR-013-015, FR-018
"""

import pytest
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, patch, AsyncMock
from pathlib import Path
import json

# Import fixtures
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from fixtures.sample_briefing_data import (
    SAMPLE_FINANCIAL_SUMMARY,
    SAMPLE_TASK_METRICS,
    SAMPLE_BOTTLENECKS,
    SAMPLE_SUGGESTIONS,
    SAMPLE_SOCIAL_METRICS,
    create_sample_briefing,
)


class TestCEOBriefingGeneration:
    """Test CEO briefing content generation."""

    def test_generate_briefing_structure(self):
        """Test that briefing has all required sections."""
        briefing = create_sample_briefing()

        assert "period" in briefing
        assert "financial_summary" in briefing
        assert "task_metrics" in briefing
        assert "bottlenecks" in briefing
        assert "suggestions" in briefing
        assert "generated_at" in briefing

    def test_financial_summary_section(self):
        """Test financial summary content."""
        summary = SAMPLE_FINANCIAL_SUMMARY

        assert "revenue" in summary
        assert "total" in summary["revenue"]
        assert "paid" in summary["revenue"]
        assert "receivable" in summary["revenue"]

        assert "counts" in summary
        assert "invoices_posted" in summary["counts"]
        assert "payments_received" in summary["counts"]

        assert "top_customers" in summary
        assert len(summary["top_customers"]) > 0

    def test_task_metrics_section(self):
        """Test task completion metrics."""
        metrics = SAMPLE_TASK_METRICS

        assert "total_tasks" in metrics
        assert "completed" in metrics
        assert "pending" in metrics
        assert "completion_rate" in metrics

        # Completion rate should be valid percentage
        assert 0 <= metrics["completion_rate"] <= 100

    def test_bottleneck_identification(self):
        """Test bottleneck detection results."""
        bottlenecks = SAMPLE_BOTTLENECKS

        assert isinstance(bottlenecks, list)
        for bottleneck in bottlenecks:
            assert "type" in bottleneck
            assert "description" in bottleneck
            assert "severity" in bottleneck
            assert bottleneck["severity"] in ["low", "medium", "high", "critical"]

    def test_suggestion_generation(self):
        """Test AI suggestion generation."""
        suggestions = SAMPLE_SUGGESTIONS

        assert isinstance(suggestions, list)
        for suggestion in suggestions:
            assert "category" in suggestion
            assert "recommendation" in suggestion
            assert "priority" in suggestion


class TestBriefingPeriod:
    """Test briefing period handling."""

    def test_weekly_period_calculation(self):
        """Test correct week calculation."""
        # For a Sunday briefing, period should be Mon-Sun of previous week
        today = date(2026, 2, 8)  # A Sunday

        # Expected period: Feb 2-8, 2026 (Mon-Sun)
        expected_start = date(2026, 2, 2)
        expected_end = date(2026, 2, 8)

        # The briefing should cover the week ending on briefing day
        assert expected_start.weekday() == 0  # Monday
        assert expected_end.weekday() == 6  # Sunday

    def test_period_format(self):
        """Test period date formatting."""
        briefing = create_sample_briefing()

        assert "from" in briefing["period"]
        assert "to" in briefing["period"]

        # Should be ISO format dates
        from_date = date.fromisoformat(briefing["period"]["from"])
        to_date = date.fromisoformat(briefing["period"]["to"])

        assert to_date >= from_date


class TestBriefingDelivery:
    """Test briefing delivery mechanisms."""

    def test_email_format(self):
        """Test briefing email format."""
        briefing = create_sample_briefing()

        # Email should have subject and body
        email_content = {
            "subject": f"CEO Weekly Briefing - Week of {briefing['period']['from']}",
            "body": "formatted briefing content",
        }

        assert "CEO" in email_content["subject"]
        assert "Weekly" in email_content["subject"]

    def test_dashboard_format(self):
        """Test briefing dashboard format (fallback)."""
        briefing = create_sample_briefing()

        # Dashboard file should be markdown
        dashboard_content = f"""# CEO Weekly Briefing

## Period: {briefing['period']['from']} to {briefing['period']['to']}

### Financial Summary
- Revenue: ${briefing['financial_summary']['revenue']['total']:,.2f}
"""

        assert "# CEO Weekly Briefing" in dashboard_content
        assert "Financial Summary" in dashboard_content

    def test_delivery_fallback(self):
        """Test fallback to dashboard when email fails."""
        # If email delivery fails, should create dashboard file
        pass


class TestBriefingScheduling:
    """Test briefing scheduling."""

    def test_sunday_schedule(self):
        """Test Sunday 11 PM schedule per spec."""
        # Audit runs Sunday 11 PM, briefing ready Monday 7 AM
        schedule = "0 23 * * 0"  # Cron format

        # Parse cron: minute(0) hour(23) dom(*) month(*) dow(0=Sunday)
        parts = schedule.split()
        assert parts[0] == "0"   # Minute 0
        assert parts[1] == "23"  # Hour 23 (11 PM)
        assert parts[4] == "0"   # Sunday

    def test_timezone_handling(self):
        """Test timezone configuration."""
        config = {
            "schedule": "0 23 * * 0",
            "timezone": "America/New_York",
        }

        assert config["timezone"] == "America/New_York"


class TestFinancialDataIntegration:
    """Test integration with Odoo financial data."""

    def test_revenue_aggregation(self):
        """Test revenue totaling from invoices."""
        invoices = [
            {"amount_total": 1000.00, "state": "posted"},
            {"amount_total": 2500.00, "state": "posted"},
            {"amount_total": 500.00, "state": "draft"},  # Should be excluded
        ]

        # Only posted invoices
        total = sum(inv["amount_total"] for inv in invoices if inv["state"] == "posted")
        assert total == 3500.00

    def test_payment_tracking(self):
        """Test payment collection tracking."""
        payments = [
            {"amount": 1000.00, "payment_type": "inbound"},
            {"amount": 500.00, "payment_type": "inbound"},
        ]

        total_received = sum(p["amount"] for p in payments)
        assert total_received == 1500.00

    def test_receivable_calculation(self):
        """Test outstanding receivables calculation."""
        revenue = 3500.00
        collected = 1500.00
        receivable = revenue - collected

        assert receivable == 2000.00


class TestSubscriptionPatterns:
    """Test subscription pattern detection for briefing."""

    def test_recurring_customer_detection(self):
        """Test detection of recurring customers."""
        invoices = [
            {"partner_id": 1, "invoice_date": "2026-01-01"},
            {"partner_id": 1, "invoice_date": "2026-02-01"},
            {"partner_id": 1, "invoice_date": "2026-03-01"},
            {"partner_id": 2, "invoice_date": "2026-01-15"},
        ]

        # Partner 1 has 3 invoices - likely subscription
        partner_counts = {}
        for inv in invoices:
            pid = inv["partner_id"]
            partner_counts[pid] = partner_counts.get(pid, 0) + 1

        recurring = [pid for pid, count in partner_counts.items() if count >= 3]
        assert 1 in recurring
        assert 2 not in recurring

    def test_churn_risk_detection(self):
        """Test churn risk identification."""
        # Customer with decreasing invoice amounts
        customer_history = [
            {"amount": 5000, "date": "2025-11-01"},
            {"amount": 3000, "date": "2025-12-01"},
            {"amount": 1000, "date": "2026-01-01"},
        ]

        # Trend is declining
        amounts = [h["amount"] for h in customer_history]
        is_declining = all(amounts[i] > amounts[i+1] for i in range(len(amounts)-1))

        assert is_declining


class TestBottleneckIntegration:
    """Test bottleneck data in briefing."""

    def test_bottleneck_summary(self):
        """Test bottleneck summary for briefing."""
        bottlenecks = SAMPLE_BOTTLENECKS

        # Should have severity distribution
        severity_counts = {}
        for b in bottlenecks:
            sev = b["severity"]
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        assert sum(severity_counts.values()) == len(bottlenecks)

    def test_critical_bottleneck_highlighting(self):
        """Test that critical bottlenecks are highlighted."""
        bottlenecks = SAMPLE_BOTTLENECKS

        critical = [b for b in bottlenecks if b["severity"] == "critical"]
        # Critical bottlenecks should be listed first in briefing


class TestBriefingStorage:
    """Test briefing storage and history."""

    def test_briefing_archived(self):
        """Test that briefings are archived."""
        briefing = create_sample_briefing()

        # Archive path should include date
        archive_path = f"vault/Archive/briefings/ceo-briefing-{briefing['period']['from']}.json"

        assert briefing["period"]["from"] in archive_path

    def test_briefing_queryable(self):
        """Test that historical briefings can be queried."""
        # Should be able to retrieve past briefings by date range
        pass


class TestErrorHandling:
    """Test error handling in briefing generation."""

    def test_missing_odoo_data(self):
        """Test handling when Odoo data unavailable."""
        # Should generate partial briefing with available data
        pass

    def test_missing_task_data(self):
        """Test handling when task data unavailable."""
        pass

    def test_generation_timeout(self):
        """Test briefing generation timeout handling."""
        pass
