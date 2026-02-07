/**
 * Twitter Post Tweet Tool (T055).
 *
 * Posts tweets to Twitter/X via API v2.
 * Supports:
 * - Single tweets (up to 280 characters)
 * - Replies to other tweets
 * - Tweets with media
 * - HITL approval workflow
 */

import { z } from 'zod';
import * as fs from 'fs/promises';
import * as path from 'path';
import { createTwitterClient, TwitterClient, TWEET_CHAR_LIMIT } from '../lib/twitter_client.js';

/**
 * Input schema for post_tweet tool.
 */
export const PostTweetInputSchema = z.object({
  text: z.string().max(TWEET_CHAR_LIMIT).describe(`Tweet text (max ${TWEET_CHAR_LIMIT} characters)`),
  reply_to: z.string().optional().describe('Tweet ID to reply to'),
  media_ids: z.array(z.string()).optional().describe('Media IDs to attach'),
  require_approval: z.boolean().default(true).describe('Whether to require HITL approval'),
});

export type PostTweetInput = z.infer<typeof PostTweetInputSchema>;

/**
 * Output schema for post_tweet tool.
 */
export interface PostTweetOutput {
  success: boolean;
  tweet_id?: string;
  text?: string;
  platform: 'twitter';
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
  input: PostTweetInput,
  vaultPath: string
): Promise<string> {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const filename = `twitter-tweet-${timestamp}.md`;
  const approvalDir = path.join(vaultPath, 'Needs_Action');

  await fs.mkdir(approvalDir, { recursive: true });

  const charCount = input.text.length;
  const hasHashtags = input.text.includes('#');
  const hasMentions = input.text.includes('@');

  const content = `---
type: social_post
platform: twitter
status: pending
created: ${new Date().toISOString()}
${input.reply_to ? `reply_to: ${input.reply_to}` : ''}
---

# Twitter Post Approval Required

## Content

${input.text}

## Validation

- **Character count**: ${charCount}/${TWEET_CHAR_LIMIT}
- **Remaining**: ${TWEET_CHAR_LIMIT - charCount}
- **Has hashtags**: ${hasHashtags ? 'Yes' : 'No'}
- **Has mentions**: ${hasMentions ? 'Yes' : 'No'}
${input.reply_to ? `- **Reply to**: ${input.reply_to}` : ''}
${input.media_ids ? `- **Media attached**: ${input.media_ids.length}` : ''}

## Actions

- [ ] **Approve**: Move this file to \`/Done\` folder to publish
- [ ] **Reject**: Move to \`/Rejected\` folder with reason

## Post Data

\`\`\`json
${JSON.stringify({
  text: input.text,
  reply_to: input.reply_to,
  media_ids: input.media_ids,
}, null, 2)}
\`\`\`
`;

  const filePath = path.join(approvalDir, filename);
  await fs.writeFile(filePath, content, 'utf-8');

  return filePath;
}

/**
 * Post tweet directly (after approval or if approval not required).
 */
async function postTweetDirect(input: PostTweetInput): Promise<PostTweetOutput> {
  try {
    const client = createTwitterClient();
    const result = await client.postTweet(input.text, {
      replyTo: input.reply_to,
      mediaIds: input.media_ids,
    });

    if (!result.success) {
      return {
        success: false,
        platform: 'twitter',
        error: result.error,
      };
    }

    return {
      success: true,
      tweet_id: result.tweetId,
      text: result.text,
      platform: 'twitter',
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

/**
 * Main tool handler for post_tweet.
 */
export async function postTweet(
  input: PostTweetInput
): Promise<PostTweetOutput> {
  // Validate input
  const parsed = PostTweetInputSchema.safeParse(input);
  if (!parsed.success) {
    return {
      success: false,
      platform: 'twitter',
      error: {
        code: 'LOGIC',
        message: `Invalid input: ${parsed.error.message}`,
      },
    };
  }

  const validInput = parsed.data;

  // Validate text is not empty
  if (!validInput.text.trim()) {
    return {
      success: false,
      platform: 'twitter',
      error: {
        code: 'LOGIC',
        message: 'Tweet text cannot be empty',
      },
    };
  }

  // Validate character count
  if (validInput.text.length > TWEET_CHAR_LIMIT) {
    return {
      success: false,
      platform: 'twitter',
      error: {
        code: 'LOGIC',
        message: `Tweet exceeds ${TWEET_CHAR_LIMIT} character limit (${validInput.text.length} chars)`,
      },
    };
  }

  // Handle HITL approval workflow
  if (validInput.require_approval) {
    const vaultPath = process.env.VAULT_PATH || './vault';

    try {
      const approvalFile = await createApprovalFile(validInput, vaultPath);

      return {
        success: true,
        platform: 'twitter',
        approval_file: approvalFile,
      };
    } catch (error) {
      return {
        success: false,
        platform: 'twitter',
        error: {
          code: 'SYSTEM',
          message: `Failed to create approval file: ${error instanceof Error ? error.message : 'Unknown error'}`,
        },
      };
    }
  }

  // Post directly without approval
  return postTweetDirect(validInput);
}

/**
 * Execute approved tweet from approval file.
 */
export async function executeApprovedTweet(
  approvalFilePath: string
): Promise<PostTweetOutput> {
  try {
    const content = await fs.readFile(approvalFilePath, 'utf-8');

    // Extract JSON data from markdown
    const jsonMatch = content.match(/```json\n([\s\S]*?)\n```/);
    if (!jsonMatch) {
      return {
        success: false,
        platform: 'twitter',
        error: {
          code: 'DATA',
          message: 'Could not find post data in approval file.',
        },
      };
    }

    const postData = JSON.parse(jsonMatch[1]) as PostTweetInput;

    // Execute the tweet (without requiring approval again)
    return postTweetDirect({ ...postData, require_approval: false });
  } catch (error) {
    return {
      success: false,
      platform: 'twitter',
      error: {
        code: 'SYSTEM',
        message: `Failed to execute approved tweet: ${error instanceof Error ? error.message : 'Unknown error'}`,
      },
    };
  }
}
