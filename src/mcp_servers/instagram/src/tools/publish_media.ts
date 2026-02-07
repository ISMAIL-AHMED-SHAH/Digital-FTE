/**
 * Instagram Publish Media Tool (T046).
 *
 * Publishes media to Instagram Business accounts via Meta Graph API.
 * Uses the two-step container workflow:
 * 1. Create media container
 * 2. Wait for processing (videos)
 * 3. Publish container
 *
 * Supported media types:
 * - IMAGE: Single photo
 * - VIDEO: Short video
 * - REELS: Reels video
 * - CAROUSEL: Multiple images/videos
 *
 * Requires HITL approval for posts (FR-011).
 */

import axios, { AxiosError } from 'axios';
import { z } from 'zod';
import * as fs from 'fs/promises';
import * as path from 'path';

const GRAPH_API_VERSION = 'v18.0';
const GRAPH_API_BASE = `https://graph.facebook.com/${GRAPH_API_VERSION}`;

// Maximum hashtags allowed by Instagram
const MAX_HASHTAGS = 30;

// Container polling configuration
const CONTAINER_POLL_INTERVAL_MS = 5000;
const CONTAINER_POLL_MAX_ATTEMPTS = 60; // 5 minutes max

/**
 * Child media schema for carousel posts.
 */
const CarouselChildSchema = z.object({
  image_url: z.string().url().optional(),
  video_url: z.string().url().optional(),
  media_type: z.enum(['IMAGE', 'VIDEO']).optional(),
});

/**
 * Input schema for publish_media tool.
 */
export const PublishMediaInputSchema = z.object({
  account_id: z.string().describe('Instagram Business Account ID'),
  image_url: z.string().url().optional().describe('URL of image to post'),
  video_url: z.string().url().optional().describe('URL of video to post'),
  caption: z.string().max(2200).optional().describe('Post caption (max 2,200 characters)'),
  media_type: z.enum(['IMAGE', 'VIDEO', 'REELS', 'CAROUSEL']).optional().describe('Type of media'),
  children: z.array(CarouselChildSchema).optional().describe('Child media for carousel (2-10 items)'),
  location_id: z.string().optional().describe('Facebook Page ID for location tag'),
  user_tags: z.array(z.object({
    username: z.string(),
    x: z.number().min(0).max(1),
    y: z.number().min(0).max(1),
  })).optional().describe('Users to tag in the post'),
  access_token: z.string().optional().describe('Access token (uses env if not provided)'),
  require_approval: z.boolean().default(true).describe('Whether to require HITL approval'),
  poll_timeout_seconds: z.number().default(300).describe('Max time to wait for video processing'),
});

export type PublishMediaInput = z.infer<typeof PublishMediaInputSchema>;

/**
 * Output schema for publish_media tool.
 */
export interface PublishMediaOutput {
  success: boolean;
  media_id?: string;
  container_id?: string;
  platform: 'instagram';
  status?: 'published' | 'processing' | 'pending_approval';
  approval_file?: string;
  error?: {
    code: string;
    message: string;
    retry_after?: number;
  };
}

/**
 * Count hashtags in caption.
 */
function countHashtags(caption: string): number {
  const matches = caption.match(/#\w+/g);
  return matches ? matches.length : 0;
}

/**
 * Validate caption for Instagram requirements.
 */
function validateCaption(caption?: string): { valid: boolean; error?: string } {
  if (!caption) return { valid: true };

  if (caption.length > 2200) {
    return { valid: false, error: `Caption too long (${caption.length}/2200 characters)` };
  }

  const hashtagCount = countHashtags(caption);
  if (hashtagCount > MAX_HASHTAGS) {
    return { valid: false, error: `Too many hashtags (${hashtagCount}). Maximum is ${MAX_HASHTAGS}.` };
  }

  return { valid: true };
}

/**
 * Create approval file for HITL workflow.
 */
async function createApprovalFile(
  input: PublishMediaInput,
  vaultPath: string
): Promise<string> {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const filename = `instagram-post-${timestamp}.md`;
  const approvalDir = path.join(vaultPath, 'Needs_Action');

  await fs.mkdir(approvalDir, { recursive: true });

  const mediaType = input.media_type ||
    (input.video_url ? 'VIDEO' : input.children ? 'CAROUSEL' : 'IMAGE');

  const hashtagCount = input.caption ? countHashtags(input.caption) : 0;

  const content = `---
type: social_post
platform: instagram
account_id: ${input.account_id}
media_type: ${mediaType}
status: pending
created: ${new Date().toISOString()}
---

# Instagram Post Approval Required

## Content

**Caption:**
${input.caption || '(no caption)'}

**Media Type:** ${mediaType}
${input.image_url ? `\n**Image:** ${input.image_url}` : ''}
${input.video_url ? `\n**Video:** ${input.video_url}` : ''}
${input.children ? `\n**Carousel Items:** ${input.children.length}` : ''}

## Metadata

- **Account ID**: ${input.account_id}
- **Type**: ${mediaType}
- **Caption length**: ${input.caption?.length || 0}/2200
- **Hashtags**: ${hashtagCount}/${MAX_HASHTAGS}
${input.location_id ? `- **Location**: ${input.location_id}` : ''}
${input.user_tags ? `- **Tagged users**: ${input.user_tags.map(t => t.username).join(', ')}` : ''}

## Actions

- [ ] **Approve**: Move this file to \`/Done\` folder to publish
- [ ] **Reject**: Move to \`/Rejected\` folder with reason

## Post Data

\`\`\`json
${JSON.stringify({
  account_id: input.account_id,
  image_url: input.image_url,
  video_url: input.video_url,
  caption: input.caption,
  media_type: mediaType,
  children: input.children,
  location_id: input.location_id,
  user_tags: input.user_tags,
}, null, 2)}
\`\`\`
`;

  const filePath = path.join(approvalDir, filename);
  await fs.writeFile(filePath, content, 'utf-8');

  return filePath;
}

/**
 * Create media container for Instagram post.
 */
async function createMediaContainer(
  accountId: string,
  accessToken: string,
  params: Record<string, unknown>
): Promise<{ success: boolean; containerId?: string; error?: { code: string; message: string } }> {
  try {
    const response = await axios.post(
      `${GRAPH_API_BASE}/${accountId}/media`,
      {
        ...params,
        access_token: accessToken,
      },
      { timeout: 30000 }
    );

    return {
      success: true,
      containerId: response.data.id,
    };
  } catch (error) {
    return handleError(error);
  }
}

/**
 * Wait for container to finish processing (videos).
 */
async function waitForContainerReady(
  containerId: string,
  accessToken: string,
  timeoutSeconds: number
): Promise<{ ready: boolean; error?: string }> {
  const maxAttempts = Math.min(
    Math.ceil(timeoutSeconds / (CONTAINER_POLL_INTERVAL_MS / 1000)),
    CONTAINER_POLL_MAX_ATTEMPTS
  );

  for (let i = 0; i < maxAttempts; i++) {
    try {
      const response = await axios.get(
        `${GRAPH_API_BASE}/${containerId}`,
        {
          params: {
            fields: 'status_code,status',
            access_token: accessToken,
          },
          timeout: 10000,
        }
      );

      const statusCode = response.data.status_code;

      if (statusCode === 'FINISHED') {
        return { ready: true };
      }

      if (statusCode === 'ERROR') {
        return {
          ready: false,
          error: response.data.status || 'Container processing failed',
        };
      }

      // Still processing, wait and retry
      await new Promise(resolve => setTimeout(resolve, CONTAINER_POLL_INTERVAL_MS));
    } catch (error) {
      // Ignore polling errors and continue
      await new Promise(resolve => setTimeout(resolve, CONTAINER_POLL_INTERVAL_MS));
    }
  }

  return { ready: false, error: 'Container processing timeout' };
}

/**
 * Publish container to Instagram.
 */
async function publishContainer(
  accountId: string,
  containerId: string,
  accessToken: string
): Promise<{ success: boolean; mediaId?: string; error?: { code: string; message: string } }> {
  try {
    const response = await axios.post(
      `${GRAPH_API_BASE}/${accountId}/media_publish`,
      {
        creation_id: containerId,
        access_token: accessToken,
      },
      { timeout: 30000 }
    );

    return {
      success: true,
      mediaId: response.data.id,
    };
  } catch (error) {
    return handleError(error);
  }
}

/**
 * Handle API errors.
 */
function handleError(error: unknown): { success: false; error: { code: string; message: string; retry_after?: number } } {
  if (error instanceof AxiosError) {
    const status = error.response?.status;
    const errorData = error.response?.data?.error;
    const apiCode = errorData?.code;

    let code = 'SYSTEM';
    let retryAfter: number | undefined;

    if (status === 429 || apiCode === 32 || apiCode === 17) {
      code = 'TRANSIENT';
      retryAfter = parseInt(error.response?.headers?.['retry-after'] || '60', 10);
    } else if (status === 401 || apiCode === 190 || apiCode === 102) {
      code = 'AUTH';
    } else if (status === 400) {
      code = 'LOGIC';
    } else if (status === 404) {
      code = 'DATA';
    } else if (status && status >= 500) {
      code = 'TRANSIENT';
      retryAfter = 5;
    }

    return {
      success: false,
      error: {
        code,
        message: errorData?.message || error.message,
        retry_after: retryAfter,
      },
    };
  }

  return {
    success: false,
    error: {
      code: 'SYSTEM',
      message: error instanceof Error ? error.message : 'Unknown error',
    },
  };
}

/**
 * Publish media to Instagram.
 */
async function publishToInstagram(input: PublishMediaInput): Promise<PublishMediaOutput> {
  const accessToken = input.access_token || process.env.META_ACCESS_TOKEN;

  if (!accessToken) {
    return {
      success: false,
      platform: 'instagram',
      error: {
        code: 'AUTH',
        message: 'No access token provided. Set META_ACCESS_TOKEN or provide access_token parameter.',
      },
    };
  }

  // Determine media type
  const mediaType = input.media_type ||
    (input.video_url ? 'VIDEO' : input.children ? 'CAROUSEL' : 'IMAGE');

  // Build container parameters
  const containerParams: Record<string, unknown> = {};

  if (input.caption) {
    containerParams.caption = input.caption;
  }

  if (input.location_id) {
    containerParams.location_id = input.location_id;
  }

  if (input.user_tags) {
    containerParams.user_tags = input.user_tags;
  }

  // Handle different media types
  if (mediaType === 'CAROUSEL' && input.children) {
    // Create child containers first
    const childIds: string[] = [];

    for (const child of input.children) {
      const childParams: Record<string, unknown> = {
        is_carousel_item: true,
      };

      if (child.image_url) {
        childParams.image_url = child.image_url;
      } else if (child.video_url) {
        childParams.video_url = child.video_url;
        childParams.media_type = 'VIDEO';
      }

      const childResult = await createMediaContainer(
        input.account_id,
        accessToken,
        childParams
      );

      if (!childResult.success) {
        return {
          success: false,
          platform: 'instagram',
          error: childResult.error,
        };
      }

      // Wait for video children to process
      if (child.video_url && childResult.containerId) {
        const ready = await waitForContainerReady(
          childResult.containerId,
          accessToken,
          input.poll_timeout_seconds || 300
        );

        if (!ready.ready) {
          return {
            success: false,
            platform: 'instagram',
            error: {
              code: 'TRANSIENT',
              message: ready.error || 'Video processing timeout',
            },
          };
        }
      }

      if (childResult.containerId) {
        childIds.push(childResult.containerId);
      }
    }

    containerParams.media_type = 'CAROUSEL';
    containerParams.children = childIds;
  } else if (input.video_url || mediaType === 'VIDEO' || mediaType === 'REELS') {
    containerParams.video_url = input.video_url;
    containerParams.media_type = mediaType === 'REELS' ? 'REELS' : 'VIDEO';
  } else {
    containerParams.image_url = input.image_url;
  }

  // Step 1: Create container
  const containerResult = await createMediaContainer(
    input.account_id,
    accessToken,
    containerParams
  );

  if (!containerResult.success || !containerResult.containerId) {
    return {
      success: false,
      platform: 'instagram',
      error: containerResult.error || { code: 'SYSTEM', message: 'Failed to create container' },
    };
  }

  // Step 2: Wait for processing (videos)
  if (input.video_url || mediaType === 'VIDEO' || mediaType === 'REELS') {
    const ready = await waitForContainerReady(
      containerResult.containerId,
      accessToken,
      input.poll_timeout_seconds || 300
    );

    if (!ready.ready) {
      return {
        success: false,
        platform: 'instagram',
        container_id: containerResult.containerId,
        status: 'processing',
        error: {
          code: 'TRANSIENT',
          message: ready.error || 'Video processing timeout',
        },
      };
    }
  }

  // Step 3: Publish container
  const publishResult = await publishContainer(
    input.account_id,
    containerResult.containerId,
    accessToken
  );

  if (!publishResult.success) {
    return {
      success: false,
      platform: 'instagram',
      container_id: containerResult.containerId,
      error: publishResult.error,
    };
  }

  return {
    success: true,
    media_id: publishResult.mediaId,
    container_id: containerResult.containerId,
    platform: 'instagram',
    status: 'published',
  };
}

/**
 * Main tool handler for publish_media.
 */
export async function publishInstagramMedia(
  input: PublishMediaInput
): Promise<PublishMediaOutput> {
  // Validate input
  const parsed = PublishMediaInputSchema.safeParse(input);
  if (!parsed.success) {
    return {
      success: false,
      platform: 'instagram',
      error: {
        code: 'LOGIC',
        message: `Invalid input: ${parsed.error.message}`,
      },
    };
  }

  const validInput = parsed.data;

  // Validate caption
  const captionValidation = validateCaption(validInput.caption);
  if (!captionValidation.valid) {
    return {
      success: false,
      platform: 'instagram',
      error: {
        code: 'LOGIC',
        message: captionValidation.error!,
      },
    };
  }

  // Validate media presence
  if (!validInput.image_url && !validInput.video_url && !validInput.children) {
    return {
      success: false,
      platform: 'instagram',
      error: {
        code: 'LOGIC',
        message: 'Must provide image_url, video_url, or children for carousel.',
      },
    };
  }

  // Validate carousel
  if (validInput.children) {
    if (validInput.children.length < 2 || validInput.children.length > 10) {
      return {
        success: false,
        platform: 'instagram',
        error: {
          code: 'LOGIC',
          message: 'Carousel must have 2-10 items.',
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
        platform: 'instagram',
        status: 'pending_approval',
        approval_file: approvalFile,
      };
    } catch (error) {
      return {
        success: false,
        platform: 'instagram',
        error: {
          code: 'SYSTEM',
          message: `Failed to create approval file: ${error instanceof Error ? error.message : 'Unknown error'}`,
        },
      };
    }
  }

  // Publish directly without approval
  return publishToInstagram(validInput);
}

/**
 * Execute approved post from approval file.
 */
export async function executeApprovedInstagramPost(
  approvalFilePath: string
): Promise<PublishMediaOutput> {
  try {
    const content = await fs.readFile(approvalFilePath, 'utf-8');

    // Extract JSON data from markdown
    const jsonMatch = content.match(/```json\n([\s\S]*?)\n```/);
    if (!jsonMatch) {
      return {
        success: false,
        platform: 'instagram',
        error: {
          code: 'DATA',
          message: 'Could not find post data in approval file.',
        },
      };
    }

    const postData = JSON.parse(jsonMatch[1]) as PublishMediaInput;

    // Execute the post (without requiring approval again)
    return publishToInstagram({ ...postData, require_approval: false });
  } catch (error) {
    return {
      success: false,
      platform: 'instagram',
      error: {
        code: 'SYSTEM',
        message: `Failed to execute approved post: ${error instanceof Error ? error.message : 'Unknown error'}`,
      },
    };
  }
}
