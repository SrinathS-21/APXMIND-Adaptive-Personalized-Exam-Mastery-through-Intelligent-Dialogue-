-- ============================================================================
-- APXMIND Database Improvement Script
-- ============================================================================
-- This script contains SQL commands for critical schema improvements
-- Run these in phases to avoid disruption
-- ============================================================================

-- ============================================================================
-- PHASE 1: CRITICAL FIXES (Run First)
-- ============================================================================

-- 1.1: Add missing user fields for security and onboarding
-- ----------------------------------------------------------------------------
ALTER TABLE users ADD COLUMN email_verified BOOLEAN DEFAULT FALSE;

ALTER TABLE users ADD COLUMN email_verification_token VARCHAR(256);

ALTER TABLE users ADD COLUMN verification_sent_at DATETIME;

ALTER TABLE users ADD COLUMN phone_number VARCHAR(20);

ALTER TABLE users ADD COLUMN phone_verified BOOLEAN DEFAULT FALSE;

ALTER TABLE users
ADD COLUMN two_factor_enabled BOOLEAN DEFAULT FALSE;

ALTER TABLE users ADD COLUMN two_factor_secret VARCHAR(128);

ALTER TABLE users ADD COLUMN last_password_change DATETIME;

ALTER TABLE users
ADD COLUMN failed_login_attempts SMALLINT DEFAULT 0;

ALTER TABLE users ADD COLUMN account_locked_until DATETIME;

ALTER TABLE users
ADD COLUMN onboarding_completed BOOLEAN DEFAULT FALSE;

ALTER TABLE users ADD COLUMN onboarding_step VARCHAR(50);

-- 1.2: Add missing subject fields
-- ----------------------------------------------------------------------------
ALTER TABLE subjects ADD COLUMN total_topics INTEGER DEFAULT 0;

ALTER TABLE subjects ADD COLUMN avg_completion_time_minutes INTEGER;

ALTER TABLE subjects ADD COLUMN difficulty_distribution JSON;

ALTER TABLE subjects ADD COLUMN prerequisites JSON;

-- 1.3: Add missing lesson fields
-- ----------------------------------------------------------------------------
ALTER TABLE lessons ADD COLUMN learning_outcomes JSON;

ALTER TABLE lessons ADD COLUMN prerequisites JSON;

ALTER TABLE lessons ADD COLUMN ncert_chapter VARCHAR(100);

ALTER TABLE lessons ADD COLUMN video_url TEXT;

ALTER TABLE lessons
ADD COLUMN has_interactive_content BOOLEAN DEFAULT FALSE;

ALTER TABLE lessons ADD COLUMN avg_completion_rate NUMERIC(5, 2);

ALTER TABLE lessons ADD COLUMN avg_time_taken_minutes INTEGER;

-- 1.4: Add quiz question metadata
-- ----------------------------------------------------------------------------
ALTER TABLE quiz_questions ADD COLUMN pyq_year SMALLINT;

ALTER TABLE quiz_questions ADD COLUMN concept_tags JSON;

ALTER TABLE quiz_questions ADD COLUMN difficulty_score NUMERIC(3, 1);

-- 1.5: Add badge enhancements
-- ----------------------------------------------------------------------------
ALTER TABLE badge_definitions
ADD COLUMN rarity VARCHAR(20) DEFAULT 'common';

ALTER TABLE badge_definitions ADD COLUMN category VARCHAR(30);

ALTER TABLE badge_definitions ADD COLUMN available_from DATETIME;

ALTER TABLE badge_definitions ADD COLUMN available_until DATETIME;

ALTER TABLE badge_definitions
ADD COLUMN global_earned_count INTEGER DEFAULT 0;

-- 1.6: Add gamification leaderboard fields
-- ----------------------------------------------------------------------------
ALTER TABLE user_gamification_snapshot
ADD COLUMN rank_global INTEGER;

ALTER TABLE user_gamification_snapshot ADD COLUMN rank_state INTEGER;

ALTER TABLE user_gamification_snapshot
ADD COLUMN rank_school INTEGER;

ALTER TABLE user_gamification_snapshot
ADD COLUMN total_badges_earned INTEGER DEFAULT 0;

ALTER TABLE user_gamification_snapshot
ADD COLUMN rare_badges_earned INTEGER DEFAULT 0;

-- 1.7: Add daily progress goal tracking
-- ----------------------------------------------------------------------------
ALTER TABLE daily_progress
ADD COLUMN goal_minutes INTEGER DEFAULT 240;
-- 4 hours default
ALTER TABLE daily_progress ADD COLUMN goal_met BOOLEAN DEFAULT FALSE;

ALTER TABLE daily_progress ADD COLUMN peak_study_hour SMALLINT;

ALTER TABLE daily_progress ADD COLUMN focus_score NUMERIC(5, 2);

-- 1.8: Add learning session metadata
-- ----------------------------------------------------------------------------
ALTER TABLE learning_sessions ADD COLUMN session_type VARCHAR(30);

ALTER TABLE learning_sessions
ADD COLUMN avg_response_time_ms INTEGER;

ALTER TABLE learning_sessions ADD COLUMN user_satisfaction SMALLINT;

ALTER TABLE learning_sessions ADD COLUMN model_used VARCHAR(50);

ALTER TABLE learning_sessions ADD COLUMN tokens_used INTEGER;

-- 1.9: Add query event quality tracking
-- ----------------------------------------------------------------------------
ALTER TABLE query_events ADD COLUMN difficulty_level VARCHAR(20);

ALTER TABLE query_events
ADD COLUMN knowledge_gap_detected BOOLEAN DEFAULT FALSE;

ALTER TABLE query_events
ADD COLUMN follow_up_needed BOOLEAN DEFAULT FALSE;

ALTER TABLE query_events ADD COLUMN user_helpful_rating SMALLINT;

ALTER TABLE query_events
ADD COLUMN follow_up_query_id INTEGER REFERENCES query_events (id);

-- 1.10: Add bookmark collections support
-- ----------------------------------------------------------------------------
ALTER TABLE bookmarks ADD COLUMN collection_id INTEGER;

ALTER TABLE bookmarks ADD COLUMN is_favorite BOOLEAN DEFAULT FALSE;

-- 1.11: Add note sharing features
-- ----------------------------------------------------------------------------
ALTER TABLE study_notes ADD COLUMN is_public BOOLEAN DEFAULT FALSE;

ALTER TABLE study_notes ADD COLUMN likes_count INTEGER DEFAULT 0;

ALTER TABLE study_notes
ADD COLUMN linked_lesson_id INTEGER REFERENCES lessons (id);

-- 1.12: Add event source tracking
-- ----------------------------------------------------------------------------
ALTER TABLE learning_events ADD COLUMN source VARCHAR(20);

ALTER TABLE learning_events ADD COLUMN session_id VARCHAR(64);

-- ============================================================================
-- PHASE 2: NEW TABLES (Critical for Personalization)
-- ============================================================================

-- 2.1: Question Bank (Master Repository)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS question_bank (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject VARCHAR(20) NOT NULL,
    topic VARCHAR(120),
    question_text TEXT NOT NULL,
    options JSON NOT NULL,
    correct_answer TEXT NOT NULL,
    explanation TEXT,
    difficulty VARCHAR(20) NOT NULL,
    pyq_year SMALLINT,
    concept_tags JSON,
    times_used INTEGER DEFAULT 0,
    avg_accuracy NUMERIC(5, 2),
    source VARCHAR(50), -- 'neet_2023', 'ncert', 'custom'
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_qb_subject_topic ON question_bank (subject, topic);

CREATE INDEX idx_qb_difficulty ON question_bank (difficulty);

CREATE INDEX idx_qb_pyq_year ON question_bank (pyq_year);

-- 2.2: Quiz Templates
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS quiz_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    subject VARCHAR(20) NOT NULL,
    duration_minutes INTEGER,
    question_distribution JSON NOT NULL, -- {"easy": 5, "medium": 10, "hard": 5}
    total_marks INTEGER,
    created_by INTEGER REFERENCES users (id),
    is_public BOOLEAN DEFAULT FALSE,
    times_used INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_quiz_template_subject ON quiz_templates (subject);

CREATE INDEX idx_quiz_template_public ON quiz_templates (is_public);

-- 2.3: Bookmark Collections
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS bookmark_collections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users (id),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    color VARCHAR(20),
    icon VARCHAR(50),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_bookmark_coll_user ON bookmark_collections (user_id);

-- 2.4: Study Groups (for collaborative learning)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS study_groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    subject VARCHAR(20),
    created_by INTEGER NOT NULL REFERENCES users (id),
    max_members INTEGER DEFAULT 10,
    is_private BOOLEAN DEFAULT FALSE,
    invite_code VARCHAR(20) UNIQUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS study_group_members (
    group_id INTEGER NOT NULL REFERENCES study_groups (id),
    user_id INTEGER NOT NULL REFERENCES users (id),
    role VARCHAR(20) DEFAULT 'member', -- admin/moderator/member
    joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_active DATETIME,
    PRIMARY KEY (group_id, user_id)
);

CREATE INDEX idx_sgm_user ON study_group_members (user_id);

-- 2.5: Mock Exams (Full NEET simulation)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS mock_exams (
    id VARCHAR(36) PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users (id),
    exam_type VARCHAR(50) NOT NULL, -- 'full_neet', 'subject_wise', 'chapter_test'
    biology_score INTEGER DEFAULT 0,
    chemistry_score INTEGER DEFAULT 0,
    physics_score INTEGER DEFAULT 0,
    total_score INTEGER DEFAULT 0,
    max_score INTEGER NOT NULL,
    duration_minutes INTEGER,
    scheduled_for DATETIME,
    started_at DATETIME,
    completed_at DATETIME,
    status VARCHAR(20) DEFAULT 'scheduled', -- scheduled/in_progress/completed/abandoned
    rank_percentile NUMERIC(5, 2),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_mock_exam_user ON mock_exams (user_id, status);

CREATE INDEX idx_mock_exam_completed ON mock_exams (completed_at);

-- 2.6: Audit Log (Security)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users (id),
    action VARCHAR(50) NOT NULL,
    resource_type VARCHAR(30),
    resource_id VARCHAR(64),
    ip_address VARCHAR(45),
    user_agent TEXT,
    details JSON,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_user_time ON audit_log (user_id, timestamp);

CREATE INDEX idx_audit_action ON audit_log (action);

-- 2.7: User Sessions (Enhanced auth)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_sessions (
    id VARCHAR(36) PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users (id),
    token_hash VARCHAR(256) NOT NULL,
    device_info JSON,
    ip_address VARCHAR(45),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME NOT NULL,
    last_activity DATETIME,
    is_revoked BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_session_user ON user_sessions (user_id);

CREATE INDEX idx_session_token ON user_sessions (token_hash);

CREATE INDEX idx_session_expires ON user_sessions (expires_at);

-- 2.8: Syllabus Coverage Tracking
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS syllabus_coverage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users (id),
    subject VARCHAR(20) NOT NULL,
    total_topics INTEGER NOT NULL,
    topics_started INTEGER DEFAULT 0,
    topics_completed INTEGER DEFAULT 0,
    coverage_percent NUMERIC(5, 2) DEFAULT 0,
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, subject)
);

CREATE INDEX idx_syllabus_cov_user ON syllabus_coverage (user_id);

-- ============================================================================
-- PHASE 3: CRITICAL INDEXES (Performance)
-- ============================================================================

-- 3.1: Gamification leaderboard indexes
-- ----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_user_gam_xp ON user_gamification_snapshot (total_xp DESC);

CREATE INDEX IF NOT EXISTS idx_user_gam_streak ON user_gamification_snapshot (current_streak DESC);

CREATE INDEX IF NOT EXISTS idx_user_gam_level ON user_gamification_snapshot (current_level DESC);

-- 3.2: Quiz performance indexes
-- ----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_quiz_user_subject ON quizzes (user_id, subject, status);

CREATE INDEX IF NOT EXISTS idx_quiz_completed_at ON quizzes (completed_at DESC);

-- 3.3: Topic mastery indexes
-- ----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_topic_mastery_user_subj ON topic_mastery (user_id, subject);

CREATE INDEX IF NOT EXISTS idx_topic_mastery_score ON topic_mastery (mastery_score);

-- 3.4: Daily progress range queries
-- ----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_daily_progress_range ON daily_progress (user_id, date DESC);

-- 3.5: Learning events analytics
-- ----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_le_user_type_subject ON learning_events (user_id, event_type, subject);

-- 3.6: Recommendation prioritization
-- ----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_lr_user_status_priority ON learning_recommendations (
    user_id,
    status,
    priority_score DESC
);

-- ============================================================================
-- PHASE 4: DATA SEEDING (After schema is ready)
-- ============================================================================

-- 4.1: Seed Topic Structure (Biology Example)
-- ----------------------------------------------------------------------------
-- Run this after subjects table is populated
INSERT INTO
    topics (
        subject_id,
        name,
        syllabus_weight
    )
VALUES (
        1,
        'Diversity in Living World',
        7.00
    ),
    (
        1,
        'Cell Structure and Function',
        9.00
    ),
    (1, 'Plant Physiology', 8.00),
    (1, 'Human Physiology', 20.00),
    (1, 'Reproduction', 9.00),
    (
        1,
        'Genetics and Evolution',
        18.00
    ),
    (
        1,
        'Biology and Human Welfare',
        9.00
    ),
    (1, 'Biotechnology', 5.00),
    (
        1,
        'Ecology and Environment',
        6.00
    );

-- 4.2: Expand Level Definitions (11-50)
-- ----------------------------------------------------------------------------
INSERT INTO
    level_definitions (level, xp_required, label)
VALUES (11, 6000, 'Advanced Scholar'),
    (12, 7500, 'Expert'),
    (13, 9500, 'Master'),
    (14, 12000, 'Grand Master'),
    (15, 15000, 'Champion'),
    (16, 18500, 'Elite'),
    (17, 22500, 'Legend'),
    (18, 27000, 'Prodigy'),
    (19, 32000, 'Virtuoso'),
    (20, 38000, 'Genius'),
    (21, 45000, 'Sage'),
    (22, 53000, 'Enlightened'),
    (23, 62000, 'Transcendent'),
    (24, 72000, 'Immortal'),
    (25, 83000, 'Deity');
-- Continue pattern up to level 50...

-- 4.3: Add Enhanced Badge Definitions
-- ----------------------------------------------------------------------------
-- Update existing badges with rarity
UPDATE badge_definitions
SET
    rarity = 'common',
    category = 'streak'
WHERE
    id LIKE 'streak_%';

UPDATE badge_definitions
SET
    rarity = 'rare',
    category = 'milestone'
WHERE
    id LIKE 'quiz_%';

UPDATE badge_definitions
SET
    rarity = 'epic',
    category = 'mastery'
WHERE
    id LIKE 'master_%';

-- Add new badges
INSERT INTO
    badge_definitions (
        id,
        name,
        description,
        icon,
        criteria,
        rarity,
        category
    )
VALUES (
        'perfect_quiz_10',
        'Perfect 10',
        'Score 100% in 10 quizzes',
        '🎯',
        '{"perfect_quizzes": 10}',
        'epic',
        'mastery'
    ),
    (
        'study_streak_30',
        '30-Day Warrior',
        'Study for 30 days straight',
        '⚡',
        '{"streak_days": 30}',
        'legendary',
        'streak'
    ),
    (
        'neet_ready',
        'NEET Ready',
        'Complete 100% syllabus coverage',
        '🎓',
        '{"syllabus_coverage": 100}',
        'legendary',
        'milestone'
    ),
    (
        'speed_demon',
        'Speed Demon',
        'Solve 100 questions in 1 hour',
        '🏃',
        '{"questions_per_hour": 100}',
        'rare',
        'speed'
    ),
    (
        'night_owl',
        'Night Owl',
        'Study after 11 PM for 7 days',
        '🦉',
        '{"late_night_days": 7}',
        'common',
        'habit'
    );

-- ============================================================================
-- PHASE 5: TRIGGERS (Automation)
-- ============================================================================

-- 5.1: Auto-update badge earned count
-- ----------------------------------------------------------------------------
CREATE TRIGGER IF NOT EXISTS update_badge_count
AFTER INSERT ON user_badges
BEGIN
    UPDATE badge_definitions
    SET global_earned_count = global_earned_count + 1
    WHERE id = NEW.badge_id;

    UPDATE user_gamification_snapshot
    SET total_badges_earned = total_badges_earned + 1
    WHERE user_id = NEW.user_id;
END;

-- 5.2: Auto-update syllabus coverage
-- ----------------------------------------------------------------------------
CREATE TRIGGER IF NOT EXISTS update_syllabus_coverage
AFTER UPDATE ON topic_mastery
WHEN NEW.mastery_score >= 70
BEGIN
    UPDATE syllabus_coverage
    SET topics_completed = (
        SELECT COUNT(*) FROM topic_mastery
        WHERE user_id = NEW.user_id AND subject = NEW.subject AND mastery_score >= 70
    ),
    coverage_percent = ROUND(
        (topics_completed * 100.0) / total_topics, 2
    ),
    last_updated = CURRENT_TIMESTAMP
    WHERE user_id = NEW.user_id AND subject = NEW.subject;
END;

-- 5.3: Auto-calculate daily goal met
-- ----------------------------------------------------------------------------
CREATE TRIGGER IF NOT EXISTS check_daily_goal
AFTER UPDATE ON daily_progress
BEGIN
    UPDATE daily_progress
    SET goal_met = (study_minutes >= goal_minutes)
    WHERE id = NEW.id;
END;

-- ============================================================================
-- PHASE 6: VIEWS (Query Optimization)
-- ============================================================================

-- 6.1: User Dashboard Summary View
-- ----------------------------------------------------------------------------
CREATE VIEW IF NOT EXISTS v_user_dashboard AS
SELECT
    u.id as user_id,
    u.name,
    u.email,
    u.target_score,
    g.total_xp,
    g.current_level,
    g.current_streak,
    g.longest_streak,
    g.total_badges_earned,
    (
        SELECT COUNT(*)
        FROM quizzes
        WHERE
            user_id = u.id
            AND status = 'completed'
    ) as total_quizzes,
    (
        SELECT COUNT(*)
        FROM learning_events
        WHERE
            user_id = u.id
            AND event_type = 'lesson_completed'
    ) as lessons_completed,
    (
        SELECT AVG(study_minutes)
        FROM daily_progress
        WHERE
            user_id = u.id
            AND date >= date('now', '-7 days')
    ) as avg_daily_minutes_7d
FROM
    users u
    LEFT JOIN user_gamification_snapshot g ON u.id = g.user_id;

-- 6.2: Weak Topics View (for recommendations)
-- ----------------------------------------------------------------------------
CREATE VIEW IF NOT EXISTS v_weak_topics AS
SELECT
    tm.user_id,
    tm.subject,
    tm.topic,
    tm.mastery_score,
    tm.last_assessed_at,
    CASE
        WHEN tm.mastery_score < 40 THEN 'critical'
        WHEN tm.mastery_score < 60 THEN 'needs_work'
        ELSE 'improvement'
    END as urgency
FROM topic_mastery tm
WHERE
    tm.mastery_score < 70
ORDER BY tm.mastery_score ASC;

-- 6.3: Leaderboard View
-- ----------------------------------------------------------------------------
CREATE VIEW IF NOT EXISTS v_leaderboard AS
SELECT u.id, u.name, u.avatar_url, g.total_xp, g.current_level, g.current_streak, RANK() OVER (
        ORDER BY g.total_xp DESC
    ) as rank
FROM
    users u
    JOIN user_gamification_snapshot g ON u.id = g.user_id
WHERE
    u.deleted_at IS NULL
ORDER BY g.total_xp DESC;

-- ============================================================================
-- PHASE 7: DATA MIGRATION SCRIPTS
-- ============================================================================

-- 7.1: Migrate strong/weak subjects to user_subject_preferences
-- ----------------------------------------------------------------------------
-- Note: This requires application logic to parse JSON and insert
-- Python migration script needed

-- 7.2: Link lessons to topics
-- ----------------------------------------------------------------------------
-- Note: This requires matching lesson.topics JSON to actual topic names
-- Python migration script needed

-- 7.3: Calculate initial topic mastery
-- ----------------------------------------------------------------------------
-- Note: Requires analyzing quiz performance per topic
-- Use background job to calculate

-- ============================================================================
-- PHASE 8: CLEANUP (After migration)
-- ============================================================================

-- Remove legacy columns after migration is complete and verified
-- DO NOT RUN THESE UNTIL DATA IS SAFELY MIGRATED!

-- ALTER TABLE users DROP COLUMN strong_subjects;
-- ALTER TABLE users DROP COLUMN weak_subjects;
-- ALTER TABLE users DROP COLUMN daily_study_target;
-- ALTER TABLE users DROP COLUMN last_active;

-- ALTER TABLE lessons DROP COLUMN order;
-- ALTER TABLE lessons DROP COLUMN estimated_time;
-- ALTER TABLE lessons DROP COLUMN topics;

-- ============================================================================
-- END OF SCHEMA IMPROVEMENTS
-- ============================================================================

-- Run this to verify schema after applying changes:
-- SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;
-- SELECT name FROM sqlite_master WHERE type='index' ORDER BY name;