/**
 * Facebook Create Post Tool (T044).
 *
 * Creates posts on Facebook Pages via Meta Graph API:
 * - Text posts
 * - Link posts with preview
 * - Photo posts
 * - Scheduled posts
 *
 * Requires HITL approval for posts (FR-011).
 */

import axios, { AxiosError } from 'axios';
import { z } from 'zod';
import * as fs from 'fs/promises';
import * as path from 'path';
import { categorizeMetaError } from '../lib/meta_oauth.js';

const GRAPH_API_VERSION = 'v18.0';
const GRAPH_API_BASE = `https://graph.facebook.com/${GRAPH_API_VERSION}`;

/**
 * Input schema for create_post tool.
 */
export const CreatePostInputSchema = z.object({
  page_id: z.string().describe('Facebook Page ID'),
  message: z.string().max(63206).describe('Post message text (max 63,206 characters)'),
  link: z.string().url().optional().describe('URL to share'),
  photo_url: z.string().url().optional().describe('Photo URL to post'),
  scheduled_publish_time: z.number().optional().describe('Unix timestamp for scheduled post (10 min to 6 months in future)'),
  access_token: z.string().optional().describe('Page access token (uses env if not provided)'),
  require_approval: z.boolean().default(true).describe('Whether to require HITL approval'),
});

export type CreatePostInput = z.infer<typeof CreatePostInputSchema>;

/**
 * Output schema for create_post tool.
 */
export interface CreatePostOutput {
  success: boolean;
  post_id?: string;
  platform: 'facebook';
  scheduled?: boolean;
  approval_file?: string;
  error?: {
    code: string;
    message: string;
    retry_after?: number;
  };
}

/**
 * Create approval file for HITL workflow.
 */
async function createApprovalFile(
  input: CreatePostInput,
  vaultPath: string
): Promise<string> {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const filename = `facebook-post-${timestamp}.md`;
  const approvalDir = path.join(vaultPath, 'Needs_Action');

  // Ensure directory exists
  await fs.mkdir(approvalDir, { recursive: true });

  const content = `---
type: social_post
platform: facebook
page_id: ${input.page_id}
status: pending
created: ${new Date().toISOString()}
${input.scheduled_publish_time ? `scheduled_for: ${new Date(input.scheduled_publish_time * 1000).toISOString()}` : ''}
---

# Facebook Post Approval Required

## Content

${input.message}

${input.link ? `\n**Link:** ${input.link}` : ''}
${input.photo_url ? `\n**Photo:** ${input.photo_url}` : ''}
${input.scheduled_publish_time ? `\n**Scheduled for:** ${new Date(input.scheduled_publish_time * 1000).toLocaleString()}` : ''}

## Actions

- [ ] **Approve**: Move this file to \`/Done\` folder to publish
- [ ] **Reject**: Move to \`/Rejected\` folder with reason

## Post Data

\`\`\`json
${JSON.stringify({
  page_id: input.page_id,
  message: input.message,
  link: input.link,
  photo_url: input.photo_url,
  scheduled_publish_time: input.scheduled_publish_time,
}, null, 2)}
\`\`\`

## Metadata

- **Page ID**: ${input.page_id}
- **Type**: ${input.photo_url ? 'Photo' : input.link ? 'Link' : 'Text'} post
- **Character count**: ${input.message.length}
`;

  const filePath = path.join(approvalDir, filename);
  await fs.writeFile(filePath, content, 'utf-8');

  return filePath;
}

/**
 * Post directly to Facebook (after approval or if approval not required).
 */
async function postToFacebook(input: CreatePostInput): Promise<CreatePostOutput> {
  const accessToken = input.access_token || process.env.META_ACCESS_TOKEN;

  if (!accessToken) {
    return {
      success: false,
      platform: 'facebook',
      error: {
        code: 'AUTH',
        message: 'No access token provided. Set META_ACCESS_TOKEN or provide access_token parameter.',
      },
    };
  }

  try {
    let endpoint: string;
    const params: Record<string, unknown> = {
      access_token: accessToken,
      message: input.message,
    };

    if (input.photo_url) {
      // Photo post
      endpoint = `${GRAPH_API_BASE}/${input.page_id}/photos`;
      params.url = input.photo_url;
    } else {
      // Text or link post
      endpoint = `${GRAPH_API_BASE}/${input.page_id}/feed`;
      if (input.link) {
        params.link = input.link;
      }
    }

    // Handle scheduling
    if (input.scheduled_publish_time) {
      params.scheduled_publish_time = input.scheduled_publish_time;
      params.published = false;
    }

    const response = await axios.post(endpoint, params, {
      timeout: 30000,
    });

    return {
      success: true,
      post_id: response.data.id || response.data.post_id,
      platform: 'facebook',
      scheduled: !!input.scheduled_publish_time,
    };
  } catch (error) {
    if (error instanceof AxiosError) {
      const categorized = categorizeMetaError(error);
      const errorData = error.response?.data?.error;

      return {
        success: false,
        platform: 'facebook',
        error: {
          code: categorized.code,
          message: errorData?.message || error.message,
          retry_after: categorized.retryAfter,
        },
      };
    }

    return {
      success: false,
      platform: 'facebook',
      error: {
        code: 'SYSTEM',
        message: error instanceof Error ? error.message : 'Unknown error',
      },
    };
  }
}

/**
 * Main tool handler for create_post.
 */
export async function createFacebookPost(
  input: CreatePostInput
): Promise<CreatePostOutput> {
  // Validate input
  const parsed = CreatePostInputSchema.safeParse(input);
  if (!parsed.success) {
    return {
      success: false,
      platform: 'facebook',
      error: {
        code: 'LOGIC',
        message: `Invalid input: ${parsed.error.message}`,
      },
    };
  }

  const validInput = parsed.data;

  // Validate scheduled time if provided
  if (validInput.scheduled_publish_time) {
    const now = Math.floor(Date.now() / 1000);
    const tenMinutes = 10 * 60;
    const sixMonths = 6 * 30 * 24 * 60 * 60;

    if (validInput.scheduled_publish_time < now + tenMinutes) {
      return {
        success: false,
        platform: 'facebook',
        error: {
          code: 'LOGIC',
          message: 'Scheduled time must be at least 10 minutes in the future.',
        },
      };
    }

    if (validInput.scheduled_publish_time > now + sixMonths) {
      return {
        success: false,
        platform: 'facebook',
        error: {
          code: 'LOGIC',
          message: 'Scheduled time cannot be more than 6 months in the future.',
        },
      };
    }
  }

  // Handle HITL approval workflow
  if (validInput.require_approval) {
    const vaultPath = process.env.VAULT_PATH || './vault';

    try {
      const approvalFile = await createApprovalFile(validInput, vaultPath);

      return {
        success: true,
        platform: 'facebook',
        approval_file: approvalFile,
      };
    } catch (error) {
      return {
        success: false,
        platform: 'facebook',
        error: {
          code: 'SYSTEM',
          message: `Failed to create approval file: ${error instanceof Error ? error.message : 'Unknown error'}`,
        },
      };
    }
  }

  // Post directly without approval
  return postToFacebook(validInput);
}

/**
 * Execute approved post from approval file.
 *
 * Called by the approval workflow when a post is approved.
 */
export async function executeApprovedPost(
  approvalFilePath: string
): Promise<CreatePostOutput> {
  try {
    const content = await fs.readFile(approvalFilePath, 'utf-8');

    // Extract JSON data from markdown
    const jsonMatch = content.match(/```json\n([\s\S]*?)\n```/);
    if (!jsonMatch) {
      return {
        success: false,
        platform: 'facebook',
        error: {
          code: 'DATA',
          message: 'Could not find post data in approval file.',
        },
      };
    }

    const postData = JSON.parse(jsonMatch[1]) as CreatePostInput;

    // Execute the post (without requiring approval again)
    return postToFacebook({ ...postData, require_approval: false });
  } catch (error) {
    return {
      success: false,
      platform: 'facebook',
      error: {
        code: 'SYSTEM',
        message: `Failed to execute approved post: ${error instanceof Error ? error.message : 'Unknown error'}`,
      },
    };
  }
}
