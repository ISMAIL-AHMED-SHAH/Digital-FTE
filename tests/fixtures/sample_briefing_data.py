"""
Sample CEO Briefing test data for testing.

This module provides sample data for testing the CEO Briefing generation
functionality including revenue data, task summaries, bottlenecks, and suggestions.
"""

from typing import Any
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
import json


# =============================================================================
# Gold Tier Exports (used by test_ceo_briefing.py)
# =============================================================================

SAMPLE_FINANCIAL_SUMMARY = {
    "period": {
        "from": "2026-01-27",
        "to": "2026-02-02",
    },
    "revenue": {
        "total": 45000.00,
        "paid": 38000.00,
        "receivable": 7000.00,
    },
    "counts": {
        "invoices_posted": 12,
        "invoices_draft": 3,
        "payments_received": 8,
    },
    "top_customers": [
        {"name": "Acme Corp", "partner_id": 1, "revenue": 15000.00, "invoice_count": 3},
        {"name": "TechStart Inc", "partner_id": 2, "revenue": 12000.00, "invoice_count": 2},
        {"name": "BigCo Ltd", "partner_id": 3, "revenue": 8000.00, "invoice_count": 4},
        {"name": "SmallBiz", "partner_id": 4, "revenue": 5500.00, "invoice_count": 2},
        {"name": "NewClient", "partner_id": 5, "revenue": 4500.00, "invoice_count": 1},
    ],
    "currency": "USD",
}

SAMPLE_TASK_METRICS = {
    "total_tasks": 45,
    "completed": 38,
    "pending": 5,
    "overdue": 2,
    "completion_rate": 84.4,
    "avg_completion_hours": 4.2,
    "median_completion_hours": 2.8,
}

SAMPLE_SOCIAL_METRICS = {
    "platforms": {
        "facebook": {"posts": 5, "reach": 12500, "engagement": 450},
        "instagram": {"posts": 3, "reach": 8200, "engagement": 620},
        "twitter": {"tweets": 8, "impressions": 15000, "engagement": 380},
    },
    "total_reach": 35700,
    "total_engagement": 1450,
}


def create_sample_briefing() -> dict:
    """Create a complete sample CEO briefing for Gold Tier tests."""
    return {
        "title": "CEO Weekly Briefing",
        "generated_at": datetime.now().isoformat(),
        "period": {
            "from": "2026-01-27",
            "to": "2026-02-02",
        },
        "financial_summary": SAMPLE_FINANCIAL_SUMMARY,
        "task_metrics": SAMPLE_TASK_METRICS,
        "bottlenecks": SAMPLE_BOTTLENECKS,
        "suggestions": SAMPLE_SUGGESTIONS,
        "social_engagement": SAMPLE_SOCIAL_METRICS,
        "subscription_health": {
            "mrr": 3500.00,
            "arr": 42000.00,
            "total_subscriptions": 3,
            "at_risk_count": 0,
            "at_risk_revenue": 0,
            "status": "healthy",
        },
    }


# =============================================================================
# Sample Revenue Data
# =============================================================================

SAMPLE_REVENUE_DATA = {
    "weekly_total": 15600.00,
    "month_to_date": 42500.00,
    "monthly_target": 50000.00,
    "target_percentage": 85.0,
    "trend": "on_track",
    "top_customers": [
        {"name": "Acme Corporation", "revenue": 8100.00, "invoice_count": 2},
        {"name": "TechStart Inc", "revenue": 4500.00, "invoice_count": 1},
        {"name": "Global Services Ltd", "revenue": 3000.00, "invoice_count": 1}
    ],
    "comparison": {
        "previous_week": 14200.00,
        "week_over_week_change": 9.86,
        "previous_month": 48000.00,
        "year_to_date": 95000.00
    }
}

SAMPLE_REVENUE_DATA_BEHIND = {
    "weekly_total": 8500.00,
    "month_to_date": 28000.00,
    "monthly_target": 50000.00,
    "target_percentage": 56.0,
    "trend": "behind",
    "top_customers": [
        {"name": "Acme Corporation", "revenue": 5000.00, "invoice_count": 1},
        {"name": "TechStart Inc", "revenue": 3500.00, "invoice_count": 1}
    ]
}

SAMPLE_REVENUE_DATA_AHEAD = {
    "weekly_total": 22000.00,
    "month_to_date": 55000.00,
    "monthly_target": 50000.00,
    "target_percentage": 110.0,
    "trend": "ahead",
    "top_customers": [
        {"name": "Enterprise Corp", "revenue": 15000.00, "invoice_count": 1},
        {"name": "Acme Corporation", "revenue": 7000.00, "invoice_count": 2}
    ]
}


# =============================================================================
# Sample Tasks Data
# =============================================================================

SAMPLE_COMPLETED_TASKS = [
    {
        "title": "Complete Q1 financial report",
        "completed_at": "2026-02-04T14:30:00",
        "duration_hours": 4.5,
        "expected_hours": 4.0,
        "category": "Finance"
    },
    {
        "title": "Review and approve vendor contracts",
        "completed_at": "2026-02-03T16:00:00",
        "duration_hours": 2.0,
        "expected_hours": 2.0,
        "category": "Legal"
    },
    {
        "title": "Update marketing calendar for February",
        "completed_at": "2026-02-02T11:00:00",
        "duration_hours": 1.5,
        "expected_hours": 1.0,
        "category": "Marketing"
    },
    {
        "title": "Process customer support tickets",
        "completed_at": "2026-02-05T09:00:00",
        "duration_hours": 3.0,
        "expected_hours": 2.5,
        "category": "Support"
    },
    {
        "title": "Schedule team meetings for next week",
        "completed_at": "2026-02-01T15:00:00",
        "duration_hours": 0.5,
        "expected_hours": 0.5,
        "category": "Admin"
    }
]

SAMPLE_TASKS_SUMMARY = {
    "completed_count": 5,
    "completed_tasks": SAMPLE_COMPLETED_TASKS,
    "total_hours_spent": 11.5,
    "total_hours_expected": 10.0,
    "efficiency_ratio": 0.87,
    "by_category": {
        "Finance": 1,
        "Legal": 1,
        "Marketing": 1,
        "Support": 1,
        "Admin": 1
    }
}


# =============================================================================
# Sample Bottlenecks Data
# =============================================================================

SAMPLE_BOTTLENECKS = [
    {
        "task_title": "Complete Q1 financial report",
        "expected_hours": 4.0,
        "actual_hours": 4.5,
        "delay_hours": 0.5,
        "reason": "Additional data reconciliation required",
        "severity": "low"
    },
    {
        "task_title": "Update marketing calendar for February",
        "expected_hours": 1.0,
        "actual_hours": 1.5,
        "delay_hours": 0.5,
        "reason": "Waiting for campaign assets from design team",
        "severity": "medium"
    },
    {
        "task_title": "Process customer support tickets",
        "expected_hours": 2.5,
        "actual_hours": 3.0,
        "delay_hours": 0.5,
        "reason": "Higher than expected ticket volume",
        "severity": "low"
    }
]

SAMPLE_BOTTLENECKS_SEVERE = [
    {
        "task_title": "Launch new product feature",
        "expected_hours": 8.0,
        "actual_hours": 16.0,
        "delay_hours": 8.0,
        "reason": "Unexpected integration issues with third-party API",
        "severity": "high"
    },
    {
        "task_title": "Complete security audit",
        "expected_hours": 4.0,
        "actual_hours": 10.0,
        "delay_hours": 6.0,
        "reason": "Discovery of additional vulnerabilities requiring remediation",
        "severity": "high"
    }
]


# =============================================================================
# Sample Suggestions Data
# =============================================================================

SAMPLE_COST_OPTIMIZATION = [
    "Consider canceling Unused Analytics Tool subscription ($99/month) - no logins in 45 days",
    "Premium Cloud Storage tier can be downgraded - only using 40% of capacity (save $50/month)",
    "Annual billing available for Project Management Tool - potential 20% savings"
]

SAMPLE_UPCOMING_DEADLINES = [
    {
        "title": "Q1 Tax Filing",
        "due_date": "2026-02-15",
        "days_remaining": 10,
        "priority": "high"
    },
    {
        "title": "Insurance Renewal",
        "due_date": "2026-02-20",
        "days_remaining": 15,
        "priority": "medium"
    },
    {
        "title": "Annual Report Submission",
        "due_date": "2026-02-28",
        "days_remaining": 23,
        "priority": "high"
    },
    {
        "title": "Vendor Contract Renewal",
        "due_date": "2026-03-01",
        "days_remaining": 24,
        "priority": "medium"
    }
]

SAMPLE_SUGGESTIONS = {
    "cost_optimization": SAMPLE_COST_OPTIMIZATION,
    "upcoming_deadlines": SAMPLE_UPCOMING_DEADLINES,
    "proactive_actions": [
        "Schedule Q1 review meeting with accountant",
        "Begin preparation for annual audit",
        "Review and update business continuity plan"
    ]
}


# =============================================================================
# Sample Subscription Data
# =============================================================================

SAMPLE_SUBSCRIPTIONS = [
    {
        "id": "sub_001",
        "name": "Cloud Storage Premium",
        "provider": "CloudCo",
        "monthly_cost": 149.00,
        "billing_date": 15,
        "last_used_at": "2026-02-04T10:30:00",
        "usage_count": 45,
        "category": "storage",
        "status": "active"
    },
    {
        "id": "sub_002",
        "name": "Project Management Tool",
        "provider": "TaskMaster",
        "monthly_cost": 49.00,
        "billing_date": 1,
        "last_used_at": "2026-02-05T09:00:00",
        "usage_count": 120,
        "category": "productivity",
        "status": "active"
    },
    {
        "id": "sub_003",
        "name": "Analytics Platform",
        "provider": "DataViz",
        "monthly_cost": 99.00,
        "billing_date": 10,
        "last_used_at": "2025-12-15T14:00:00",  # Over 45 days ago
        "usage_count": 5,
        "category": "analytics",
        "status": "active"
    },
    {
        "id": "sub_004",
        "name": "Email Marketing Service",
        "provider": "MailPro",
        "monthly_cost": 79.00,
        "billing_date": 20,
        "last_used_at": "2026-02-01T16:00:00",
        "usage_count": 8,
        "category": "marketing",
        "status": "active"
    }
]

SAMPLE_UNUSED_SUBSCRIPTIONS = [
    {
        "id": "sub_003",
        "name": "Analytics Platform",
        "provider": "DataViz",
        "monthly_cost": 99.00,
        "days_since_last_use": 52,
        "recommendation": "Consider canceling - no activity in 52 days"
    }
]


# =============================================================================
# Complete Sample Briefing
# =============================================================================

def get_sample_briefing(
    period_start: date | None = None,
    period_end: date | None = None
) -> dict:
    """
    Get a complete sample CEO briefing.

    Args:
        period_start: Start of reporting period (defaults to 7 days ago)
        period_end: End of reporting period (defaults to today)

    Returns:
        Complete briefing data dict
    """
    if period_end is None:
        period_end = date.today()
    if period_start is None:
        period_start = period_end - timedelta(days=7)

    return {
        "id": "briefing_2026_02_05",
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "generated_at": datetime.now().isoformat(),
        "generated_by": "AI Employee v0.3 (Gold Tier)",
        "executive_summary": (
            "Strong week with revenue 10% above target pace. "
            "5 tasks completed with minor delays in marketing and support. "
            "One subscription flagged for potential cancellation."
        ),
        "revenue_data": SAMPLE_REVENUE_DATA,
        "tasks_summary": SAMPLE_TASKS_SUMMARY,
        "bottlenecks": SAMPLE_BOTTLENECKS,
        "suggestions": SAMPLE_SUGGESTIONS,
        "vault_path": f"/Vault/Briefings/ceo_briefing_{period_end.isoformat()}.md",
        "status": "generated"
    }


def get_sample_briefing_markdown(briefing: dict | None = None) -> str:
    """
    Generate sample CEO briefing in markdown format.

    Args:
        briefing: Briefing data dict (uses sample if not provided)

    Returns:
        Formatted markdown string
    """
    if briefing is None:
        briefing = get_sample_briefing()

    revenue = briefing["revenue_data"]
    tasks = briefing["tasks_summary"]
    bottlenecks = briefing["bottlenecks"]
    suggestions = briefing["suggestions"]

    # Format top customers table
    customer_rows = "\n".join([
        f"| {c['name']} | ${c['revenue']:,.2f} |"
        for c in revenue["top_customers"]
    ])

    # Format bottleneck table
    bottleneck_rows = "\n".join([
        f"| {b['task_title']} | {b['expected_hours']}h | {b['actual_hours']}h | +{b['delay_hours']}h |"
        for b in bottlenecks
    ])

    # Format completed tasks
    task_list = "\n".join([
        f"- {t['title']} ({t['duration_hours']}h)"
        for t in tasks["completed_tasks"]
    ])

    # Format deadlines
    deadline_list = "\n".join([
        f"- **{d['title']}** - {d['due_date']} ({d['days_remaining']} days, {d['priority']} priority)"
        for d in suggestions["upcoming_deadlines"]
    ])

    # Format cost suggestions
    cost_list = "\n".join([f"- {s}" for s in suggestions["cost_optimization"]])

    return f"""# Monday Morning CEO Briefing

**Generated**: {briefing['generated_at']}
**Period**: {briefing['period_start']} to {briefing['period_end']}

## Executive Summary

{briefing['executive_summary']}

## Revenue

- **This Week**: ${revenue['weekly_total']:,.2f}
- **MTD**: ${revenue['month_to_date']:,.2f} ({revenue['target_percentage']:.0f}% of ${revenue['monthly_target']:,.2f} target)
- **Trend**: {revenue['trend'].replace('_', ' ').title()}

### Top Customers This Week

| Customer | Revenue |
|----------|---------|
{customer_rows}

## Completed Tasks ({tasks['completed_count']} total)

{task_list}

## Bottlenecks

| Task | Expected | Actual | Delay |
|------|----------|--------|-------|
{bottleneck_rows}

## Proactive Suggestions

### Cost Optimization

{cost_list}

### Upcoming Deadlines

{deadline_list}

---
*Generated by AI Employee v0.3 (Gold Tier)*
"""


# =============================================================================
# Empty/Edge Case Data
# =============================================================================

SAMPLE_EMPTY_WEEK = {
    "revenue_data": {
        "weekly_total": 0.0,
        "month_to_date": 0.0,
        "monthly_target": 50000.00,
        "target_percentage": 0.0,
        "trend": "behind",
        "top_customers": []
    },
    "tasks_summary": {
        "completed_count": 0,
        "completed_tasks": [],
        "total_hours_spent": 0,
        "total_hours_expected": 0,
        "efficiency_ratio": 1.0,
        "by_category": {}
    },
    "bottlenecks": [],
    "suggestions": {
        "cost_optimization": [],
        "upcoming_deadlines": [],
        "proactive_actions": ["Review watcher health - no activity detected this week"]
    }
}

SAMPLE_ODOO_UNAVAILABLE = {
    "revenue_data": {
        "weekly_total": None,
        "month_to_date": None,
        "monthly_target": 50000.00,
        "target_percentage": None,
        "trend": "unknown",
        "top_customers": [],
        "error": "Accounting data unavailable - Odoo connection failed"
    },
    "tasks_summary": SAMPLE_TASKS_SUMMARY,
    "bottlenecks": SAMPLE_BOTTLENECKS,
    "suggestions": SAMPLE_SUGGESTIONS
}


# =============================================================================
# Fixtures for pytest
# =============================================================================

def pytest_fixtures():
    """Return fixtures for pytest."""
    return {
        "sample_revenue": SAMPLE_REVENUE_DATA,
        "sample_tasks": SAMPLE_TASKS_SUMMARY,
        "sample_bottlenecks": SAMPLE_BOTTLENECKS,
        "sample_suggestions": SAMPLE_SUGGESTIONS,
        "sample_subscriptions": SAMPLE_SUBSCRIPTIONS,
        "sample_briefing": get_sample_briefing(),
        "sample_briefing_markdown": get_sample_briefing_markdown(),
        "sample_empty_week": SAMPLE_EMPTY_WEEK,
        "sample_odoo_unavailable": SAMPLE_ODOO_UNAVAILABLE
    }
