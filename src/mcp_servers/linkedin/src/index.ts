/**
 * LinkedIn MCP Server for AI Employee
 *
 * Provides LinkedIn post publishing capabilities through the Model Context Protocol.
 * Integrates with the approval workflow for human-in-the-loop validation.
 *
 * Features:
 * - create_post tool with idempotency and rate limiting
 * - OAuth2 authentication via OS credential manager
 * - Full audit logging
 *
 * Usage:
 *   npx tsx src/index.ts
 *
 * Or add to Claude Desktop config:
 *   {
 *     "mcpServers": {
 *       "linkedin": {
 *         "command": "npx",
 *         "args": ["tsx", "path/to/src/mcp_servers/linkedin/src/index.ts"]
 *       }
 *     }
 *   }
 *
 * Implements T039 from tasks.md
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
  createPost,
  createPostToolDefinition,
  CreatePostInputSchema,
} from "./tools/create_post.js";
import { getLinkedInToken, validateToken } from "./credentials.js";

/**
 * Server metadata
 */
const SERVER_NAME = "linkedin-mcp-server";
const SERVER_VERSION = "1.0.0";

/**
 * Create and configure the MCP server
 */
function createServer(): Server {
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

  // Register tool list handler
  server.setRequestHandler(ListToolsRequestSchema, async (_request: ListToolsRequest) => {
    return {
      tools: [createPostToolDefinition],
    };
  });

  // Register tool call handler
  server.setRequestHandler(CallToolRequestSchema, async (request: CallToolRequest) => {
    const { name, arguments: args } = request.params;

    console.error(`[${SERVER_NAME}] Tool called: ${name}`);

    switch (name) {
      case "create_post": {
        // Validate input
        const parseResult = CreatePostInputSchema.safeParse(args);

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

        // Execute post creation
        const result = await createPost(parseResult.data);

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

/**
 * Verify credentials are available before starting
 */
async function verifyCredentials(): Promise<boolean> {
  try {
    const token = await getLinkedInToken();

    if (!token) {
      console.error(
        "[linkedin-mcp-server] No LinkedIn credentials found. " +
          "Please configure OAuth credentials in the credential manager."
      );
      return false;
    }

    if (!validateToken(token)) {
      console.error(
        "[linkedin-mcp-server] LinkedIn credentials are invalid or incomplete."
      );
      return false;
    }

    console.error("[linkedin-mcp-server] LinkedIn credentials verified");
    return true;
  } catch (error) {
    console.error("[linkedin-mcp-server] Failed to verify credentials:", error);
    return false;
  }
}

/**
 * Main entry point
 */
async function main(): Promise<void> {
  console.error(`[${SERVER_NAME}] Starting v${SERVER_VERSION}...`);

  // Verify credentials (warn but don't fail - credentials might be added later)
  const hasCredentials = await verifyCredentials();
  if (!hasCredentials) {
    console.error(
      "[linkedin-mcp-server] Warning: Credentials not configured. " +
        "create_post tool will fail until credentials are set up."
    );
  }

  // Create server
  const server = createServer();

  // Create stdio transport
  const transport = new StdioServerTransport();

  // Connect server to transport
  await server.connect(transport);

  console.error(`[${SERVER_NAME}] Server running on stdio`);

  // Handle shutdown
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

// Run
main().catch((error) => {
  console.error(`[${SERVER_NAME}] Fatal error:`, error);
  process.exit(1);
});
