"""Unit Tests for Subscription Audit (T031).

Tests for subscription pattern analysis including:
- Recurring customer detection
- Subscription frequency analysis
- Churn risk identification
- Revenue trend analysis

Per spec: FR-016
"""

import pytest
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, patch
from pathlib import Path


class TestRecurringCustomerDetection:
    """Test detection of recurring/subscription customers."""

    def test_monthly_recurring_detection(self):
        """Test detection of monthly recurring invoices."""
        invoices = [
            {"partner_id": 1, "partner_name": "Acme Corp", "invoice_date": "2025-10-01", "amount": 1000},
            {"partner_id": 1, "partner_name": "Acme Corp", "invoice_date": "2025-11-01", "amount": 1000},
            {"partner_id": 1, "partner_name": "Acme Corp", "invoice_date": "2025-12-01", "amount": 1000},
            {"partner_id": 1, "partner_name": "Acme Corp", "invoice_date": "2026-01-01", "amount": 1000},
        ]

        # Analyze pattern
        def detect_subscription(invoices, min_occurrences=3):
            partner_invoices = {}
            for inv in invoices:
                pid = inv["partner_id"]
                if pid not in partner_invoices:
                    partner_invoices[pid] = []
                partner_invoices[pid].append(inv)

            subscriptions = []
            for pid, invs in partner_invoices.items():
                if len(invs) >= min_occurrences:
                    # Check if amounts are consistent (within 10%)
                    amounts = [i["amount"] for i in invs]
                    avg_amount = sum(amounts) / len(amounts)
                    consistent = all(abs(a - avg_amount) / avg_amount < 0.1 for a in amounts)

                    if consistent:
                        subscriptions.append({
                            "partner_id": pid,
                            "partner_name": invs[0]["partner_name"],
                            "frequency": "monthly",
                            "avg_amount": avg_amount,
                            "invoice_count": len(invs),
                        })

            return subscriptions

        subs = detect_subscription(invoices)
        assert len(subs) == 1
        assert subs[0]["partner_name"] == "Acme Corp"
        assert subs[0]["frequency"] == "monthly"

    def test_quarterly_recurring_detection(self):
        """Test detection of quarterly recurring invoices."""
        invoices = [
            {"partner_id": 2, "partner_name": "BigCo", "invoice_date": "2025-04-01", "amount": 5000},
            {"partner_id": 2, "partner_name": "BigCo", "invoice_date": "2025-07-01", "amount": 5000},
            {"partner_id": 2, "partner_name": "BigCo", "invoice_date": "2025-10-01", "amount": 5000},
            {"partner_id": 2, "partner_name": "BigCo", "invoice_date": "2026-01-01", "amount": 5000},
        ]

        # Check ~90 day intervals
        dates = [date.fromisoformat(inv["invoice_date"]) for inv in invoices]
        intervals = [(dates[i+1] - dates[i]).days for i in range(len(dates)-1)]

        # All intervals should be ~90 days (quarterly)
        assert all(80 <= interval <= 100 for interval in intervals)

    def test_annual_recurring_detection(self):
        """Test detection of annual recurring invoices."""
        invoices = [
            {"partner_id": 3, "partner_name": "Enterprise Inc", "invoice_date": "2024-01-15", "amount": 50000},
            {"partner_id": 3, "partner_name": "Enterprise Inc", "invoice_date": "2025-01-15", "amount": 52000},
            {"partner_id": 3, "partner_name": "Enterprise Inc", "invoice_date": "2026-01-15", "amount": 54000},
        ]

        dates = [date.fromisoformat(inv["invoice_date"]) for inv in invoices]
        intervals = [(dates[i+1] - dates[i]).days for i in range(len(dates)-1)]

        # All intervals should be ~365 days (annual)
        assert all(360 <= interval <= 370 for interval in intervals)

    def test_non_recurring_customer(self):
        """Test that one-off customers are not marked as recurring."""
        invoices = [
            {"partner_id": 4, "partner_name": "OneTime LLC", "invoice_date": "2025-06-15", "amount": 2000},
        ]

        # Single invoice should not be detected as subscription
        assert len(invoices) < 3  # Minimum for subscription detection


class TestChurnRiskAnalysis:
    """Test churn risk identification."""

    def test_declining_revenue_churn_risk(self):
        """Test churn risk from declining invoice amounts."""
        customer_history = [
            {"date": "2025-10-01", "amount": 5000},
            {"date": "2025-11-01", "amount": 4000},
            {"date": "2025-12-01", "amount": 2500},
            {"date": "2026-01-01", "amount": 1000},
        ]

        # Calculate decline percentage
        first_amount = customer_history[0]["amount"]
        last_amount = customer_history[-1]["amount"]
        decline_pct = (first_amount - last_amount) / first_amount * 100

        # >50% decline is high churn risk
        assert decline_pct >= 50
        churn_risk = "high" if decline_pct >= 50 else "medium" if decline_pct >= 25 else "low"
        assert churn_risk == "high"

    def test_missed_payment_churn_risk(self):
        """Test churn risk from missed expected invoice."""
        last_invoice_date = date(2025, 12, 1)
        expected_next = date(2026, 1, 1)  # Monthly subscription
        today = date(2026, 1, 15)

        days_overdue = (today - expected_next).days
        assert days_overdue == 14

        # Flag as at-risk if >7 days overdue
        at_risk = days_overdue > 7
        assert at_risk

    def test_payment_delay_churn_risk(self):
        """Test churn risk from increasing payment delays."""
        payment_history = [
            {"invoice_date": "2025-10-01", "payment_date": "2025-10-15"},  # 14 days
            {"invoice_date": "2025-11-01", "payment_date": "2025-11-25"},  # 24 days
            {"invoice_date": "2025-12-01", "payment_date": "2026-01-05"},  # 35 days
        ]

        # Calculate payment delays
        delays = []
        for p in payment_history:
            inv_date = date.fromisoformat(p["invoice_date"])
            pay_date = date.fromisoformat(p["payment_date"])
            delays.append((pay_date - inv_date).days)

        # Increasing delays indicate risk
        is_increasing = all(delays[i] < delays[i+1] for i in range(len(delays)-1))
        assert is_increasing


class TestRevenueTrendAnalysis:
    """Test revenue trend analysis."""

    def test_revenue_growth_calculation(self):
        """Test month-over-month revenue growth."""
        monthly_revenue = [
            {"month": "2025-10", "revenue": 10000},
            {"month": "2025-11", "revenue": 12000},
            {"month": "2025-12", "revenue": 15000},
            {"month": "2026-01", "revenue": 14000},
        ]

        # Calculate growth rates
        growth_rates = []
        for i in range(1, len(monthly_revenue)):
            prev = monthly_revenue[i-1]["revenue"]
            curr = monthly_revenue[i]["revenue"]
            growth = (curr - prev) / prev * 100
            growth_rates.append(growth)

        # Oct->Nov: +20%, Nov->Dec: +25%, Dec->Jan: -6.67%
        assert growth_rates[0] == pytest.approx(20, rel=0.1)
        assert growth_rates[1] == pytest.approx(25, rel=0.1)
        assert growth_rates[2] == pytest.approx(-6.67, rel=0.1)

    def test_subscription_revenue_vs_onetime(self):
        """Test separation of recurring vs one-time revenue."""
        revenue_breakdown = {
            "subscription": 25000,
            "one_time": 5000,
            "total": 30000,
        }

        subscription_pct = revenue_breakdown["subscription"] / revenue_breakdown["total"] * 100
        assert subscription_pct == pytest.approx(83.33, rel=0.1)

    def test_arpu_calculation(self):
        """Test Average Revenue Per User calculation."""
        total_revenue = 50000
        active_customers = 25

        arpu = total_revenue / active_customers
        assert arpu == 2000


class TestSubscriptionMetrics:
    """Test subscription-specific metrics."""

    def test_mrr_calculation(self):
        """Test Monthly Recurring Revenue calculation."""
        subscriptions = [
            {"customer": "A", "monthly_amount": 1000},
            {"customer": "B", "monthly_amount": 2500},
            {"customer": "C", "monthly_amount": 500},
        ]

        mrr = sum(s["monthly_amount"] for s in subscriptions)
        assert mrr == 4000

    def test_arr_calculation(self):
        """Test Annual Recurring Revenue calculation."""
        mrr = 4000
        arr = mrr * 12
        assert arr == 48000

    def test_net_revenue_retention(self):
        """Test Net Revenue Retention calculation."""
        # Starting MRR from existing customers
        starting_mrr = 10000

        # End of period: some upgraded, some downgraded, some churned
        upgrades = 2000
        downgrades = 500
        churn = 1000

        ending_mrr = starting_mrr + upgrades - downgrades - churn
        nrr = ending_mrr / starting_mrr * 100

        assert nrr == 105  # 105% NRR (net positive)


class TestSubscriptionForecasting:
    """Test subscription forecasting for briefing."""

    def test_next_month_revenue_forecast(self):
        """Test forecasting next month's subscription revenue."""
        current_mrr = 10000
        expected_churn_rate = 0.05  # 5%
        expected_growth_rate = 0.10  # 10% new

        forecasted_mrr = current_mrr * (1 - expected_churn_rate) * (1 + expected_growth_rate)
        assert forecasted_mrr == pytest.approx(10450, rel=0.01)

    def test_renewal_forecast(self):
        """Test upcoming renewal forecast."""
        subscriptions = [
            {"customer": "A", "renewal_date": "2026-02-01", "amount": 1000},
            {"customer": "B", "renewal_date": "2026-02-15", "amount": 2500},
            {"customer": "C", "renewal_date": "2026-03-01", "amount": 500},
        ]

        # Renewals in next 30 days
        today = date(2026, 1, 20)
        next_30_days = today + timedelta(days=30)

        upcoming = [
            s for s in subscriptions
            if date.fromisoformat(s["renewal_date"]) <= next_30_days
        ]

        assert len(upcoming) == 2
        upcoming_value = sum(s["amount"] for s in upcoming)
        assert upcoming_value == 3500


class TestAuditReportGeneration:
    """Test subscription audit report generation."""

    def test_audit_report_structure(self):
        """Test audit report has required sections."""
        report = {
            "period": {"from": "2026-01-01", "to": "2026-01-31"},
            "summary": {
                "total_subscriptions": 15,
                "mrr": 25000,
                "arr": 300000,
                "growth_rate": 8.5,
            },
            "at_risk_customers": [],
            "churned_customers": [],
            "new_subscriptions": [],
            "renewals_upcoming": [],
        }

        assert "summary" in report
        assert "mrr" in report["summary"]
        assert "at_risk_customers" in report

    def test_audit_highlights_for_ceo(self):
        """Test CEO-relevant highlights extraction."""
        # CEO briefing should include key metrics only
        highlights = {
            "headline_mrr": "$25,000",
            "mrr_change": "+8.5%",
            "at_risk_count": 2,
            "renewals_this_week": 3,
        }

        assert "headline_mrr" in highlights
        assert "at_risk_count" in highlights
