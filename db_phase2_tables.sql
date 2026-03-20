-- APXMIND Phase 2: New Tables

-- Question Bank
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
    source VARCHAR(50),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Quiz Templates
CREATE TABLE IF NOT EXISTS quiz_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    subject VARCHAR(20) NOT NULL,
    duration_minutes INTEGER,
    question_distribution JSON NOT NULL,
    total_marks INTEGER,
    created_by INTEGER REFERENCES users (id),
    is_public BOOLEAN DEFAULT 0,
    times_used INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Bookmark Collections
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

-- Study Groups
CREATE TABLE IF NOT EXISTS study_groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    subject VARCHAR(20),
    created_by INTEGER NOT NULL REFERENCES users (id),
    max_members INTEGER DEFAULT 10,
    is_private BOOLEAN DEFAULT 0,
    invite_code VARCHAR(20) UNIQUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS study_group_members (
    group_id INTEGER NOT NULL REFERENCES study_groups (id),
    user_id INTEGER NOT NULL REFERENCES users (id),
    role VARCHAR(20) DEFAULT 'member',
    joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_active DATETIME,
    PRIMARY KEY (group_id, user_id)
);

-- Mock Exams
CREATE TABLE IF NOT EXISTS mock_exams (
    id VARCHAR(36) PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users (id),
    exam_type VARCHAR(50) NOT NULL,
    biology_score INTEGER DEFAULT 0,
    chemistry_score INTEGER DEFAULT 0,
    physics_score INTEGER DEFAULT 0,
    total_score INTEGER DEFAULT 0,
    max_score INTEGER NOT NULL,
    duration_minutes INTEGER,
    scheduled_for DATETIME,
    started_at DATETIME,
    completed_at DATETIME,
    status VARCHAR(20) DEFAULT 'scheduled',
    rank_percentile NUMERIC(5, 2),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Audit Log
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

-- User Sessions
CREATE TABLE IF NOT EXISTS user_sessions (
    id VARCHAR(36) PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users (id),
    token_hash VARCHAR(256) NOT NULL,
    device_info JSON,
    ip_address VARCHAR(45),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME NOT NULL,
    last_activity DATETIME,
    is_revoked BOOLEAN DEFAULT 0
);

-- Syllabus Coverage
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