# Approval Required: Odoo Invoice Draft

**Requested**: 2026-02-17 11:22:37 UTC
**Type**: odoo_invoice_approval
**Status**: pending_approval
**Dry Run**: True

## What will happen on approval

The following draft invoice will be **posted** to Odoo accounting:

- **Customer**: Acme Corporation
- **Email**: billing@acmecorp.com
- **Invoice Date**: 2026-02-10
- **Due Date**: 2026-02-24
- **Currency**: USD
- **Total**: $4,000.00

## Line Items

| Description | Qty | Unit Price | Subtotal |
|---|---|---|---|
| | Gold Tier AI Employee Setup | 1.0 | $2,500.00 | $2,500.00 |
| Monthly Automation Services | 3.0 | $500.00 | $1,500.00 |

## Odoo Draft Reference

- **Draft ID**: DRAFT-DRY-001
- **State**: draft
- **Simulated At**: 2026-02-17T11:22:37.595720+00:00

## How to Approve

To approve this invoice posting, run:

```
python scripts/dry_run_odoo.py --approve odoo-invoice-approval-20260217-112237.md
```

Or rename this file to `APPROVED-odoo-invoice-approval-20260217-112237.md` and re-run the dry run script.

---
*[DRY RUN MODE — No real Odoo action has been taken]*
