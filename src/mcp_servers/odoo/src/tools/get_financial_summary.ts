/**
 * Get Financial Summary MCP Tool (T024)
 *
 * Retrieves financial summary from Odoo for CEO briefing.
 * Queries posted invoices and payments within the specified date range.
 *
 * Contract: contracts/odoo-mcp.json
 */

import { z } from 'zod';
import { OdooClient, OdooError } from '../lib/odoo_client.js';

// Input schema matching contract
export const GetFinancialSummaryInputSchema = z.object({
  date_from: z.string().regex(/^\d{4}-\d{2}-\d{2}$/).describe(
    'Start date for summary period (YYYY-MM-DD)'
  ),
  date_to: z.string().regex(/^\d{4}-\d{2}-\d{2}$/).describe(
    'End date for summary period (YYYY-MM-DD)'
  ),
  include_drafts: z.boolean().default(false).describe(
    'Include draft invoices in summary'
  ),
  top_customers_limit: z.number().int().min(1).max(20).default(5).describe(
    'Number of top customers to return'
  ),
});

export type GetFinancialSummaryInput = z.infer<typeof GetFinancialSummaryInputSchema>;

// Output schema matching contract
export interface GetFinancialSummaryOutput {
  success: boolean;
  period?: {
    from: string;
    to: string;
  };
  revenue?: {
    total: number;
    paid: number;
    receivable: number;
  };
  counts?: {
    invoices_posted: number;
    invoices_draft: number;
    payments_received: number;
  };
  top_customers?: Array<{
    name: string;
    partner_id: number;
    revenue: number;
    invoice_count: number;
  }>;
  currency?: string;
  error?: string;
}

/**
 * Execute get_financial_summary tool
 */
export async function getFinancialSummary(
  client: OdooClient,
  input: GetFinancialSummaryInput
): Promise<GetFinancialSummaryOutput> {
  try {
    // Get posted invoices
    const postedInvoices = await client.getInvoices(
      input.date_from,
      input.date_to,
      false // Only posted
    );

    // Get draft invoices if requested
    let draftInvoices: typeof postedInvoices = [];
    if (input.include_drafts) {
      const allInvoices = await client.getInvoices(
        input.date_from,
        input.date_to,
        true // Include drafts
      );
      draftInvoices = allInvoices.filter((inv) => inv.state === 'draft');
    }

    // Get payments received
    const payments = await client.getPayments(
      input.date_from,
      input.date_to,
      'inbound' // Customer payments
    );

    // Calculate totals
    const totalRevenue = postedInvoices.reduce(
      (sum, inv) => sum + inv.amount_total,
      0
    );

    const totalPaid = payments.reduce((sum, pay) => sum + pay.amount, 0);

    const receivable = totalRevenue - totalPaid;

    // Get top customers
    const topCustomers = await client.getTopCustomers(
      input.date_from,
      input.date_to,
      input.top_customers_limit
    );

    // Determine currency (use first invoice's currency or default to USD)
    const currency =
      postedInvoices.length > 0 && postedInvoices[0].currency_id
        ? postedInvoices[0].currency_id[1]
        : 'USD';

    return {
      success: true,
      period: {
        from: input.date_from,
        to: input.date_to,
      },
      revenue: {
        total: Math.round(totalRevenue * 100) / 100,
        paid: Math.round(totalPaid * 100) / 100,
        receivable: Math.round(Math.max(0, receivable) * 100) / 100,
      },
      counts: {
        invoices_posted: postedInvoices.length,
        invoices_draft: draftInvoices.length,
        payments_received: payments.length,
      },
      top_customers: topCustomers.map((c) => ({
        name: c.name,
        partner_id: c.partner_id,
        revenue: Math.round(c.revenue * 100) / 100,
        invoice_count: c.invoice_count,
      })),
      currency,
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
export const getFinancialSummaryTool = {
  name: 'get_financial_summary',
  description:
    'Retrieve financial summary from Odoo for CEO briefing. Queries posted invoices and payments within the specified date range.',
  inputSchema: {
    type: 'object' as const,
    properties: {
      date_from: {
        type: 'string',
        format: 'date',
        description: 'Start date for summary period (YYYY-MM-DD)',
      },
      date_to: {
        type: 'string',
        format: 'date',
        description: 'End date for summary period (YYYY-MM-DD)',
      },
      include_drafts: {
        type: 'boolean',
        default: false,
        description: 'Include draft invoices in summary',
      },
      top_customers_limit: {
        type: 'integer',
        default: 5,
        minimum: 1,
        maximum: 20,
        description: 'Number of top customers to return',
      },
    },
    required: ['date_from', 'date_to'],
  },
};

export default getFinancialSummary;
