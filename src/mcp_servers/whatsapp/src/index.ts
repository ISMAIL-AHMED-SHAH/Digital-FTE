/**
 * WhatsApp MCP Server for AI Employee
 *
 * Provides WhatsApp messaging capabilities through the Model Context Protocol.
 * Uses the WhatsApp Business Cloud API (Meta Graph API v19.0).
 *
 * Tools exposed:
 *   - send_message: Send a text message to a WhatsApp number
 *
 * Required environment variables (.env):
 *   ACCESS_TOKEN                  - Meta Graph API access token
 *   WHATSAPP_PHONE_NUMBER_ID      - Sender phone number ID
 *   WHATSAPP_BUSINESS_ACCOUNT_ID  - WhatsApp Business Account ID
 *
 * Usage:
 *   npx tsx src/index.ts
 *
 * Or register in Claude Desktop / settings.local.json:
 *   {
 *     "mcpServers": {
 *       "whatsapp": {
 *         "command": "node",
 *         "args": ["src/mcp_servers/whatsapp/dist/index.js"]
 *       }
 *     }
 *   }
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  type CallToolRequest,
  type ListToolsRequest,
} from "@modelcontextprotocol/sdk/types.js";

import {
  sendMessage,
  sendMessageToolDefinition,
  SendMessageInputSchema,
} from "./tools/send_message.js";
import { getWhatsAppCredentials, validateCredentials } from "./credentials.js";

const SERVER_NAME = "whatsapp-mcp-server";
const SERVER_VERSION = "1.0.0";

// ─── Server setup ─────────────────────────────────────────────────────────────

function createServer(): Server {
  const server = new Server(
    { name: SERVER_NAME, version: SERVER_VERSION },
    { capabilities: { tools: {} } }
  );

  // List available tools
  server.setRequestHandler(ListToolsRequestSchema, async (_request: ListToolsRequest) => {
    return { tools: [sendMessageToolDefinition] };
  });

  // Handle tool calls
  server.setRequestHandler(CallToolRequestSchema, async (request: CallToolRequest) => {
    const { name, arguments: args } = request.params;

    console.error(`[${SERVER_NAME}] Tool called: ${name}`);

    switch (name) {
      case "send_message": {
        const parseResult = SendMessageInputSchema.safeParse(args);

        if (!parseResult.success) {
          return {
            content: [
              {
                type: "text" as const,
                text: JSON.stringify({
                  success: false,
                  error: `Invalid input: ${parseResult.error.message}`,
                }),
              },
            ],
            isError: true,
          };
        }

        const result = await sendMessage(parseResult.data);

        return {
          content: [
            {
              type: "text" as const,
              text: JSON.stringify(result, null, 2),
            },
          ],
          isError: !result.success,
        };
      }

      default:
        return {
          content: [
            {
              type: "text" as const,
              text: JSON.stringify({
                success: false,
                error: `Unknown tool: ${name}`,
              }),
            },
          ],
          isError: true,
        };
    }
  });

  return server;
}

// ─── Startup ──────────────────────────────────────────────────────────────────

async function main(): Promise<void> {
  console.error(`[${SERVER_NAME}] Starting v${SERVER_VERSION}...`);

  // Warn if credentials are missing (don't block — they may be provided later)
  const creds = getWhatsAppCredentials();
  if (!creds || !validateCredentials(creds)) {
    console.error(
      `[${SERVER_NAME}] Warning: WhatsApp credentials not fully configured. ` +
        "send_message will fail until ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID, " +
        "and WHATSAPP_BUSINESS_ACCOUNT_ID are set in .env"
    );
  } else {
    console.error(
      `[${SERVER_NAME}] Credentials loaded (phone_number_id=${creds.phoneNumberId})`
    );
  }

  const server = createServer();
  const transport = new StdioServerTransport();
  await server.connect(transport);

  console.error(`[${SERVER_NAME}] Server running on stdio`);

  process.on("SIGINT", async () => {
    console.error(`[${SERVER_NAME}] Shutting down...`);
    await server.close();
    process.exit(0);
  });

  process.on("SIGTERM", async () => {
    console.error(`[${SERVER_NAME}] Shutting down...`);
    await server.close();
    process.exit(0);
  });
}

main().catch((error) => {
  console.error(`[${SERVER_NAME}] Fatal error:`, error);
  process.exit(1);
});
