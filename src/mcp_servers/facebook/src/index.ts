#!/usr/bin/env node
/**
 * Facebook MCP Server (T045).
 *
 * MCP server for Facebook Page management via Meta Graph API.
 *
 * Tools:
 * - create_post: Create text, link, or photo posts
 * - get_page_insights: Get page metrics and analytics
 * - execute_approved_post: Execute a post after HITL approval
 *
 * Environment Variables:
 * - META_APP_ID: Facebook App ID
 * - META_APP_SECRET: Facebook App Secret
 * - META_ACCESS_TOKEN: Page or User access token
 * - VAULT_PATH: Path to vault for approval files
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  ErrorCode,
  McpError,
} from '@modelcontextprotocol/sdk/types.js';
import { z } from 'zod';
import {
  createFacebookPost,
  executeApprovedPost,
  CreatePostInputSchema,
} from './tools/create_post.js';
import { createMetaOAuthClient } from './lib/meta_oauth.js';

const SERVER_NAME = 'facebook-mcp';
const SERVER_VERSION = '1.0.0';

/**
 * Tool definitions for MCP.
 */
const TOOLS = [
  {
    name: 'create_post',
    description: `Create a post on a Facebook Page.

Supports text, link, and photo posts. Posts require HITL approval by default.

For scheduled posts, provide scheduled_publish_time as Unix timestamp (10 min to 6 months in future).`,
    inputSchema: {
      type: 'object',
      properties: {
        page_id: {
          type: 'string',
          description: 'Facebook Page ID',
        },
        message: {
          type: 'string',
          description: 'Post message text (max 63,206 characters)',
          maxLength: 63206,
        },
        link: {
          type: 'string',
          format: 'uri',
          description: 'URL to share (optional)',
        },
        photo_url: {
          type: 'string',
          format: 'uri',
          description: 'Photo URL to post (optional)',
        },
        scheduled_publish_time: {
          type: 'number',
          description: 'Unix timestamp for scheduled post (optional)',
        },
        require_approval: {
          type: 'boolean',
          description: 'Whether to require HITL approval (default: true)',
          default: true,
        },
      },
      required: ['page_id', 'message'],
    },
  },
  {
    name: 'execute_approved_post',
    description: `Execute a post that has been approved via HITL workflow.

Call this after an approval file has been moved to the /Done folder.`,
    inputSchema: {
      type: 'object',
      properties: {
        approval_file: {
          type: 'string',
          description: 'Path to the approval file',
        },
      },
      required: ['approval_file'],
    },
  },
  {
    name: 'check_token',
    description: `Check the validity and expiration of the current access token.

Returns token status, expiration date, and whether refresh is needed.`,
    inputSchema: {
      type: 'object',
      properties: {},
    },
  },
  {
    name: 'refresh_token',
    description: `Exchange current token for a long-lived token.

Long-lived page tokens don't expire. User tokens last ~60 days.`,
    inputSchema: {
      type: 'object',
      properties: {
        token: {
          type: 'string',
          description: 'Token to refresh (uses env token if not provided)',
        },
      },
    },
  },
];

/**
 * Handle tool execution.
 */
async function handleToolCall(
  name: string,
  args: Record<string, unknown>
): Promise<unknown> {
  switch (name) {
    case 'create_post': {
      const parsed = CreatePostInputSchema.safeParse(args);
      if (!parsed.success) {
        throw new McpError(
          ErrorCode.InvalidParams,
          `Invalid parameters: ${parsed.error.message}`
        );
      }
      return createFacebookPost(parsed.data);
    }

    case 'execute_approved_post': {
      const approvalFile = args.approval_file;
      if (typeof approvalFile !== 'string') {
        throw new McpError(
          ErrorCode.InvalidParams,
          'approval_file must be a string'
        );
      }
      return executeApprovedPost(approvalFile);
    }

    case 'check_token': {
      try {
        const client = createMetaOAuthClient();
        const tokenInfo = await client.debugToken();
        return {
          success: true,
          token_info: {
            is_valid: tokenInfo.isValid,
            expires_at: tokenInfo.expiresAt?.toISOString(),
            days_until_expiration: tokenInfo.daysUntilExpiration,
            needs_refresh: tokenInfo.needsRefresh,
            scopes: tokenInfo.scopes,
            error: tokenInfo.error,
          },
        };
      } catch (error) {
        return {
          success: false,
          error: {
            code: 'AUTH',
            message: error instanceof Error ? error.message : 'Unknown error',
          },
        };
      }
    }

    case 'refresh_token': {
      try {
        const client = createMetaOAuthClient();
        const token = typeof args.token === 'string' ? args.token : undefined;
        const result = await client.exchangeForLongLivedToken(token);
        return result;
      } catch (error) {
        return {
          success: false,
          error: {
            code: 'AUTH',
            message: error instanceof Error ? error.message : 'Unknown error',
          },
        };
      }
    }

    default:
      throw new McpError(ErrorCode.MethodNotFound, `Unknown tool: ${name}`);
  }
}

/**
 * Main server entry point.
 */
async function main() {
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
    return { tools: TOOLS };
  });

  // Handle tool calls
  server.setRequestHandler(CallToolRequestSchema, async (request) => {
    const { name, arguments: args } = request.params;

    try {
      const result = await handleToolCall(name, args || {});

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

      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify({
              success: false,
              error: {
                code: 'SYSTEM',
                message: errorMessage,
              },
            }, null, 2),
          },
        ],
        isError: true,
      };
    }
  });

  // Start server
  const transport = new StdioServerTransport();
  await server.connect(transport);

  console.error(`${SERVER_NAME} v${SERVER_VERSION} started`);
}

main().catch((error) => {
  console.error('Server error:', error);
  process.exit(1);
});
