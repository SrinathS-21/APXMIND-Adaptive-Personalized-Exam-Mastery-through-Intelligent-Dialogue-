-- ============================================================================
-- APXMIND Production Schema - Phase 1: Security & Authentication
-- ============================================================================
-- Run this AFTER backing up your database!
-- ============================================================================

-- ============================================================================
-- 1.1 PASSWORD RESET TOKENS
-- ============================================================================
-- Secure password reset flow with expiring tokens

CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    token_hash VARCHAR(256) NOT NULL UNIQUE,
    expires_at DATETIME NOT NULL,
    used_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(45)
);

CREATE INDEX IF NOT EXISTS idx_reset_token ON password_reset_tokens (token_hash);

CREATE INDEX IF NOT EXISTS idx_reset_user_expires ON password_reset_tokens (user_id, expires_at);

-- ============================================================================
-- 1.2 REFRESH TOKENS (JWT Authentication)
-- ============================================================================
-- Long-lived refresh tokens for mobile apps and web sessions

CREATE TABLE IF NOT EXISTS user_sessions (
    id VARCHAR(36) PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    token_hash VARCHAR(256) NOT NULL,
    device_info JSON,
    ip_address VARCHAR(45),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME NOT NULL,
    last_activity DATETIME,
    is_revoked BOOLEAN DEFAULT 0
);

CREATE TABLE IF NOT EXISTS refresh_tokens (
    id VARCHAR(36) PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    session_id VARCHAR(36) REFERENCES user_sessions (id) ON DELETE SET NULL,
    token_hash VARCHAR(256) NOT NULL UNIQUE,
    device_fingerprint VARCHAR(256),
    expires_at DATETIME NOT NULL,
    revoked_at DATETIME,
    revoke_reason VARCHAR(50), -- 'logout', 'password_change', 'security', 'admin'
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_refresh_token ON refresh_tokens (token_hash);

CREATE INDEX IF NOT EXISTS idx_refresh_user ON refresh_tokens (user_id);

CREATE INDEX IF NOT EXISTS idx_refresh_expires ON refresh_tokens (expires_at);

-- ============================================================================
-- 1.3 RATE LIMITING
-- ============================================================================
-- Prevent API abuse and brute force attacks

CREATE TABLE IF NOT EXISTS rate_limits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    identifier VARCHAR(256) NOT NULL, -- IP address or user_id
    identifier_type VARCHAR(20) NOT NULL, -- 'ip', 'user', 'api_key'
    endpoint VARCHAR(255) NOT NULL, -- '/api/login', '/api/quiz/submit'
    request_count INTEGER NOT NULL DEFAULT 1,
    window_start DATETIME NOT NULL,
    window_end DATETIME NOT NULL,
    UNIQUE (
        identifier,
        endpoint,
        window_start
    )
);

CREATE INDEX IF NOT EXISTS idx_rate_limit_lookup ON rate_limits (
    identifier,
    endpoint,
    window_end
);

CREATE INDEX IF NOT EXISTS idx_rate_limit_cleanup ON rate_limits (window_end);

-- ============================================================================
-- 1.4 SECURITY BLOCKS
-- ============================================================================
-- Block malicious IPs, devices, or users

CREATE TABLE IF NOT EXISTS security_blocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    block_type VARCHAR(20) NOT NULL, -- 'ip', 'user', 'device', 'country'
    identifier VARCHAR(256) NOT NULL,
    reason TEXT NOT NULL,
    severity VARCHAR(20) DEFAULT 'medium', -- 'low', 'medium', 'high', 'critical'
    blocked_by INTEGER REFERENCES users (id), -- admin who blocked (NULL for auto)
    blocked_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME, -- NULL = permanent
    is_active BOOLEAN DEFAULT TRUE,
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_block_lookup ON security_blocks (
    block_type,
    identifier,
    is_active
);

CREATE INDEX IF NOT EXISTS idx_block_expires ON security_blocks (expires_at);

-- ============================================================================
-- 1.5 LOGIN HISTORY
-- ============================================================================
-- Track all login attempts for security monitoring

CREATE TABLE IF NOT EXISTS login_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    success BOOLEAN NOT NULL,
    failure_reason VARCHAR(50), -- 'wrong_password', 'locked', '2fa_failed', etc.
    ip_address VARCHAR(45),
    user_agent TEXT,
    device_type VARCHAR(30), -- 'mobile', 'tablet', 'desktop'
    browser VARCHAR(50),
    browser_version VARCHAR(20),
    os VARCHAR(50),
    os_version VARCHAR(20),
    location_country VARCHAR(50),
    location_state VARCHAR(100),
    location_city VARCHAR(100),
    is_suspicious BOOLEAN DEFAULT FALSE, -- Flagged for unusual activity
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_login_user_time ON login_history (user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_login_ip ON login_history (ip_address);

CREATE INDEX IF NOT EXISTS idx_login_suspicious ON login_history (
    is_suspicious,
    created_at DESC
);

-- ============================================================================
-- 1.6 EMAIL VERIFICATION TOKENS
-- ============================================================================
-- For email verification flow (separate from password reset)

CREATE TABLE IF NOT EXISTS email_verification_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    email VARCHAR(120) NOT NULL, -- The email being verified
    token_hash VARCHAR(256) NOT NULL UNIQUE,
    expires_at DATETIME NOT NULL,
    verified_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, email)
);

CREATE INDEX IF NOT EXISTS idx_email_verify_token ON email_verification_tokens (token_hash);

CREATE INDEX IF NOT EXISTS idx_email_verify_user ON email_verification_tokens (user_id);

-- ============================================================================
-- 1.7 TWO-FACTOR AUTHENTICATION BACKUP CODES
-- ============================================================================
-- Emergency recovery codes for 2FA

CREATE TABLE IF NOT EXISTS two_factor_backup_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    code_hash VARCHAR(256) NOT NULL,
    used_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_2fa_backup_user ON two_factor_backup_codes (user_id);

-- ============================================================================
-- 1.8 ACTIVE DEVICES
-- ============================================================================
-- Track user's trusted devices (for "manage devices" feature)

CREATE TABLE IF NOT EXISTS user_devices (
    id VARCHAR(36) PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    device_name VARCHAR(100), -- "iPhone 15 Pro", "Chrome on Windows"
    device_fingerprint VARCHAR(256),
    device_type VARCHAR(30) NOT NULL, -- 'mobile', 'tablet', 'desktop', 'tv'
    platform VARCHAR(30), -- 'ios', 'android', 'web', 'desktop'
    os VARCHAR(50),
    browser VARCHAR(50),
    is_trusted BOOLEAN DEFAULT FALSE,
    last_active_at DATETIME,
    last_ip_address VARCHAR(45),
    last_location VARCHAR(100),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_device_user ON user_devices (user_id);

CREATE INDEX IF NOT EXISTS idx_device_fingerprint ON user_devices (device_fingerprint);

-- ============================================================================
-- 1.9 USER COLUMNS ADDITIONS
-- ============================================================================
-- Add missing security columns to users table

-- Password security
ALTER TABLE users ADD COLUMN password_changed_at DATETIME;

ALTER TABLE users
ADD COLUMN must_change_password BOOLEAN DEFAULT FALSE;

-- Recovery options
ALTER TABLE users ADD COLUMN recovery_email VARCHAR(120);

ALTER TABLE users ADD COLUMN recovery_phone VARCHAR(20);

ALTER TABLE users ADD COLUMN security_questions JSON;

-- Legal & Compliance
ALTER TABLE users ADD COLUMN terms_accepted_at DATETIME;

ALTER TABLE users ADD COLUMN privacy_accepted_at DATETIME;

ALTER TABLE users ADD COLUMN gdpr_consent_at DATETIME;

ALTER TABLE users ADD COLUMN marketing_consent BOOLEAN DEFAULT FALSE;

ALTER TABLE users ADD COLUMN data_export_requested_at DATETIME;

ALTER TABLE users ADD COLUMN account_deletion_requested_at DATETIME;

-- ============================================================================
-- 1.10 SECURITY EVENTS (Detailed Audit Log)
-- ============================================================================
-- More detailed than audit_log, specifically for security events

CREATE TABLE IF NOT EXISTS security_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users (id) ON DELETE SET NULL,
    event_type VARCHAR(50) NOT NULL, -- 'password_change', 'login_suspicious', '2fa_enabled', etc.
    severity VARCHAR(20) NOT NULL, -- 'info', 'warning', 'critical'
    description TEXT NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    device_id VARCHAR(36),
    metadata JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_security_event_user ON security_events (user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_security_event_type ON security_events (event_type, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_security_event_severity ON security_events (severity, created_at DESC);

-- ============================================================================
-- PHASE 1 INDEXES (Performance)
-- ============================================================================

-- Ensure user_sessions has all needed indexes
CREATE INDEX IF NOT EXISTS idx_session_revoked ON user_sessions (is_revoked);

CREATE INDEX IF NOT EXISTS idx_session_last_activity ON user_sessions (last_activity);

-- ============================================================================
-- END OF PHASE 1
-- ============================================================================