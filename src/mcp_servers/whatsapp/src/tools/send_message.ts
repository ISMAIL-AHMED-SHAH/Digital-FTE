/**
 * send_message tool for WhatsApp MCP Server
 *
 * Sends a text message via the WhatsApp Business Cloud API.
 *
 * API reference:
 *   POST https://graph.facebook.com/v19.0/{phone_number_id}/messages
 *
 * Notes:
 *   - recipient_phone must include country code, e.g. "923001234567" (no + prefix)
 *   - Free-form text is allowed only within the 24-hour customer service window
 *   - Outside that window, use template messages (type: "template")
 */

import axios from "axios";
import { z } from "zod";
import { getWhatsAppCredentials } from "../credentials.js";

const GRAPH_API_BASE = "https://graph.facebook.com/v19.0";

// ─── Input Schema ────────────────────────────────────────────────────────────

export const SendMessageInputSchema = z.object({
  to: z
    .string()
    .min(7)
    .describe(
      "Recipient WhatsApp phone number with country code, no + or spaces (e.g. 923001234567)"
    ),
  message: z
    .string()
    .min(1)
    .max(4096)
    .describe("Text message body (max 4096 characters)"),
  dry_run: z
    .boolean()
    .optional()
    .default(false)
    .describe("If true, validate inputs without sending the message"),
});

export type SendMessageInput = z.infer<typeof SendMessageInputSchema>;

// ─── Output ──────────────────────────────────────────────────────────────────

export interface SendMessageOutput {
  success: boolean;
  message_id?: string;
  to?: string;
  error?: string;
}

// ─── Tool implementation ─────────────────────────────────────────────────────

export async function sendMessage(input: SendMessageInput): Promise<SendMessageOutput> {
  // Dry run — validate only
  if (input.dry_run) {
    console.error("[DRY RUN] Would send WhatsApp message:");
    console.error(`  To: ${input.to}`);
    console.error(`  Message: ${input.message.slice(0, 80)}...`);
    return {
      success: true,
      message_id: "dry-run-msg-id",
      to: input.to,
    };
  }

  // Load credentials
  const creds = getWhatsAppCredentials();
  if (!creds) {
    return {
      success: false,
      error:
        "WhatsApp credentials not configured. Set ACCESS_TOKEN, " +
        "WHATSAPP_PHONE_NUMBER_ID, and WHATSAPP_BUSINESS_ACCOUNT_ID in .env",
    };
  }

  try {
    const url = `${GRAPH_API_BASE}/${creds.phoneNumberId}/messages`;

    const payload = {
      messaging_product: "whatsapp",
      recipient_type: "individual",
      to: input.to,
      type: "text",
      text: {
        preview_url: false,
        body: input.message,
      },
    };

    const response = await axios.post(url, payload, {
      headers: {
        Authorization: `Bearer ${creds.accessToken}`,
        "Content-Type": "application/json",
      },
    });

    // The API returns { messages: [{ id: "wamid.xxx" }] }
    const messageId =
      response.data?.messages?.[0]?.id ?? "unknown";

    console.error(`[whatsapp-mcp] Message sent successfully: ${messageId}`);

    return {
      success: true,
      message_id: messageId,
      to: input.to,
    };
  } catch (error) {
    let errorMessage: string;

    if (axios.isAxiosError(error)) {
      if (error.response) {
        errorMessage = `WhatsApp API error (${error.response.status}): ${JSON.stringify(
          error.response.data
        )}`;
      } else if (error.request) {
        errorMessage = "No response from WhatsApp API";
      } else {
        errorMessage = error.message;
      }
    } else {
      errorMessage = error instanceof Error ? error.message : String(error);
    }

    console.error("[whatsapp-mcp] Failed to send message:", errorMessage);

    return {
      success: false,
      error: errorMessage,
    };
  }
}

// ─── MCP Tool Definition ─────────────────────────────────────────────────────

export const sendMessageToolDefinition = {
  name: "send_message",
  description:
    "Send a WhatsApp text message to a phone number via the WhatsApp Business Cloud API. " +
    "The recipient must have an active WhatsApp account. " +
    "Free-form text messages are delivered within the 24-hour customer service window; " +
    "outside that window you must use an approved template. " +
    "Phone number must include country code without + (e.g. 923001234567).",
  inputSchema: {
    type: "object" as const,
    properties: {
      to: {
        type: "string",
        description:
          "Recipient phone number with country code, no + or spaces (e.g. 923001234567)",
      },
      message: {
        type: "string",
        description: "Text message body (max 4096 characters)",
        maxLength: 4096,
      },
      dry_run: {
        type: "boolean",
        description: "If true, validate inputs without actually sending",
        default: false,
      },
    },
    required: ["to", "message"],
  },
};
