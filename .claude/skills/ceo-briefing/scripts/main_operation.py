#!/usr/bin/env python3
"""CEO Briefing Skill Entry Point (T038).

Generates weekly CEO briefings by aggregating data from multiple sources.

Usage:
    python .claude/skills/ceo-briefing/scripts/main_operation.py generate
    python .claude/skills/ceo-briefing/scripts/main_operation.py generate --date 2026-02-01
    python .claude/skills/ceo-briefing/scripts/main_operation.py show
    python .claude/skills/ceo-briefing/scripts/main_operation.py archive

Operations:
    generate    Generate CEO briefing (runs full analysis)
    show        Display the current briefing
    archive     List archived briefings
    health      Check subscription health only
    bottlenecks Check bottlenecks only
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))


def output_json(data: dict) -> None:
    """Output data as JSON to stdout."""
    print(json.dumps(data, indent=2, default=str))


def output_error(message: str, code: str = "SKILL_ERROR") -> None:
    """Output error as JSON."""
    output_json({
        "success": False,
        "error": {
            "code": code,
            "message": message,
        }
    })
    sys.exit(1)


def load_config() -> dict:
    """Load configuration from environment and config files."""
    config = {
        "vault_path": Path(os.environ.get("VAULT_PATH", str(PROJECT_ROOT / "vault"))),
        "delivery_method": os.environ.get("CEO_BRIEFING_DELIVERY", "dashboard"),
        "email_recipient": os.environ.get("CEO_BRIEFING_EMAIL"),
        "odoo_available": bool(os.environ.get("ODOO_URL")),
    }
    return config


async def get_financial_data() -> dict | None:
    """Get financial data from Odoo MCP."""
    if not os.environ.get("ODOO_URL"):
        return None

    return {
        "success": True,
        "note": "Would fetch from Odoo MCP",
        "revenue": {"total": 0, "paid": 0, "receivable": 0},
        "counts": {"invoices_posted": 0, "payments_received": 0},
        "top_customers": [],
    }


async def get_task_data() -> list[dict]:
    """Get task data from vault."""
    config = load_config()
    vault_path = config["vault_path"]

    tasks = []

    needs_action = vault_path / "Needs_Action"
    if needs_action.exists():
        for file in needs_action.glob("*.md"):
            tasks.append({
                "id": file.stem,
                "status": "pending",
                "created_at": datetime.fromtimestamp(file.stat().st_ctime).isoformat(),
                "source": str(file),
            })

    done = vault_path / "Done"
    if done.exists():
        for file in done.glob("*.md"):
            tasks.append({
                "id": file.stem,
                "status": "completed",
                "created_at": datetime.fromtimestamp(file.stat().st_ctime).isoformat(),
                "completed_at": datetime.fromtimestamp(file.stat().st_mtime).isoformat(),
                "source": str(file),
            })

    return tasks


async def get_approval_data() -> list[dict]:
    """Get approval data from data directory."""
    approval_dir = PROJECT_ROOT / "data" / "approvals"

    approvals = []

    if approval_dir.exists():
        for file in approval_dir.glob("*.json"):
            try:
                with open(file, "r") as f:
                    data = json.load(f)
                    approvals.append(data)
            except Exception:
                pass

    return approvals


async def cmd_generate(args: argparse.Namespace) -> None:
    """Generate CEO briefing."""
    try:
        from tasks.ceo_briefing import CEOBriefingGenerator, BriefingConfig
    except ImportError:
        output_error("Could not import ceo_briefing module. Run from project root.", "IMPORT_ERROR")
        return

    config = load_config()

    briefing_config = BriefingConfig(
        vault_path=config["vault_path"],
        delivery_method=config["delivery_method"],
        email_recipient=config["email_recipient"],
    )

    generator = CEOBriefingGenerator(briefing_config)

    briefing_date = None
    if args.date:
        briefing_date = date.fromisoformat(args.date)

    print("Gathering data...", file=sys.stderr)

    financial_data = await get_financial_data()
    tasks = await get_task_data()
    approvals = await get_approval_data()

    print(f"Found {len(tasks)} tasks, {len(approvals)} approvals", file=sys.stderr)
    print("Generating briefing...", file=sys.stderr)

    briefing = await generator.generate(
        financial_data=financial_data,
        tasks=tasks,
        approvals=approvals,
        briefing_date=briefing_date,
    )

    print("Delivering briefing...", file=sys.stderr)

    result = await generator.deliver(briefing)

    output_json({
        "success": True,
        "briefing": briefing,
        "delivery": result,
    })


async def cmd_show(args: argparse.Namespace) -> None:
    """Show current CEO briefing."""
    config = load_config()
    briefing_path = config["vault_path"] / "CEO_Briefing.md"

    if not briefing_path.exists():
        output_error("No CEO briefing found. Run 'generate' first.", "NOT_FOUND")

    content = briefing_path.read_text(encoding="utf-8")

    output_json({
        "success": True,
        "path": str(briefing_path),
        "content": content,
        "modified": datetime.fromtimestamp(briefing_path.stat().st_mtime).isoformat(),
    })


async def cmd_archive(args: argparse.Namespace) -> None:
    """List archived briefings."""
    config = load_config()
    archive_dir = config["vault_path"] / "Archive" / "briefings"

    if not archive_dir.exists():
        output_json({
            "success": True,
            "archives": [],
            "message": "No archived briefings found",
        })
        return

    archives = []
    for file in sorted(archive_dir.glob("ceo-briefing-*.json"), reverse=True):
        archives.append({
            "date": file.stem.replace("ceo-briefing-", ""),
            "path": str(file),
            "size_bytes": file.stat().st_size,
        })

    output_json({
        "success": True,
        "archives": archives[:20],
        "total": len(archives),
    })


async def cmd_health(args: argparse.Namespace) -> None:
    """Check subscription health only."""
    try:
        from tasks.subscription_audit import SubscriptionAuditor
    except ImportError:
        output_error("Could not import subscription_audit module.", "IMPORT_ERROR")
        return

    # Use sample data for demo
    sys.path.insert(0, str(PROJECT_ROOT / "tests"))
    try:
        from fixtures.sample_briefing_data import SAMPLE_INVOICES
        invoices = SAMPLE_INVOICES
    except ImportError:
        invoices = []

    auditor = SubscriptionAuditor()
    subscriptions = auditor.detect_subscriptions(invoices)
    at_risk = auditor.assess_churn_risk(subscriptions)
    metrics = auditor.calculate_metrics(subscriptions)

    output_json({
        "success": True,
        "metrics": {
            "mrr": metrics.mrr,
            "arr": metrics.arr,
            "total_subscriptions": metrics.total_subscriptions,
        },
        "subscriptions": [
            {"name": s.partner_name, "frequency": s.frequency, "mrr": s.mrr_contribution}
            for s in subscriptions
        ],
        "at_risk": [
            {"name": r.partner_name, "risk_level": r.risk_level, "factors": r.risk_factors}
            for r in at_risk
        ],
    })


async def cmd_bottlenecks(args: argparse.Namespace) -> None:
    """Check bottlenecks only."""
    try:
        from tasks.bottleneck_detector import BottleneckDetector
    except ImportError:
        output_error("Could not import bottleneck_detector module.", "IMPORT_ERROR")
        return

    detector = BottleneckDetector()

    tasks = await get_task_data()
    approvals = await get_approval_data()

    bottlenecks = detector.detect_bottlenecks(tasks=tasks, approvals=approvals)
    metrics = detector.analyze_tasks(tasks)

    output_json({
        "success": True,
        "task_metrics": {
            "total": metrics.total_tasks,
            "completed": metrics.completed,
            "pending": metrics.pending,
            "overdue": metrics.overdue,
            "completion_rate": metrics.completion_rate,
        },
        "bottlenecks": [
            {"type": b.type, "description": b.description, "severity": b.severity, "recommendation": b.recommendation}
            for b in bottlenecks
        ],
    })


def main():
    parser = argparse.ArgumentParser(
        description="CEO Weekly Briefing Skill",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Operation to perform")

    gen_parser = subparsers.add_parser("generate", help="Generate CEO briefing")
    gen_parser.add_argument("--date", help="Briefing date (YYYY-MM-DD)")
    gen_parser.set_defaults(func=cmd_generate)

    show_parser = subparsers.add_parser("show", help="Show current briefing")
    show_parser.set_defaults(func=cmd_show)

    arch_parser = subparsers.add_parser("archive", help="List archived briefings")
    arch_parser.set_defaults(func=cmd_archive)

    health_parser = subparsers.add_parser("health", help="Check subscription health")
    health_parser.set_defaults(func=cmd_health)

    bn_parser = subparsers.add_parser("bottlenecks", help="Check bottlenecks")
    bn_parser.set_defaults(func=cmd_bottlenecks)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        asyncio.run(args.func(args))
    except Exception as e:
        output_error(str(e), "EXECUTION_ERROR")


if __name__ == "__main__":
    main()
