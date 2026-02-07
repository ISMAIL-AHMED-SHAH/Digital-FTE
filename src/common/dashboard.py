"""Dashboard Writer for Silver Tier.

Updates Dashboard.md in the vault root with:
- Approval queue status (pending, recent approvals/rejections)
- Watcher status (running, paused, errors)
- Recent activity summary
- System health metrics

The dashboard is designed to be viewed in Obsidian for quick status checks.
"""

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from src.common.vault import get_vault, Vault

logger = logging.getLogger(__name__)


class DashboardSection:
    """Dashboard section identifiers."""
    HEADER = "header"
    APPROVAL_QUEUE = "approval_queue"
    RECENT_ACTIVITY = "recent_activity"
    WATCHER_STATUS = "watcher_status"
    SYSTEM_HEALTH = "system_health"
    ALERTS = "alerts"


def _format_timestamp(dt: datetime | None) -> str:
    """Format datetime for display."""
    if dt is None:
        return "Never"
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")


def _format_relative_time(dt: datetime | None) -> str:
    """Format datetime as relative time."""
    if dt is None:
        return "Never"

    now = datetime.now(timezone.utc)
    diff = now - dt

    if diff.total_seconds() < 60:
        return "Just now"
    elif diff.total_seconds() < 3600:
        minutes = int(diff.total_seconds() / 60)
        return f"{minutes}m ago"
    elif diff.total_seconds() < 86400:
        hours = int(diff.total_seconds() / 3600)
        return f"{hours}h ago"
    else:
        days = int(diff.total_seconds() / 86400)
        return f"{days}d ago"


def _get_status_emoji(status: str) -> str:
    """Get emoji for status."""
    return {
        "running": "🟢",
        "paused": "🟡",
        "stopped": "🔴",
        "error": "❌",
        "pending": "⏳",
        "approved": "✅",
        "rejected": "❌",
        "expired": "⏰",
    }.get(status.lower(), "⚪")


class DashboardWriter:
    """Writer for updating Dashboard.md in the vault.

    Usage:
        dashboard = DashboardWriter(vault)

        # Update approval queue
        dashboard.update_approval_queue(
            pending_count=3,
            recent_approvals=[...],
            recent_rejections=[...]
        )

        # Update watcher status
        dashboard.update_watcher_status({
            "gmail_watcher": {"status": "running", "memory_mb": 45},
            "approval_watcher": {"status": "running", "memory_mb": 30},
        })

        # Write full dashboard
        dashboard.write()
    """

    def __init__(self, vault: Vault | None = None):
        """Initialize dashboard writer.

        Args:
            vault: Vault instance (default: from env)
        """
        self.vault = vault or get_vault()
        self.dashboard_path = self.vault.vault_path / "Dashboard.md"

        # Data storage
        self._approval_queue: dict[str, Any] = {}
        self._watcher_status: dict[str, dict[str, Any]] = {}
        self._recent_activity: list[dict[str, Any]] = []
        self._system_health: dict[str, Any] = {}
        self._alerts: list[dict[str, Any]] = []
        self._last_update: datetime | None = None

    def update_approval_queue(
        self,
        pending_count: int = 0,
        recent_approvals: list[dict[str, Any]] | None = None,
        recent_rejections: list[dict[str, Any]] | None = None,
        expired_today: int = 0
    ) -> None:
        """Update approval queue status.

        Args:
            pending_count: Number of pending approvals
            recent_approvals: List of recently approved actions
            recent_rejections: List of recently rejected actions
            expired_today: Number of expired approvals today
        """
        self._approval_queue = {
            "pending_count": pending_count,
            "recent_approvals": recent_approvals or [],
            "recent_rejections": recent_rejections or [],
            "expired_today": expired_today,
            "updated_at": datetime.now(timezone.utc)
        }

    def update_watcher_status(
        self,
        watchers: dict[str, dict[str, Any]]
    ) -> None:
        """Update watcher status.

        Args:
            watchers: Dict of watcher name -> status dict
                     Each status dict should have: status, memory_mb, last_run, errors_count
        """
        self._watcher_status = watchers

    def add_activity(
        self,
        action_type: str,
        target: str,
        result: str,
        timestamp: datetime | None = None
    ) -> None:
        """Add an activity to the recent activity list.

        Args:
            action_type: Type of action
            target: Target of the action
            result: Result (success, failed, etc.)
            timestamp: When the action occurred
        """
        self._recent_activity.append({
            "action_type": action_type,
            "target": target,
            "result": result,
            "timestamp": timestamp or datetime.now(timezone.utc)
        })

        # Keep only last 20 activities
        self._recent_activity = self._recent_activity[-20:]

    def update_system_health(
        self,
        total_memory_mb: float,
        memory_budget_mb: float,
        db_size_mb: float,
        uptime_hours: float
    ) -> None:
        """Update system health metrics.

        Args:
            total_memory_mb: Total memory usage
            memory_budget_mb: Memory budget
            db_size_mb: Idempotency database size
            uptime_hours: Total uptime in hours
        """
        self._system_health = {
            "total_memory_mb": total_memory_mb,
            "memory_budget_mb": memory_budget_mb,
            "memory_percent": (total_memory_mb / memory_budget_mb) * 100 if memory_budget_mb > 0 else 0,
            "db_size_mb": db_size_mb,
            "uptime_hours": uptime_hours,
            "updated_at": datetime.now(timezone.utc)
        }

    def add_alert(
        self,
        severity: str,
        title: str,
        timestamp: datetime | None = None
    ) -> None:
        """Add an alert to the alerts section.

        Args:
            severity: Alert severity
            title: Alert title
            timestamp: When the alert was created
        """
        self._alerts.append({
            "severity": severity,
            "title": title,
            "timestamp": timestamp or datetime.now(timezone.utc)
        })

        # Keep only last 10 alerts
        self._alerts = self._alerts[-10:]

    def _generate_header(self) -> str:
        """Generate dashboard header."""
        now = datetime.now(timezone.utc)
        return f"""# 📊 AI Employee Dashboard

**Last Updated**: {_format_timestamp(now)}

---
"""

    def _generate_approval_queue_section(self) -> str:
        """Generate approval queue section."""
        data = self._approval_queue
        pending = data.get("pending_count", 0)
        approvals = data.get("recent_approvals", [])
        rejections = data.get("recent_rejections", [])
        expired = data.get("expired_today", 0)

        section = f"""## ⏳ Approval Queue

| Metric | Count |
|--------|-------|
| Pending Approvals | **{pending}** |
| Approved Today | {len(approvals)} |
| Rejected Today | {len(rejections)} |
| Expired Today | {expired} |

"""

        if pending > 0:
            section += f"📋 **[View Pending Approvals](Pending_Approval/)** ({pending} waiting)\n\n"

        if approvals:
            section += "### Recent Approvals\n\n"
            for item in approvals[-5:]:
                emoji = _get_status_emoji("approved")
                section += f"- {emoji} {item.get('action_type', 'Action')} → {item.get('target', 'Unknown')} ({_format_relative_time(item.get('timestamp'))})\n"
            section += "\n"

        if rejections:
            section += "### Recent Rejections\n\n"
            for item in rejections[-5:]:
                emoji = _get_status_emoji("rejected")
                section += f"- {emoji} {item.get('action_type', 'Action')} → {item.get('target', 'Unknown')} ({_format_relative_time(item.get('timestamp'))})\n"
            section += "\n"

        return section

    def _generate_watcher_status_section(self) -> str:
        """Generate watcher status section."""
        if not self._watcher_status:
            return """## 🔄 Watcher Status

*No watcher data available*

"""

        section = """## 🔄 Watcher Status

| Watcher | Status | Memory | Last Run | Errors |
|---------|--------|--------|----------|--------|
"""

        for name, status in self._watcher_status.items():
            emoji = _get_status_emoji(status.get("status", "unknown"))
            status_str = status.get("status", "unknown")
            memory = f"{status.get('memory_mb', 0):.1f}MB"
            last_run = _format_relative_time(status.get("last_run"))
            errors = status.get("errors_count", 0)

            display_name = name.replace("_", " ").title()
            section += f"| {display_name} | {emoji} {status_str} | {memory} | {last_run} | {errors} |\n"

        section += "\n"
        return section

    def _generate_recent_activity_section(self) -> str:
        """Generate recent activity section."""
        if not self._recent_activity:
            return """## 📋 Recent Activity

*No recent activity*

"""

        section = """## 📋 Recent Activity

| Time | Action | Target | Result |
|------|--------|--------|--------|
"""

        for activity in reversed(self._recent_activity[-10:]):
            time_str = _format_relative_time(activity.get("timestamp"))
            action = activity.get("action_type", "Unknown")
            target = activity.get("target", "Unknown")
            result = activity.get("result", "Unknown")
            emoji = "✅" if result == "success" else "❌" if result == "failed" else "⚪"

            section += f"| {time_str} | {action} | {target} | {emoji} {result} |\n"

        section += "\n"
        return section

    def _generate_system_health_section(self) -> str:
        """Generate system health section."""
        if not self._system_health:
            return """## 💚 System Health

*No health data available*

"""

        health = self._system_health
        memory_percent = health.get("memory_percent", 0)

        # Memory bar visualization
        bar_width = 20
        filled = int((memory_percent / 100) * bar_width)
        bar = "█" * filled + "░" * (bar_width - filled)

        status_emoji = "🟢" if memory_percent < 70 else "🟡" if memory_percent < 90 else "🔴"

        section = f"""## 💚 System Health

### Memory Usage

{status_emoji} `[{bar}]` {memory_percent:.0f}%

- **Used**: {health.get('total_memory_mb', 0):.1f}MB / {health.get('memory_budget_mb', 0):.0f}MB

### Other Metrics

- **Database Size**: {health.get('db_size_mb', 0):.2f}MB
- **Uptime**: {health.get('uptime_hours', 0):.1f} hours

"""
        return section

    def _generate_alerts_section(self) -> str:
        """Generate alerts section."""
        if not self._alerts:
            return """## 🔔 Recent Alerts

*No recent alerts*

"""

        section = """## 🔔 Recent Alerts

"""

        for alert in reversed(self._alerts[-5:]):
            severity = alert.get("severity", "info")
            emoji = _get_status_emoji(severity) if severity in ("error", "critical") else "⚠️"
            title = alert.get("title", "Unknown")
            time_str = _format_relative_time(alert.get("timestamp"))

            section += f"- {emoji} **{title}** ({time_str})\n"

        section += "\n📁 **[View All Alerts](Alerts/)**\n\n"
        return section

    def _generate_footer(self) -> str:
        """Generate dashboard footer."""
        return """---

*This dashboard is automatically updated by the AI Employee system.*
*Refresh the page to see the latest status.*
"""

    def generate(self) -> str:
        """Generate the full dashboard content.

        Returns:
            Complete dashboard markdown
        """
        sections = [
            self._generate_header(),
            self._generate_approval_queue_section(),
            self._generate_watcher_status_section(),
            self._generate_recent_activity_section(),
            self._generate_system_health_section(),
            self._generate_alerts_section(),
            self._generate_footer()
        ]

        return "\n".join(sections)

    def write(self) -> Path:
        """Write the dashboard to the vault.

        Returns:
            Path to the dashboard file
        """
        content = self.generate()
        self.dashboard_path.write_text(content, encoding="utf-8")
        self._last_update = datetime.now(timezone.utc)

        logger.debug(f"Updated dashboard: {self.dashboard_path}")
        return self.dashboard_path


# Module-level convenience instance
_default_writer: DashboardWriter | None = None


def get_dashboard_writer(vault: Vault | None = None) -> DashboardWriter:
    """Get the default dashboard writer instance."""
    global _default_writer
    if _default_writer is None:
        _default_writer = DashboardWriter(vault)
    return _default_writer


def update_approval_queue(**kwargs) -> None:
    """Convenience function to update approval queue."""
    get_dashboard_writer().update_approval_queue(**kwargs)
    get_dashboard_writer().write()


def update_watcher_status(watchers: dict[str, dict[str, Any]]) -> None:
    """Convenience function to update watcher status."""
    get_dashboard_writer().update_watcher_status(watchers)
    get_dashboard_writer().write()


def add_activity(action_type: str, target: str, result: str) -> None:
    """Convenience function to add activity."""
    get_dashboard_writer().add_activity(action_type, target, result)
    get_dashboard_writer().write()
