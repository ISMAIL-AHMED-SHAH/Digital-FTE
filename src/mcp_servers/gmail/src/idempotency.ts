/**
 * Idempotency and Rate Limiting for Gmail MCP Server
 *
 * Connects to the shared SQLite idempotency database to:
 * - Prevent duplicate email sends
 * - Enforce rate limits (50 emails/day)
 *
 * Database schema defined in scripts/init_idempotency_db.sql
 */

import Database from "better-sqlite3";
import * as crypto from "crypto";
import * as path from "path";
import * as fs from "fs";

// Database path (relative to project root)
const DB_PATH = path.resolve(process.cwd(), "data", "idempotency.db");

/**
 * Rate limit configuration
 */
const DAILY_EMAIL_LIMIT = 50;

/**
 * Generate idempotency key for an email
 */
export function generateEmailKey(
  to: string,
  subject: string,
  body: string,
  timestamp: Date
): string {
  // Round timestamp to nearest minute to handle slight timing variations
  const roundedTime = new Date(timestamp);
  roundedTime.setSeconds(0, 0);

  const data = JSON.stringify({
    to: to.toLowerCase().trim(),
    subject: subject.trim(),
    body: body.trim(),
    timestamp: roundedTime.toISOString(),
  });

  return crypto.createHash("sha256").update(data).digest("hex");
}

/**
 * Idempotency database client
 */
export class IdempotencyClient {
  private db: Database.Database | null = null;

  constructor() {
    this.ensureDatabase();
  }

  /**
   * Ensure database exists and is connected
   */
  private ensureDatabase(): void {
    if (this.db) return;

    // Ensure data directory exists
    const dataDir = path.dirname(DB_PATH);
    if (!fs.existsSync(dataDir)) {
      fs.mkdirSync(dataDir, { recursive: true });
    }

    // Connect to database
    this.db = new Database(DB_PATH);

    // Create tables if they don't exist
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS sent_actions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        action_id TEXT NOT NULL UNIQUE,
        action_type TEXT NOT NULL,
        target TEXT,
        result TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        metadata TEXT
      );

      CREATE INDEX IF NOT EXISTS idx_sent_actions_type_created
        ON sent_actions(action_type, created_at);
    `);
  }

  /**
   * Check if an action has already been sent
   */
  isActionSent(actionId: string): boolean {
    this.ensureDatabase();

    const row = this.db!.prepare(
      "SELECT 1 FROM sent_actions WHERE action_id = ?"
    ).get(actionId);

    return !!row;
  }

  /**
   * Mark an action as sent
   */
  markActionSent(
    actionId: string,
    actionType: string,
    target: string,
    result: string,
    metadata?: Record<string, unknown>
  ): void {
    this.ensureDatabase();

    this.db!.prepare(
      `INSERT INTO sent_actions (action_id, action_type, target, result, metadata)
       VALUES (?, ?, ?, ?, ?)`
    ).run(
      actionId,
      actionType,
      target,
      result,
      metadata ? JSON.stringify(metadata) : null
    );
  }

  /**
   * Check rate limit for email sending
   *
   * @returns Object with allowed (boolean) and count (number sent today)
   */
  checkRateLimit(): { allowed: boolean; count: number; limit: number } {
    this.ensureDatabase();

    // Count emails sent in last 24 hours
    const row = this.db!.prepare(
      `SELECT COUNT(*) as count FROM sent_actions
       WHERE action_type = 'email'
       AND created_at >= datetime('now', '-1 day')`
    ).get() as { count: number };

    const count = row?.count ?? 0;

    return {
      allowed: count < DAILY_EMAIL_LIMIT,
      count,
      limit: DAILY_EMAIL_LIMIT,
    };
  }

  /**
   * Close database connection
   */
  close(): void {
    if (this.db) {
      this.db.close();
      this.db = null;
    }
  }
}

// Module-level singleton
let _client: IdempotencyClient | null = null;

export function getIdempotencyClient(): IdempotencyClient {
  if (!_client) {
    _client = new IdempotencyClient();
  }
  return _client;
}
