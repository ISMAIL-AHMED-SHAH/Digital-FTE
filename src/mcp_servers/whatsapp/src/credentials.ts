/**
 * Credential management for WhatsApp MCP Server
 *
 * Reads WhatsApp Business Cloud API credentials from environment variables.
 * Required env vars (set in .env):
 *   ACCESS_TOKEN              - Meta Graph API access token
 *   WHATSAPP_PHONE_NUMBER_ID  - Sender phone number ID from Meta dashboard
 *   WHATSAPP_BUSINESS_ACCOUNT_ID - WhatsApp Business Account ID
 */

export interface WhatsAppCredentials {
  accessToken: string;
  phoneNumberId: string;
  businessAccountId: string;
}

/**
 * Load WhatsApp credentials from environment variables.
 * Returns null if any required variable is missing.
 */
export function getWhatsAppCredentials(): WhatsAppCredentials | null {
  const accessToken = process.env["ACCESS_TOKEN"];
  const phoneNumberId = process.env["WHATSAPP_PHONE_NUMBER_ID"];
  const businessAccountId = process.env["WHATSAPP_BUSINESS_ACCOUNT_ID"];

  if (!accessToken || !phoneNumberId || !businessAccountId) {
    console.error(
      "[whatsapp-mcp] Missing credentials. Required: ACCESS_TOKEN, " +
        "WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_BUSINESS_ACCOUNT_ID"
    );
    return null;
  }

  return { accessToken, phoneNumberId, businessAccountId };
}

/**
 * Validate that credentials object has all required non-empty fields.
 */
export function validateCredentials(creds: WhatsAppCredentials): boolean {
  return !!(creds.accessToken && creds.phoneNumberId && creds.businessAccountId);
}
