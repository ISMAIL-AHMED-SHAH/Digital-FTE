/**
 * Idempotency and Rate Limiting for LinkedIn MCP Server
 *
 * Connects to the shared SQLite idempotency database to:
 * - Prevent duplicate LinkedIn posts
 * - Enforce rate limits (10 posts/day)
 *
 * Implements T042, T043 from tasks.md
 */

import Database from "better-sqlite3";
import * as crypto from "crypto";
import * as path from "path";
import * as fs from "fs";

// Database path (relative to project root)
const DB_PATH = path.resolve(process.cwd(), "data", "idempotency.db");

/**
 * Rate limit configuration for LinkedIn
 * Max 10 posts per day per plan.md
 */
const DAILY_POST_LIMIT = 10;

/**
 * Generate idempotency key for a LinkedIn post
 *
 * Hash content + visibility + timestamp (rounded to minute)
 * per plan.md section 3.4 and T042
 */
export function generatePostKey(
  content: string,
  visibility: string,
  timestamp: Date
): string {
  // Round timestamp to nearest minute to handle slight timing variations
  const roundedTime = new Date(timestamp);
  roundedTime.setSeconds(0, 0);

  const data = JSON.stringify({
    content: content.trim(),
    visibility: visibility.toUpperCase(),
    timestamp: roundedTime.toISOString(),
  });

  return crypto.createHash("sha256").update(data).digest("hex");
}

/**
 * Idempotency database client for LinkedIn
 */
export class LinkedInIdempotencyClient {
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
   * Check if a post has already been sent
   */
  isPostSent(actionId: string): boolean {
    this.ensureDatabase();

    const row = this.db!.prepare(
      "SELECT 1 FROM sent_actions WHERE action_id = ? AND action_type = 'linkedin_post'"
    ).get(actionId);

    return !!row;
  }

  /**
   * Mark a post as sent
   */
  markPostSent(
    actionId: string,
    visibility: string,
    result: string,
    metadata?: Record<string, unknown>
  ): void {
    this.ensureDatabase();

    this.db!.prepare(
      `INSERT INTO sent_actions (action_id, action_type, target, result, metadata)
       VALUES (?, ?, ?, ?, ?)`
    ).run(
      actionId,
      "linkedin_post",
      visibility,
      result,
      metadata ? JSON.stringify(metadata) : null
    );
  }

  /**
   * Check rate limit for LinkedIn posting
   *
   * @returns Object with allowed (boolean) and count (number posted today)
   */
  checkRateLimit(): { allowed: boolean; count: number; limit: number } {
    this.ensureDatabase();

    // Count posts sent in last 24 hours
    const row = this.db!.prepare(
      `SELECT COUNT(*) as count FROM sent_actions
       WHERE action_type = 'linkedin_post'
       AND created_at >= datetime('now', '-1 day')`
    ).get() as { count: number };

    const count = row?.count ?? 0;

    return {
      allowed: count < DAILY_POST_LIMIT,
      count,
      limit: DAILY_POST_LIMIT,
    };
  }

  /**
   * Get recent posts for debugging/status
   */
  getRecentPosts(limit: number = 10): Array<{
    action_id: string;
    created_at: string;
    result: string;
    metadata: string | null;
  }> {
    this.ensureDatabase();

    return this.db!.prepare(
      `SELECT action_id, created_at, result, metadata FROM sent_actions
       WHERE action_type = 'linkedin_post'
       ORDER BY created_at DESC
       LIMIT ?`
    ).all(limit) as Array<{
      action_id: string;
      created_at: string;
      result: string;
      metadata: string | null;
    }>;
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
let _client: LinkedInIdempotencyClient | null = null;

export function getIdempotencyClient(): LinkedInIdempotencyClient {
  if (!_client) {
    _client = new LinkedInIdempotencyClient();
  }
  return _client;
}
