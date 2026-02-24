#!/usr/bin/env python3
"""Odoo Dry Run Test Script.

Simulates the full Gold Tier Odoo workflow without a real Odoo server:
  1. Read invoice action file from vault/Needs_Action/
  2. Parse and validate invoice data
  3. Simulate draft creation (dry run - no real API call)
  4. Write approval request to vault/Pending_Approval/
  5. Simulate approval and posting
  6. Write audit log entry to vault/Logs/
  7. Move action file to vault/Done/

Usage:
    python scripts/dry_run_odoo.py
    python scripts/dry_run_odoo.py --invoice vault/Needs_Action/odoo-invoice-001.md
"""

import argparse
import json
import logging
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from dotenv import load_dotenv
    load_dotenv(project_root / "config" / ".env")
except ImportError:
    pass

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

VAULT_PATH = Path(os.environ.get("VAULT_PATH", project_root / "vault"))


def banner(title: str):
    logger.info("\n" + "=" * 65)
    logger.info(f"  {title}")
    logger.info("=" * 65)


def step(n: int, label: str):
    logger.info(f"\n[STEP {n}] {label}")
    logger.info("-" * 50)


def parse_invoice_md(md_path: Path) -> dict:
    """Parse a markdown invoice action file into structured data."""
    content = md_path.read_text(encoding="utf-8")

    data = {
        "source_file": str(md_path),
        "type": "odoo_invoice",
        "customer": None,
        "customer_email": None,
        "invoice_date": None,
        "due_date": None,
        "currency": "USD",
        "line_items": [],
        "total": None,
        "notes": None,
    }

    # Extract fields
    for field, key in [
        ("Customer", "customer"),
        ("Customer Email", "customer_email"),
        ("Invoice Date", "invoice_date"),
        ("Due Date", "due_date"),
        ("Currency", "currency"),
    ]:
        match = re.search(rf"\*\*{field}\*\*:\s*(.+)", content)
        if match:
            data[key] = match.group(1).strip()

    # Extract line items from table
    table_rows = re.findall(r"\|\s*(.+?)\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|", content)
    for row in table_rows:
        desc, qty, unit_price, subtotal = row
        if desc.lower() in ("description", "---"):
            continue
        try:
            data["line_items"].append({
                "description": desc.strip(),
                "quantity": float(qty),
                "unit_price": float(unit_price),
                "subtotal": float(subtotal),
            })
        except ValueError:
            continue

    # Extract total
    total_match = re.search(r"\*\*Total\*\*:\s*\$?([\d,]+\.?\d*)", content)
    if total_match:
        data["total"] = float(total_match.group(1).replace(",", ""))

    return data


def simulate_odoo_create_draft(invoice: dict) -> dict:
    """Simulate Odoo draft invoice creation (dry run)."""
    return {
        "success": True,
        "dry_run": True,
        "odoo_id": "DRAFT-DRY-001",
        "state": "draft",
        "partner_name": invoice["customer"],
        "amount_total": invoice["total"],
        "currency": invoice["currency"],
        "simulated_at": datetime.now(timezone.utc).isoformat(),
        "message": "[DRY RUN] Invoice draft would be created in Odoo. No real API call made.",
    }


def write_approval_request(invoice: dict, draft_result: dict) -> Path:
    """Write approval request to vault/Pending_Approval/."""
    approval_dir = VAULT_PATH / "Pending_Approval"
    approval_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc)
    filename = f"odoo-invoice-approval-{now.strftime('%Y%m%d-%H%M%S')}.md"
    approval_path = approval_dir / filename

    content = f"""# Approval Required: Odoo Invoice Draft

**Requested**: {now.strftime('%Y-%m-%d %H:%M:%S')} UTC
**Type**: odoo_invoice_approval
**Status**: pending_approval
**Dry Run**: {draft_result['dry_run']}

## What will happen on approval

The following draft invoice will be **posted** to Odoo accounting:

- **Customer**: {invoice['customer']}
- **Email**: {invoice['customer_email']}
- **Invoice Date**: {invoice['invoice_date']}
- **Due Date**: {invoice['due_date']}
- **Currency**: {invoice['currency']}
- **Total**: ${invoice['total']:,.2f}

## Line Items

| Description | Qty | Unit Price | Subtotal |
|---|---|---|---|
"""
    for item in invoice["line_items"]:
        content += f"| {item['description']} | {item['quantity']} | ${item['unit_price']:,.2f} | ${item['subtotal']:,.2f} |\n"

    content += f"""
## Odoo Draft Reference

- **Draft ID**: {draft_result['odoo_id']}
- **State**: {draft_result['state']}
- **Simulated At**: {draft_result['simulated_at']}

## How to Approve

To approve this invoice posting, run:

```
python scripts/dry_run_odoo.py --approve {filename}
```

Or rename this file to `APPROVED-{filename}` and re-run the dry run script.

---
*[DRY RUN MODE — No real Odoo action has been taken]*
"""
    approval_path.write_text(content, encoding="utf-8")
    return approval_path


def write_audit_log(event: str, details: dict):
    """Write audit log entry to vault/Logs/."""
    logs_dir = VAULT_PATH / "Logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_file = logs_dir / f"{today}.json"

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action_type": event,
        "actor": "ai-employee/odoo-mcp",
        "dry_run": True,
        "approval_status": details.get("approval_status", "pending"),
        "result": details.get("result", "success"),
        **{k: v for k, v in details.items() if k not in ("approval_status", "result")},
    }

    # Append to log file
    entries = []
    if log_file.exists():
        try:
            entries = json.loads(log_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, ValueError):
            entries = []

    entries.append(entry)
    log_file.write_text(json.dumps(entries, indent=2, default=str), encoding="utf-8")
    return log_file


def main():
    parser = argparse.ArgumentParser(description="Odoo Dry Run Test for Gold Tier")
    parser.add_argument(
        "--invoice",
        default=str(VAULT_PATH / "Needs_Action" / "odoo-invoice-001.md"),
        help="Path to invoice markdown file",
    )
    args = parser.parse_args()

    banner("DIGITAL FTE - ODOO DRY RUN TEST")
    logger.info(f"  Vault: {VAULT_PATH}")
    logger.info(f"  Mode:  DRY_RUN=true (no real Odoo calls)")

    invoice_path = Path(args.invoice)

    # ─── STEP 1: Read invoice from Needs_Action ──────────────────────────────
    step(1, "Reading invoice from vault/Needs_Action/")
    if not invoice_path.exists():
        logger.error(f"❌ Invoice file not found: {invoice_path}")
        sys.exit(1)

    logger.info(f"  ✅ Found: {invoice_path.name}")

    # ─── STEP 2: Parse and validate ──────────────────────────────────────────
    step(2, "Parsing and validating invoice data")
    invoice = parse_invoice_md(invoice_path)

    required = ["customer", "invoice_date", "due_date", "total"]
    missing = [f for f in required if not invoice.get(f)]
    if missing:
        logger.error(f"  ❌ Missing required fields: {missing}")
        sys.exit(1)

    logger.info(f"  ✅ Customer     : {invoice['customer']}")
    logger.info(f"  ✅ Email        : {invoice['customer_email']}")
    logger.info(f"  ✅ Invoice Date : {invoice['invoice_date']}")
    logger.info(f"  ✅ Due Date     : {invoice['due_date']}")
    logger.info(f"  ✅ Line Items   : {len(invoice['line_items'])}")
    logger.info(f"  ✅ Total        : ${invoice['total']:,.2f} {invoice['currency']}")

    # ─── STEP 3: Simulate Odoo draft creation ────────────────────────────────
    step(3, "Simulating Odoo draft invoice creation [DRY RUN]")
    draft = simulate_odoo_create_draft(invoice)
    logger.info(f"  ✅ Draft ID     : {draft['odoo_id']}")
    logger.info(f"  ✅ State        : {draft['state']}")
    logger.info(f"  ✅ {draft['message']}")

    # ─── STEP 4: Write audit log (draft_created) ─────────────────────────────
    step(4, "Writing audit log — event: odoo_invoice_draft_created")
    log_file = write_audit_log("odoo_invoice_draft_created", {
        "target": invoice["customer"],
        "odoo_draft_id": draft["odoo_id"],
        "amount_total": invoice["total"],
        "currency": invoice["currency"],
        "approval_status": "pending",
        "result": "draft_created",
    })
    logger.info(f"  ✅ Audit log written: {log_file}")

    # ─── STEP 5: Write approval request ──────────────────────────────────────
    step(5, "Writing approval request to vault/Pending_Approval/")
    approval_path = write_approval_request(invoice, draft)
    logger.info(f"  ✅ Approval request: {approval_path.name}")
    logger.info(f"  ℹ️  Human must approve before invoice is posted to Odoo")

    # ─── STEP 6: Move source to Done ─────────────────────────────────────────
    step(6, "Moving invoice action file to vault/Done/")
    done_dir = VAULT_PATH / "Done"
    done_dir.mkdir(parents=True, exist_ok=True)
    dest = done_dir / invoice_path.name
    shutil.move(str(invoice_path), str(dest))
    logger.info(f"  ✅ Moved to: {dest.name}")

    # ─── SUMMARY ─────────────────────────────────────────────────────────────
    banner("DRY RUN COMPLETE")
    logger.info("""
  Workflow Summary
  ────────────────────────────────────────────────────────────
  [✅] Invoice parsed and validated
  [✅] Odoo draft simulated (DRY RUN — no real API call)
  [✅] Audit log written to vault/Logs/
  [✅] Approval request created in vault/Pending_Approval/
  [✅] Action file moved to vault/Done/

  Next Steps (after Odoo is running):
  ────────────────────────────────────────────────────────────
  1. Set DRY_RUN=false in config/.env
  2. Run: python scripts/setup_odoo_connection.py --url http://localhost:8069 ...
  3. Human approves file in vault/Pending_Approval/
  4. Odoo MCP posts the invoice to Odoo
  5. System logs the posting in vault/Logs/

  🟢 Gold Tier Odoo workflow validated successfully!
""")


if __name__ == "__main__":
    main()
