-- ============================================================================
-- APXMIND Production Schema - Phase 3: Notifications System
-- ============================================================================
-- Multi-channel notifications: In-app, Push (FCM/APNs), Email, SMS
-- ============================================================================

-- ============================================================================
-- 3.1 NOTIFICATION TEMPLATES
-- ============================================================================
-- Admin-defined templates for all notification types

CREATE TABLE IF NOT EXISTS notification_templates (
    id VARCHAR(50) PRIMARY KEY,            -- 'streak_reminder', 'quiz_complete', etc.
    name VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,         -- 'achievement', 'reminder', 'social', 'system', 'promo'

-- Templates with variable placeholders
title_template TEXT NOT NULL, -- "🔥 {{streak}} day streak!"
body_template TEXT NOT NULL, -- "Keep going {{name}}! You're on fire!"

-- Rich content
image_url TEXT,
icon VARCHAR(50), -- Emoji or icon code
color VARCHAR(20), -- Hex color for notification

-- Channel configuration
channels JSON NOT NULL DEFAULT '["in_app"]',
-- ["in_app", "push", "email", "sms"]

-- Email specific
email_subject_template TEXT, email_html_template TEXT,

-- SMS specific
sms_template TEXT, -- Shorter version for SMS

-- Variables schema
variables JSON, -- {"name": "string", "streak": "number"}

-- Behavior
is_transactional BOOLEAN DEFAULT FALSE, -- Bypasses preferences
    priority VARCHAR(10) DEFAULT 'normal', -- 'low', 'normal', 'high', 'urgent'
    ttl_hours INTEGER,                     -- Time to live (auto-expire)

    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- 3.2 USER NOTIFICATIONS
-- ============================================================================
-- Actual notifications sent to users

CREATE TABLE IF NOT EXISTS user_notifications (
    id VARCHAR(36) PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    template_id VARCHAR(50) REFERENCES notification_templates(id),

-- Content (rendered from template)
title VARCHAR(255) NOT NULL,
body TEXT NOT NULL,
image_url TEXT,
icon VARCHAR(50),

-- Categorization
category VARCHAR(50) NOT NULL, -- 'achievement', 'reminder', 'social', 'system', 'promo'
subcategory VARCHAR(50), -- More specific: 'badge_earned', 'streak_broken'

-- Action
action_type VARCHAR(30), -- 'open_lesson', 'open_quiz', 'open_url', 'open_screen'
action_data JSON, -- {"lesson_id": 123} or {"url": "https://..."}

-- Priority & Grouping
priority VARCHAR(10) DEFAULT 'normal', -- 'low', 'normal', 'high', 'urgent'
group_key VARCHAR(50), -- Group similar notifications

-- Status
is_read BOOLEAN DEFAULT FALSE,
read_at DATETIME,
is_seen BOOLEAN DEFAULT FALSE, -- Seen in notification list (not necessarily read)
seen_at DATETIME,
is_dismissed BOOLEAN DEFAULT FALSE,
dismissed_at DATETIME,

-- Delivery tracking
delivered_via JSON DEFAULT '[]', -- ["in_app", "push"]
delivery_errors JSON,

-- Timestamps
created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME,
    scheduled_for DATETIME                 -- NULL = immediate
);

CREATE INDEX IF NOT EXISTS idx_notif_user_unread ON user_notifications (
    user_id,
    is_read,
    created_at DESC
);

CREATE INDEX IF NOT EXISTS idx_notif_user_category ON user_notifications (
    user_id,
    category,
    created_at DESC
);

CREATE INDEX IF NOT EXISTS idx_notif_scheduled ON user_notifications (scheduled_for)
WHERE
    scheduled_for IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_notif_expires ON user_notifications (expires_at)
WHERE
    expires_at IS NOT NULL;

-- ============================================================================
-- 3.3 PUSH NOTIFICATION TOKENS
-- ============================================================================
-- FCM (Android/Web) and APNs (iOS) tokens

CREATE TABLE IF NOT EXISTS push_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,

-- Token
token VARCHAR(512) NOT NULL,
token_type VARCHAR(20) NOT NULL, -- 'fcm', 'apns', 'web_push'

-- Device info
device_id VARCHAR(100),
device_name VARCHAR(100), -- "iPhone 15", "Samsung Galaxy S24"
platform VARCHAR(20) NOT NULL, -- 'ios', 'android', 'web'
app_version VARCHAR(20),

-- Status
is_active BOOLEAN DEFAULT TRUE,
    last_used_at DATETIME,
    failed_count INTEGER DEFAULT 0,        -- Increment on delivery failure
    last_failure_at DATETIME,
    last_failure_reason TEXT,

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(user_id, token)
);

CREATE INDEX IF NOT EXISTS idx_push_user ON push_tokens (user_id, is_active);

CREATE INDEX IF NOT EXISTS idx_push_token ON push_tokens (token);

-- ============================================================================
-- 3.4 NOTIFICATION PREFERENCES
-- ============================================================================
-- User preferences for each notification category

CREATE TABLE IF NOT EXISTS notification_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category VARCHAR(50) NOT NULL,

-- Per-channel preferences
in_app BOOLEAN DEFAULT TRUE,
push BOOLEAN DEFAULT TRUE,
email BOOLEAN DEFAULT FALSE,
sms BOOLEAN DEFAULT FALSE,

-- Frequency limits
max_per_day INTEGER,                   -- NULL = unlimited
    digest_mode VARCHAR(20),               -- NULL, 'daily', 'weekly'

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(user_id, category)
);

-- ============================================================================
-- 3.5 GLOBAL NOTIFICATION SETTINGS
-- ============================================================================
-- User's global notification settings

CREATE TABLE IF NOT EXISTS notification_settings (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,

-- Master switches
all_notifications_enabled BOOLEAN DEFAULT TRUE,
push_enabled BOOLEAN DEFAULT TRUE,
email_enabled BOOLEAN DEFAULT TRUE,
sms_enabled BOOLEAN DEFAULT FALSE,

-- Quiet hours (DND)
quiet_hours_enabled BOOLEAN DEFAULT FALSE,
quiet_hours_start TIME, -- "22:00"
quiet_hours_end TIME, -- "07:00"
quiet_hours_timezone VARCHAR(64) DEFAULT 'Asia/Kolkata',

-- Email preferences
email_digest_enabled BOOLEAN DEFAULT TRUE,
email_digest_frequency VARCHAR(20) DEFAULT 'daily', -- 'daily', 'weekly'
email_digest_time TIME DEFAULT '09:00',

-- Language
preferred_language VARCHAR(10) DEFAULT 'en',

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- 3.6 SCHEDULED NOTIFICATIONS
-- ============================================================================
-- For reminders, scheduled campaigns, etc.

CREATE TABLE IF NOT EXISTS scheduled_notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

-- Target
user_id INTEGER REFERENCES users (id) ON DELETE CASCADE, -- NULL = segment-based
segment_id INTEGER, -- Target a user segment

-- Content
template_id VARCHAR(50) REFERENCES notification_templates (id),
title VARCHAR(255), -- Override template
body TEXT, -- Override template
variables JSON, -- Template variables

-- Schedule
scheduled_for DATETIME NOT NULL,
timezone VARCHAR(64) DEFAULT 'Asia/Kolkata',

-- Recurrence
is_recurring BOOLEAN DEFAULT FALSE,
recurrence_rule VARCHAR(100), -- iCal RRULE format
-- 'FREQ=DAILY;BYDAY=MO,TU,WE,TH,FR' (weekdays)
-- 'FREQ=WEEKLY;BYDAY=SU' (every Sunday)
recurrence_end_date DATE,
last_sent_at DATETIME,
next_occurrence DATETIME,

-- Status
status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'sent', 'cancelled', 'failed', 'paused'
sent_at DATETIME,
failure_reason TEXT,

-- Metadata
campaign_name VARCHAR(100),
    created_by INTEGER,                    -- Admin who created
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sched_pending ON scheduled_notifications (status, scheduled_for);

CREATE INDEX IF NOT EXISTS idx_sched_user ON scheduled_notifications (user_id, status);

CREATE INDEX IF NOT EXISTS idx_sched_recurring ON scheduled_notifications (is_recurring, next_occurrence);

-- ============================================================================
-- 3.7 NOTIFICATION DELIVERY LOG
-- ============================================================================
-- Track delivery status for each channel


CREATE TABLE IF NOT EXISTS notification_delivery_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    notification_id VARCHAR(36) NOT NULL REFERENCES user_notifications(id) ON DELETE CASCADE,

    channel VARCHAR(20) NOT NULL,          -- 'push', 'email', 'sms'

-- Delivery status
status VARCHAR(20) NOT NULL, -- 'pending', 'sent', 'delivered', 'failed', 'bounced'

-- Provider details
provider VARCHAR(30), -- 'fcm', 'apns', 'sendgrid', 'twilio'
provider_message_id VARCHAR(255),

-- Error handling
error_code VARCHAR(50),
error_message TEXT,
retry_count INTEGER DEFAULT 0,

-- Timestamps
sent_at DATETIME,
    delivered_at DATETIME,
    failed_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_delivery_notification ON notification_delivery_log (notification_id);

CREATE INDEX IF NOT EXISTS idx_delivery_status ON notification_delivery_log (status, created_at);

-- ============================================================================
-- 3.8 EMAIL TEMPLATES (for transactional emails)
-- ============================================================================

CREATE TABLE IF NOT EXISTS email_templates (
    id VARCHAR(50) PRIMARY KEY,            -- 'welcome', 'password_reset', 'subscription_confirm'
    name VARCHAR(100) NOT NULL,

-- Content
subject_template TEXT NOT NULL,
html_template TEXT NOT NULL,
text_template TEXT, -- Plain text fallback

-- Sender
from_name VARCHAR(100) DEFAULT 'ApxMind',
from_email VARCHAR(120) DEFAULT 'noreply@apxmind.com',
reply_to VARCHAR(120),

-- Variables
variables JSON,

    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- 3.9 EMAIL SEND LOG
-- ============================================================================

CREATE TABLE IF NOT EXISTS email_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id),
    template_id VARCHAR(50) REFERENCES email_templates(id),

-- Email details
to_email VARCHAR(120) NOT NULL, subject VARCHAR(500) NOT NULL,

-- Status
status VARCHAR(20) NOT NULL, -- 'queued', 'sent', 'delivered', 'opened', 'clicked', 'bounced', 'spam'

-- Provider
provider VARCHAR(30) DEFAULT 'sendgrid',
provider_message_id VARCHAR(255),

-- Tracking
opened_at DATETIME, clicked_at DATETIME, bounced_at DATETIME,

-- Error
error_message TEXT,

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_email_user ON email_log (user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_email_status ON email_log (status);

-- ============================================================================
-- 3.10 STUDY REMINDERS (User-configured)
-- ============================================================================
-- User's personal study reminder schedule


CREATE TABLE IF NOT EXISTS study_reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    name VARCHAR(100) NOT NULL,            -- "Morning Study", "Evening Revision"

-- Schedule
reminder_time TIME NOT NULL, -- "09:00"
days_of_week JSON NOT NULL, -- [1,2,3,4,5] = Mon-Fri
timezone VARCHAR(64) DEFAULT 'Asia/Kolkata',

-- Content
message TEXT, -- Custom message (optional)

-- Target
target_type VARCHAR(30), -- 'general', 'subject', 'weak_topics'
target_subject VARCHAR(20),

-- Status
is_active BOOLEAN DEFAULT TRUE,
    last_sent_at DATETIME,

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_reminder_user ON study_reminders (user_id, is_active);

-- ============================================================================
-- SEED DATA: Default Notification Templates
-- ============================================================================

INSERT OR IGNORE INTO
    notification_templates (
        id,
        name,
        category,
        title_template,
        body_template,
        channels,
        priority,
        is_active
    )
VALUES
    -- Achievement notifications
    (
        'badge_earned',
        'Badge Earned',
        'achievement',
        '🏆 New Badge Unlocked!',
        'Congratulations! You earned the "{{badge_name}}" badge!',
        '["in_app", "push"]',
        'high',
        TRUE
    ),
    (
        'level_up',
        'Level Up',
        'achievement',
        '🎉 Level Up!',
        'Amazing! You reached Level {{level}} ({{level_name}})!',
        '["in_app", "push"]',
        'high',
        TRUE
    ),
    (
        'streak_milestone',
        'Streak Milestone',
        'achievement',
        '🔥 {{streak}} Day Streak!',
        'Incredible dedication! Keep the momentum going!',
        '["in_app", "push"]',
        'high',
        TRUE
    ),

-- Reminder notifications
(
    'streak_at_risk',
    'Streak at Risk',
    'reminder',
    '⚠️ Your streak is at risk!',
    'Don''t lose your {{streak}} day streak! Study for just 5 minutes to keep it alive.',
    '["in_app", "push"]',
    'urgent',
    TRUE
),
(
    'daily_reminder',
    'Daily Study Reminder',
    'reminder',
    '📚 Time to Study!',
    'Your daily study session awaits. Let''s crush your NEET goals!',
    '["in_app", "push"]',
    'normal',
    TRUE
),
(
    'goal_progress',
    'Goal Progress',
    'reminder',
    '📊 Daily Progress Update',
    'You''ve studied {{minutes}} minutes today. {{remaining}} more to hit your goal!',
    '["in_app"]',
    'low',
    TRUE
),

-- Social notifications
(
    'friend_request',
    'Friend Request',
    'social',
    '👋 New Study Buddy Request',
    '{{friend_name}} wants to connect with you!',
    '["in_app", "push"]',
    'normal',
    TRUE
),
(
    'group_invite',
    'Study Group Invite',
    'social',
    '👥 Study Group Invitation',
    'You''ve been invited to join "{{group_name}}"',
    '["in_app", "push"]',
    'normal',
    TRUE
),

-- System notifications
(
    'welcome',
    'Welcome',
    'system',
    '🚀 Welcome to ApxMind!',
    'Your NEET preparation journey starts now. Let''s ace it together!',
    '["in_app", "push", "email"]',
    'high',
    TRUE
),
(
    'subscription_activated',
    'Subscription Activated',
    'system',
    '✅ Subscription Activated',
    'Your {{plan_name}} subscription is now active until {{expires_date}}.',
    '["in_app", "email"]',
    'high',
    TRUE
),
(
    'subscription_expiring',
    'Subscription Expiring',
    'system',
    '⏰ Subscription Expiring Soon',
    'Your subscription expires in {{days}} days. Renew to keep learning!',
    '["in_app", "push", "email"]',
    'high',
    TRUE
),

-- Promo notifications
(
    'special_offer',
    'Special Offer',
    'promo',
    '🎁 Special Offer for You!',
    '{{offer_text}}',
    '["in_app", "push"]',
    'normal',
    TRUE
);

-- ============================================================================
-- SEED DATA: Default Notification Preferences Categories
-- ============================================================================
-- These will be inserted for each new user via application code

-- Categories:
-- 'achievement' - Badges, levels, streaks
-- 'reminder' - Study reminders, goals
-- 'social' - Friends, groups
-- 'system' - Account, subscription
-- 'promo' - Offers, announcements

-- ============================================================================
-- END OF PHASE 3
-- ============================================================================