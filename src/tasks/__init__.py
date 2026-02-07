"""Scheduled Tasks for AI Employee.

This package contains task implementations that can be scheduled
via the scheduler or cron/Task Scheduler.

Bronze/Silver Tier tasks:
- daily_briefing: Generate daily briefing document

Gold Tier tasks (T033):
- ceo_briefing: Weekly CEO briefing with financial and operational summary
- subscription_audit: Subscription pattern analysis and churn detection
- bottleneck_detector: Task completion time analysis and bottleneck identification
- log_maintenance: Log compression, cleanup, and size monitoring
"""

__version__ = "1.0.0"

# Gold Tier exports (added as modules are implemented)
__all__ = [
    # CEO Briefing
    # "CEOBriefingGenerator",
    # "generate_briefing",
    # Subscription Audit
    # "SubscriptionAuditor",
    # Bottleneck Detection
    # "BottleneckDetector",
    # Log Maintenance
    # "run_maintenance",
]
