#!/usr/bin/env node
/**
 * Instagram MCP Server (T047).
 *
 * MCP server for Instagram Business account management via Meta Graph API.
 *
 * Tools:
 * - publish_media: Publish photos, videos, reels, or carousels
 * - execute_approved_post: Execute a post after HITL approval
 *
 * Environment Variables:
 * - META_APP_ID: Facebook App ID
 * - META_APP_SECRET: Facebook App Secret
 * - META_ACCESS_TOKEN: Page access token with Instagram permissions
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
import {
  publishInstagramMedia,
  executeApprovedInstagramPost,
  PublishMediaInputSchema,
} from './tools/publish_media.js';

const SERVER_NAME = 'instagram-mcp';
const SERVER_VERSION = '1.0.0';

/**
 * Tool definitions for MCP.
 */
const TOOLS = [
  {
    name: 'publish_media',
    description: `Publish media to Instagram Business account.

Supports:
- IMAGE: Single photo post
- VIDEO: Short video post
- REELS: Reels video
- CAROUSEL: 2-10 images/videos

Posts require HITL approval by default. Uses the two-step container workflow.

Caption limit: 2,200 characters. Maximum 30 hashtags.`,
    inputSchema: {
      type: 'object',
      properties: {
        account_id: {
          type: 'string',
          description: 'Instagram Business Account ID',
        },
        image_url: {
          type: 'string',
          format: 'uri',
          description: 'URL of image to post',
        },
        video_url: {
          type: 'string',
          format: 'uri',
          description: 'URL of video to post',
        },
        caption: {
          type: 'string',
          description: 'Post caption (max 2,200 characters)',
          maxLength: 2200,
        },
        media_type: {
          type: 'string',
          enum: ['IMAGE', 'VIDEO', 'REELS', 'CAROUSEL'],
          description: 'Type of media (auto-detected if not specified)',
        },
        children: {
          type: 'array',
          description: 'Child media for carousel (2-10 items)',
          items: {
            type: 'object',
            properties: {
              image_url: { type: 'string', format: 'uri' },
              video_url: { type: 'string', format: 'uri' },
              media_type: { type: 'string', enum: ['IMAGE', 'VIDEO'] },
            },
          },
        },
        location_id: {
          type: 'string',
          description: 'Facebook Page ID for location tag',
        },
        user_tags: {
          type: 'array',
          description: 'Users to tag in the post',
          items: {
            type: 'object',
            properties: {
              username: { type: 'string' },
              x: { type: 'number', minimum: 0, maximum: 1 },
              y: { type: 'number', minimum: 0, maximum: 1 },
            },
            required: ['username', 'x', 'y'],
          },
        },
        require_approval: {
          type: 'boolean',
          description: 'Whether to require HITL approval (default: true)',
          default: true,
        },
        poll_timeout_seconds: {
          type: 'number',
          description: 'Max time to wait for video processing (default: 300)',
          default: 300,
        },
      },
      required: ['account_id'],
    },
  },
  {
    name: 'execute_approved_post',
    description: `Execute an Instagram post that has been approved via HITL workflow.

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
    name: 'get_media_insights',
    description: `Get insights/analytics for a published Instagram media.

Returns engagement metrics like likes, comments, reach, etc.`,
    inputSchema: {
      type: 'object',
      properties: {
        media_id: {
          type: 'string',
          description: 'Instagram Media ID',
        },
        metrics: {
          type: 'array',
          description: 'Metrics to retrieve (default: engagement, impressions, reach)',
          items: {
            type: 'string',
            enum: ['engagement', 'impressions', 'reach', 'saved', 'video_views'],
          },
        },
      },
      required: ['media_id'],
    },
  },
];

/**
 * Get media insights from Instagram.
 */
async function getMediaInsights(
  mediaId: string,
  metrics: string[] = ['engagement', 'impressions', 'reach']
): Promise<Record<string, unknown>> {
  const accessToken = process.env.META_ACCESS_TOKEN;

  if (!accessToken) {
    return {
      success: false,
      error: {
        code: 'AUTH',
        message: 'No access token configured',
      },
    };
  }

  try {
    const response = await fetch(
      `https://graph.facebook.com/v18.0/${mediaId}/insights?metric=${metrics.join(',')}&access_token=${accessToken}`
    );

    const data = await response.json() as Record<string, unknown>;

    if (!response.ok) {
      return {
        success: false,
        error: {
          code: response.status === 401 ? 'AUTH' : 'SYSTEM',
          message: (data as { error?: { message?: string } }).error?.message || 'Failed to get insights',
        },
      };
    }

    return {
      success: true,
      media_id: mediaId,
      insights: data,
    };
  } catch (error) {
    return {
      success: false,
      error: {
        code: 'SYSTEM',
        message: error instanceof Error ? error.message : 'Unknown error',
      },
    };
  }
}

/**
 * Handle tool execution.
 */
async function handleToolCall(
  name: string,
  args: Record<string, unknown>
): Promise<unknown> {
  switch (name) {
    case 'publish_media': {
      const parsed = PublishMediaInputSchema.safeParse(args);
      if (!parsed.success) {
        throw new McpError(
          ErrorCode.InvalidParams,
          `Invalid parameters: ${parsed.error.message}`
        );
      }
      return publishInstagramMedia(parsed.data);
    }

    case 'execute_approved_post': {
      const approvalFile = args.approval_file;
      if (typeof approvalFile !== 'string') {
        throw new McpError(
          ErrorCode.InvalidParams,
          'approval_file must be a string'
        );
      }
      return executeApprovedInstagramPost(approvalFile);
    }

    case 'get_media_insights': {
      const mediaId = args.media_id;
      if (typeof mediaId !== 'string') {
        throw new McpError(
          ErrorCode.InvalidParams,
          'media_id must be a string'
        );
      }
      const metrics = Array.isArray(args.metrics)
        ? args.metrics.filter((m): m is string => typeof m === 'string')
        : undefined;
      return getMediaInsights(mediaId, metrics);
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
