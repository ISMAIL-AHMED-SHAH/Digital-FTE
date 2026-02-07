/**
 * Credential Retrieval for LinkedIn MCP Server
 *
 * Retrieves OAuth tokens from OS credential manager (via keytar) or
 * falls back to encrypted file storage.
 *
 * Implements T041 from tasks.md
 */

import * as fs from "fs";
import * as path from "path";
import * as crypto from "crypto";
import * as os from "os";
import axios from "axios";

// Service name for credential storage (matches Python side)
// Python: f"{SERVICE_PREFIX}-{service}" -> "ai-employee-linkedin"
const SERVICE_NAME = "ai-employee-linkedin";
// Python: key -> "oauth_token"
const LINKEDIN_ACCOUNT = "oauth_token";

// Fallback encrypted file path
const ENCRYPTED_FILE_PATH = path.join(
  os.homedir(),
  ".ai-employee",
  "credentials.enc"
);

// LinkedIn OAuth endpoints
const LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken";

/**
 * LinkedIn OAuth token structure
 */
export interface LinkedInToken {
  access_token: string;
  refresh_token?: string;
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
 * Compatible with Python's cryptography format (simplified)
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
async function getFromKeyring(): Promise<LinkedInToken | null> {
  try {
    // Dynamic import to handle if keytar is not available
    const keytar = await import("keytar");
    const password = await keytar.getPassword(SERVICE_NAME, LINKEDIN_ACCOUNT);

    if (!password) {
      return null;
    }

    return JSON.parse(password) as LinkedInToken;
  } catch (error) {
    // keytar not available or failed
    console.debug("Keyring not available:", error);
    return null;
  }
}

/**
 * Try to get credentials from encrypted file fallback
 */
function getFromEncryptedFile(): LinkedInToken | null {
  try {
    if (!fs.existsSync(ENCRYPTED_FILE_PATH)) {
      return null;
    }

    const encryptedData = fs.readFileSync(ENCRYPTED_FILE_PATH);
    const key = getMachineKey();

    // The file contains JSON with service-keyed tokens
    const decrypted = decryptData(encryptedData, key);
    const allTokens = JSON.parse(decrypted) as Record<string, LinkedInToken>;

    return allTokens[LINKEDIN_ACCOUNT] || null;
  } catch (error) {
    console.error("Failed to read encrypted credentials:", error);
    return null;
  }
}

/**
 * Get LinkedIn OAuth token from credential storage
 *
 * Tries OS credential manager first, falls back to encrypted file
 *
 * @returns LinkedIn token or null if not found
 */
export async function getLinkedInToken(): Promise<LinkedInToken | null> {
  // Try keyring first
  let token = await getFromKeyring();

  if (token) {
    console.error("Retrieved LinkedIn token from OS credential manager");
    return token;
  }

  // Fall back to encrypted file
  token = getFromEncryptedFile();

  if (token) {
    console.error("Retrieved LinkedIn token from encrypted file");
    return token;
  }

  console.error("No LinkedIn credentials found in any storage");
  return null;
}

/**
 * Validate that a token has required fields
 */
export function validateToken(token: LinkedInToken): boolean {
  return !!(
    token.access_token &&
    token.client_id &&
    token.client_secret
  );
}

/**
 * Check if token is expired
 */
export function isTokenExpired(token: LinkedInToken): boolean {
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
 * Refresh LinkedIn access token
 *
 * LinkedIn's refresh tokens are long-lived but access tokens expire.
 * Note: LinkedIn OAuth refresh requires the refresh_token grant type.
 */
export async function refreshToken(token: LinkedInToken): Promise<LinkedInToken | null> {
  if (!token.refresh_token) {
    console.error("No refresh token available for LinkedIn");
    return null;
  }

  try {
    const response = await axios.post(
      LINKEDIN_TOKEN_URL,
      new URLSearchParams({
        grant_type: "refresh_token",
        refresh_token: token.refresh_token,
        client_id: token.client_id,
        client_secret: token.client_secret,
      }).toString(),
      {
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
      }
    );

    const newToken: LinkedInToken = {
      ...token,
      access_token: response.data.access_token,
      refresh_token: response.data.refresh_token || token.refresh_token,
      expires_at: response.data.expires_in
        ? new Date(Date.now() + response.data.expires_in * 1000).toISOString()
        : undefined,
    };

    // Store the updated token
    await storeLinkedInToken(newToken);

    console.error("LinkedIn token refreshed successfully");
    return newToken;
  } catch (error) {
    console.error("Failed to refresh LinkedIn token:", error);
    return null;
  }
}

/**
 * Store token back to credential manager
 */
export async function storeLinkedInToken(token: LinkedInToken): Promise<boolean> {
  try {
    const keytar = await import("keytar");
    await keytar.setPassword(SERVICE_NAME, LINKEDIN_ACCOUNT, JSON.stringify(token));
    console.error("Stored LinkedIn token to OS credential manager");
    return true;
  } catch (error) {
    console.error("Failed to store token:", error);
    return false;
  }
}

/**
 * Get valid access token, refreshing if necessary
 */
export async function getValidToken(): Promise<LinkedInToken | null> {
  const token = await getLinkedInToken();

  if (!token) {
    return null;
  }

  if (!validateToken(token)) {
    console.error("LinkedIn token is invalid or incomplete");
    return null;
  }

  if (isTokenExpired(token)) {
    console.error("LinkedIn token is expired, attempting refresh...");
    const refreshed = await refreshToken(token);
    if (refreshed) {
      return refreshed;
    }
    console.error("Token refresh failed");
    return null;
  }

  return token;
}
