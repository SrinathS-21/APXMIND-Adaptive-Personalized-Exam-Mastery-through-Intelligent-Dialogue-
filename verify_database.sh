#!/bin/bash
# Database Verification Script
# Verifies all improvements have been applied successfully

echo "=========================================="
echo "APXMIND DATABASE VERIFICATION REPORT"
echo "=========================================="
echo ""

echo "DATABASE INFO:"
echo "-------------"
sqlite3 APXMIND.db "SELECT 'Database Size: ' || (page_count * page_size / 1024) || ' KB' FROM pragma_page_count(), pragma_page_size();"
sqlite3 APXMIND.db "SELECT 'SQLite Version: ' || sqlite_version();"
echo ""

echo "TABLE COUNT:"
echo "-----------"
sqlite3 APXMIND.db "SELECT 'Total Tables: ' || COUNT(*) FROM sqlite_master WHERE type='table';"
echo ""

echo "NEW TABLES ADDED:"
echo "----------------"
sqlite3 APXMIND.db "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('question_bank', 'quiz_templates', 'bookmark_collections', 'study_groups', 'study_group_members', 'mock_exams', 'audit_log', 'user_sessions', 'syllabus_coverage') ORDER BY name;"
echo ""

echo "INDEX COUNT:"
echo "-----------"
sqlite3 APXMIND.db "SELECT 'Custom Indexes: ' || COUNT(*) FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%';"
echo ""

echo "CONTENT DATA:"
echo "------------"
sqlite3 APXMIND.db "SELECT 'Subjects: ' || COUNT(*) FROM subjects;"
sqlite3 APXMIND.db "SELECT 'Topics: ' || COUNT(*) FROM topics;"
sqlite3 APXMIND.db "SELECT 'Lessons: ' || COUNT(*) FROM lessons;"
sqlite3 APXMIND.db "SELECT 'Lessons Linked to Topics: ' || COUNT(*) FROM lessons WHERE topic_id IS NOT NULL;"
sqlite3 APXMIND.db "SELECT 'Unlinked Lessons: ' || COUNT(*) FROM lessons WHERE topic_id IS NULL;"
echo ""

echo "TOPICS BY SUBJECT:"
echo "-----------------"
sqlite3 APXMIND.db "SELECT s.name || ': ' || COUNT(t.id) || ' topics' FROM subjects s LEFT JOIN topics t ON s.id = t.subject_id GROUP BY s.name ORDER BY s.name;"
echo ""

echo "GAMIFICATION:"
echo "------------"
sqlite3 APXMIND.db "SELECT 'Level Definitions: ' || COUNT(*) FROM level_definitions;"
sqlite3 APXMIND.db "SELECT 'Max Level: ' || MAX(level) || ' (' || label || ', ' || xp_required || ' XP)' FROM level_definitions;"
sqlite3 APXMIND.db "SELECT 'Badge Definitions: ' || COUNT(*) FROM badge_definitions;"
sqlite3 APXMIND.db "SELECT 'Epic/Legendary Badges: ' || COUNT(*) FROM badge_definitions WHERE rarity IN ('epic', 'legendary');"
sqlite3 APXMIND.db "SELECT 'User Gamification Snapshots: ' || COUNT(*) FROM user_gamification_snapshot;"
echo ""

echo "BADGE BREAKDOWN BY RARITY:"
echo "-------------------------"
sqlite3 APXMIND.db "SELECT rarity || ': ' || COUNT(*) FROM badge_definitions GROUP BY rarity ORDER BY CASE rarity WHEN 'legendary' THEN 1 WHEN 'epic' THEN 2 WHEN 'rare' THEN 3 ELSE 4 END;"
echo ""

echo "USER DATA:"
echo "---------"
sqlite3 APXMIND.db "SELECT 'Total Users: ' || COUNT(*) FROM users;"
sqlite3 APXMIND.db "SELECT 'Users with Email Verified: ' || COUNT(*) FROM users WHERE email_verified = 1;"
sqlite3 APXMIND.db "SELECT 'Users with Phone Number: ' || COUNT(*) FROM users WHERE phone_number IS NOT NULL;"
echo ""

echo "ACTIVITY DATA:"
echo "-------------"
sqlite3 APXMIND.db "SELECT 'Learning Events: ' || COUNT(*) FROM learning_events;"
sqlite3 APXMIND.db "SELECT 'Daily Progress Records: ' || COUNT(*) FROM daily_progress;"
sqlite3 APXMIND.db "SELECT 'Quizzes Created: ' || COUNT(*) FROM quizzes;"
sqlite3 APXMIND.db "SELECT 'Learning Sessions: ' || COUNT(*) FROM learning_sessions;"
sqlite3 APXMIND.db "SELECT 'Chat Messages: ' || COUNT(*) FROM chat_messages;"
echo ""

echo "NEW COLUMNS ADDED:"
echo "-----------------"
echo "Users table enhancements:"
sqlite3 APXMIND.db "PRAGMA table_info(users);" | grep -E "(email_verified|phone_number|onboarding)" | wc -l | awk '{print "  Added " $1 " new columns"}'

echo "Badge enhancements:"
sqlite3 APXMIND.db "PRAGMA table_info(badge_definitions);" | grep -E "(rarity|category|available)" | wc -l | awk '{print "  Added " $1 " new columns"}'

echo "Gamification enhancements:"
sqlite3 APXMIND.db "PRAGMA table_info(user_gamification_snapshot);" | grep -E "(rank_|badges_earned)" | wc -l | awk '{print "  Added " $1 " new columns"}'
echo ""

echo "CRITICAL GAPS STATUS:"
echo "--------------------"
topics_count=$(sqlite3 APXMIND.db "SELECT COUNT(*) FROM topics;")
if [ $topics_count -gt 0 ]; then
    echo "[SUCCESS] Topics table populated: $topics_count topics"
else
    echo "[FAILED] Topics table is still empty!"
fi

linked_lessons=$(sqlite3 APXMIND.db "SELECT COUNT(*) FROM lessons WHERE topic_id IS NOT NULL;")
total_lessons=$(sqlite3 APXMIND.db "SELECT COUNT(*) FROM lessons;")
if [ $linked_lessons -gt 0 ]; then
    echo "[SUCCESS] Lessons linked to topics: $linked_lessons / $total_lessons"
else
    echo "[FAILED] No lessons linked to topics yet!"
fi

levels_count=$(sqlite3 APXMIND.db "SELECT COUNT(*) FROM level_definitions;")
if [ $levels_count -ge 50 ]; then
    echo "[SUCCESS] Level system expanded: $levels_count levels"
else
    echo "[WARNING] Level system not fully expanded: $levels_count levels (need 50)"
fi

badges_count=$(sqlite3 APXMIND.db "SELECT COUNT(*) FROM badge_definitions;")
if [ $badges_count -ge 29 ]; then
    echo "[SUCCESS] Enhanced badges added: $badges_count badges"
else
    echo "[WARNING] Badge system incomplete: $badges_count badges"
fi

echo ""
echo "SAMPLE DATA:"
echo "-----------"
echo "Top 5 Topics by Syllabus Weight:"
sqlite3 APXMIND.db "SELECT '  ' || name || ' (' || syllabus_weight || '%)' FROM topics ORDER BY syllabus_weight DESC LIMIT 5;"
echo ""

echo "Recently Added Badges:"
sqlite3 APXMIND.db "SELECT '  ' || name || ' [' || rarity || ']' FROM badge_definitions WHERE rarity IN ('epic', 'legendary') LIMIT 5;"
echo ""

echo "=========================================="
echo "VERIFICATION COMPLETE"
echo "=========================================="
echo ""
echo "Next Steps:"
echo "1. Review the output above"
echo "2. Check DATABASE_SCHEMA_ANALYSIS.md for implementation guide"
echo "3. Implement topic mastery calculation (background job)"
echo "4. Build recommendation engine"
echo "5. Create exam readiness calculator"
echo ""
