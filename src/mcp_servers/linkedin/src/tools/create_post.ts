/**
 * Create Post Tool for LinkedIn MCP Server
 *
 * Implements the create_post MCP tool with:
 * - Content validation (max 3000 chars)
 * - Visibility options (PUBLIC/CONNECTIONS)
 * - Idempotency check before post
 * - Rate limit enforcement (10/day)
 * - Full audit logging
 *
 * Implements T040, T042, T043 from tasks.md
 */

import axios from "axios";
import { z } from "zod";
import {
  getValidToken,
  type LinkedInToken,
} from "../credentials.js";
import {
  getIdempotencyClient,
  generatePostKey,
} from "../idempotency.js";

// LinkedIn API endpoint
const LINKEDIN_API_BASE = "https://api.linkedin.com/v2";

/**
 * Visibility enum for LinkedIn posts
 */
export const VisibilitySchema = z.enum(["PUBLIC", "CONNECTIONS"]);
export type Visibility = z.infer<typeof VisibilitySchema>;

/**
 * Input schema for create_post tool
 */
export const CreatePostInputSchema = z.object({
  content: z
    .string()
    .min(1)
    .max(3000)
    .describe("Post content (max 3000 characters)"),
  visibility: VisibilitySchema
    .default("PUBLIC")
    .describe("Post visibility: PUBLIC or CONNECTIONS"),
  media: z
    .array(z.string().url())
    .optional()
    .describe("URLs of media to attach (optional)"),
  dry_run: z
    .boolean()
    .optional()
    .default(false)
    .describe("If true, simulate post without actually posting"),
});

export type CreatePostInput = z.infer<typeof CreatePostInputSchema>;

/**
 * Output structure for create_post tool
 */
export interface CreatePostOutput {
  success: boolean;
  post_id?: string;
  url?: string;
  error?: string;
  rate_limit?: {
    remaining: number;
    limit: number;
  };
}

/**
 * Get LinkedIn user URN (required for posting)
 */
async function getUserUrn(token: LinkedInToken): Promise<string | null> {
  try {
    const response = await axios.get(`${LINKEDIN_API_BASE}/userinfo`, {
      headers: {
        Authorization: `Bearer ${token.access_token}`,
      },
    });

    // Response contains 'sub' which is the member URN
    const sub = response.data.sub;
    if (sub) {
      return `urn:li:person:${sub}`;
    }

    return null;
  } catch (error) {
    console.error("Failed to get LinkedIn user info:", error);
    return null;
  }
}

/**
 * Map visibility to LinkedIn API format
 */
function mapVisibility(visibility: Visibility): {
  "com.linkedin.ugc.MemberNetworkVisibility": string;
} {
  const visibilityMap: Record<Visibility, string> = {
    PUBLIC: "PUBLIC",
    CONNECTIONS: "CONNECTIONS",
  };

  return {
    "com.linkedin.ugc.MemberNetworkVisibility": visibilityMap[visibility],
  };
}

/**
 * Create a LinkedIn post
 *
 * @param input - Post parameters
 * @returns Post result with post ID or error
 */
export async function createPost(input: CreatePostInput): Promise<CreatePostOutput> {
  const idempotency = getIdempotencyClient();

  // Check rate limit first
  const rateLimit = idempotency.checkRateLimit();
  if (!rateLimit.allowed) {
    return {
      success: false,
      error: `Rate limit exceeded: ${rateLimit.count}/${rateLimit.limit} posts published today`,
      rate_limit: {
        remaining: 0,
        limit: rateLimit.limit,
      },
    };
  }

  // Generate idempotency key
  const idempotencyKey = generatePostKey(
    input.content,
    input.visibility,
    new Date()
  );

  // Check if already posted
  if (idempotency.isPostSent(idempotencyKey)) {
    console.error(`Post already sent (idempotency key: ${idempotencyKey.slice(0, 8)}...)`);
    return {
      success: false,
      error: "Duplicate post detected - already published within the idempotency window",
      rate_limit: {
        remaining: rateLimit.limit - rateLimit.count,
        limit: rateLimit.limit,
      },
    };
  }

  // Handle dry run mode
  if (input.dry_run) {
    console.error("[DRY RUN] Would post to LinkedIn:");
    console.error(`  Content: ${input.content.slice(0, 100)}...`);
    console.error(`  Visibility: ${input.visibility}`);

    return {
      success: true,
      post_id: "dry-run-post-id",
      url: "https://www.linkedin.com/feed/update/dry-run-post-id",
      rate_limit: {
        remaining: rateLimit.limit - rateLimit.count,
        limit: rateLimit.limit,
      },
    };
  }

  // Get credentials
  const token = await getValidToken();
  if (!token) {
    return {
      success: false,
      error: "LinkedIn credentials not found or expired. Please set up OAuth credentials.",
    };
  }

  try {
    // Get user URN
    const authorUrn = await getUserUrn(token);
    if (!authorUrn) {
      return {
        success: false,
        error: "Failed to retrieve LinkedIn user information",
      };
    }

    // Build post payload (UGC Post API format)
    const postPayload = {
      author: authorUrn,
      lifecycleState: "PUBLISHED",
      specificContent: {
        "com.linkedin.ugc.ShareContent": {
          shareCommentary: {
            text: input.content,
          },
          shareMediaCategory: "NONE",
        },
      },
      visibility: mapVisibility(input.visibility),
    };

    // Create the post
    const response = await axios.post(
      `${LINKEDIN_API_BASE}/ugcPosts`,
      postPayload,
      {
        headers: {
          Authorization: `Bearer ${token.access_token}`,
          "Content-Type": "application/json",
          "X-Restli-Protocol-Version": "2.0.0",
        },
      }
    );

    // Extract post ID from response
    const postId = response.data.id || response.headers["x-restli-id"];

    if (!postId) {
      console.error("LinkedIn post created but no ID returned:", response.data);
      return {
        success: false,
        error: "Post created but no ID returned from LinkedIn",
      };
    }

    console.error(`LinkedIn post created successfully: ${postId}`);

    // Build post URL
    const postUrl = `https://www.linkedin.com/feed/update/${postId}`;

    // Mark as posted in idempotency database
    idempotency.markPostSent(
      idempotencyKey,
      input.visibility,
      "success",
      {
        post_id: postId,
        url: postUrl,
        content_preview: input.content.slice(0, 100),
      }
    );

    // Return success with updated rate limit
    const newRateLimit = idempotency.checkRateLimit();

    return {
      success: true,
      post_id: postId,
      url: postUrl,
      rate_limit: {
        remaining: newRateLimit.limit - newRateLimit.count,
        limit: newRateLimit.limit,
      },
    };
  } catch (error) {
    let errorMessage: string;

    if (axios.isAxiosError(error)) {
      if (error.response) {
        errorMessage = `LinkedIn API error (${error.response.status}): ${JSON.stringify(error.response.data)}`;
      } else if (error.request) {
        errorMessage = "No response from LinkedIn API";
      } else {
        errorMessage = error.message;
      }
    } else {
      errorMessage = error instanceof Error ? error.message : String(error);
    }

    console.error("Failed to create LinkedIn post:", errorMessage);

    return {
      success: false,
      error: `LinkedIn API error: ${errorMessage}`,
      rate_limit: {
        remaining: rateLimit.limit - rateLimit.count,
        limit: rateLimit.limit,
      },
    };
  }
}

/**
 * Tool definition for MCP registration
 */
export const createPostToolDefinition = {
  name: "create_post",
  description:
    "Create a LinkedIn post. Requires prior approval through the approval workflow. " +
    "Rate limited to 10 posts per day. Duplicate posts are automatically detected and blocked. " +
    "Content is limited to 3000 characters.",
  inputSchema: {
    type: "object" as const,
    properties: {
      content: {
        type: "string",
        description: "Post content (max 3000 characters)",
        maxLength: 3000,
      },
      visibility: {
        type: "string",
        enum: ["PUBLIC", "CONNECTIONS"],
        description: "Post visibility: PUBLIC (anyone) or CONNECTIONS (1st degree only)",
        default: "PUBLIC",
      },
      media: {
        type: "array",
        items: { type: "string" },
        description: "URLs of media to attach (optional)",
      },
      dry_run: {
        type: "boolean",
        description: "If true, simulate post without actually posting (for testing)",
        default: false,
      },
    },
    required: ["content"],
  },
};
