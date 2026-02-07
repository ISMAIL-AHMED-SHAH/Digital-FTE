"""Subscription Pattern Analysis (T034 - FR-016).

Analyzes invoice history to detect subscription patterns:
- Recurring customer identification
- Subscription frequency analysis (monthly, quarterly, annual)
- Churn risk detection
- Revenue trend analysis

Used by CEO Briefing to report on subscription health.
"""

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any
from collections import defaultdict
import statistics

logger = logging.getLogger(__name__)


@dataclass
class SubscriptionPattern:
    """Detected subscription pattern for a customer.

    Attributes:
        partner_id: Odoo partner ID
        partner_name: Customer name
        frequency: Detected frequency (monthly, quarterly, annual, irregular)
        avg_amount: Average invoice amount
        avg_interval_days: Average days between invoices
        invoice_count: Number of invoices analyzed
        consistency_score: 0-100 score for pattern consistency
        first_invoice_date: Date of first invoice
        last_invoice_date: Date of most recent invoice
    """
    partner_id: int
    partner_name: str
    frequency: str
    avg_amount: float
    avg_interval_days: float
    invoice_count: int
    consistency_score: float
    first_invoice_date: date
    last_invoice_date: date
    mrr_contribution: float = 0.0


@dataclass
class ChurnRisk:
    """Churn risk assessment for a customer.

    Attributes:
        partner_id: Odoo partner ID
        partner_name: Customer name
        risk_level: low, medium, high, critical
        risk_score: 0-100 score
        risk_factors: List of contributing factors
        expected_next_invoice: When next invoice was expected
        days_overdue: Days since expected invoice (if overdue)
        revenue_at_risk: Monthly revenue that could be lost
    """
    partner_id: int
    partner_name: str
    risk_level: str
    risk_score: float
    risk_factors: list[str]
    expected_next_invoice: date | None
    days_overdue: int
    revenue_at_risk: float


@dataclass
class SubscriptionMetrics:
    """Subscription metrics summary.

    Attributes:
        total_subscriptions: Count of detected subscriptions
        mrr: Monthly Recurring Revenue
        arr: Annual Recurring Revenue
        subscription_revenue_pct: % of revenue from subscriptions
        avg_subscription_value: Average subscription amount
        churn_risk_count: Number of at-risk customers
        new_subscriptions_count: New subscriptions this period
        churned_count: Churned subscriptions this period
    """
    total_subscriptions: int = 0
    mrr: float = 0.0
    arr: float = 0.0
    subscription_revenue_pct: float = 0.0
    avg_subscription_value: float = 0.0
    churn_risk_count: int = 0
    new_subscriptions_count: int = 0
    churned_count: int = 0


class SubscriptionAuditor:
    """Analyzes invoice data to detect subscription patterns.

    Usage:
        auditor = SubscriptionAuditor()

        # Analyze invoices from Odoo
        subscriptions = auditor.detect_subscriptions(invoices)

        # Check churn risk
        at_risk = auditor.assess_churn_risk(subscriptions, today=date.today())

        # Get summary metrics
        metrics = auditor.calculate_metrics(subscriptions)
    """

    # Frequency detection thresholds (days)
    MONTHLY_MIN = 25
    MONTHLY_MAX = 35
    QUARTERLY_MIN = 80
    QUARTERLY_MAX = 100
    ANNUAL_MIN = 350
    ANNUAL_MAX = 380

    # Minimum invoices to consider a subscription
    MIN_INVOICES = 3

    # Consistency threshold (standard deviation as % of mean)
    CONSISTENCY_THRESHOLD = 0.15

    def __init__(self):
        """Initialize the auditor."""
        pass

    def detect_subscriptions(
        self,
        invoices: list[dict[str, Any]],
        min_invoices: int | None = None
    ) -> list[SubscriptionPattern]:
        """Detect subscription patterns in invoice history.

        Args:
            invoices: List of invoice dicts with partner_id, partner_name,
                     invoice_date, amount_total, state
            min_invoices: Minimum invoices to consider (default: 3)

        Returns:
            List of detected SubscriptionPattern objects
        """
        min_inv = min_invoices or self.MIN_INVOICES

        # Group invoices by partner
        by_partner: dict[int, list[dict]] = defaultdict(list)
        for inv in invoices:
            if inv.get("state") == "posted":  # Only posted invoices
                by_partner[inv["partner_id"]].append(inv)

        subscriptions = []

        for partner_id, partner_invoices in by_partner.items():
            if len(partner_invoices) < min_inv:
                continue

            # Sort by date
            partner_invoices.sort(key=lambda x: x["invoice_date"])

            # Analyze pattern
            pattern = self._analyze_pattern(partner_id, partner_invoices)
            if pattern:
                subscriptions.append(pattern)

        logger.info(f"Detected {len(subscriptions)} subscription patterns")
        return subscriptions

    def _analyze_pattern(
        self,
        partner_id: int,
        invoices: list[dict]
    ) -> SubscriptionPattern | None:
        """Analyze invoice pattern for a single partner.

        Args:
            partner_id: Partner ID
            invoices: Sorted list of invoices for this partner

        Returns:
            SubscriptionPattern if pattern detected, None otherwise
        """
        if len(invoices) < self.MIN_INVOICES:
            return None

        partner_name = invoices[0].get("partner_name", f"Partner {partner_id}")

        # Parse dates
        dates = []
        amounts = []
        for inv in invoices:
            inv_date = inv["invoice_date"]
            if isinstance(inv_date, str):
                inv_date = date.fromisoformat(inv_date)
            dates.append(inv_date)
            amounts.append(inv["amount_total"])

        # Calculate intervals
        intervals = []
        for i in range(1, len(dates)):
            interval = (dates[i] - dates[i-1]).days
            intervals.append(interval)

        if not intervals:
            return None

        # Calculate statistics
        avg_interval = statistics.mean(intervals)
        avg_amount = statistics.mean(amounts)

        # Calculate consistency score
        if len(intervals) > 1:
            std_interval = statistics.stdev(intervals)
            consistency = max(0, 100 - (std_interval / avg_interval * 100))
        else:
            consistency = 50  # Single interval, medium confidence

        # Detect frequency
        frequency = self._classify_frequency(avg_interval)

        # Only consider as subscription if reasonably consistent
        if consistency < 40 and frequency == "irregular":
            return None

        # Calculate MRR contribution
        if frequency == "monthly":
            mrr = avg_amount
        elif frequency == "quarterly":
            mrr = avg_amount / 3
        elif frequency == "annual":
            mrr = avg_amount / 12
        else:
            mrr = avg_amount / (avg_interval / 30)  # Approximate

        return SubscriptionPattern(
            partner_id=partner_id,
            partner_name=partner_name,
            frequency=frequency,
            avg_amount=round(avg_amount, 2),
            avg_interval_days=round(avg_interval, 1),
            invoice_count=len(invoices),
            consistency_score=round(consistency, 1),
            first_invoice_date=dates[0],
            last_invoice_date=dates[-1],
            mrr_contribution=round(mrr, 2),
        )

    def _classify_frequency(self, avg_interval: float) -> str:
        """Classify subscription frequency based on average interval.

        Args:
            avg_interval: Average days between invoices

        Returns:
            Frequency string: monthly, quarterly, annual, irregular
        """
        if self.MONTHLY_MIN <= avg_interval <= self.MONTHLY_MAX:
            return "monthly"
        elif self.QUARTERLY_MIN <= avg_interval <= self.QUARTERLY_MAX:
            return "quarterly"
        elif self.ANNUAL_MIN <= avg_interval <= self.ANNUAL_MAX:
            return "annual"
        else:
            return "irregular"

    def assess_churn_risk(
        self,
        subscriptions: list[SubscriptionPattern],
        today: date | None = None
    ) -> list[ChurnRisk]:
        """Assess churn risk for subscription customers.

        Args:
            subscriptions: List of detected subscriptions
            today: Current date (default: today)

        Returns:
            List of ChurnRisk for at-risk customers
        """
        today = today or date.today()
        at_risk = []

        for sub in subscriptions:
            risk_factors = []
            risk_score = 0

            # Calculate expected next invoice
            if sub.frequency == "monthly":
                expected_interval = 30
            elif sub.frequency == "quarterly":
                expected_interval = 90
            elif sub.frequency == "annual":
                expected_interval = 365
            else:
                expected_interval = int(sub.avg_interval_days)

            expected_next = sub.last_invoice_date + timedelta(days=expected_interval)
            days_overdue = (today - expected_next).days

            # Factor 1: Overdue invoice
            if days_overdue > 0:
                risk_factors.append(f"Invoice {days_overdue} days overdue")
                risk_score += min(50, days_overdue * 2)

            # Factor 2: Low consistency (erratic payment pattern)
            if sub.consistency_score < 60:
                risk_factors.append("Inconsistent payment pattern")
                risk_score += 20

            # Factor 3: Declining amounts (would need historical comparison)
            # TODO: Compare recent amounts to historical average

            # Factor 4: Long time since last invoice relative to pattern
            days_since_last = (today - sub.last_invoice_date).days
            if days_since_last > expected_interval * 1.5:
                risk_factors.append("Extended gap since last invoice")
                risk_score += 25

            # Classify risk level
            if risk_score >= 70:
                risk_level = "critical"
            elif risk_score >= 50:
                risk_level = "high"
            elif risk_score >= 30:
                risk_level = "medium"
            elif risk_score > 0:
                risk_level = "low"
            else:
                continue  # No risk detected

            at_risk.append(ChurnRisk(
                partner_id=sub.partner_id,
                partner_name=sub.partner_name,
                risk_level=risk_level,
                risk_score=min(100, risk_score),
                risk_factors=risk_factors,
                expected_next_invoice=expected_next if days_overdue > 0 else None,
                days_overdue=max(0, days_overdue),
                revenue_at_risk=sub.mrr_contribution,
            ))

        # Sort by risk score descending
        at_risk.sort(key=lambda x: x.risk_score, reverse=True)

        logger.info(f"Identified {len(at_risk)} at-risk customers")
        return at_risk

    def calculate_metrics(
        self,
        subscriptions: list[SubscriptionPattern],
        total_revenue: float | None = None
    ) -> SubscriptionMetrics:
        """Calculate subscription metrics summary.

        Args:
            subscriptions: List of detected subscriptions
            total_revenue: Total revenue for period (to calculate %)

        Returns:
            SubscriptionMetrics summary
        """
        if not subscriptions:
            return SubscriptionMetrics()

        mrr = sum(s.mrr_contribution for s in subscriptions)
        arr = mrr * 12

        avg_value = statistics.mean(s.avg_amount for s in subscriptions)

        # Calculate subscription revenue percentage
        subscription_revenue = sum(s.avg_amount * s.invoice_count for s in subscriptions)
        if total_revenue and total_revenue > 0:
            sub_pct = (subscription_revenue / total_revenue) * 100
        else:
            sub_pct = 0

        return SubscriptionMetrics(
            total_subscriptions=len(subscriptions),
            mrr=round(mrr, 2),
            arr=round(arr, 2),
            subscription_revenue_pct=round(sub_pct, 1),
            avg_subscription_value=round(avg_value, 2),
        )

    def generate_report(
        self,
        subscriptions: list[SubscriptionPattern],
        at_risk: list[ChurnRisk],
        metrics: SubscriptionMetrics,
        period_from: date,
        period_to: date
    ) -> dict[str, Any]:
        """Generate subscription audit report.

        Args:
            subscriptions: Detected subscriptions
            at_risk: Churn risk assessments
            metrics: Calculated metrics
            period_from: Report period start
            period_to: Report period end

        Returns:
            Report dictionary for CEO briefing
        """
        return {
            "period": {
                "from": period_from.isoformat(),
                "to": period_to.isoformat(),
            },
            "summary": {
                "total_subscriptions": metrics.total_subscriptions,
                "mrr": metrics.mrr,
                "arr": metrics.arr,
                "subscription_revenue_pct": metrics.subscription_revenue_pct,
                "avg_subscription_value": metrics.avg_subscription_value,
                "at_risk_count": len([r for r in at_risk if r.risk_level in ("high", "critical")]),
            },
            "subscriptions_by_frequency": {
                "monthly": len([s for s in subscriptions if s.frequency == "monthly"]),
                "quarterly": len([s for s in subscriptions if s.frequency == "quarterly"]),
                "annual": len([s for s in subscriptions if s.frequency == "annual"]),
                "irregular": len([s for s in subscriptions if s.frequency == "irregular"]),
            },
            "at_risk_customers": [
                {
                    "name": r.partner_name,
                    "risk_level": r.risk_level,
                    "revenue_at_risk": r.revenue_at_risk,
                    "factors": r.risk_factors,
                }
                for r in at_risk[:5]  # Top 5 at-risk
            ],
            "top_subscriptions": [
                {
                    "name": s.partner_name,
                    "mrr": s.mrr_contribution,
                    "frequency": s.frequency,
                }
                for s in sorted(subscriptions, key=lambda x: x.mrr_contribution, reverse=True)[:5]
            ],
        }
