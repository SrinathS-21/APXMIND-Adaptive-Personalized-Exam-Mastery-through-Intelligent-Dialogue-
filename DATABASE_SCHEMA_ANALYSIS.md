# APXMIND Database Schema Analysis
**Generated:** March 20, 2026
**Database:** SQLite (sqlite+aiosqlite)
**Location:** `APXMIND.db` (348 KB)

---

## 📊 Current Schema Overview

### Database Statistics
- **Total Tables:** 29
- **Active Users:** 2
- **Total Lessons:** 42
- **Learning Events:** 82
- **Badge Definitions:** 20
- **Level Definitions:** 10

---

## 🏗️ Schema Structure

### ✅ 1. IDENTITY & PROFILE (Well Implemented)

#### **users** (2 rows)
**Current Implementation:**
```sql
- id (PK, autoincrement)
- username, name, email, password_hash
- avatar_url, dob, current_class, attempt_number
- target_year, target_score
- daily_study_target_hours (Numeric)
- preferred_language, learning_level, timezone
- created_at, updated_at, last_active_at, deleted_at
- Legacy: strong_subjects (JSON), weak_subjects (JSON)
```

**Strengths:**
- ✅ Comprehensive user profile fields
- ✅ Supports soft deletes (deleted_at)
- ✅ Timezone-aware for Indian students
- ✅ Both legacy and blueprint fields for backward compatibility

**Recommendations:**
1. **Add Email Verification:**
   - Add `email_verified` (Boolean, default False)
   - Add `email_verification_token` (String)
   - Add `verification_sent_at` (DateTime)

2. **Add Phone Number Support:**
   - Add `phone_number` (String, nullable)
   - Add `phone_verified` (Boolean)
   - Important for Indian users who prefer WhatsApp notifications

3. **Add Account Security:**
   - Add `two_factor_enabled` (Boolean, default False)
   - Add `two_factor_secret` (String, nullable)
   - Add `last_password_change` (DateTime)
   - Add `failed_login_attempts` (SmallInteger, default 0)
   - Add `account_locked_until` (DateTime, nullable)

4. **Add Onboarding State:**
   - Add `onboarding_completed` (Boolean, default False)
   - Add `onboarding_step` (String, nullable) - track where user is in setup

5. **Deprecate Legacy Fields:**
   - Start migrating `strong_subjects`/`weak_subjects` → `user_subject_preferences`
   - Remove `daily_study_target` (duplicate of `daily_study_target_hours`)

---

#### **user_subject_preferences** (0 rows ⚠️)
**Status:** Table exists but UNUSED

**Action Required:**
- Implement API endpoints to populate this table
- Migrate legacy `strong_subjects`/`weak_subjects` JSON data
- Use this for personalized recommendations

---

### ✅ 2. CONTENT CATALOG (Good Structure)

#### **subjects** (3 rows: Biology, Chemistry, Physics)
**Strengths:**
- ✅ Clean subject structure
- ✅ Display metadata (icon, color)

**Recommendations:**
1. **Add Subject Statistics:**
   - Add `total_topics` (Integer)
   - Add `avg_completion_time_minutes` (Integer)
   - Add `difficulty_distribution` (JSON) - % easy/medium/hard

2. **Add Subject Prerequisites:**
   - Add `prerequisites` (JSON array of subject codes)

---

#### **topics** (0 rows ⚠️)
**Status:** Table exists but EMPTY

**Critical Action Required:**
1. **Populate NEET Syllabus Topics:**
   ```sql
   Biology: Diversity, Cell Biology, Plant Physiology, Human Physiology,
            Reproduction, Genetics, Evolution, Ecology
   Chemistry: Physical Chemistry, Organic Chemistry, Inorganic Chemistry
   Physics: Mechanics, Thermodynamics, Optics, Electromagnetism, Modern Physics
   ```

2. **Add NEET-Specific Weightage:**
   - Use `syllabus_weight` field to store % of questions in NEET
   - Example: "Human Physiology" = 20%, "Genetics" = 15%

3. **Link Existing Lessons to Topics:**
   - 42 lessons currently have `topic_id = NULL`
   - Need migration to associate lessons with proper topics

---

#### **lessons** (42 rows)
**Strengths:**
- ✅ Good lesson structure
- ✅ Difficulty levels defined
- ✅ Time estimates present

**Recommendations:**
1. **Add Learning Outcomes:**
   - Add `learning_outcomes` (JSON array) - what student will learn
   - Add `prerequisites` (JSON array of lesson IDs)

2. **Add Content Metadata:**
   - Add `ncert_chapter` (String) - link to NCERT chapter
   - Add `video_url` (Text) - YouTube/embedded video
   - Add `has_interactive_content` (Boolean)

3. **Add Progress Tracking:**
   - Add `avg_completion_rate` (Numeric) - % of users who complete
   - Add `avg_time_taken_minutes` (Integer) - actual vs estimated

4. **Fix Current Issues:**
   - Populate `topic_id` for all lessons
   - Populate `sequence_no` for proper ordering
   - Remove duplicate `order`/`estimated_time` fields

---

#### **content_resources** (0 rows ⚠️)
**Status:** Table exists but EMPTY

**Critical Action Required:**
1. **Add NCERT PDFs:**
   - Type: "ncert", "chapter", "pyq", "video", "note"
   - Populate with NCERT Biology/Chemistry/Physics PDFs

2. **Add Previous Year Questions:**
   - Link PYQ sets to relevant lessons/subjects

---

### ✅ 3. REAL-TIME ACTIVITY (Excellent Implementation)

#### **learning_events** (82 rows)
**Strengths:**
- ✅ Append-only event log (excellent for analytics)
- ✅ Idempotency support
- ✅ Proper indexing on user/time/type
- ✅ Flexible JSON payload

**Recommendations:**
1. **Add Event Source Tracking:**
   - Add `source` (String) - "web", "mobile", "api"
   - Add `session_id` (String) - track continuous sessions

2. **Add Retention Policy:**
   - Consider archiving events older than 1 year
   - Implement partitioning for large datasets

---

### ✅ 4. GAMIFICATION & PROGRESS (Well Designed)

#### **level_definitions** (10 rows)
**Strengths:**
- ✅ XP-based leveling system in place

**Recommendations:**
1. **Expand Level System:**
   - Current: 10 levels (500 XP each)
   - Suggested: Add levels 11-50 with exponential XP curve
   - Add level rewards/unlocks

2. **Add Level Metadata:**
   - Add `icon` (String) - badge icon for level
   - Add `title_prefix` (String) - "Novice", "Scholar", "Expert", etc.
   - Add `unlocks` (JSON) - features unlocked at level

---

#### **daily_progress** (10 rows)
**Strengths:**
- ✅ Per-day aggregation working
- ✅ Multi-metric tracking (minutes, lessons, quizzes, XP)

**Recommendations:**
1. **Add Goal Comparison:**
   - Add `goal_minutes` (Integer) - daily target
   - Add `goal_met` (Boolean) - did user meet goal?

2. **Add Productivity Metrics:**
   - Add `peak_study_hour` (Integer) - best hour of day
   - Add `focus_score` (Numeric) - calculated focus rating

---

#### **user_gamification_snapshot** (17 rows)
**Strengths:**
- ✅ Ultra-fast dashboard reads
- ✅ Streak tracking implemented

**Recommendations:**
1. **Add Leaderboard Support:**
   - Add `rank_global` (Integer)
   - Add `rank_state` (Integer) - for regional competition
   - Add `rank_school` (Integer)

2. **Add Achievement Summary:**
   - Add `total_badges_earned` (Integer)
   - Add `rare_badges_earned` (Integer)

---

#### **badge_definitions** (20 rows) + **user_badges** (6 earned)
**Strengths:**
- ✅ 20 badges defined
- ✅ Flexible criteria system (JSON)
- ✅ Users earning badges (6 so far)

**Recommendations:**
1. **Add Badge Rarity:**
   - Add `rarity` (String) - "common", "rare", "epic", "legendary"
   - Add `global_earned_count` (Integer) - how many users earned it

2. **Add Badge Categories:**
   - Add `category` (String) - "streak", "mastery", "milestone", "social"

3. **Add Time-Limited Badges:**
   - Add `available_from` (DateTime)
   - Add `available_until` (DateTime)
   - Example: "NEET 2026 Marathon" badge

---

### ⚠️ 5. QUIZ SYSTEM (Partially Implemented)

#### **quizzes** (1 row) + **quiz_questions** (3 rows)
**Status:** New system starting, but mostly empty

**Critical Actions:**
1. **Build Question Bank:**
   - Import NEET previous year questions
   - Categorize by subject/topic/difficulty
   - Add detailed explanations

2. **Add Question Metadata:**
   - In `quiz_questions`, add:
     - `pyq_year` (SmallInteger) - if from past NEET
     - `concept_tags` (JSON array) - tagged concepts
     - `difficulty_score` (Numeric) - 1-10 scale

3. **Add Quiz Templates:**
   - Create new table: `quiz_templates`
     - `name`, `subject`, `question_distribution` (JSON)
     - Allow teachers to create quiz templates

4. **Add Adaptive Quizzing:**
   - Track question difficulty vs user performance
   - Adjust next questions based on answers

---

#### **quiz_attempt_answers** (0 rows) + **quiz_attempt_summaries** (0 rows)
**Status:** Infrastructure ready, needs usage

**Actions:**
- Ensure quiz flow is complete and tested
- Add analytics on question-level performance

---

### ✅ 6. LEARNING SESSIONS (Chat/Tutor)

#### **learning_sessions** (1 row) + **chat_messages** (2 rows)
**Strengths:**
- ✅ UUID-based sessions
- ✅ Session duration tracking

**Recommendations:**
1. **Add Session Metadata:**
   - Add `session_type` (String) - "doubt_clearing", "concept_learning", "revision"
   - Add `avg_response_time_ms` (Integer)
   - Add `user_satisfaction` (Integer) - 1-5 rating

2. **Add AI Model Tracking:**
   - Add `model_used` (String) - track which LLM was used
   - Add `tokens_used` (Integer) - cost tracking

---

#### **query_events** (9 rows)
**Strengths:**
- ✅ Query analytics in place
- ✅ Confidence scoring
- ✅ Latency tracking

**Recommendations:**
1. **Add Query Classification:**
   - Add `difficulty_level` (String) - complexity of query
   - Add `knowledge_gap_detected` (Boolean)
   - Add `follow_up_needed` (Boolean)

2. **Add Quality Metrics:**
   - Add `user_helpful_rating` (Integer) - thumbs up/down
   - Add `follow_up_query_id` (Integer FK) - link related queries

---

### ⚠️ 7. LIBRARY (Underutilized)

#### **bookmarks** (1 row) + **study_notes** (1 row)
**Status:** Feature implemented but barely used

**Actions:**
1. **Promote Feature:**
   - Add UI hints to bookmark important lessons
   - Show bookmarks in sidebar for quick access

2. **Add Smart Collections:**
   - Create new table: `bookmark_collections`
     - Users can organize bookmarks into folders
     - "Weak Topics", "Before Exam", "Quick Revision"

3. **Add Note Features:**
   - Add `is_public` (Boolean) - allow sharing notes
   - Add `likes_count` (Integer)
   - Add `linked_lesson_id` (Integer FK) - attach notes to lessons

---

### ⚠️ 8. PERSONALIZATION (Critical Gap)

#### **topic_mastery** (0 rows ⚠️)
**Status:** Empty - THIS IS A CRITICAL MISSING PIECE

**Priority Actions:**
1. **Implement Mastery Calculation:**
   - After each quiz, calculate topic mastery:
     - Accuracy on topic questions
     - Consistency over time
     - Speed of answering
   - Update `mastery_score` (0-100)

2. **Add Weak Topic Detection:**
   - Topics with mastery < 40 = weak
   - Flag for targeted practice

3. **Add Syllabus Coverage Dashboard:**
   - Show % mastery across all topics
   - Visual heatmap of strong/weak areas

---

#### **learning_recommendations** (0 rows ⚠️)
**Status:** Empty - AI Recommendations Not Working

**Critical Actions:**
1. **Build Recommendation Engine:**
   ```python
   - Analyze topic_mastery → suggest weak topics
   - Analyze daily_progress → suggest study time adjustments
   - Analyze quiz performance → suggest practice quizzes
   - Analyze syllabus_weight → prioritize high-weight topics
   ```

2. **Add Recommendation Types:**
   - "Practice [Weak Topic]" - target weak areas
   - "Revise [Strong Topic]" - maintain mastery
   - "Take Mock Test" - readiness check
   - "Focus on [Subject]" - balance study time

3. **Add Smart Scheduling:**
   - Spaced repetition for topics
   - Recommend optimal study times based on habits

---

#### **exam_readiness_snapshots** (0 rows ⚠️)
**Status:** Empty - Exam Prep Insights Missing

**Priority Actions:**
1. **Calculate Readiness Score:**
   ```python
   readiness_score = (
       syllabus_coverage * 0.3 +
       avg_quiz_accuracy * 0.3 +
       consistency_score * 0.2 +
       speed_score * 0.2
   )
   ```

2. **Add Projected Score:**
   - Based on current performance, project NEET score
   - Show "On track for 650+" or "Need improvement"

3. **Add Risk Analysis:**
   - High risk: < 40% syllabus coverage with exam < 3 months
   - Medium risk: inconsistent study patterns
   - Low risk: on track, steady progress

4. **Daily Snapshot Generation:**
   - Run scheduled job to create daily snapshots
   - Track progress over time

---

#### **habit_signals** (0 rows ⚠️)
**Status:** Empty - Study Habit Tracking Not Active

**Actions:**
1. **Track Study Patterns:**
   - Best study time (morning/afternoon/evening)
   - Session frequency
   - Focus vs distraction patterns

2. **Add Habit Coaching:**
   - "You study best in the morning - continue!"
   - "You haven't studied for 3 days - let's get back on track"

---

### 📋 9. LEGACY TABLES (Migration Needed)

#### **progress** (6 rows) - Legacy lesson completion
**Issue:** Duplicates `learning_events` functionality

**Action:**
- Migrate to event-based system
- Deprecate table after migration

#### **quiz_attempts** (0 rows) - Legacy quiz tracking
**Action:**
- Use new `quizzes` system going forward
- Can safely ignore this table

---

## 🎯 Priority Action Items

### 🔴 **CRITICAL (Do First)**
1. **Populate `topics` table with NEET syllabus** (currently 0 rows)
   - Add all Biology/Chemistry/Physics topics with syllabus weights
2. **Link lessons to topics** (42 lessons have `topic_id = NULL`)
3. **Implement `topic_mastery` calculation** (currently 0 rows)
   - THIS IS THE CORE OF PERSONALIZATION
4. **Build recommendation engine** (populate `learning_recommendations`)
5. **Create exam readiness calculator** (populate `exam_readiness_snapshots`)

### 🟠 **HIGH PRIORITY (Do Next)**
1. Add email verification system
2. Add phone number support for Indian users
3. Populate `content_resources` with NCERT PDFs
4. Build comprehensive question bank (import PYQs)
5. Implement adaptive quiz difficulty
6. Add habit tracking and coaching

### 🟡 **MEDIUM PRIORITY**
1. Add two-factor authentication
2. Add leaderboards (global/state/school ranks)
3. Add badge rarity system
4. Expand level system to 50 levels
5. Add note sharing features
6. Add bookmark collections

### 🟢 **LOW PRIORITY (Nice to Have)**
1. Archive old learning events
2. Add session quality metrics
3. Add AI model cost tracking
4. Add user satisfaction ratings

---

## 📈 Recommended New Tables

### 1. **question_bank** (Master Question Repository)
```sql
CREATE TABLE question_bank (
    id INTEGER PRIMARY KEY,
    subject VARCHAR(20) NOT NULL,
    topic VARCHAR(120),
    question_text TEXT NOT NULL,
    options JSON NOT NULL,
    correct_answer TEXT NOT NULL,
    explanation TEXT,
    difficulty VARCHAR(20),
    pyq_year SMALLINT,
    concept_tags JSON,
    times_used INTEGER DEFAULT 0,
    avg_accuracy NUMERIC(5,2),
    created_at DATETIME
);
```

### 2. **quiz_templates**
```sql
CREATE TABLE quiz_templates (
    id INTEGER PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    subject VARCHAR(20) NOT NULL,
    duration_minutes INTEGER,
    question_distribution JSON, -- {"easy": 5, "medium": 10, "hard": 5}
    created_by INTEGER REFERENCES users(id),
    is_public BOOLEAN DEFAULT FALSE
);
```

### 3. **bookmark_collections**
```sql
CREATE TABLE bookmark_collections (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    name VARCHAR(100) NOT NULL,
    color VARCHAR(20),
    created_at DATETIME
);

ALTER TABLE bookmarks ADD COLUMN collection_id INTEGER REFERENCES bookmark_collections(id);
```

### 4. **study_groups** (For Collaborative Learning)
```sql
CREATE TABLE study_groups (
    id INTEGER PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    subject VARCHAR(20),
    created_by INTEGER REFERENCES users(id),
    max_members INTEGER DEFAULT 10,
    created_at DATETIME
);

CREATE TABLE study_group_members (
    group_id INTEGER REFERENCES study_groups(id),
    user_id INTEGER REFERENCES users(id),
    role VARCHAR(20) DEFAULT 'member', -- admin/moderator/member
    joined_at DATETIME,
    PRIMARY KEY (group_id, user_id)
);
```

### 5. **mock_exams**
```sql
CREATE TABLE mock_exams (
    id VARCHAR(36) PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    exam_type VARCHAR(50), -- "full_neet", "subject_wise", "chapter_test"
    scheduled_for DATETIME,
    status VARCHAR(20), -- scheduled/in_progress/completed
    total_marks INTEGER,
    scored_marks NUMERIC(5,2),
    created_at DATETIME
);
```

---

## 🔒 Security Recommendations

1. **Add Audit Logging:**
   ```sql
   CREATE TABLE audit_log (
       id INTEGER PRIMARY KEY,
       user_id INTEGER REFERENCES users(id),
       action VARCHAR(50) NOT NULL, -- login/logout/data_access/data_modify
       ip_address VARCHAR(45),
       user_agent TEXT,
       details JSON,
       timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
   );
   ```

2. **Add Session Management:**
   ```sql
   CREATE TABLE user_sessions (
       id VARCHAR(36) PRIMARY KEY,
       user_id INTEGER REFERENCES users(id),
       token_hash VARCHAR(256) NOT NULL,
       device_info JSON,
       ip_address VARCHAR(45),
       created_at DATETIME,
       expires_at DATETIME,
       last_activity DATETIME
   );
   ```

---

## 📊 Index Optimization Recommendations

### Add Missing Indexes:
```sql
-- For faster leaderboard queries
CREATE INDEX idx_user_gam_xp ON user_gamification_snapshot(total_xp DESC);
CREATE INDEX idx_user_gam_streak ON user_gamification_snapshot(current_streak DESC);

-- For faster quiz analytics
CREATE INDEX idx_quiz_user_subject ON quizzes(user_id, subject, status);
CREATE INDEX idx_quiz_completed_at ON quizzes(completed_at);

-- For faster topic mastery lookups
CREATE INDEX idx_topic_mastery_score ON topic_mastery(user_id, subject, mastery_score);

-- For faster daily reports
CREATE INDEX idx_daily_progress_range ON daily_progress(user_id, date DESC);
```

---

## 📝 Data Migration Scripts Needed

1. **Migrate strong/weak subjects to user_subject_preferences:**
   ```python
   # Read users.strong_subjects and weak_subjects JSON
   # Insert into user_subject_preferences with proper strength values
   ```

2. **Link lessons to topics:**
   ```python
   # Analyze lesson.topics JSON field
   # Match with topic names
   # Update lesson.topic_id
   ```

3. **Seed level definitions (11-50):**
   ```python
   # Create exponential XP curve for levels 11-50
   # Level 11: 6000 XP, Level 20: 50000 XP, etc.
   ```

---

## 🏆 Gamification System Enhancement

### Current XP Awards:
```python
lesson_completed:       50 XP
quiz_completed:         correct_answers × 4 XP
chat_query_sent:        2 XP
bookmark_added:         1 XP
note_created:           2 XP
badge_earned:           25 XP (bonus)
study_session_recorded: 1 XP per minute (max 60 XP)
```

### Recommended Additional XP Events:
```python
profile_setup_complete:      100 XP (one-time)
first_lesson:                50 XP (bonus)
first_quiz:                  50 XP (bonus)
perfect_quiz (100%):         50 XP (bonus)
daily_goal_met:              20 XP
weekly_goal_met:             100 XP
help_another_student:        10 XP (if study groups added)
share_study_note:            5 XP
topic_mastered (>90%):       100 XP
```

---

## 💡 Summary

### ✅ What's Working Well:
1. ✅ User management and authentication
2. ✅ Real-time event logging (learning_events)
3. ✅ Gamification infrastructure (XP, levels, streaks, badges)
4. ✅ Quiz system architecture
5. ✅ Chat/tutoring session tracking

### ⚠️ Critical Gaps:
1. ❌ **Topics table is empty** - No syllabus structure
2. ❌ **Topic mastery not calculated** - No personalization
3. ❌ **Recommendations not generated** - No AI guidance
4. ❌ **Exam readiness not tracked** - No progress insights
5. ❌ **Habit tracking not active** - Missing coaching opportunities
6. ❌ **Question bank underdeveloped** - Need NEET PYQs

### 🎯 Impact Priority:
| Feature | Impact | Effort | Priority |
|---------|--------|--------|----------|
| Populate Topics | High | Low | 🔴 Critical |
| Calculate Topic Mastery | High | Medium | 🔴 Critical |
| Build Recommendations | High | Medium | 🔴 Critical |
| Exam Readiness Tracking | High | Medium | 🔴 Critical |
| Question Bank | High | High | 🟠 High |
| Email Verification | Medium | Low | 🟠 High |
| Two-Factor Auth | Medium | Medium | 🟡 Medium |
| Leaderboards | Medium | Low | 🟡 Medium |

---

**Next Steps:**
1. Review this analysis with the team
2. Prioritize the critical actions
3. Create tickets for each improvement
4. Set timeline for implementation
5. Consider database backup strategy before major changes

---

*Generated by Claude Code - APXMIND Database Schema Analyzer*
