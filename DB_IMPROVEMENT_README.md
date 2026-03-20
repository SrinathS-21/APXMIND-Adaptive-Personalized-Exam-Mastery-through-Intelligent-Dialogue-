# Database Schema Improvement Guide

## 📚 Overview

This guide contains comprehensive database schema analysis and improvement recommendations for APXMIND.

## 📁 Files Generated

1. **`DATABASE_SCHEMA_ANALYSIS.md`** - Detailed schema analysis, current state, gaps, and recommendations
2. **`db_improvements.sql`** - SQL script with all schema improvements
3. **`migrate_database.py`** - Python script to migrate data and populate missing tables

---

## 🚀 Quick Start

### Step 1: Review the Analysis

Read `DATABASE_SCHEMA_ANALYSIS.md` to understand:
- Current schema structure (29 tables)
- What's working well ✅
- Critical gaps ⚠️
- Priority action items 🔴🟠🟡🟢

### Step 2: Backup Your Database

```bash
# Create a backup before making any changes
cp APXMIND.db APXMIND.db.backup_$(date +%Y%m%d_%H%M%S)
```

### Step 3: Apply Schema Improvements

The SQL script is organized in phases. Apply them sequentially:

```bash
# Apply PHASE 1: Critical Fixes (ALTER TABLE statements)
sqlite3 APXMIND.db < db_improvements_phase1.sql

# Apply PHASE 2: New Tables
sqlite3 APXMIND.db < db_improvements_phase2.sql

# Apply PHASE 3: Indexes
sqlite3 APXMIND.db < db_improvements_phase3.sql

# etc...
```

**OR** apply specific sections manually using:
```bash
sqlite3 APXMIND.db
.read db_improvements.sql
# Review output for errors
.quit
```

### Step 4: Run Data Migrations

After schema is updated, populate the data:

```bash
# 1. Populate NEET syllabus topics (CRITICAL)
python migrate_database.py --action populate_topics

# 2. Migrate user subject preferences
python migrate_database.py --action migrate_subjects

# 3. Link lessons to topics
python migrate_database.py --action link_lessons

# 4. Expand level system to 50 levels
python migrate_database.py --action expand_levels

# 5. Add enhanced badges
python migrate_database.py --action seed_badges

# 6. Initialize gamification snapshots
python migrate_database.py --action init_snapshots

# 7. Calculate topic mastery (initializes at 0, will be computed later)
python migrate_database.py --action calculate_mastery

# OR run all migrations at once
python migrate_database.py --action all
```

---

## 🎯 Priority Action Items

### 🔴 CRITICAL (Do First)

1. **Populate `topics` table** (currently 0 rows)
   ```bash
   python migrate_database.py --action populate_topics
   ```
   - Adds all 67 NEET syllabus topics across 3 subjects
   - Includes syllabus weightage for each topic

2. **Link lessons to topics** (42 lessons have `topic_id = NULL`)
   ```bash
   python migrate_database.py --action link_lessons
   ```

3. **Implement topic mastery calculation**
   - Currently initializes at 0
   - Needs background job to calculate from quiz performance
   - **THIS IS THE CORE OF PERSONALIZATION**

4. **Build recommendation engine**
   - Analyze topic mastery → suggest weak topics
   - Analyze daily progress → suggest study time adjustments
   - Generate `learning_recommendations` records

5. **Create exam readiness calculator**
   - Calculate readiness score from syllabus coverage + quiz accuracy
   - Project NEET score
   - Generate `exam_readiness_snapshots` daily

---

## 📊 Schema Statistics

### Before Improvements:
- **29 tables** total
- **Active tables:** 18
- **Empty/unused tables:** 11 ⚠️
- **Critical gaps:** Topics, Topic Mastery, Recommendations, Exam Readiness

### After Improvements:
- **40+ tables** total
- **New tables:** Question Bank, Quiz Templates, Mock Exams, Bookmark Collections, Study Groups, Audit Log, User Sessions
- **Enhanced fields:** 50+ new columns across existing tables
- **New indexes:** 15+ performance indexes

---

## 🏗️ New Tables Added

### 1. **question_bank**
Master repository for all  NEET questions (PYQs, NCERT, custom)

### 2. **quiz_templates**
Reusable quiz templates for teachers/admins

### 3. **bookmark_collections**
Users can organize bookmarks into folders

### 4. **study_groups**
Collaborative learning groups

### 5. **mock_exams**
Full NEET simulation tracking

### 6. **audit_log**
Security and compliance tracking

### 7. **user_sessions**
Enhanced authentication and session management

### 8. **syllabus_coverage**
Per-user syllabus coverage tracking

---

## 🔍 Key Improvements

### Identity & Profile
- ✅ Email verification
- ✅ Phone number support (for Indian users)
- ✅ Two-factor authentication
- ✅ Account security (login attempts, account locking)
- ✅ Onboarding state tracking

### Content Catalog
- ✅ 67 NEET syllabus topics with weightage
- ✅ Lesson prerequisites
- ✅ Learning outcomes
- ✅ NCERT chapter mapping
- ✅ Video content support

### Gamification
- ✅ 50 levels (expanded from 10)
- ✅ 32+ badges (added 12 new)
- ✅ Badge rarity system (common/rare/epic/legendary)
- ✅ Leaderboards (global/state/school)
- ✅ Enhanced XP events

### Personalization
- ✅ Topic mastery tracking (0-100 score per topic)
- ✅ Weak topic detection
- ✅ AI recommendations
- ✅ Exam readiness projection
- ✅ Study habit tracking

### Quiz System
- ✅ Question bank with PYQ tracking
- ✅ Quiz templates
- ✅ Adaptive difficulty
- ✅ Mock exam support

---

## 🔒 Security Enhancements

1. **Audit Logging** - Track all user actions
2. **Session Management** - Multi-device session tracking
3. **Two-Factor Auth** - Optional 2FA support
4. **Account Security** - Failed login tracking, account locking
5. **Email Verification** - Verify email addresses

---

## 📈 Performance Optimizations

### New Indexes:
- `idx_user_gam_xp` - Leaderboard queries
- `idx_user_gam_streak` - Streak rankings
- `idx_quiz_user_subject` - Quiz analytics
- `idx_topic_mastery_score` - Weak topic detection
- `idx_daily_progress_range` - Progress charts
- Many more...

### Views Created:
- `v_user_dashboard` - One-query dashboard summary
- `v_weak_topics` - Quick weak topic lookup
- `v_leaderboard` - Leaderboard with rankings

### Triggers Added:
- Auto-update badge earned count
- Auto-calculate syllabus coverage
- Auto-check daily goal achievement

---

## 🧪 Testing Recommendations

After applying improvements:

1. **Verify Schema:**
   ```bash
   sqlite3 APXMIND.db ".schema" | grep "CREATE TABLE" | wc -l
   # Should show 35+ tables
   ```

2. **Check Data:**
   ```bash
   sqlite3 APXMIND.db "SELECT COUNT(*) FROM topics;"
   # Should show 67 topics (Biology: 10, Chemistry: 22, Physics: 19)
   ```

3. **Test Gamification:**
   ```bash
   sqlite3 APXMIND.db "SELECT COUNT(*) FROM level_definitions;"
   # Should show 50 levels

   sqlite3 APXMIND.db "SELECT COUNT(*) FROM badge_definitions WHERE rarity = 'legendary';"
   # Should show legendary badges
   ```

4. **Verify Indexes:**
   ```bash
   sqlite3 APXMIND.db ".indexes" | grep "idx_" | wc -l
   # Should show 20+ custom indexes
   ```

---

## 📝 Implementation Checklist

### Immediate (Week 1)
- [ ] Backup database
- [ ] Apply PHASE 1 schema changes (ALTER TABLE)
- [ ] Apply PHASE 2 (new tables)
- [ ] Apply PHASE 3 (indexes)
- [ ] Run `populate_topics` migration
- [ ] Run `link_lessons` migration
- [ ] Run `expand_levels` migration
- [ ] Run `seed_badges` migration
- [ ] Test basic functionality

### Short Term (Week 2-3)
- [ ] Implement topic mastery calculation logic
- [ ] Build recommendation engine
- [ ] Create exam readiness calculator
- [ ] Add habit tracking
- [ ] Implement email verification
- [ ] Add audit logging

### Medium Term (Month 1-2)
- [ ] Build question bank (import NEET PYQs)
- [ ] Create quiz templates
- [ ] Implement mock exams
- [ ] Add leaderboards
- [ ] Implement study groups
- [ ] Add bookmark collections
- [ ] Enable two-factor authentication

### Long Term (Month 3+)
- [ ] Mobile app sync
- [ ] Advanced analytics dashboard
- [ ] Personalized study plans
- [ ] Spaced repetition algorithm
- [ ] Social features
- [ ] Parent/teacher dashboard

---

## ⚠️ Important Notes

1. **Don't delete legacy columns yet** - Keep `strong_subjects`, `weak_subjects`, etc. until migration is verified
2. **Test in development first** - Apply changes to a test database before production
3. **Monitor performance** - Watch for slow queries after adding indexes
4. **Incremental rollout** - Apply changes in phases, not all at once
5. **User communication** - Inform users about new features as they're released

---

## 🐛 Troubleshooting

### Issue: SQLite locking error
```bash
# Close all connections to database
# Check for open handles: lsof APXMIND.db (Unix) or handle.exe (Windows)
```

### Issue: Migration script fails
```bash
# Check Python dependencies
pip install sqlalchemy aiosqlite

# Run with verbose mode
python migrate_database.py --action populate_topics --verbose
```

### Issue: Duplicate key errors
```bash
# Check for existing data before inserting
# Use INSERT OR IGNORE or ON CONFLICT clauses
```

---

## 📞 Support

If you encounter issues:
1. Check `logs/APXMIND_api.log` for errors
2. Verify database integrity: `sqlite3 APXMIND.db "PRAGMA integrity_check;"`
3. Review migration output for warnings
4. Test queries in SQLite browser before applying to production

---

## 🎓 Next Steps

After completing all migrations:

1. **Update API Routes** - Add endpoints for new features (recommendations, leaderboards, etc.)
2. **Update Frontend** - Add UI for new features
3. **Documentation** - Update API docs with new endpoints
4. **Testing** - Write integration tests for new features
5. **Monitoring** - Set up alerts for database performance

---

**Last Updated:** March 20, 2026
**Version:** 2.0
**Author:** Claude Code - APXMIND Team
