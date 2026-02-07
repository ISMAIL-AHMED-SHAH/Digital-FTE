/**
 * Create Invoice MCP Tool (T022)
 *
 * Creates a draft customer invoice in Odoo.
 * All invoices are created in 'draft' state per HITL safety requirements.
 *
 * Contract: contracts/odoo-mcp.json
 */

import { z } from 'zod';
import { OdooClient, OdooError, OdooErrorCode } from '../lib/odoo_client.js';
import * as fs from 'fs/promises';
import * as path from 'path';
import { randomUUID } from 'crypto';

// Input schema matching contract
export const CreateInvoiceInputSchema = z.object({
  customer_name: z.string().describe(
    'Customer name (will resolve to partner_id) or numeric Odoo partner ID'
  ),
  invoice_date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/).describe(
    'Invoice date in YYYY-MM-DD format'
  ),
  due_date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/).optional().describe(
    'Payment due date in YYYY-MM-DD format (optional)'
  ),
  lines: z.array(
    z.object({
      description: z.string(),
      quantity: z.number().min(0),
      unit_price: z.number().min(0),
      tax_ids: z.array(z.number()).optional(),
    })
  ).min(1).describe('Invoice line items'),
  notes: z.string().optional().describe('Optional invoice notes or memo'),
  currency: z.string().default('USD').describe('Currency code (ISO 4217)'),
});

export type CreateInvoiceInput = z.infer<typeof CreateInvoiceInputSchema>;

// Output schema matching contract
export interface CreateInvoiceOutput {
  success: boolean;
  invoice_id?: number;
  invoice_number?: string;
  state?: 'draft';
  amount_untaxed?: number;
  amount_tax?: number;
  amount_total?: number;
  approval_file?: string;
  error?: string;
}

/**
 * Create an approval request file in the vault
 */
async function createApprovalFile(
  invoiceId: number,
  invoiceNumber: string,
  customerName: string,
  amount: number,
  currency: string
): Promise<string> {
  const vaultPath = process.env.VAULT_PATH || './vault';
  const approvalDir = path.join(vaultPath, 'Needs_Action');

  // Ensure directory exists
  await fs.mkdir(approvalDir, { recursive: true });

  const approvalId = randomUUID();
  const fileName = `odoo-invoice-${invoiceId}-${Date.now()}.md`;
  const filePath = path.join(approvalDir, fileName);

  const content = `---
type: approval_request
source: odoo
action: post_invoice
created: ${new Date().toISOString()}
approval_id: ${approvalId}
---

# Invoice Approval Required

## Invoice Details

- **Invoice ID**: ${invoiceId}
- **Invoice Number**: ${invoiceNumber}
- **Customer**: ${customerName}
- **Amount**: ${currency} ${amount.toFixed(2)}
- **Status**: Draft (pending approval)

## Actions

To approve this invoice and post it to Odoo:

\`\`\`
approve odoo invoice ${invoiceId} token:${approvalId}
\`\`\`

To reject this invoice:

\`\`\`
reject odoo invoice ${invoiceId}
\`\`\`

---
*This approval request was generated automatically by the AI Employee.*
`;

  await fs.writeFile(filePath, content, 'utf-8');

  return filePath;
}

/**
 * Execute create_invoice tool
 */
export async function createInvoice(
  client: OdooClient,
  input: CreateInvoiceInput
): Promise<CreateInvoiceOutput> {
  try {
    // Resolve customer name to partner_id
    const partnerId = parseInt(input.customer_name);
    let partner;

    if (isNaN(partnerId)) {
      // Search by name
      partner = await client.findPartner(input.customer_name);
      if (!partner) {
        return {
          success: false,
          error: `Customer not found: ${input.customer_name}`,
        };
      }
    } else {
      // Use provided ID
      partner = await client.findPartner(partnerId);
      if (!partner) {
        return {
          success: false,
          error: `Partner ID not found: ${partnerId}`,
        };
      }
    }

    // Create invoice
    const invoice = await client.createInvoice({
      partner_id: partner.id,
      invoice_date: input.invoice_date,
      invoice_date_due: input.due_date,
      lines: input.lines,
      narration: input.notes,
    });

    // Create approval file
    const approvalFile = await createApprovalFile(
      invoice.id,
      invoice.name,
      partner.name,
      invoice.amount_total,
      input.currency
    );

    return {
      success: true,
      invoice_id: invoice.id,
      invoice_number: invoice.name,
      state: 'draft',
      amount_untaxed: invoice.amount_untaxed,
      amount_tax: invoice.amount_tax,
      amount_total: invoice.amount_total,
      approval_file: approvalFile,
    };
  } catch (error) {
    if (error instanceof OdooError) {
      return {
        success: false,
        error: `${error.code}: ${error.message}`,
      };
    }

    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

/**
 * MCP Tool definition
 */
export const createInvoiceTool = {
  name: 'create_invoice',
  description:
    "Create a draft customer invoice in Odoo. Requires approval before posting. All invoices are created in 'draft' state per HITL safety requirements.",
  inputSchema: {
    type: 'object' as const,
    properties: {
      customer_name: {
        type: 'string',
        description:
          'Customer name (will resolve to partner_id) or numeric Odoo partner ID',
      },
      invoice_date: {
        type: 'string',
        format: 'date',
        description: 'Invoice date in YYYY-MM-DD format',
      },
      due_date: {
        type: 'string',
        format: 'date',
        description:
          'Payment due date in YYYY-MM-DD format (optional, defaults to invoice_date + payment terms)',
      },
      lines: {
        type: 'array',
        minItems: 1,
        items: {
          type: 'object',
          properties: {
            description: { type: 'string', description: 'Line item description' },
            quantity: {
              type: 'number',
              minimum: 0,
              description: 'Quantity (must be positive)',
            },
            unit_price: {
              type: 'number',
              minimum: 0,
              description: 'Price per unit',
            },
            tax_ids: {
              type: 'array',
              items: { type: 'integer' },
              description: 'Optional array of Odoo tax IDs to apply',
            },
          },
          required: ['description', 'quantity', 'unit_price'],
        },
        description: 'Invoice line items',
      },
      notes: {
        type: 'string',
        description: 'Optional invoice notes or memo',
      },
      currency: {
        type: 'string',
        default: 'USD',
        description: 'Currency code (ISO 4217)',
      },
    },
    required: ['customer_name', 'invoice_date', 'lines'],
  },
};

export default createInvoice;
