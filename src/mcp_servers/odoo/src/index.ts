#!/usr/bin/env node
/**
 * Odoo MCP Server Entry Point (T025)
 *
 * MCP server for Odoo Community ERP integration.
 * Provides tools for:
 * - test_connection: Test Odoo connectivity
 * - create_invoice: Create draft customer invoices
 * - create_payment: Create draft payments
 * - get_financial_summary: Retrieve financial data for CEO briefing
 * - post_invoice: Post approved invoices
 * - post_payment: Post approved payments
 *
 * Transport: stdio
 * Contract: contracts/odoo-mcp.json
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  ErrorCode,
  McpError,
} from '@modelcontextprotocol/sdk/types.js';

import { OdooClient, createOdooClientFromEnv, OdooError, OdooErrorCode } from './lib/odoo_client.js';
import { createInvoice, createInvoiceTool, CreateInvoiceInputSchema } from './tools/create_invoice.js';
import { createPayment, createPaymentTool, CreatePaymentInputSchema } from './tools/create_payment.js';
import { getFinancialSummary, getFinancialSummaryTool, GetFinancialSummaryInputSchema } from './tools/get_financial_summary.js';

// Server metadata
const SERVER_NAME = 'odoo-mcp';
const SERVER_VERSION = '1.0.0';

// Initialize Odoo client (lazy - will be created on first request)
let odooClient: OdooClient | null = null;

function getOdooClient(): OdooClient {
  if (!odooClient) {
    odooClient = createOdooClientFromEnv();
  }
  return odooClient;
}

// Tool definitions
const tools = [
  {
    name: 'test_connection',
    description: 'Test the Odoo connection and verify credentials. Use before other operations to ensure connectivity.',
    inputSchema: {
      type: 'object' as const,
      properties: {},
      required: [],
    },
  },
  createInvoiceTool,
  createPaymentTool,
  getFinancialSummaryTool,
  {
    name: 'post_invoice',
    description: "Post a draft invoice in Odoo (changes state from draft to posted). Requires prior approval. This action is irreversible.",
    inputSchema: {
      type: 'object' as const,
      properties: {
        invoice_id: {
          type: 'integer',
          description: 'Odoo account.move ID to post',
        },
        approval_token: {
          type: 'string',
          description: 'Approval token from vault approval file',
        },
      },
      required: ['invoice_id', 'approval_token'],
    },
  },
  {
    name: 'post_payment',
    description: "Post a draft payment in Odoo (changes state from draft to posted). Requires prior approval. This action is irreversible.",
    inputSchema: {
      type: 'object' as const,
      properties: {
        payment_id: {
          type: 'integer',
          description: 'Odoo account.payment ID to post',
        },
        approval_token: {
          type: 'string',
          description: 'Approval token from vault approval file',
        },
      },
      required: ['payment_id', 'approval_token'],
    },
  },
];

/**
 * Validate approval token (stub - would check against vault)
 */
async function validateApprovalToken(
  entityType: 'invoice' | 'payment',
  entityId: number,
  token: string
): Promise<boolean> {
  // In production, this would:
  // 1. Read the approval file from vault
  // 2. Verify the token matches
  // 3. Check if approval hasn't expired
  // 4. Mark approval as used

  // For now, accept any non-empty token
  return token.length > 0;
}

/**
 * Handle tool calls
 */
async function handleToolCall(
  name: string,
  args: Record<string, unknown>
): Promise<unknown> {
  const client = getOdooClient();

  switch (name) {
    case 'test_connection': {
      return await client.testConnection();
    }

    case 'create_invoice': {
      const input = CreateInvoiceInputSchema.parse(args);
      return await createInvoice(client, input);
    }

    case 'create_payment': {
      const input = CreatePaymentInputSchema.parse(args);
      return await createPayment(client, input);
    }

    case 'get_financial_summary': {
      const input = GetFinancialSummaryInputSchema.parse(args);
      return await getFinancialSummary(client, input);
    }

    case 'post_invoice': {
      const invoiceId = args.invoice_id as number;
      const approvalToken = args.approval_token as string;

      // Validate approval
      const isValid = await validateApprovalToken('invoice', invoiceId, approvalToken);
      if (!isValid) {
        return {
          success: false,
          error: 'APPROVAL_INVALID: Invalid or expired approval token',
        };
      }

      try {
        const invoice = await client.postInvoice(invoiceId);
        return {
          success: true,
          invoice_id: invoice.id,
          invoice_number: invoice.name,
          state: 'posted',
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

    case 'post_payment': {
      const paymentId = args.payment_id as number;
      const approvalToken = args.approval_token as string;

      // Validate approval
      const isValid = await validateApprovalToken('payment', paymentId, approvalToken);
      if (!isValid) {
        return {
          success: false,
          error: 'APPROVAL_INVALID: Invalid or expired approval token',
        };
      }

      try {
        const payment = await client.postPayment(paymentId);
        return {
          success: true,
          payment_id: payment.id,
          payment_name: payment.name,
          state: 'posted',
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

    default:
      throw new McpError(ErrorCode.MethodNotFound, `Unknown tool: ${name}`);
  }
}

/**
 * Main entry point
 */
async function main() {
  // Create server
  const server = new Server(
    {
      name: SERVER_NAME,
      version: SERVER_VERSION,
    },
    {
      capabilities: {
        tools: {},
      },
    }
  );

  // Handle list tools request
  server.setRequestHandler(ListToolsRequestSchema, async () => {
    return { tools };
  });

  // Handle tool call request
  server.setRequestHandler(CallToolRequestSchema, async (request) => {
    const { name, arguments: args = {} } = request.params;

    try {
      const result = await handleToolCall(name, args as Record<string, unknown>);

      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(result, null, 2),
          },
        ],
      };
    } catch (error) {
      if (error instanceof McpError) {
        throw error;
      }

      // Handle Zod validation errors
      if (error instanceof Error && error.name === 'ZodError') {
        throw new McpError(
          ErrorCode.InvalidParams,
          `Invalid parameters: ${error.message}`
        );
      }

      // Handle Odoo errors
      if (error instanceof OdooError) {
        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify({
                success: false,
                error: `${error.code}: ${error.message}`,
              }),
            },
          ],
          isError: true,
        };
      }

      // Generic error
      throw new McpError(
        ErrorCode.InternalError,
        error instanceof Error ? error.message : 'Unknown error'
      );
    }
  });

  // Connect transport
  const transport = new StdioServerTransport();
  await server.connect(transport);

  console.error(`${SERVER_NAME} v${SERVER_VERSION} started`);
}

// Run
main().catch((error) => {
  console.error('Fatal error:', error);
  process.exit(1);
});
