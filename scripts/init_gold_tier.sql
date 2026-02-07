-- Gold Tier SQLite Schema Extensions
-- AI Employee - Autonomous Employee
-- Version: 0.3.0
--
-- This script extends the Silver Tier idempotency database with Gold Tier entities.
-- Run this after Silver Tier schema is initialized.

-- =============================================================================
-- Invoice Tracking (local cache of Odoo invoices)
-- =============================================================================
CREATE TABLE IF NOT EXISTS invoices (
    id TEXT PRIMARY KEY,
    odoo_id INTEGER,
    invoice_number TEXT,
    partner_id INTEGER NOT NULL,
    partner_name TEXT NOT NULL,
    invoice_date TEXT NOT NULL,
    due_date TEXT,
    amount_untaxed REAL DEFAULT 0,
    amount_tax REAL DEFAULT 0,
    amount_total REAL NOT NULL,
    amount_residual REAL DEFAULT 0,
    state TEXT NOT NULL DEFAULT 'draft' CHECK (state IN ('draft', 'pending_approval', 'posted', 'paid', 'cancelled')),
    notes TEXT,
    vault_reference TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_invoices_odoo_id ON invoices(odoo_id);
CREATE INDEX IF NOT EXISTS idx_invoices_state ON invoices(state);
CREATE INDEX IF NOT EXISTS idx_invoices_partner ON invoices(partner_id);
CREATE INDEX IF NOT EXISTS idx_invoices_date ON invoices(invoice_date);

-- Invoice line items
CREATE TABLE IF NOT EXISTS invoice_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id TEXT NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    quantity REAL NOT NULL DEFAULT 1,
    unit_price REAL NOT NULL,
    tax_ids TEXT,  -- JSON array of tax IDs
    subtotal REAL NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_invoice_lines_invoice ON invoice_lines(invoice_id);

-- =============================================================================
-- Payment Tracking (local cache of Odoo payments)
-- =============================================================================
CREATE TABLE IF NOT EXISTS payments (
    id TEXT PRIMARY KEY,
    odoo_id INTEGER,
    partner_id INTEGER NOT NULL,
    partner_name TEXT NOT NULL,
    amount REAL NOT NULL,
    currency TEXT DEFAULT 'USD',
    payment_type TEXT NOT NULL CHECK (payment_type IN ('inbound', 'outbound')),
    payment_method TEXT DEFAULT 'manual' CHECK (payment_method IN ('manual', 'check', 'bank_transfer', 'credit_card')),
    journal_id INTEGER,
    reference TEXT,
    payment_date TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'draft' CHECK (state IN ('draft', 'pending_approval', 'posted', 'reconciled', 'cancelled')),
    reconciled_invoice_ids TEXT,  -- JSON array of invoice IDs
    vault_reference TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_payments_odoo_id ON payments(odoo_id);
CREATE INDEX IF NOT EXISTS idx_payments_state ON payments(state);
CREATE INDEX IF NOT EXISTS idx_payments_partner ON payments(partner_id);
CREATE INDEX IF NOT EXISTS idx_payments_date ON payments(payment_date);

-- =============================================================================
-- Social Media Posts (extends Silver Tier pattern)
-- =============================================================================
CREATE TABLE IF NOT EXISTS social_media_posts (
    id TEXT PRIMARY KEY,
    platform TEXT NOT NULL CHECK (platform IN ('facebook', 'instagram', 'twitter', 'linkedin')),
    platform_post_id TEXT,
    platform_url TEXT,
    account_id TEXT NOT NULL,
    content_text TEXT,
    media_urls TEXT,  -- JSON array of URLs
    media_type TEXT DEFAULT 'none' CHECK (media_type IN ('none', 'image', 'video', 'carousel')),
    link TEXT,
    scheduled_time TEXT,
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'pending_approval', 'approved', 'publishing', 'published', 'failed', 'cancelled')),
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    character_count INTEGER,
    character_limit INTEGER,
    vault_reference TEXT NOT NULL,
    published_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_social_posts_platform ON social_media_posts(platform);
CREATE INDEX IF NOT EXISTS idx_social_posts_status ON social_media_posts(status);
CREATE INDEX IF NOT EXISTS idx_social_posts_scheduled ON social_media_posts(scheduled_time);

-- =============================================================================
-- CEO Briefings
-- =============================================================================
CREATE TABLE IF NOT EXISTS ceo_briefings (
    id TEXT PRIMARY KEY,
    period_start TEXT NOT NULL,
    period_end TEXT NOT NULL,
    generated_at TEXT NOT NULL,
    generated_by TEXT DEFAULT 'AI Employee v0.3 (Gold Tier)',
    executive_summary TEXT,
    revenue_data TEXT,  -- JSON object
    tasks_summary TEXT,  -- JSON object
    bottlenecks TEXT,  -- JSON array
    suggestions TEXT,  -- JSON object
    vault_path TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'generating' CHECK (status IN ('generating', 'generated', 'delivered', 'acknowledged')),
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_briefings_period ON ceo_briefings(period_start, period_end);
CREATE INDEX IF NOT EXISTS idx_briefings_status ON ceo_briefings(status);

-- =============================================================================
-- Ralph Wiggum Loop Tracking
-- =============================================================================
CREATE TABLE IF NOT EXISTS ralph_loops (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    task_prompt TEXT NOT NULL,
    task_file_path TEXT,
    completion_strategy TEXT DEFAULT 'hybrid' CHECK (completion_strategy IN ('file_based', 'promise_based', 'hybrid')),
    max_iterations INTEGER DEFAULT 10,
    current_iteration INTEGER DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'running' CHECK (status IN ('running', 'completed', 'max_iterations_reached', 'error', 'cancelled')),
    started_at TEXT NOT NULL,
    completed_at TEXT,
    timeout_minutes INTEGER DEFAULT 30,
    iteration_history TEXT,  -- JSON array of iteration records
    completion_signal TEXT,
    error_message TEXT,
    summary_path TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_ralph_loops_session ON ralph_loops(session_id);
CREATE INDEX IF NOT EXISTS idx_ralph_loops_status ON ralph_loops(status);

-- =============================================================================
-- Quarantined Files
-- =============================================================================
CREATE TABLE IF NOT EXISTS quarantined_files (
    id TEXT PRIMARY KEY,
    original_path TEXT NOT NULL,
    quarantine_path TEXT NOT NULL,
    filename TEXT NOT NULL,
    error_type TEXT NOT NULL CHECK (error_type IN ('parse_error', 'validation_error', 'processing_error', 'integrity_error', 'permission_error', 'unknown_error')),
    error_message TEXT NOT NULL,
    error_stack TEXT,
    file_hash TEXT NOT NULL,
    file_size_bytes INTEGER NOT NULL,
    quarantined_at TEXT NOT NULL,
    quarantined_by TEXT NOT NULL,
    resolution_status TEXT DEFAULT 'pending' CHECK (resolution_status IN ('pending', 'reviewed', 'fixed', 'deleted', 'restored')),
    resolution_notes TEXT,
    resolved_at TEXT,
    resolved_by TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_quarantine_status ON quarantined_files(resolution_status);
CREATE INDEX IF NOT EXISTS idx_quarantine_error_type ON quarantined_files(error_type);

-- =============================================================================
-- Action Queue (for graceful degradation)
-- =============================================================================
CREATE TABLE IF NOT EXISTS action_queue (
    id TEXT PRIMARY KEY,
    action_type TEXT NOT NULL,
    target_service TEXT NOT NULL,  -- 'odoo', 'facebook', 'instagram', 'twitter', 'gmail'
    payload TEXT NOT NULL,  -- JSON object
    priority INTEGER DEFAULT 5,  -- 1=highest, 10=lowest
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 5,
    last_error TEXT,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'cancelled')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    scheduled_at TEXT,
    processed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_action_queue_status ON action_queue(status);
CREATE INDEX IF NOT EXISTS idx_action_queue_service ON action_queue(target_service);
CREATE INDEX IF NOT EXISTS idx_action_queue_priority ON action_queue(priority);
CREATE INDEX IF NOT EXISTS idx_action_queue_scheduled ON action_queue(scheduled_at);

-- =============================================================================
-- Audit Log Extensions (supplements file-based logs)
-- =============================================================================
-- Note: Primary audit logs are in /Vault/Logs/YYYY-MM-DD.json
-- This table is for fast querying and analytics only
CREATE TABLE IF NOT EXISTS audit_log_index (
    id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    action_type TEXT NOT NULL,
    actor TEXT NOT NULL,
    target TEXT NOT NULL,
    success INTEGER NOT NULL,  -- 0=false, 1=true
    correlation_id TEXT,
    log_file_path TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log_index(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_action_type ON audit_log_index(action_type);
CREATE INDEX IF NOT EXISTS idx_audit_target ON audit_log_index(target);
CREATE INDEX IF NOT EXISTS idx_audit_success ON audit_log_index(success);
CREATE INDEX IF NOT EXISTS idx_audit_correlation ON audit_log_index(correlation_id);

-- =============================================================================
-- OAuth Token Metadata (tokens stored in OS credential manager)
-- =============================================================================
CREATE TABLE IF NOT EXISTS oauth_tokens (
    id TEXT PRIMARY KEY,
    service TEXT NOT NULL,  -- 'meta', 'twitter', 'gmail', 'linkedin'
    account_id TEXT NOT NULL,
    credential_ref TEXT NOT NULL,  -- Reference to OS credential manager key
    expires_at TEXT,
    refresh_token_ref TEXT,  -- Reference to refresh token in credential manager
    scopes TEXT,  -- JSON array of granted scopes
    last_refreshed_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(service, account_id)
);

CREATE INDEX IF NOT EXISTS idx_oauth_service ON oauth_tokens(service);
CREATE INDEX IF NOT EXISTS idx_oauth_expires ON oauth_tokens(expires_at);

-- =============================================================================
-- Subscription Tracking (for CEO Briefing cost optimization)
-- =============================================================================
CREATE TABLE IF NOT EXISTS subscriptions (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    provider TEXT NOT NULL,
    monthly_cost REAL NOT NULL,
    billing_date INTEGER,  -- Day of month
    last_used_at TEXT,
    usage_count INTEGER DEFAULT 0,
    category TEXT,  -- 'software', 'service', 'api', etc.
    notes TEXT,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'cancelled', 'paused')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON subscriptions(status);
CREATE INDEX IF NOT EXISTS idx_subscriptions_last_used ON subscriptions(last_used_at);

-- =============================================================================
-- Version tracking
-- =============================================================================
INSERT OR REPLACE INTO schema_version (version, applied_at, description)
VALUES ('0.3.0', datetime('now'), 'Gold Tier - Autonomous Employee schema extensions');

-- Create schema_version table if it doesn't exist
CREATE TABLE IF NOT EXISTS schema_version (
    version TEXT PRIMARY KEY,
    applied_at TEXT NOT NULL,
    description TEXT
);
