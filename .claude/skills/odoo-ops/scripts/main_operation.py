#!/usr/bin/env python3
"""Odoo Operations Skill Entry Point (T028).

This skill provides Odoo accounting operations through the MCP server.
It acts as a bridge between Claude Code skills and the Odoo MCP tools.

Usage:
    python .claude/skills/odoo-ops/scripts/main_operation.py <operation> [args...]

Operations:
    test-connection     Test Odoo connectivity
    create-invoice      Create a draft invoice
    create-payment      Create a draft payment
    get-summary         Get financial summary
    post-invoice        Post an approved invoice
    post-payment        Post an approved payment
"""

import argparse
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
        "odoo_url": os.environ.get("ODOO_URL"),
        "odoo_database": os.environ.get("ODOO_DATABASE"),
        "odoo_username": os.environ.get("ODOO_USERNAME"),
        "odoo_password": os.environ.get("ODOO_PASSWORD"),
        "odoo_api_key": os.environ.get("ODOO_API_KEY"),
        "vault_path": os.environ.get("VAULT_PATH", str(PROJECT_ROOT / "vault")),
    }

    # Check required config
    if not config["odoo_url"]:
        output_error("ODOO_URL not configured", "CONFIG_ERROR")
    if not config["odoo_database"]:
        output_error("ODOO_DATABASE not configured", "CONFIG_ERROR")
    if not config["odoo_username"]:
        output_error("ODOO_USERNAME not configured", "CONFIG_ERROR")
    if not config["odoo_api_key"] and not config["odoo_password"]:
        output_error("ODOO_API_KEY or ODOO_PASSWORD required", "CONFIG_ERROR")

    return config


def call_mcp_tool(tool_name: str, arguments: dict) -> dict:
    """
    Call an MCP tool via the Odoo MCP server.

    In production, this would use the MCP SDK to call the tool.
    For now, we'll use direct HTTP/JSON-RPC to Odoo.
    """
    # This is a placeholder - actual implementation would use MCP client
    # For skill execution, Claude Code handles MCP tool calls directly

    return {
        "success": True,
        "note": f"MCP tool '{tool_name}' would be called with: {arguments}",
        "tool": tool_name,
        "arguments": arguments,
    }


def cmd_test_connection(args: argparse.Namespace) -> None:
    """Test Odoo connection."""
    config = load_config()

    result = call_mcp_tool("test_connection", {})
    output_json(result)


def cmd_create_invoice(args: argparse.Namespace) -> None:
    """Create a draft invoice."""
    config = load_config()

    # Parse line items
    lines = []
    if args.lines:
        for line in args.lines:
            parts = line.split(":")
            if len(parts) >= 3:
                lines.append({
                    "description": parts[0],
                    "quantity": float(parts[1]),
                    "unit_price": float(parts[2]),
                })

    if not lines:
        output_error("At least one line item required (format: description:qty:price)")

    arguments = {
        "customer_name": args.customer,
        "invoice_date": args.date or date.today().isoformat(),
        "lines": lines,
    }

    if args.due_date:
        arguments["due_date"] = args.due_date
    if args.notes:
        arguments["notes"] = args.notes
    if args.currency:
        arguments["currency"] = args.currency

    result = call_mcp_tool("create_invoice", arguments)
    output_json(result)


def cmd_create_payment(args: argparse.Namespace) -> None:
    """Create a draft payment."""
    config = load_config()

    arguments = {
        "partner_name": args.partner,
        "amount": args.amount,
        "payment_type": args.type,
    }

    if args.method:
        arguments["payment_method"] = args.method
    if args.date:
        arguments["payment_date"] = args.date
    if args.reference:
        arguments["reference"] = args.reference
    if args.currency:
        arguments["currency"] = args.currency

    result = call_mcp_tool("create_payment", arguments)
    output_json(result)


def cmd_get_summary(args: argparse.Namespace) -> None:
    """Get financial summary."""
    config = load_config()

    arguments = {
        "date_from": args.date_from,
        "date_to": args.date_to,
    }

    if args.include_drafts:
        arguments["include_drafts"] = True
    if args.top_customers:
        arguments["top_customers_limit"] = args.top_customers

    result = call_mcp_tool("get_financial_summary", arguments)
    output_json(result)


def cmd_post_invoice(args: argparse.Namespace) -> None:
    """Post an approved invoice."""
    config = load_config()

    arguments = {
        "invoice_id": args.invoice_id,
        "approval_token": args.token,
    }

    result = call_mcp_tool("post_invoice", arguments)
    output_json(result)


def cmd_post_payment(args: argparse.Namespace) -> None:
    """Post an approved payment."""
    config = load_config()

    arguments = {
        "payment_id": args.payment_id,
        "approval_token": args.token,
    }

    result = call_mcp_tool("post_payment", arguments)
    output_json(result)


def main():
    parser = argparse.ArgumentParser(
        description="Odoo Accounting Operations Skill",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Operation to perform")

    # test-connection
    test_parser = subparsers.add_parser("test-connection", help="Test Odoo connectivity")
    test_parser.set_defaults(func=cmd_test_connection)

    # create-invoice
    invoice_parser = subparsers.add_parser("create-invoice", help="Create draft invoice")
    invoice_parser.add_argument("--customer", required=True, help="Customer name or ID")
    invoice_parser.add_argument("--date", help="Invoice date (YYYY-MM-DD)")
    invoice_parser.add_argument("--due-date", help="Due date (YYYY-MM-DD)")
    invoice_parser.add_argument(
        "--lines", nargs="+",
        help="Line items (format: description:quantity:unit_price)"
    )
    invoice_parser.add_argument("--notes", help="Invoice notes")
    invoice_parser.add_argument("--currency", default="USD", help="Currency code")
    invoice_parser.set_defaults(func=cmd_create_invoice)

    # create-payment
    payment_parser = subparsers.add_parser("create-payment", help="Create draft payment")
    payment_parser.add_argument("--partner", required=True, help="Partner name or ID")
    payment_parser.add_argument("--amount", type=float, required=True, help="Payment amount")
    payment_parser.add_argument(
        "--type", required=True,
        choices=["inbound", "outbound"],
        help="Payment type"
    )
    payment_parser.add_argument(
        "--method",
        choices=["manual", "check", "bank_transfer", "credit_card"],
        help="Payment method"
    )
    payment_parser.add_argument("--date", help="Payment date (YYYY-MM-DD)")
    payment_parser.add_argument("--reference", help="Payment reference")
    payment_parser.add_argument("--currency", default="USD", help="Currency code")
    payment_parser.set_defaults(func=cmd_create_payment)

    # get-summary
    summary_parser = subparsers.add_parser("get-summary", help="Get financial summary")
    summary_parser.add_argument("--date-from", required=True, help="Start date (YYYY-MM-DD)")
    summary_parser.add_argument("--date-to", required=True, help="End date (YYYY-MM-DD)")
    summary_parser.add_argument("--include-drafts", action="store_true", help="Include drafts")
    summary_parser.add_argument("--top-customers", type=int, default=5, help="Top N customers")
    summary_parser.set_defaults(func=cmd_get_summary)

    # post-invoice
    post_inv_parser = subparsers.add_parser("post-invoice", help="Post approved invoice")
    post_inv_parser.add_argument("--invoice-id", type=int, required=True, help="Invoice ID")
    post_inv_parser.add_argument("--token", required=True, help="Approval token")
    post_inv_parser.set_defaults(func=cmd_post_invoice)

    # post-payment
    post_pay_parser = subparsers.add_parser("post-payment", help="Post approved payment")
    post_pay_parser.add_argument("--payment-id", type=int, required=True, help="Payment ID")
    post_pay_parser.add_argument("--token", required=True, help="Approval token")
    post_pay_parser.set_defaults(func=cmd_post_payment)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        args.func(args)
    except Exception as e:
        output_error(str(e), "EXECUTION_ERROR")


if __name__ == "__main__":
    main()
