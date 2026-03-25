-- ============================================================================
-- APXMIND Production Schema - Phase 4: Admin & Moderation
-- ============================================================================
-- Admin panel, support tickets, content moderation, feature flags
-- ============================================================================

-- ============================================================================
-- 4.1 ADMIN ROLES
-- ============================================================================
-- Role-based access control for admin panel

CREATE TABLE IF NOT EXISTS admin_roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(50) UNIQUE NOT NULL,      -- 'super_admin', 'content_admin', 'support', 'analyst'
    display_name VARCHAR(100) NOT NULL,

-- Permissions (granular)
permissions JSON NOT NULL,
    /*
    {
        "users": ["view", "edit", "delete", "ban"],
        "content": ["view", "create", "edit", "delete", "publish"],
        "payments": ["view", "refund"],
        "analytics": ["view", "export"],
        "settings": ["view", "edit"],
        "admins": ["view", "create", "edit"]
    }
    */

    description TEXT,
    is_system BOOLEAN DEFAULT FALSE,       -- System roles can't be deleted

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- 4.2 ADMIN USERS
-- ============================================================================
-- Separate admin accounts (not regular users)

CREATE TABLE IF NOT EXISTS admin_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

-- Auth
email VARCHAR(120) UNIQUE NOT NULL,
password_hash VARCHAR(256) NOT NULL,

-- Profile
name VARCHAR(100) NOT NULL,
avatar_url TEXT,
phone VARCHAR(20),

-- Role
role_id INTEGER NOT NULL REFERENCES admin_roles (id),

-- Security
two_factor_enabled BOOLEAN DEFAULT FALSE,
two_factor_secret VARCHAR(128),
last_login_at DATETIME,
last_login_ip VARCHAR(45),
failed_login_attempts INTEGER DEFAULT 0,
account_locked_until DATETIME,

-- Status
is_active BOOLEAN DEFAULT TRUE,
deactivated_at DATETIME,
deactivated_by INTEGER REFERENCES admin_users (id),
deactivation_reason TEXT,

-- Metadata
created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES admin_users(id),
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_admin_email ON admin_users (email);

CREATE INDEX IF NOT EXISTS idx_admin_role ON admin_users (role_id);

-- ============================================================================
-- 4.3 ADMIN SESSIONS
-- ============================================================================

CREATE TABLE IF NOT EXISTS admin_sessions (
    id VARCHAR(36) PRIMARY KEY,
    admin_id INTEGER NOT NULL REFERENCES admin_users (id) ON DELETE CASCADE,
    token_hash VARCHAR(256) NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    expires_at DATETIME NOT NULL,
    is_revoked BOOLEAN DEFAULT FALSE,
    revoked_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_activity DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_admin_session_token ON admin_sessions (token_hash);

CREATE INDEX IF NOT EXISTS idx_admin_session_admin ON admin_sessions (admin_id);

-- ============================================================================
-- 4.4 ADMIN ACTIONS LOG
-- ============================================================================
-- Complete audit trail of admin actions

CREATE TABLE IF NOT EXISTS admin_actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_id INTEGER NOT NULL REFERENCES admin_users(id),

-- Action details
action VARCHAR(100) NOT NULL, -- 'user.ban', 'content.publish', 'refund.process'
action_category VARCHAR(50) NOT NULL, -- 'user', 'content', 'payment', 'system'

-- Target
target_type VARCHAR(30), -- 'user', 'lesson', 'payment', 'subscription'
target_id VARCHAR(64),
target_name VARCHAR(255), -- For easy display

-- Changes
old_value JSON, -- State before
new_value JSON, -- State after
change_summary TEXT, -- Human-readable summary

-- Context
reason TEXT, -- Why the action was taken
ip_address VARCHAR(45),
user_agent TEXT,

-- Status
status VARCHAR(20) DEFAULT 'success',  -- 'success', 'failed', 'reverted'
    error_message TEXT,

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_admin_action_admin ON admin_actions (admin_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_admin_action_target ON admin_actions (target_type, target_id);

CREATE INDEX IF NOT EXISTS idx_admin_action_type ON admin_actions (action, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_admin_action_category ON admin_actions (
    action_category,
    created_at DESC
);

-- ============================================================================
-- 4.5 SUPPORT TICKETS
-- ============================================================================
-- Customer support ticket system

CREATE TABLE IF NOT EXISTS support_tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_number VARCHAR(20) UNIQUE NOT NULL,  -- 'TKT-2026-00001'

-- Reporter
user_id INTEGER REFERENCES users (id), -- NULL = non-registered user
email VARCHAR(120) NOT NULL,
name VARCHAR(100),
phone VARCHAR(20),

-- Ticket details
subject VARCHAR(255) NOT NULL,
description TEXT NOT NULL,
category VARCHAR(50) NOT NULL, -- 'bug', 'payment', 'content', 'account', 'feedback', 'other'
subcategory VARCHAR(50),

-- Priority & Status
priority VARCHAR(20) DEFAULT 'normal', -- 'low', 'normal', 'high', 'urgent'
status VARCHAR(20) DEFAULT 'open', -- 'open', 'in_progress', 'waiting_user', 'waiting_internal', 'resolved', 'closed'

-- Assignment
assigned_to INTEGER REFERENCES admin_users (id),
assigned_at DATETIME,
escalated_to INTEGER REFERENCES admin_users (id),
escalated_at DATETIME,

-- SLA tracking
first_response_at DATETIME,
first_response_sla_met BOOLEAN,
resolution_sla_hours INTEGER DEFAULT 24,
resolution_sla_met BOOLEAN,

-- Resolution
resolution_summary TEXT,
resolution_type VARCHAR(30), -- 'resolved', 'duplicate', 'invalid', 'wont_fix'
resolved_at DATETIME,
resolved_by INTEGER REFERENCES admin_users (id),

-- Feedback
satisfaction_rating INTEGER, -- 1-5
satisfaction_comment TEXT,

-- Metadata
source VARCHAR(30) DEFAULT 'app', -- 'app', 'email', 'web', 'phone'
browser VARCHAR(50),
os VARCHAR(50),
app_version VARCHAR(20),
attachments JSON, -- List of attachment URLs

-- Tags
tags JSON,                             -- ["payment", "urgent", "bug"]

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    closed_at DATETIME
);

CREATE INDEX IF NOT EXISTS idx_ticket_number ON support_tickets (ticket_number);

CREATE INDEX IF NOT EXISTS idx_ticket_user ON support_tickets (user_id);

CREATE INDEX IF NOT EXISTS idx_ticket_status ON support_tickets (status, priority, created_at);

CREATE INDEX IF NOT EXISTS idx_ticket_assigned ON support_tickets (assigned_to, status);

CREATE INDEX IF NOT EXISTS idx_ticket_category ON support_tickets (category, status);

-- ============================================================================
-- 4.6 TICKET RESPONSES
-- ============================================================================
-- Messages within a support ticket

CREATE TABLE IF NOT EXISTS ticket_responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id INTEGER NOT NULL REFERENCES support_tickets(id) ON DELETE CASCADE,

-- Responder
responder_type VARCHAR(20) NOT NULL, -- 'user', 'admin', 'system'
responder_id INTEGER, -- user_id or admin_id
responder_name VARCHAR(100),

-- Content
message TEXT NOT NULL,
is_internal BOOLEAN DEFAULT FALSE, -- Internal notes (not visible to user)

-- Attachments
attachments JSON,

-- Auto-generated
is_automated BOOLEAN DEFAULT FALSE,    -- Auto-response
    automation_type VARCHAR(50),           -- 'initial_response', 'sla_warning', etc.

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_response_ticket ON ticket_responses (ticket_id, created_at);

-- ============================================================================
-- 4.7 CANNED RESPONSES
-- ============================================================================
-- Pre-written support responses

CREATE TABLE IF NOT EXISTS canned_responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(100) NOT NULL,
    content TEXT NOT NULL,
    category VARCHAR(50),
    tags JSON,
    usage_count INTEGER DEFAULT 0,
    created_by INTEGER REFERENCES admin_users (id),
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- 4.8 CONTENT REPORTS
-- ============================================================================
-- User-reported inappropriate content

CREATE TABLE IF NOT EXISTS content_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

-- Reporter
reporter_id INTEGER NOT NULL REFERENCES users (id),

-- Reported content
content_type VARCHAR(30) NOT NULL, -- 'note', 'comment', 'question', 'user', 'message'
content_id VARCHAR(64) NOT NULL,
content_preview TEXT, -- Snapshot of reported content

-- Report details
reason VARCHAR(50) NOT NULL, -- 'spam', 'inappropriate', 'harassment', 'copyright', 'misinformation', 'other'
description TEXT,

-- Review
status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'under_review', 'action_taken', 'dismissed'
reviewed_by INTEGER REFERENCES admin_users (id),
reviewed_at DATETIME,
review_notes TEXT,

-- Action taken
action_taken VARCHAR(50),              -- 'content_removed', 'user_warned', 'user_banned', 'no_action'
    action_details TEXT,

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_report_status ON content_reports (status, created_at);

CREATE INDEX IF NOT EXISTS idx_report_content ON content_reports (content_type, content_id);

CREATE INDEX IF NOT EXISTS idx_report_reporter ON content_reports (reporter_id);

-- ============================================================================
-- 4.9 USER WARNINGS & BANS
-- ============================================================================
-- Track warnings and bans issued to users

CREATE TABLE IF NOT EXISTS user_warnings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),

-- Warning details
warning_type VARCHAR(30) NOT NULL, -- 'content_violation', 'behavior', 'spam'
severity VARCHAR(20) NOT NULL, -- 'notice', 'warning', 'final_warning'
reason TEXT NOT NULL,

-- Related content
related_content_type VARCHAR(30),
related_content_id VARCHAR(64),
report_id INTEGER REFERENCES content_reports (id),

-- Issued by
issued_by INTEGER REFERENCES admin_users (id),

-- User acknowledgment
acknowledged_at DATETIME,

-- Expiry (for temporary records)
expires_at DATETIME,

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_warning_user ON user_warnings (user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS user_bans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),

-- Ban details
ban_type VARCHAR(30) NOT NULL, -- 'temporary', 'permanent', 'feature'
reason TEXT NOT NULL,
feature_restricted VARCHAR(50), -- For feature bans: 'comments', 'notes', 'chat'

-- Duration
starts_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
ends_at DATETIME, -- NULL = permanent

-- Related
warning_count_at_ban INTEGER, -- How many warnings before ban
report_id INTEGER REFERENCES content_reports (id),

-- Issued by
issued_by INTEGER REFERENCES admin_users (id),

-- Appeal
appeal_text TEXT,
appeal_status VARCHAR(20), -- 'pending', 'approved', 'denied'
appeal_reviewed_by INTEGER REFERENCES admin_users (id),
appeal_reviewed_at DATETIME,
appeal_notes TEXT,

-- Status
is_active BOOLEAN DEFAULT TRUE,
    lifted_at DATETIME,
    lifted_by INTEGER REFERENCES admin_users(id),
    lift_reason TEXT,

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ban_user ON user_bans (user_id, is_active);

CREATE INDEX IF NOT EXISTS idx_ban_active ON user_bans (is_active, ends_at);

-- ============================================================================
-- 4.10 FEATURE FLAGS
-- ============================================================================
-- Control feature rollout

CREATE TABLE IF NOT EXISTS feature_flags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) UNIQUE NOT NULL,     -- 'new_quiz_ui', 'ai_tutor_v2'
    display_name VARCHAR(100) NOT NULL,
    description TEXT,

-- Status
is_enabled BOOLEAN DEFAULT FALSE,

-- Rollout
rollout_percentage INTEGER DEFAULT 0, -- 0-100 for gradual rollout
rollout_strategy VARCHAR(30), -- 'random', 'user_id_hash', 'created_at'

-- Targeting
target_user_ids JSON, -- Specific users (beta testers)
target_segments JSON, -- ["premium", "new_users"]
exclude_user_ids JSON, -- Exclude specific users

-- Scheduling
enable_at DATETIME, disable_at DATETIME,

-- Variants (for A/B tests)
has_variants BOOLEAN DEFAULT FALSE,
variants JSON, -- [{"name": "control", "weight": 50}, {"name": "variant_a", "weight": 50}]

-- Metadata
owner VARCHAR(100),                    -- Team/person responsible
    jira_ticket VARCHAR(50),
    updated_by INTEGER REFERENCES admin_users(id),

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_feature_name ON feature_flags (name);

CREATE INDEX IF NOT EXISTS idx_feature_enabled ON feature_flags (is_enabled);

-- ============================================================================
-- 4.11 FEATURE FLAG USER OVERRIDES
-- ============================================================================
-- Per-user feature flag overrides

CREATE TABLE IF NOT EXISTS feature_flag_overrides (
    feature_id INTEGER NOT NULL REFERENCES feature_flags (id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    is_enabled BOOLEAN NOT NULL,
    variant VARCHAR(50), -- If using variants
    reason TEXT,
    set_by INTEGER REFERENCES admin_users (id),
    expires_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (feature_id, user_id)
);

-- ============================================================================
-- 4.12 SYSTEM SETTINGS
-- ============================================================================
-- Global application settings

CREATE TABLE IF NOT EXISTS system_settings (
    key VARCHAR(100) PRIMARY KEY,
    value JSON NOT NULL,
    value_type VARCHAR(20) NOT NULL, -- 'string', 'number', 'boolean', 'json'
    description TEXT,
    category VARCHAR(50) NOT NULL, -- 'general', 'limits', 'features', 'integrations'
    is_sensitive BOOLEAN DEFAULT FALSE, -- Don't log changes
    updated_by INTEGER REFERENCES admin_users (id),
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- 4.13 ANNOUNCEMENTS
-- ============================================================================
-- System-wide announcements

CREATE TABLE IF NOT EXISTS announcements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    content_type VARCHAR(20) DEFAULT 'text', -- 'text', 'markdown', 'html'

-- Display
announcement_type VARCHAR(30) NOT NULL, -- 'info', 'warning', 'maintenance', 'promo'
display_location VARCHAR(30), -- 'banner', 'modal', 'notification'
priority INTEGER DEFAULT 0,

-- Targeting
target_all BOOLEAN DEFAULT TRUE,
target_segments JSON,
target_platforms JSON, -- ['web', 'ios', 'android']

-- Scheduling
starts_at DATETIME NOT NULL, ends_at DATETIME,

-- Status
is_active BOOLEAN DEFAULT TRUE,
is_dismissible BOOLEAN DEFAULT TRUE,

-- Tracking
view_count INTEGER DEFAULT 0,
    dismiss_count INTEGER DEFAULT 0,

    created_by INTEGER REFERENCES admin_users(id),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_announcement_active ON announcements (is_active, starts_at, ends_at);

-- ============================================================================
-- 4.14 ANNOUNCEMENT DISMISSALS
-- ============================================================================

CREATE TABLE IF NOT EXISTS announcement_dismissals (
    announcement_id INTEGER NOT NULL REFERENCES announcements (id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    dismissed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (announcement_id, user_id)
);

-- ============================================================================
-- SEED DATA: Default Admin Roles
-- ============================================================================

INSERT OR IGNORE INTO
    admin_roles (
        name,
        display_name,
        permissions,
        description,
        is_system
    )
VALUES (
        'super_admin',
        'Super Administrator',
        '{"users": ["view", "edit", "delete", "ban"], "content": ["view", "create", "edit", "delete", "publish"], "payments": ["view", "refund", "adjust"], "analytics": ["view", "export"], "settings": ["view", "edit"], "admins": ["view", "create", "edit", "delete"], "support": ["view", "respond", "assign", "close"]}',
        'Full access to all admin functions',
        TRUE
    ),
    (
        'content_admin',
        'Content Administrator',
        '{"users": ["view"], "content": ["view", "create", "edit", "delete", "publish"], "analytics": ["view"], "settings": [], "admins": [], "support": ["view"]}',
        'Manage lessons, quizzes, and educational content',
        TRUE
    ),
    (
        'support_agent',
        'Support Agent',
        '{"users": ["view"], "content": ["view"], "payments": ["view"], "analytics": [], "settings": [], "admins": [], "support": ["view", "respond", "assign"]}',
        'Handle customer support tickets',
        TRUE
    ),
    (
        'moderator',
        'Content Moderator',
        '{"users": ["view", "warn", "ban"], "content": ["view", "hide"], "payments": [], "analytics": [], "settings": [], "admins": [], "support": ["view"], "reports": ["view", "action"]}',
        'Review and moderate user-generated content',
        TRUE
    ),
    (
        'analyst',
        'Data Analyst',
        '{"users": ["view"], "content": ["view"], "payments": ["view"], "analytics": ["view", "export"], "settings": [], "admins": [], "support": []}',
        'View analytics and generate reports',
        TRUE
    );

-- ============================================================================
-- SEED DATA: Default System Settings
-- ============================================================================

INSERT OR IGNORE INTO
    system_settings (
        key,
        value,
        value_type,
        description,
        category
    )
VALUES
    -- General
    (
        'app_name',
        '"ApxMind"',
        'string',
        'Application name',
        'general'
    ),
    (
        'app_tagline',
        '"Your AI NEET Companion"',
        'string',
        'Application tagline',
        'general'
    ),
    (
        'support_email',
        '"support@apxmind.com"',
        'string',
        'Support email address',
        'general'
    ),
    (
        'maintenance_mode',
        'false',
        'boolean',
        'Enable maintenance mode',
        'general'
    ),

-- Limits
(
    'free_daily_queries',
    '10',
    'number',
    'Daily query limit for free users',
    'limits'
),
(
    'basic_daily_queries',
    '50',
    'number',
    'Daily query limit for basic plan',
    'limits'
),
(
    'pro_daily_queries',
    '200',
    'number',
    'Daily query limit for pro plan',
    'limits'
),
(
    'max_bookmarks_free',
    '20',
    'number',
    'Max bookmarks for free users',
    'limits'
),
(
    'max_notes_free',
    '10',
    'number',
    'Max notes for free users',
    'limits'
),

-- Features
(
    'study_groups_enabled',
    'true',
    'boolean',
    'Enable study groups feature',
    'features'
),
(
    'mock_tests_enabled',
    'true',
    'boolean',
    'Enable mock tests feature',
    'features'
),
(
    'ai_tutor_version',
    '"v2"',
    'string',
    'Current AI tutor version',
    'features'
),

-- Gamification
(
    'xp_per_lesson',
    '50',
    'number',
    'XP awarded per lesson completion',
    'gamification'
),
(
    'xp_per_quiz_correct',
    '10',
    'number',
    'XP per correct quiz answer',
    'gamification'
),
(
    'streak_bonus_multiplier',
    '1.5',
    'number',
    'XP multiplier for streaks > 7 days',
    'gamification'
);

-- ============================================================================
-- SEED DATA: Default Feature Flags
-- ============================================================================

INSERT OR IGNORE INTO
    feature_flags (
        name,
        display_name,
        description,
        is_enabled,
        rollout_percentage
    )
VALUES (
        'new_dashboard',
        'New Dashboard UI',
        'Redesigned student dashboard',
        FALSE,
        0
    ),
    (
        'ai_tutor_v2',
        'AI Tutor V2',
        'Enhanced AI tutor with context memory',
        TRUE,
        100
    ),
    (
        'study_groups',
        'Study Groups',
        'Collaborative study groups feature',
        TRUE,
        100
    ),
    (
        'mock_tests',
        'Mock Tests',
        'Full NEET mock test simulations',
        TRUE,
        100
    ),
    (
        'offline_mode',
        'Offline Mode',
        'Download content for offline access',
        FALSE,
        0
    ),
    (
        'parent_portal',
        'Parent Portal',
        'Parent dashboard and reports',
        FALSE,
        0
    ),
    (
        'voice_input',
        'Voice Input',
        'Ask questions via voice',
        FALSE,
        10
    ),
    (
        'dark_mode',
        'Dark Mode',
        'Dark theme support',
        TRUE,
        100
    );

-- ============================================================================
-- END OF PHASE 4
-- ============================================================================