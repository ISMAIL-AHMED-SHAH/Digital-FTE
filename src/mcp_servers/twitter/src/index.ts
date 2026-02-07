#!/usr/bin/env node
/**
 * Twitter MCP Server (T057).
 *
 * MCP server for Twitter/X posting via Twitter API v2.
 *
 * Tools:
 * - post_tweet: Post a single tweet (with HITL approval)
 * - post_thread: Post a thread of tweets
 * - validate_tweet: Validate tweet content before posting
 * - execute_approved_tweet: Execute a tweet after HITL approval
 *
 * Environment Variables:
 * - TWITTER_API_KEY: Twitter API Key (Consumer Key)
 * - TWITTER_API_SECRET: Twitter API Secret (Consumer Secret)
 * - TWITTER_ACCESS_TOKEN: User Access Token
 * - TWITTER_ACCESS_SECRET: User Access Token Secret
 * - TWITTER_BEARER_TOKEN: Bearer Token (optional)
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
  postTweet,
  executeApprovedTweet,
  PostTweetInputSchema,
} from './tools/post_tweet.js';
import {
  validateTweet,
  suggestThreadSplit,
  ValidateTweetInputSchema,
} from './tools/validate_tweet.js';
import { createTwitterClient, TWEET_CHAR_LIMIT } from './lib/twitter_client.js';
import { z } from 'zod';

const SERVER_NAME = 'twitter-mcp';
const SERVER_VERSION = '1.0.0';

/**
 * Thread input schema.
 */
const PostThreadInputSchema = z.object({
  tweets: z.array(z.object({
    text: z.string().max(TWEET_CHAR_LIMIT),
    media_ids: z.array(z.string()).optional(),
  })).min(1).max(25).describe('Array of tweets in the thread (1-25)'),
  require_approval: z.boolean().default(true),
});

/**
 * Tool definitions for MCP.
 */
const TOOLS = [
  {
    name: 'post_tweet',
    description: `Post a single tweet to Twitter/X.

Maximum ${TWEET_CHAR_LIMIT} characters. URLs count as 23 characters regardless of length.

Posts require HITL approval by default. The tweet will be saved to an approval file
and only posted after the file is moved to the /Done folder.`,
    inputSchema: {
      type: 'object',
      properties: {
        text: {
          type: 'string',
          description: `Tweet text (max ${TWEET_CHAR_LIMIT} characters)`,
          maxLength: TWEET_CHAR_LIMIT,
        },
        reply_to: {
          type: 'string',
          description: 'Tweet ID to reply to (optional)',
        },
        media_ids: {
          type: 'array',
          items: { type: 'string' },
          description: 'Media IDs to attach (optional)',
        },
        require_approval: {
          type: 'boolean',
          description: 'Whether to require HITL approval (default: true)',
          default: true,
        },
      },
      required: ['text'],
    },
  },
  {
    name: 'post_thread',
    description: `Post a thread (multiple tweets as replies to each other).

Each tweet is limited to ${TWEET_CHAR_LIMIT} characters. Maximum 25 tweets per thread.
Threads are posted sequentially with each tweet replying to the previous.`,
    inputSchema: {
      type: 'object',
      properties: {
        tweets: {
          type: 'array',
          description: 'Array of tweets in the thread',
          items: {
            type: 'object',
            properties: {
              text: {
                type: 'string',
                maxLength: TWEET_CHAR_LIMIT,
              },
              media_ids: {
                type: 'array',
                items: { type: 'string' },
              },
            },
            required: ['text'],
          },
          minItems: 1,
          maxItems: 25,
        },
        require_approval: {
          type: 'boolean',
          default: true,
        },
      },
      required: ['tweets'],
    },
  },
  {
    name: 'validate_tweet',
    description: `Validate tweet content before posting.

Checks:
- Character count (${TWEET_CHAR_LIMIT} limit)
- URL counting (23 chars per URL)
- Warnings for potential issues
- Suggestions for improvement`,
    inputSchema: {
      type: 'object',
      properties: {
        text: {
          type: 'string',
          description: 'Tweet text to validate',
        },
      },
      required: ['text'],
    },
  },
  {
    name: 'suggest_thread_split',
    description: `Suggest how to split long text into a thread.

Takes text that exceeds the character limit and suggests how to split it
into multiple tweets while maintaining readability.`,
    inputSchema: {
      type: 'object',
      properties: {
        text: {
          type: 'string',
          description: 'Long text to split into thread',
        },
      },
      required: ['text'],
    },
  },
  {
    name: 'execute_approved_tweet',
    description: `Execute a tweet that has been approved via HITL workflow.

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
];

/**
 * Handle tool execution.
 */
async function handleToolCall(
  name: string,
  args: Record<string, unknown>
): Promise<unknown> {
  switch (name) {
    case 'post_tweet': {
      const parsed = PostTweetInputSchema.safeParse(args);
      if (!parsed.success) {
        throw new McpError(
          ErrorCode.InvalidParams,
          `Invalid parameters: ${parsed.error.message}`
        );
      }
      return postTweet(parsed.data);
    }

    case 'post_thread': {
      const parsed = PostThreadInputSchema.safeParse(args);
      if (!parsed.success) {
        throw new McpError(
          ErrorCode.InvalidParams,
          `Invalid parameters: ${parsed.error.message}`
        );
      }

      // If approval required, create approval file for thread
      if (parsed.data.require_approval) {
        const vaultPath = process.env.VAULT_PATH || './vault';
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
        const fs = await import('fs/promises');
        const path = await import('path');

        const approvalDir = path.join(vaultPath, 'Needs_Action');
        await fs.mkdir(approvalDir, { recursive: true });

        const content = `---
type: social_thread
platform: twitter
tweet_count: ${parsed.data.tweets.length}
status: pending
created: ${new Date().toISOString()}
---

# Twitter Thread Approval Required

## Thread (${parsed.data.tweets.length} tweets)

${parsed.data.tweets.map((t, i) => `**Tweet ${i + 1}:** ${t.text}`).join('\n\n')}

## Actions

- [ ] **Approve**: Move to /Done to publish
- [ ] **Reject**: Move to /Rejected with reason

## Thread Data

\`\`\`json
${JSON.stringify(parsed.data, null, 2)}
\`\`\`
`;

        const filePath = path.join(approvalDir, `twitter-thread-${timestamp}.md`);
        await fs.writeFile(filePath, content, 'utf-8');

        return {
          success: true,
          platform: 'twitter',
          tweet_count: parsed.data.tweets.length,
          approval_file: filePath,
        };
      }

      // Post thread directly
      try {
        const client = createTwitterClient();
        const result = await client.postThread(parsed.data.tweets);
        return {
          success: result.success,
          platform: 'twitter',
          tweet_ids: result.tweetIds,
          partial: result.partial,
          error: result.error,
        };
      } catch (error) {
        return {
          success: false,
          platform: 'twitter',
          error: {
            code: 'SYSTEM',
            message: error instanceof Error ? error.message : 'Unknown error',
          },
        };
      }
    }

    case 'validate_tweet': {
      const parsed = ValidateTweetInputSchema.safeParse(args);
      if (!parsed.success) {
        throw new McpError(
          ErrorCode.InvalidParams,
          `Invalid parameters: ${parsed.error.message}`
        );
      }
      return validateTweet(parsed.data);
    }

    case 'suggest_thread_split': {
      const text = args.text;
      if (typeof text !== 'string') {
        throw new McpError(
          ErrorCode.InvalidParams,
          'text must be a string'
        );
      }
      return suggestThreadSplit(text);
    }

    case 'execute_approved_tweet': {
      const approvalFile = args.approval_file;
      if (typeof approvalFile !== 'string') {
        throw new McpError(
          ErrorCode.InvalidParams,
          'approval_file must be a string'
        );
      }
      return executeApprovedTweet(approvalFile);
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
