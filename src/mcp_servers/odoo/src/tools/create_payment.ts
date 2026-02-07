/**
 * Create Payment MCP Tool (T023)
 *
 * Creates a draft payment entry in Odoo.
 * Supports both inbound (customer) and outbound (vendor) payments.
 * All payments are created in 'draft' state per HITL safety requirements.
 *
 * Contract: contracts/odoo-mcp.json
 */

import { z } from 'zod';
import { OdooClient, OdooError, OdooErrorCode } from '../lib/odoo_client.js';
import * as fs from 'fs/promises';
import * as path from 'path';
import { randomUUID } from 'crypto';

// Input schema matching contract
export const CreatePaymentInputSchema = z.object({
  partner_name: z.string().describe(
    'Partner name (will resolve to partner_id) or numeric Odoo partner ID'
  ),
  amount: z.number().min(0.01).describe('Payment amount (must be positive)'),
  payment_type: z.enum(['inbound', 'outbound']).describe(
    'inbound = customer payment received, outbound = payment to vendor'
  ),
  payment_method: z
    .enum(['manual', 'check', 'bank_transfer', 'credit_card'])
    .default('manual')
    .describe('Payment method'),
  payment_date: z
    .string()
    .regex(/^\d{4}-\d{2}-\d{2}$/)
    .optional()
    .describe('Payment date in YYYY-MM-DD format (defaults to today)'),
  reference: z
    .string()
    .optional()
    .describe('Payment reference (e.g., invoice number, check number)'),
  journal_id: z
    .number()
    .optional()
    .describe('Odoo journal ID for bank/cash account'),
  currency: z.string().default('USD').describe('Currency code (ISO 4217)'),
});

export type CreatePaymentInput = z.infer<typeof CreatePaymentInputSchema>;

// Output schema matching contract
export interface CreatePaymentOutput {
  success: boolean;
  payment_id?: number;
  payment_name?: string;
  state?: 'draft';
  amount?: number;
  approval_file?: string;
  error?: string;
}

/**
 * Create an approval request file for payment
 */
async function createPaymentApprovalFile(
  paymentId: number,
  paymentName: string,
  partnerName: string,
  amount: number,
  paymentType: 'inbound' | 'outbound',
  currency: string
): Promise<string> {
  const vaultPath = process.env.VAULT_PATH || './vault';
  const approvalDir = path.join(vaultPath, 'Needs_Action');

  await fs.mkdir(approvalDir, { recursive: true });

  const approvalId = randomUUID();
  const fileName = `odoo-payment-${paymentId}-${Date.now()}.md`;
  const filePath = path.join(approvalDir, fileName);

  const typeLabel = paymentType === 'inbound' ? 'Customer Payment' : 'Vendor Payment';
  const directionLabel = paymentType === 'inbound' ? 'received from' : 'to';

  const content = `---
type: approval_request
source: odoo
action: post_payment
created: ${new Date().toISOString()}
approval_id: ${approvalId}
---

# Payment Approval Required

## Payment Details

- **Payment ID**: ${paymentId}
- **Reference**: ${paymentName}
- **Type**: ${typeLabel}
- **Partner**: ${partnerName}
- **Amount**: ${currency} ${amount.toFixed(2)} ${directionLabel} ${partnerName}
- **Status**: Draft (pending approval)

## Actions

To approve this payment and post it to Odoo:

\`\`\`
approve odoo payment ${paymentId} token:${approvalId}
\`\`\`

To reject this payment:

\`\`\`
reject odoo payment ${paymentId}
\`\`\`

---
*This approval request was generated automatically by the AI Employee.*
`;

  await fs.writeFile(filePath, content, 'utf-8');

  return filePath;
}

/**
 * Execute create_payment tool
 */
export async function createPayment(
  client: OdooClient,
  input: CreatePaymentInput
): Promise<CreatePaymentOutput> {
  try {
    // Resolve partner name to partner_id
    const partnerId = parseInt(input.partner_name);
    let partner;

    if (isNaN(partnerId)) {
      partner = await client.findPartner(input.partner_name);
      if (!partner) {
        return {
          success: false,
          error: `Partner not found: ${input.partner_name}`,
        };
      }
    } else {
      partner = await client.findPartner(partnerId);
      if (!partner) {
        return {
          success: false,
          error: `Partner ID not found: ${partnerId}`,
        };
      }
    }

    // Map payment method to Odoo code
    const paymentMethodMap: Record<string, string> = {
      manual: 'manual',
      check: 'check_printing',
      bank_transfer: 'manual',
      credit_card: 'manual',
    };

    // Create payment
    const payment = await client.createPayment({
      partner_id: partner.id,
      amount: input.amount,
      payment_type: input.payment_type,
      payment_method_code: paymentMethodMap[input.payment_method],
      payment_date: input.payment_date,
      ref: input.reference,
      journal_id: input.journal_id,
    });

    // Create approval file
    const approvalFile = await createPaymentApprovalFile(
      payment.id,
      payment.name,
      partner.name,
      input.amount,
      input.payment_type,
      input.currency
    );

    return {
      success: true,
      payment_id: payment.id,
      payment_name: payment.name,
      state: 'draft',
      amount: input.amount,
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
export const createPaymentTool = {
  name: 'create_payment',
  description:
    "Create a draft payment entry in Odoo. Requires approval before posting. Supports both inbound (customer) and outbound (vendor) payments.",
  inputSchema: {
    type: 'object' as const,
    properties: {
      partner_name: {
        type: 'string',
        description:
          'Partner name (will resolve to partner_id) or numeric Odoo partner ID',
      },
      amount: {
        type: 'number',
        minimum: 0.01,
        description: 'Payment amount (must be positive)',
      },
      payment_type: {
        type: 'string',
        enum: ['inbound', 'outbound'],
        description: 'inbound = customer payment received, outbound = payment to vendor',
      },
      payment_method: {
        type: 'string',
        enum: ['manual', 'check', 'bank_transfer', 'credit_card'],
        default: 'manual',
        description: 'Payment method',
      },
      payment_date: {
        type: 'string',
        format: 'date',
        description: 'Payment date in YYYY-MM-DD format (defaults to today)',
      },
      reference: {
        type: 'string',
        description: 'Payment reference (e.g., invoice number, check number)',
      },
      journal_id: {
        type: 'integer',
        description:
          'Odoo journal ID for bank/cash account (optional, uses default if not specified)',
      },
      currency: {
        type: 'string',
        default: 'USD',
        description: 'Currency code (ISO 4217)',
      },
    },
    required: ['partner_name', 'amount', 'payment_type'],
  },
};

export default createPayment;
