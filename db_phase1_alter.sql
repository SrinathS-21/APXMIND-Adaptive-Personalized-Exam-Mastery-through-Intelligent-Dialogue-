-- APXMIND Phase 1: Critical ALTER TABLE Statements
-- Safe to apply - only adds nullable columns

-- User table enhancements
ALTER TABLE users ADD COLUMN email_verified BOOLEAN DEFAULT 0;

ALTER TABLE users ADD COLUMN email_verification_token VARCHAR(256);

ALTER TABLE users ADD COLUMN phone_number VARCHAR(20);

ALTER TABLE users ADD COLUMN phone_verified BOOLEAN DEFAULT 0;

ALTER TABLE users ADD COLUMN onboarding_completed BOOLEAN DEFAULT 0;

ALTER TABLE users ADD COLUMN onboarding_step VARCHAR(50);

-- Subject enhancements
ALTER TABLE subjects ADD COLUMN total_topics INTEGER DEFAULT 0;

ALTER TABLE subjects ADD COLUMN avg_completion_time_minutes INTEGER;

-- Lesson enhancements
ALTER TABLE lessons ADD COLUMN learning_outcomes JSON;

ALTER TABLE lessons ADD COLUMN ncert_chapter VARCHAR(100);

ALTER TABLE lessons ADD COLUMN video_url TEXT;

-- Badge enhancements
ALTER TABLE badge_definitions
ADD COLUMN rarity VARCHAR(20) DEFAULT 'common';

ALTER TABLE badge_definitions ADD COLUMN category VARCHAR(30);

-- Gamification enhancements
ALTER TABLE user_gamification_snapshot
ADD COLUMN rank_global INTEGER;

ALTER TABLE user_gamification_snapshot
ADD COLUMN total_badges_earned INTEGER DEFAULT 0;

-- Daily progress enhancements
ALTER TABLE daily_progress
ADD COLUMN goal_minutes INTEGER DEFAULT 240;

ALTER TABLE daily_progress ADD COLUMN goal_met BOOLEAN DEFAULT 0;

-- Quiz question enhancements
ALTER TABLE quiz_questions ADD COLUMN pyq_year SMALLINT;

ALTER TABLE quiz_questions ADD COLUMN concept_tags JSON;

-- Learning session enhancements
ALTER TABLE learning_sessions ADD COLUMN session_type VARCHAR(30);

ALTER TABLE learning_sessions ADD COLUMN user_satisfaction SMALLINT;

-- Query event enhancements
ALTER TABLE query_events ADD COLUMN user_helpful_rating SMALLINT;

ALTER TABLE query_events
ADD COLUMN knowledge_gap_detected BOOLEAN DEFAULT 0;

-- Bookmark enhancements
ALTER TABLE bookmarks ADD COLUMN is_favorite BOOLEAN DEFAULT 0;

-- Note enhancements
ALTER TABLE study_notes ADD COLUMN is_public BOOLEAN DEFAULT 0;

ALTER TABLE study_notes ADD COLUMN likes_count INTEGER DEFAULT 0;

-- Event tracking enhancements
ALTER TABLE learning_events ADD COLUMN source VARCHAR(20);

ALTER TABLE learning_events ADD COLUMN session_id VARCHAR(64);