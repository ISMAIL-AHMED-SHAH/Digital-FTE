"""CEO Weekly Briefing Generator (T036 - FR-013-015, FR-018).

Generates the Monday Morning CEO Briefing with:
- Financial summary from Odoo
- Task completion metrics
- Bottleneck identification
- Subscription health
- AI-generated suggestions

Scheduled to run Sunday 11 PM (via cron), with briefing ready Monday 7 AM.
"""

import logging
import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from .subscription_audit import SubscriptionAuditor, SubscriptionMetrics
from .bottleneck_detector import BottleneckDetector, TaskMetrics, Bottleneck

logger = logging.getLogger(__name__)


@dataclass
class BriefingConfig:
    """Configuration for CEO briefing generation.

    Attributes:
        vault_path: Path to vault for saving briefing
        archive_path: Path for briefing archive
        delivery_method: email or dashboard
        email_recipient: Email address for delivery
        sections: Which sections to include
        top_customers_limit: Number of top customers to show
    """
    vault_path: Path
    archive_path: Path | None = None
    delivery_method: str = "dashboard"
    email_recipient: str | None = None
    sections: list[str] | None = None
    top_customers_limit: int = 5


class CEOBriefingGenerator:
    """Generates weekly CEO briefing.

    Usage:
        generator = CEOBriefingGenerator(config)

        # Generate briefing
        briefing = await generator.generate(
            financial_data=odoo_summary,
            tasks=task_list,
            approvals=approval_list,
        )

        # Deliver briefing
        await generator.deliver(briefing)
    """

    DEFAULT_SECTIONS = [
        "financial_summary",
        "task_metrics",
        "bottlenecks",
        "subscription_health",
        "suggestions",
    ]

    def __init__(self, config: BriefingConfig):
        """Initialize the generator.

        Args:
            config: Briefing configuration
        """
        self.config = config
        self.sections = config.sections or self.DEFAULT_SECTIONS
        self.subscription_auditor = SubscriptionAuditor()
        self.bottleneck_detector = BottleneckDetector()

    def get_briefing_period(self, briefing_date: date | None = None) -> tuple[date, date]:
        """Calculate the briefing period (previous week).

        Args:
            briefing_date: Date of briefing (default: today)

        Returns:
            Tuple of (period_start, period_end)
        """
        today = briefing_date or date.today()

        # Find the most recent Sunday (end of period)
        days_since_sunday = (today.weekday() + 1) % 7
        period_end = today - timedelta(days=days_since_sunday)

        # Period starts on Monday
        period_start = period_end - timedelta(days=6)

        return period_start, period_end

    async def generate(
        self,
        financial_data: dict[str, Any] | None = None,
        invoices: list[dict[str, Any]] | None = None,
        tasks: list[dict[str, Any]] | None = None,
        approvals: list[dict[str, Any]] | None = None,
        api_calls: list[dict[str, Any]] | None = None,
        social_metrics: dict[str, Any] | None = None,
        briefing_date: date | None = None,
    ) -> dict[str, Any]:
        """Generate the CEO briefing.

        Args:
            financial_data: Financial summary from Odoo
            invoices: Invoice history for subscription analysis
            tasks: Task list for completion metrics
            approvals: Approval records for delay analysis
            api_calls: API call logs for performance analysis
            social_metrics: Social media engagement metrics
            briefing_date: Date of briefing

        Returns:
            Complete briefing dictionary
        """
        period_start, period_end = self.get_briefing_period(briefing_date)

        briefing = {
            "title": "CEO Weekly Briefing",
            "generated_at": datetime.now().isoformat(),
            "period": {
                "from": period_start.isoformat(),
                "to": period_end.isoformat(),
            },
        }

        # Generate each section
        if "financial_summary" in self.sections:
            briefing["financial_summary"] = self._generate_financial_section(
                financial_data, period_start, period_end
            )

        if "task_metrics" in self.sections and tasks:
            briefing["task_metrics"] = self._generate_task_section(tasks)

        if "bottlenecks" in self.sections:
            briefing["bottlenecks"] = self._generate_bottleneck_section(
                tasks, approvals, api_calls
            )

        if "subscription_health" in self.sections and invoices:
            briefing["subscription_health"] = self._generate_subscription_section(
                invoices, period_start, period_end
            )

        if "social_engagement" in self.sections and social_metrics:
            briefing["social_engagement"] = social_metrics

        if "suggestions" in self.sections:
            briefing["suggestions"] = self._generate_suggestions(briefing)

        logger.info(f"Generated CEO briefing for {period_start} to {period_end}")
        return briefing

    def _generate_financial_section(
        self,
        financial_data: dict[str, Any] | None,
        period_start: date,
        period_end: date
    ) -> dict[str, Any]:
        """Generate financial summary section.

        Args:
            financial_data: Odoo financial summary
            period_start: Period start date
            period_end: Period end date

        Returns:
            Financial section dictionary
        """
        if not financial_data:
            return {
                "status": "unavailable",
                "message": "Financial data not available",
            }

        revenue = financial_data.get("revenue", {})
        counts = financial_data.get("counts", {})
        top_customers = financial_data.get("top_customers", [])

        return {
            "status": "available",
            "revenue": {
                "total": revenue.get("total", 0),
                "collected": revenue.get("paid", 0),
                "outstanding": revenue.get("receivable", 0),
                "currency": financial_data.get("currency", "USD"),
            },
            "activity": {
                "invoices_posted": counts.get("invoices_posted", 0),
                "invoices_draft": counts.get("invoices_draft", 0),
                "payments_received": counts.get("payments_received", 0),
            },
            "top_customers": [
                {
                    "name": c.get("name"),
                    "revenue": c.get("revenue"),
                }
                for c in top_customers[:self.config.top_customers_limit]
            ],
        }

    def _generate_task_section(
        self,
        tasks: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Generate task metrics section.

        Args:
            tasks: List of tasks

        Returns:
            Task metrics dictionary
        """
        metrics = self.bottleneck_detector.analyze_tasks(tasks)

        return {
            "total": metrics.total_tasks,
            "completed": metrics.completed,
            "pending": metrics.pending,
            "overdue": metrics.overdue,
            "completion_rate": metrics.completion_rate,
            "avg_completion_time_hours": metrics.avg_completion_hours,
            "status": "healthy" if metrics.completion_rate >= 80 else "needs_attention",
        }

    def _generate_bottleneck_section(
        self,
        tasks: list[dict[str, Any]] | None,
        approvals: list[dict[str, Any]] | None,
        api_calls: list[dict[str, Any]] | None
    ) -> dict[str, Any]:
        """Generate bottleneck analysis section.

        Args:
            tasks: Task list
            approvals: Approval records
            api_calls: API call logs

        Returns:
            Bottleneck analysis dictionary
        """
        bottlenecks = self.bottleneck_detector.detect_bottlenecks(
            tasks=tasks,
            approvals=approvals,
            api_calls=api_calls,
        )

        critical_count = sum(1 for b in bottlenecks if b.severity == "critical")
        high_count = sum(1 for b in bottlenecks if b.severity == "high")

        return {
            "total": len(bottlenecks),
            "critical": critical_count,
            "high": high_count,
            "status": "critical" if critical_count > 0 else "warning" if high_count > 0 else "healthy",
            "items": [
                {
                    "type": b.type,
                    "description": b.description,
                    "severity": b.severity,
                    "recommendation": b.recommendation,
                }
                for b in bottlenecks[:3]  # Top 3 for executive summary
            ],
        }

    def _generate_subscription_section(
        self,
        invoices: list[dict[str, Any]],
        period_start: date,
        period_end: date
    ) -> dict[str, Any]:
        """Generate subscription health section.

        Args:
            invoices: Invoice history
            period_start: Period start
            period_end: Period end

        Returns:
            Subscription health dictionary
        """
        subscriptions = self.subscription_auditor.detect_subscriptions(invoices)
        at_risk = self.subscription_auditor.assess_churn_risk(subscriptions)
        metrics = self.subscription_auditor.calculate_metrics(subscriptions)

        high_risk = [r for r in at_risk if r.risk_level in ("high", "critical")]

        return {
            "mrr": metrics.mrr,
            "arr": metrics.arr,
            "total_subscriptions": metrics.total_subscriptions,
            "at_risk_count": len(high_risk),
            "at_risk_revenue": sum(r.revenue_at_risk for r in high_risk),
            "status": "critical" if len(high_risk) > 3 else "warning" if high_risk else "healthy",
            "at_risk_customers": [
                {
                    "name": r.partner_name,
                    "risk_level": r.risk_level,
                    "revenue_at_risk": r.revenue_at_risk,
                }
                for r in high_risk[:3]
            ],
        }

    def _generate_suggestions(
        self,
        briefing: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Generate AI suggestions based on briefing data.

        Args:
            briefing: Current briefing data

        Returns:
            List of suggestions
        """
        suggestions = []

        # Analyze financial section
        financial = briefing.get("financial_summary", {})
        if financial.get("status") == "available":
            revenue = financial.get("revenue", {})
            outstanding = revenue.get("outstanding", 0)
            total = revenue.get("total", 0)

            if total > 0 and outstanding / total > 0.3:
                suggestions.append({
                    "category": "collections",
                    "priority": "high",
                    "recommendation": f"Outstanding receivables are {outstanding/total*100:.0f}% of revenue. Consider follow-up on overdue invoices.",
                })

        # Analyze task section
        tasks = briefing.get("task_metrics", {})
        if tasks.get("overdue", 0) > 5:
            suggestions.append({
                "category": "operations",
                "priority": "high",
                "recommendation": f"{tasks['overdue']} tasks are overdue. Review and reprioritize or escalate blocked items.",
            })

        if tasks.get("completion_rate", 100) < 70:
            suggestions.append({
                "category": "productivity",
                "priority": "medium",
                "recommendation": f"Task completion rate is {tasks['completion_rate']}%. Consider reviewing workload distribution.",
            })

        # Analyze bottlenecks
        bottlenecks = briefing.get("bottlenecks", {})
        if bottlenecks.get("critical", 0) > 0:
            suggestions.append({
                "category": "process",
                "priority": "critical",
                "recommendation": "Critical bottlenecks detected. Immediate attention required - see bottleneck section.",
            })

        # Analyze subscription health
        subs = briefing.get("subscription_health", {})
        if subs.get("at_risk_count", 0) > 0:
            at_risk_rev = subs.get("at_risk_revenue", 0)
            suggestions.append({
                "category": "retention",
                "priority": "high",
                "recommendation": f"${at_risk_rev:,.0f} MRR at risk. Schedule customer success check-ins with at-risk accounts.",
            })

        # Sort by priority
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        suggestions.sort(key=lambda s: priority_order.get(s["priority"], 4))

        return suggestions[:5]  # Top 5 suggestions

    async def deliver(self, briefing: dict[str, Any]) -> dict[str, Any]:
        """Deliver the briefing via configured method.

        Args:
            briefing: Generated briefing

        Returns:
            Delivery result
        """
        # Save to vault
        vault_result = await self._save_to_vault(briefing)

        # Archive
        archive_result = await self._archive_briefing(briefing)

        # Deliver via configured method
        if self.config.delivery_method == "email" and self.config.email_recipient:
            delivery_result = await self._send_email(briefing)
        else:
            delivery_result = await self._save_to_dashboard(briefing)

        return {
            "success": True,
            "vault": vault_result,
            "archive": archive_result,
            "delivery": delivery_result,
        }

    async def _save_to_vault(self, briefing: dict[str, Any]) -> dict[str, Any]:
        """Save briefing to vault."""
        file_path = self.config.vault_path / "CEO_Briefing.md"

        content = self._format_as_markdown(briefing)

        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")

        return {"path": str(file_path)}

    async def _archive_briefing(self, briefing: dict[str, Any]) -> dict[str, Any]:
        """Archive briefing for historical reference."""
        if not self.config.archive_path:
            self.config.archive_path = self.config.vault_path / "Archive" / "briefings"

        archive_dir = self.config.archive_path
        archive_dir.mkdir(parents=True, exist_ok=True)

        period_from = briefing["period"]["from"]
        file_name = f"ceo-briefing-{period_from}.json"
        file_path = archive_dir / file_name

        file_path.write_text(
            json.dumps(briefing, indent=2, default=str),
            encoding="utf-8"
        )

        return {"path": str(file_path)}

    async def _save_to_dashboard(self, briefing: dict[str, Any]) -> dict[str, Any]:
        """Save briefing to dashboard (fallback delivery)."""
        dashboard_path = self.config.vault_path / "Dashboard.md"

        # Read existing dashboard
        if dashboard_path.exists():
            content = dashboard_path.read_text(encoding="utf-8")
        else:
            content = "# AI Employee Dashboard\n\n"

        # Add briefing section
        briefing_section = f"""
## Latest CEO Briefing

**Period**: {briefing['period']['from']} to {briefing['period']['to']}
**Generated**: {briefing['generated_at']}

[View Full Briefing](CEO_Briefing.md)

"""

        # Insert after header
        if "## Latest CEO Briefing" in content:
            # Replace existing section
            start = content.find("## Latest CEO Briefing")
            end = content.find("\n## ", start + 1)
            if end == -1:
                end = len(content)
            content = content[:start] + briefing_section + content[end:]
        else:
            # Add new section
            header_end = content.find("\n\n") + 2
            content = content[:header_end] + briefing_section + content[header_end:]

        dashboard_path.write_text(content, encoding="utf-8")

        return {"method": "dashboard", "path": str(dashboard_path)}

    async def _send_email(self, briefing: dict[str, Any]) -> dict[str, Any]:
        """Send briefing via email."""
        # Would integrate with email-ops skill
        # For now, return placeholder
        return {
            "method": "email",
            "recipient": self.config.email_recipient,
            "status": "pending_implementation",
        }

    def _format_as_markdown(self, briefing: dict[str, Any]) -> str:
        """Format briefing as markdown."""
        lines = [
            f"# {briefing['title']}",
            "",
            f"**Period**: {briefing['period']['from']} to {briefing['period']['to']}",
            f"**Generated**: {briefing['generated_at']}",
            "",
        ]

        # Financial Summary
        if "financial_summary" in briefing:
            fin = briefing["financial_summary"]
            if fin.get("status") == "available":
                rev = fin.get("revenue", {})
                lines.extend([
                    "## Financial Summary",
                    "",
                    f"- **Total Revenue**: {rev.get('currency', '$')}{rev.get('total', 0):,.2f}",
                    f"- **Collected**: {rev.get('currency', '$')}{rev.get('collected', 0):,.2f}",
                    f"- **Outstanding**: {rev.get('currency', '$')}{rev.get('outstanding', 0):,.2f}",
                    "",
                ])

        # Task Metrics
        if "task_metrics" in briefing:
            tasks = briefing["task_metrics"]
            lines.extend([
                "## Task Completion",
                "",
                f"- **Completed**: {tasks.get('completed', 0)}/{tasks.get('total', 0)} ({tasks.get('completion_rate', 0)}%)",
                f"- **Pending**: {tasks.get('pending', 0)}",
                f"- **Overdue**: {tasks.get('overdue', 0)}",
                "",
            ])

        # Bottlenecks
        if "bottlenecks" in briefing:
            bn = briefing["bottlenecks"]
            lines.extend([
                "## Bottlenecks",
                "",
                f"**Status**: {bn.get('status', 'unknown').upper()}",
                "",
            ])
            for item in bn.get("items", []):
                lines.append(f"- **{item['severity'].upper()}**: {item['description']}")
            lines.append("")

        # Subscription Health
        if "subscription_health" in briefing:
            subs = briefing["subscription_health"]
            lines.extend([
                "## Subscription Health",
                "",
                f"- **MRR**: ${subs.get('mrr', 0):,.2f}",
                f"- **ARR**: ${subs.get('arr', 0):,.2f}",
                f"- **At-Risk Accounts**: {subs.get('at_risk_count', 0)}",
                "",
            ])

        # Suggestions
        if "suggestions" in briefing:
            lines.extend([
                "## AI Suggestions",
                "",
            ])
            for i, sug in enumerate(briefing["suggestions"], 1):
                lines.append(f"{i}. **[{sug['priority'].upper()}]** {sug['recommendation']}")
            lines.append("")

        lines.extend([
            "---",
            "*Generated by AI Employee - Gold Tier*",
        ])

        return "\n".join(lines)


async def generate_briefing(
    config: BriefingConfig | None = None,
    **kwargs
) -> dict[str, Any]:
    """Convenience function to generate CEO briefing.

    Args:
        config: Optional configuration
        **kwargs: Data to pass to generate()

    Returns:
        Generated briefing
    """
    if config is None:
        config = BriefingConfig(
            vault_path=Path("./vault"),
        )

    generator = CEOBriefingGenerator(config)
    return await generator.generate(**kwargs)
