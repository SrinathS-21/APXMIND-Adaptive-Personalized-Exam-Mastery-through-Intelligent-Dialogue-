-- APXMIND Phase 3: Performance Indexes

-- Gamification leaderboard indexes
CREATE INDEX IF NOT EXISTS idx_user_gam_xp ON user_gamification_snapshot (total_xp DESC);

CREATE INDEX IF NOT EXISTS idx_user_gam_streak ON user_gamification_snapshot (current_streak DESC);

CREATE INDEX IF NOT EXISTS idx_user_gam_level ON user_gamification_snapshot (current_level DESC);

-- Quiz performance indexes
CREATE INDEX IF NOT EXISTS idx_quiz_user_subject ON quizzes (user_id, subject, status);

CREATE INDEX IF NOT EXISTS idx_quiz_completed_at ON quizzes (completed_at DESC);

-- Topic mastery indexes
CREATE INDEX IF NOT EXISTS idx_topic_mastery_user_subj ON topic_mastery (user_id, subject);

CREATE INDEX IF NOT EXISTS idx_topic_mastery_score ON topic_mastery (mastery_score);

-- Daily progress range queries
CREATE INDEX IF NOT EXISTS idx_daily_progress_range ON daily_progress (user_id, date DESC);

-- Learning events analytics
CREATE INDEX IF NOT EXISTS idx_le_user_type_subject ON learning_events (user_id, event_type, subject);

-- Recommendation prioritization
CREATE INDEX IF NOT EXISTS idx_lr_user_status_priority ON learning_recommendations (
    user_id,
    status,
    priority_score DESC
);

-- Question bank indexes
CREATE INDEX IF NOT EXISTS idx_qb_subject_topic ON question_bank (subject, topic);

CREATE INDEX IF NOT EXISTS idx_qb_difficulty ON question_bank (difficulty);

CREATE INDEX IF NOT EXISTS idx_qb_pyq_year ON question_bank (pyq_year);

-- Quiz templates
CREATE INDEX IF NOT EXISTS idx_quiz_template_subject ON quiz_templates (subject);

CREATE INDEX IF NOT EXISTS idx_quiz_template_public ON quiz_templates (is_public);

-- Bookmark collections
CREATE INDEX IF NOT EXISTS idx_bookmark_coll_user ON bookmark_collections (user_id);

-- Study group members
CREATE INDEX IF NOT EXISTS idx_sgm_user ON study_group_members (user_id);

-- Mock exams
CREATE INDEX IF NOT EXISTS idx_mock_exam_user ON mock_exams (user_id, status);

CREATE INDEX IF NOT EXISTS idx_mock_exam_completed ON mock_exams (completed_at);

-- Audit log
CREATE INDEX IF NOT EXISTS idx_audit_user_time ON audit_log (user_id, timestamp);

CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log (action);

-- User sessions
CREATE INDEX IF NOT EXISTS idx_session_user ON user_sessions (user_id);

CREATE INDEX IF NOT EXISTS idx_session_token ON user_sessions (token_hash);

CREATE INDEX IF NOT EXISTS idx_session_expires ON user_sessions (expires_at);

-- Syllabus coverage
CREATE INDEX IF NOT EXISTS idx_syllabus_cov_user ON syllabus_coverage (user_id);