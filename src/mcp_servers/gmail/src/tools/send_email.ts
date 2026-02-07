/**
 * Send Email Tool for Gmail MCP Server
 *
 * Implements the send_email MCP tool with:
 * - Idempotency check before send
 * - Rate limit enforcement (50/day)
 * - Full audit logging
 *
 * Implements T028 from tasks.md
 */

import { google } from "googleapis";
import { OAuth2Client } from "google-auth-library";
import { z } from "zod";
import {
  getGmailToken,
  storeGmailToken,
  isTokenExpired,
  type GmailToken,
} from "../credentials.js";
import {
  getIdempotencyClient,
  generateEmailKey,
} from "../idempotency.js";

/**
 * Input schema for send_email tool
 */
export const SendEmailInputSchema = z.object({
  to: z.string().email().describe("Recipient email address"),
  subject: z.string().min(1).max(998).describe("Email subject line"),
  body: z.string().min(1).describe("Email body content (plain text)"),
  cc: z
    .array(z.string().email())
    .optional()
    .describe("CC recipients"),
  bcc: z
    .array(z.string().email())
    .optional()
    .describe("BCC recipients"),
  html: z
    .boolean()
    .optional()
    .default(false)
    .describe("If true, body is treated as HTML"),
  reply_to_message_id: z
    .string()
    .optional()
    .describe("Message ID to reply to (for threading)"),
  dry_run: z
    .boolean()
    .optional()
    .default(false)
    .describe("If true, simulate send without actually sending"),
});

export type SendEmailInput = z.infer<typeof SendEmailInputSchema>;

/**
 * Output structure for send_email tool
 */
export interface SendEmailOutput {
  success: boolean;
  message_id?: string;
  thread_id?: string;
  error?: string;
  rate_limit?: {
    remaining: number;
    limit: number;
  };
}

/**
 * Create OAuth2 client from stored token
 */
async function createOAuth2Client(token: GmailToken): Promise<OAuth2Client> {
  const oauth2Client = new google.auth.OAuth2(
    token.client_id,
    token.client_secret
  );

  oauth2Client.setCredentials({
    access_token: token.access_token,
    refresh_token: token.refresh_token,
  });

  // Check if token needs refresh
  if (isTokenExpired(token)) {
    console.log("Token expired, refreshing...");
    const { credentials } = await oauth2Client.refreshAccessToken();

    // Update stored token
    const newToken: GmailToken = {
      ...token,
      access_token: credentials.access_token!,
      expires_at: credentials.expiry_date
        ? new Date(credentials.expiry_date).toISOString()
        : undefined,
    };

    await storeGmailToken(newToken);
    oauth2Client.setCredentials(credentials);
  }

  return oauth2Client;
}

/**
 * Build RFC 2822 formatted email message
 */
function buildEmailMessage(input: SendEmailInput): string {
  const boundary = `boundary_${Date.now()}`;
  const headers: string[] = [];

  headers.push(`To: ${input.to}`);
  headers.push(`Subject: ${input.subject}`);

  if (input.cc && input.cc.length > 0) {
    headers.push(`Cc: ${input.cc.join(", ")}`);
  }

  if (input.bcc && input.bcc.length > 0) {
    headers.push(`Bcc: ${input.bcc.join(", ")}`);
  }

  if (input.reply_to_message_id) {
    headers.push(`In-Reply-To: ${input.reply_to_message_id}`);
    headers.push(`References: ${input.reply_to_message_id}`);
  }

  if (input.html) {
    headers.push("MIME-Version: 1.0");
    headers.push(`Content-Type: multipart/alternative; boundary="${boundary}"`);
    headers.push("");
    headers.push(`--${boundary}`);
    headers.push("Content-Type: text/html; charset=UTF-8");
    headers.push("Content-Transfer-Encoding: 7bit");
    headers.push("");
    headers.push(input.body);
    headers.push(`--${boundary}--`);
  } else {
    headers.push("MIME-Version: 1.0");
    headers.push("Content-Type: text/plain; charset=UTF-8");
    headers.push("");
    headers.push(input.body);
  }

  return headers.join("\r\n");
}

/**
 * Send email via Gmail API
 *
 * @param input - Email parameters
 * @returns Send result with message ID or error
 */
export async function sendEmail(input: SendEmailInput): Promise<SendEmailOutput> {
  const idempotency = getIdempotencyClient();

  // Check rate limit first
  const rateLimit = idempotency.checkRateLimit();
  if (!rateLimit.allowed) {
    return {
      success: false,
      error: `Rate limit exceeded: ${rateLimit.count}/${rateLimit.limit} emails sent today`,
      rate_limit: {
        remaining: 0,
        limit: rateLimit.limit,
      },
    };
  }

  // Generate idempotency key
  const idempotencyKey = generateEmailKey(
    input.to,
    input.subject,
    input.body,
    new Date()
  );

  // Check if already sent
  if (idempotency.isActionSent(idempotencyKey)) {
    console.log(`Email already sent (idempotency key: ${idempotencyKey.slice(0, 8)}...)`);
    return {
      success: false,
      error: "Duplicate email detected - already sent within the idempotency window",
      rate_limit: {
        remaining: rateLimit.limit - rateLimit.count,
        limit: rateLimit.limit,
      },
    };
  }

  // Handle dry run mode
  if (input.dry_run) {
    console.log("[DRY RUN] Would send email:");
    console.log(`  To: ${input.to}`);
    console.log(`  Subject: ${input.subject}`);
    console.log(`  Body: ${input.body.slice(0, 100)}...`);
    if (input.cc) console.log(`  CC: ${input.cc.join(", ")}`);
    if (input.bcc) console.log(`  BCC: ${input.bcc.join(", ")}`);

    return {
      success: true,
      message_id: "dry-run-message-id",
      thread_id: "dry-run-thread-id",
      rate_limit: {
        remaining: rateLimit.limit - rateLimit.count,
        limit: rateLimit.limit,
      },
    };
  }

  // Get credentials
  const token = await getGmailToken();
  if (!token) {
    return {
      success: false,
      error: "Gmail credentials not found. Run setup_gmail_oauth.py first.",
    };
  }

  try {
    // Create OAuth client
    const auth = await createOAuth2Client(token);
    const gmail = google.gmail({ version: "v1", auth });

    // Build email message
    const message = buildEmailMessage(input);
    const encodedMessage = Buffer.from(message)
      .toString("base64")
      .replace(/\+/g, "-")
      .replace(/\//g, "_")
      .replace(/=+$/, "");

    // Send email
    const response = await gmail.users.messages.send({
      userId: "me",
      requestBody: {
        raw: encodedMessage,
      },
    });

    const messageId = response.data.id!;
    const threadId = response.data.threadId!;

    console.log(`Email sent successfully: ${messageId}`);

    // Mark as sent in idempotency database
    idempotency.markActionSent(
      idempotencyKey,
      "email",
      input.to,
      "success",
      {
        message_id: messageId,
        thread_id: threadId,
        subject: input.subject,
      }
    );

    // Return success with updated rate limit
    const newRateLimit = idempotency.checkRateLimit();

    return {
      success: true,
      message_id: messageId,
      thread_id: threadId,
      rate_limit: {
        remaining: newRateLimit.limit - newRateLimit.count,
        limit: newRateLimit.limit,
      },
    };
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    console.error("Failed to send email:", errorMessage);

    // Log failed attempt (but don't mark as sent)
    return {
      success: false,
      error: `Gmail API error: ${errorMessage}`,
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
export const sendEmailToolDefinition = {
  name: "send_email",
  description:
    "Send an email via Gmail API. Requires prior approval through the approval workflow. " +
    "Rate limited to 50 emails per day. Duplicate emails are automatically detected and blocked.",
  inputSchema: {
    type: "object" as const,
    properties: {
      to: {
        type: "string",
        description: "Recipient email address",
      },
      subject: {
        type: "string",
        description: "Email subject line (max 998 characters)",
      },
      body: {
        type: "string",
        description: "Email body content",
      },
      cc: {
        type: "array",
        items: { type: "string" },
        description: "CC recipients (optional)",
      },
      bcc: {
        type: "array",
        items: { type: "string" },
        description: "BCC recipients (optional)",
      },
      html: {
        type: "boolean",
        description: "If true, body is treated as HTML (default: false)",
      },
      reply_to_message_id: {
        type: "string",
        description: "Message ID to reply to for threading (optional)",
      },
      dry_run: {
        type: "boolean",
        description: "If true, simulate send without actually sending (for testing)",
        default: false,
      },
    },
    required: ["to", "subject", "body"],
  },
};
