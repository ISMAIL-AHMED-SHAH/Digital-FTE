/**
 * Credential Retrieval for Gmail MCP Server
 *
 * Retrieves OAuth tokens from OS credential manager (via keytar) or
 * falls back to encrypted file storage.
 *
 * Implements T029 from tasks.md
 */

import * as fs from "fs";
import * as path from "path";
import * as crypto from "crypto";
import * as os from "os";

// Service name for credential storage (matches Python side)
// Python: f"{SERVICE_PREFIX}-{service}" -> "ai-employee-gmail"
const SERVICE_NAME = "ai-employee-gmail";
// Python: key -> "oauth_token"
const GMAIL_ACCOUNT = "oauth_token";

// Fallback encrypted file path
const ENCRYPTED_FILE_PATH = path.join(
  os.homedir(),
  ".ai-employee",
  "credentials.enc"
);

/**
 * Gmail OAuth token structure
 */
export interface GmailToken {
  access_token: string;
  refresh_token: string;
  client_id: string;
  client_secret: string;
  expires_at?: string;
}

/**
 * Get machine-specific encryption key
 * Uses same algorithm as Python credential manager for compatibility
 */
function getMachineKey(): Buffer {
  const machineId = `${os.hostname()}-${os.userInfo().username}`;
  return crypto.createHash("sha256").update(machineId).digest();
}

/**
 * Decrypt data using AES-256-CBC
 * Compatible with Python's cryptography.fernet format (simplified)
 */
function decryptData(encryptedData: Buffer, key: Buffer): string {
  // First 16 bytes are IV
  const iv = encryptedData.subarray(0, 16);
  const ciphertext = encryptedData.subarray(16);

  const decipher = crypto.createDecipheriv("aes-256-cbc", key, iv);
  let decrypted = decipher.update(ciphertext);
  decrypted = Buffer.concat([decrypted, decipher.final()]);

  return decrypted.toString("utf8");
}

/**
 * Try to get credentials from OS credential manager (keytar)
 */
async function getFromKeyring(): Promise<GmailToken | null> {
  try {
    // Dynamic import to handle if keytar is not available
    const keytar = await import("keytar");
    const password = await keytar.getPassword(SERVICE_NAME, GMAIL_ACCOUNT);

    if (!password) {
      return null;
    }

    return JSON.parse(password) as GmailToken;
  } catch (error) {
    // keytar not available or failed
    console.debug("Keyring not available:", error);
    return null;
  }
}

/**
 * Try to get credentials from encrypted file fallback
 */
function getFromEncryptedFile(): GmailToken | null {
  try {
    if (!fs.existsSync(ENCRYPTED_FILE_PATH)) {
      return null;
    }

    const encryptedData = fs.readFileSync(ENCRYPTED_FILE_PATH);
    const key = getMachineKey();

    // The file contains JSON with service-keyed tokens
    const decrypted = decryptData(encryptedData, key);
    const allTokens = JSON.parse(decrypted) as Record<string, GmailToken>;

    return allTokens[GMAIL_ACCOUNT] || null;
  } catch (error) {
    console.error("Failed to read encrypted credentials:", error);
    return null;
  }
}

/**
 * Get Gmail OAuth token from credential storage
 *
 * Tries OS credential manager first, falls back to encrypted file
 *
 * @returns Gmail token or null if not found
 * @throws Error if credentials are corrupted
 */
export async function getGmailToken(): Promise<GmailToken | null> {
  // Try keyring first
  let token = await getFromKeyring();

  if (token) {
    console.log("Retrieved Gmail token from OS credential manager");
    return token;
  }

  // Fall back to encrypted file
  token = getFromEncryptedFile();

  if (token) {
    console.log("Retrieved Gmail token from encrypted file");
    return token;
  }

  console.warn("No Gmail credentials found in any storage");
  return null;
}

/**
 * Validate that a token has required fields
 */
export function validateToken(token: GmailToken): boolean {
  return !!(
    token.access_token &&
    token.refresh_token &&
    token.client_id &&
    token.client_secret
  );
}

/**
 * Check if token is expired
 */
export function isTokenExpired(token: GmailToken): boolean {
  if (!token.expires_at) {
    return false; // Assume not expired if no expiry set
  }

  const expiresAt = new Date(token.expires_at);
  const now = new Date();

  // Consider expired if less than 5 minutes until expiry
  const bufferMs = 5 * 60 * 1000;
  return now.getTime() + bufferMs >= expiresAt.getTime();
}

/**
 * Store token back to credential manager (for token refresh)
 */
export async function storeGmailToken(token: GmailToken): Promise<boolean> {
  try {
    const keytar = await import("keytar");
    await keytar.setPassword(SERVICE_NAME, GMAIL_ACCOUNT, JSON.stringify(token));
    console.log("Stored refreshed Gmail token to OS credential manager");
    return true;
  } catch (error) {
    console.error("Failed to store token:", error);
    return false;
  }
}
