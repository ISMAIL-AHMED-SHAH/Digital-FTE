# Odoo Accounting Operations Skill

**WHAT**: Manage accounting operations in Odoo ERP - create invoices, payments, and retrieve financial summaries.

**WHEN**: User says 'create invoice', 'record payment', 'financial summary', 'Odoo accounting'. Trigger on: invoice creation, payment recording, financial reporting, customer billing.

## Capabilities

### Invoice Management
- Create draft customer invoices with line items
- Support for taxes, currencies, and payment terms
- Generate approval requests for HITL workflow
- Post approved invoices to Odoo

### Payment Processing
- Create inbound (customer) and outbound (vendor) payments
- Support multiple payment methods (manual, check, bank transfer, credit card)
- Link payments to invoices
- Post approved payments

### Financial Reporting
- Retrieve financial summaries for date ranges
- Track revenue, payments received, and receivables
- Identify top customers by revenue
- Support CEO Briefing data requirements

## Usage Examples

### Create Invoice
```
create invoice for "Acme Corp" dated 2026-02-06 with:
- Consulting services: 10 hours at $150/hour
- Software license: 1 at $500
```

### Record Payment
```
record payment from "Acme Corp" for $2000 received via bank transfer
reference: INV-2026-0001
```

### Get Financial Summary
```
get financial summary for January 2026
include top 5 customers
```

## MCP Tools

This skill uses the `odoo-mcp` server with the following tools:

| Tool | Description |
|------|-------------|
| `test_connection` | Verify Odoo connectivity |
| `create_invoice` | Create draft invoice |
| `create_payment` | Create draft payment |
| `get_financial_summary` | Get financial data |
| `post_invoice` | Post approved invoice |
| `post_payment` | Post approved payment |

## Approval Workflow

All invoices and payments are created in **draft** state:

1. AI creates draft document in Odoo
2. Approval request file created in `/Needs_Action`
3. Human reviews and approves
4. AI posts approved document to Odoo

This ensures human-in-the-loop (HITL) control over financial transactions.

## Configuration

Required environment variables:
- `ODOO_URL`: Odoo server URL
- `ODOO_DATABASE`: Database name
- `ODOO_USERNAME`: Username
- `ODOO_API_KEY`: API key (recommended) or `ODOO_PASSWORD`

## Error Handling

| Error Code | Meaning | Recovery |
|------------|---------|----------|
| `ODOO_CONNECTION_FAILED` | Cannot connect | Retry with backoff |
| `ODOO_AUTH_FAILED` | Invalid credentials | Check credentials |
| `ODOO_TIMEOUT` | Request timeout | Retry |
| `PARTNER_NOT_FOUND` | Customer not found | Create or verify |
| `APPROVAL_REQUIRED` | Needs approval | Wait for human |

## Related Skills

- `ceo-briefing`: Uses financial summary for weekly reports
- `manage-approval`: Handles invoice/payment approvals
