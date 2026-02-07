-- AI Employee Idempotency Database Schema
-- Silver Tier: External Connectivity
-- Version: 1.0.0

-- =============================================================================
-- Processed Messages Table
-- Tracks messages that have been detected by watchers to prevent duplicate processing
-- =============================================================================
CREATE TABLE IF NOT EXISTS processed_messages (
    -- Primary key: Message-ID for emails, SHA-256 hash for WhatsApp
    message_id TEXT PRIMARY KEY,
    -- Source watcher: 'gmail', 'whatsapp', 'file_drop'
    source TEXT NOT NULL,
    -- When the message was processed (ISO 8601 UTC)
    processed_at TEXT NOT NULL,
    -- When this record expires (processed_at + 7 days)
    expires_at TEXT NOT NULL,
    -- Optional: sender information for debugging
    sender TEXT,
    -- Optional: subject/preview for debugging
    subject TEXT
);

-- Index for efficient cleanup queries
CREATE INDEX IF NOT EXISTS idx_processed_expires_at
ON processed_messages(expires_at);

-- Index for source-based queries
CREATE INDEX IF NOT EXISTS idx_processed_source
ON processed_messages(source);

-- =============================================================================
-- Sent Actions Table
-- Tracks external actions (emails, posts) to prevent duplicates during retries
-- =============================================================================
CREATE TABLE IF NOT EXISTS sent_actions (
    -- Primary key: Message-ID for emails, content hash for posts
    action_id TEXT PRIMARY KEY,
    -- Action type: 'email_send', 'linkedin_post', 'whatsapp_send'
    action_type TEXT NOT NULL,
    -- Recipient: email address or visibility setting
    recipient TEXT,
    -- When the action was executed (ISO 8601 UTC)
    sent_at TEXT NOT NULL,
    -- When this record expires (sent_at + 7 days)
    expires_at TEXT NOT NULL,
    -- Result status: 'success', 'failed'
    result_status TEXT NOT NULL,
    -- Optional: error message if failed
    error_message TEXT,
    -- Optional: external ID returned by API (e.g., Gmail Message-ID)
    external_id TEXT
);

-- Index for efficient cleanup queries
CREATE INDEX IF NOT EXISTS idx_sent_expires_at
ON sent_actions(expires_at);

-- Index for action type queries
CREATE INDEX IF NOT EXISTS idx_sent_action_type
ON sent_actions(action_type);

-- Index for recipient queries (finding duplicates)
CREATE INDEX IF NOT EXISTS idx_sent_recipient
ON sent_actions(recipient);

-- =============================================================================
-- Rate Limit Counters Table
-- Tracks daily rate limits for external actions
-- =============================================================================
CREATE TABLE IF NOT EXISTS rate_limits (
    -- Composite key: action_type + date
    action_type TEXT NOT NULL,
    -- Date in YYYY-MM-DD format
    limit_date TEXT NOT NULL,
    -- Current count of actions
    current_count INTEGER NOT NULL DEFAULT 0,
    -- Maximum allowed (for reference, enforced in code)
    max_count INTEGER NOT NULL,
    -- When this record was last updated
    updated_at TEXT NOT NULL,
    PRIMARY KEY (action_type, limit_date)
);

-- Index for cleanup of old rate limit records
CREATE INDEX IF NOT EXISTS idx_rate_limits_date
ON rate_limits(limit_date);

-- =============================================================================
-- Schema Version Table
-- Tracks database schema version for migrations
-- =============================================================================
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL,
    description TEXT
);

-- Insert initial version
INSERT OR IGNORE INTO schema_version (version, applied_at, description)
VALUES (1, datetime('now'), 'Initial schema for Silver Tier idempotency tracking');

-- =============================================================================
-- Cleanup View (for monitoring)
-- =============================================================================
CREATE VIEW IF NOT EXISTS v_pending_cleanup AS
SELECT
    'processed_messages' as table_name,
    COUNT(*) as expired_count
FROM processed_messages
WHERE expires_at < datetime('now')
UNION ALL
SELECT
    'sent_actions' as table_name,
    COUNT(*) as expired_count
FROM sent_actions
WHERE expires_at < datetime('now')
UNION ALL
SELECT
    'rate_limits' as table_name,
    COUNT(*) as expired_count
FROM rate_limits
WHERE limit_date < date('now', '-7 days');

-- =============================================================================
-- Comments
-- =============================================================================
--
-- Usage:
--   sqlite3 data/idempotency.db < scripts/init_idempotency_db.sql
--
-- Cleanup (run daily via cron/scheduler):
--   DELETE FROM processed_messages WHERE expires_at < datetime('now');
--   DELETE FROM sent_actions WHERE expires_at < datetime('now');
--   DELETE FROM rate_limits WHERE limit_date < date('now', '-7 days');
--   VACUUM;
--
-- Backup (run daily before cleanup):
--   .backup data/idempotency.db-backup
