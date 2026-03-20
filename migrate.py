"""
migrate.py
===========

Idempotent migration script — patches the live APXMIND.db to match the
full real-time schema defined in src/apxmind/db/models.py.

Safe to run multiple times.  Run from the project root:

    python migrate.py

Steps
-----
1. Add new columns to existing tables (users, subjects, lessons)
2. Create all new tables that do not yet exist
3. Backfill:  subjects.code  ←  subjects.name
              users.username  ←  slugified users.name
4. Create initial user_gamification_snapshot rows for existing users
5. Seed level_definitions  (skipped if rows already exist)
6. Seed badge_definitions  (skipped if rows already exist)
"""

import re
import sqlite3
import sys
from pathlib import Path

from sqlalchemy import create_engine

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).parent
DB_PATH = ROOT / "APXMIND.db"
DB_URL = f"sqlite:///{DB_PATH}"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _existing_columns(cur: sqlite3.Cursor, table: str) -> set:
    cur.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in cur.fetchall()}


def _existing_tables(cur: sqlite3.Cursor) -> set:
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return {row[0] for row in cur.fetchall()}


def _add_column(cur, table, col, col_def, existing):
    if col not in existing:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_def}")
        print(f"  + {table}.{col}")
    else:
        print(f"  . {table}.{col} (already exists)")


def _slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9_]", "_", slug)
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug or "user"


# ---------------------------------------------------------------------------
# Step 1 — ALTER TABLE: add new columns to existing tables
# ---------------------------------------------------------------------------

def step1_alter_tables(con: sqlite3.Connection):
    print("\n[1/6] Adding new columns to existing tables ...")
    cur = con.cursor()

    # ── users ──────────────────────────────────────────────────────────────
    cols = _existing_columns(cur, "users")
    _add_column(cur, "users", "username",
                "VARCHAR(50)",                       cols)   # UNIQUE index added in step 3
    _add_column(cur, "users", "avatar_url",
                "TEXT",                              cols)
    _add_column(cur, "users", "timezone",
                "VARCHAR(64) DEFAULT 'Asia/Kolkata'", cols)
    _add_column(cur, "users", "daily_study_target_hours",
                "REAL DEFAULT 4",                    cols)
    _add_column(cur, "users", "updated_at",
                "DATETIME",                          cols)   # backfilled in step 3
    _add_column(cur, "users", "last_active_at",
                "DATETIME",                          cols)
    _add_column(cur, "users", "deleted_at",
                "DATETIME",                          cols)

    # ── subjects ───────────────────────────────────────────────────────────
    cols = _existing_columns(cur, "subjects")
    _add_column(cur, "subjects", "code",
                "VARCHAR(20)",                       cols)

    # ── lessons ────────────────────────────────────────────────────────────
    cols = _existing_columns(cur, "lessons")
    _add_column(cur, "lessons", "topic_id",
                "INTEGER",                           cols)
    _add_column(cur, "lessons", "sequence_no",
                "INTEGER",                           cols)
    _add_column(cur, "lessons", "estimated_minutes",
                "INTEGER DEFAULT 30",                cols)

    con.commit()
    print("  Done.")


# ---------------------------------------------------------------------------
# Step 2 — CREATE new tables via SQLAlchemy create_all(checkfirst=True)
# ---------------------------------------------------------------------------

def step2_create_tables():
    print("\n[2/6] Creating new tables (checkfirst=True) ...")
    from src.apxmind.db.models import Base

    engine = create_engine(DB_URL, echo=False)
    Base.metadata.create_all(engine, checkfirst=True)
    engine.dispose()

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    tables = sorted(_existing_tables(cur))
    con.close()
    print(f"  Total tables in DB: {len(tables)}")
    for t in tables:
        print(f"    {t}")


# ---------------------------------------------------------------------------
# Step 3 — Backfills
# ---------------------------------------------------------------------------

def step3_backfill(con: sqlite3.Connection):
    print("\n[3/6] Backfilling data ...")
    cur = con.cursor()

    # subjects.code ← subjects.name
    cur.execute("UPDATE subjects SET code = name WHERE code IS NULL OR code = ''")
    print(f"  subjects.code backfilled:  {cur.rowcount} rows")

    # unique index on subjects.code
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name='ix_subjects_code'"
    )
    if not cur.fetchone():
        try:
            cur.execute("CREATE UNIQUE INDEX ix_subjects_code ON subjects(code)")
            print("  Created UNIQUE index on subjects.code")
        except sqlite3.OperationalError as exc:
            print(f"  Warning — subjects.code index: {exc}")

    # users.username ← slugified users.name (de-duped with _<id>)
    cur.execute("SELECT id, name FROM users WHERE username IS NULL OR username = ''")
    rows = cur.fetchall()
    updated = 0
    for uid, name in rows:
        base = _slugify(name)[:40]
        candidate = base
        cur.execute(
            "SELECT id FROM users WHERE username = ? AND id != ?", (candidate, uid)
        )
        if cur.fetchone():
            candidate = f"{base}_{uid}"
        cur.execute("UPDATE users SET username = ? WHERE id = ?", (candidate, uid))
        updated += 1
    print(f"  users.username backfilled: {updated} rows")

    # unique index on users.username (created after backfill to avoid partial-null conflicts)
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name='ix_users_username'"
    )
    if not cur.fetchone():
        try:
            cur.execute("CREATE UNIQUE INDEX ix_users_username ON users(username)")
            print("  Created UNIQUE index on users.username")
        except sqlite3.OperationalError as exc:
            print(f"  Warning — users.username index: {exc}")

    # users.updated_at ← created_at where missing
    cur.execute(
        "UPDATE users SET updated_at = created_at "
        "WHERE (updated_at IS NULL OR updated_at = '') AND created_at IS NOT NULL"
    )
    print(f"  users.updated_at backfilled: {cur.rowcount} rows")

    # lessons.sequence_no ← `order` where null
    cur.execute(
        'UPDATE lessons SET sequence_no = "order" '
        'WHERE sequence_no IS NULL AND "order" IS NOT NULL'
    )
    print(f"  lessons.sequence_no backfilled: {cur.rowcount} rows")

    # lessons.estimated_minutes ← estimated_time where null
    cur.execute(
        "UPDATE lessons SET estimated_minutes = estimated_time "
        "WHERE estimated_minutes IS NULL AND estimated_time IS NOT NULL"
    )
    print(f"  lessons.estimated_minutes backfilled: {cur.rowcount} rows")

    con.commit()
    print("  Done.")


# ---------------------------------------------------------------------------
# Step 4 — Bootstrap user_gamification_snapshot for existing users
# ---------------------------------------------------------------------------

def step4_gamification_snapshots(con: sqlite3.Connection):
    print("\n[4/6] Bootstrapping user_gamification_snapshot ...")
    cur = con.cursor()

    cur.execute(
        "SELECT id FROM users "
        "WHERE id NOT IN (SELECT user_id FROM user_gamification_snapshot)"
    )
    user_ids = [row[0] for row in cur.fetchall()]

    for uid in user_ids:
        # 4 XP per correct answer from legacy quiz_attempts
        cur.execute(
            "SELECT COALESCE(SUM(correct_answers * 4), 0) FROM quiz_attempts WHERE user_id = ?",
            (uid,),
        )
        total_xp = cur.fetchone()[0]
        current_level = min(10, int(total_xp // 500) + 1)
        xp_to_next = max(0, current_level * 500 - total_xp)

        cur.execute(
            """
            INSERT OR IGNORE INTO user_gamification_snapshot
              (user_id, total_xp, current_level, xp_to_next_level,
               current_streak, longest_streak, updated_at)
            VALUES (?, ?, ?, ?, 0, 0, CURRENT_TIMESTAMP)
            """,
            (uid, total_xp, current_level, xp_to_next),
        )

    con.commit()
    print(f"  Snapshots created: {len(user_ids)} users")


# ---------------------------------------------------------------------------
# Step 5 — Seed level_definitions
# ---------------------------------------------------------------------------

LEVEL_DEFINITIONS = [
    (1,      0, "Beginner"),
    (2,    500, "Explorer"),
    (3,   1200, "Learner"),
    (4,   2200, "Scholar"),
    (5,   3500, "Achiever"),
    (6,   5500, "Expert"),
    (7,   8000, "Master"),
    (8,  11500, "Champion"),
    (9,  16000, "Genius"),
    (10, 22000, "NEET Warrior"),
]


def step5_seed_levels(con: sqlite3.Connection):
    print("\n[5/6] Seeding level_definitions ...")
    cur = con.cursor()
    cur.execute("SELECT COUNT(*) FROM level_definitions")
    if cur.fetchone()[0] > 0:
        print("  Already seeded — skipped.")
        return
    cur.executemany(
        "INSERT INTO level_definitions (level, xp_required, label) VALUES (?, ?, ?)",
        LEVEL_DEFINITIONS,
    )
    con.commit()
    print(f"  Inserted {len(LEVEL_DEFINITIONS)} levels.")


# ---------------------------------------------------------------------------
# Step 6 — Seed badge_definitions
# ---------------------------------------------------------------------------

BADGE_DEFINITIONS = [
    ("first_lesson",   "First Step",         "Complete your very first lesson.",                    "📖", '{"lessons_completed": 1}'),
    ("first_quiz",     "Quiz Starter",        "Complete your first quiz.",                           "🧪", '{"quizzes_completed": 1}'),
    ("perfect_quiz",   "Perfect Score",       "Score 100% on any quiz.",                             "💯", '{"quiz_score_percent": 100}'),
    ("streak_3",       "3-Day Streak",        "Study 3 days in a row.",                              "🔥", '{"streak_days": 3}'),
    ("streak_7",       "Week Warrior",        "Study 7 days in a row.",                              "⚡", '{"streak_days": 7}'),
    ("streak_30",      "Monthly Master",      "Study 30 days in a row.",                             "🏆", '{"streak_days": 30}'),
    ("quiz_master_10", "Quiz Master",         "Complete 10 quizzes.",                                "🎯", '{"quizzes_completed": 10}'),
    ("quiz_master_50", "Quiz Veteran",        "Complete 50 quizzes.",                                "🥇", '{"quizzes_completed": 50}'),
    ("bookworm",       "Bookworm",            "Save 10 bookmarks.",                                  "🔖", '{"bookmarks_saved": 10}'),
    ("note_taker",     "Note Taker",          "Create 5 study notes.",                               "📝", '{"notes_created": 5}'),
    ("physicist",      "Physics Ace",         "Score 90%+ on a Physics quiz.",                       "⚛️", '{"subject": "physics", "quiz_score_percent": 90}'),
    ("chemist",        "Chemistry Ace",       "Score 90%+ on a Chemistry quiz.",                     "🧬", '{"subject": "chemistry", "quiz_score_percent": 90}'),
    ("biologist",      "Biology Ace",         "Score 90%+ on a Biology quiz.",                       "🌿", '{"subject": "biology", "quiz_score_percent": 90}'),
    ("xp_500",         "XP Collector",        "Earn a total of 500 XP.",                             "⭐", '{"total_xp": 500}'),
    ("xp_5000",        "XP Hoarder",          "Earn a total of 5000 XP.",                            "🌟", '{"total_xp": 5000}'),
    ("neet_ready",     "NEET Ready",          "Reach 80% exam readiness score.",                     "🎓", '{"readiness_percent": 80}'),
    ("early_bird",     "Early Bird",          "Start a study session before 7 AM.",                  "🌅", '{"first_activity_hour_lte": 7}'),
    ("night_owl",      "Night Owl",           "Study past midnight.",                                 "🦉", '{"last_activity_hour_gte": 0}'),
    ("consistent_5",   "Consistency King",    "Hit your daily study target 5 days in a row.",        "📅", '{"target_hit_streak": 5}'),
    ("all_subjects",   "All-Rounder",         "Study all 3 subjects in a single day.",               "🌈", '{"subjects_in_day": 3}'),
]


def step6_seed_badges(con: sqlite3.Connection):
    print("\n[6/6] Seeding badge_definitions ...")
    cur = con.cursor()
    cur.execute("SELECT COUNT(*) FROM badge_definitions")
    if cur.fetchone()[0] > 0:
        print("  Already seeded — skipped.")
        return
    cur.executemany(
        "INSERT INTO badge_definitions (id, name, description, icon, criteria) VALUES (?, ?, ?, ?, ?)",
        BADGE_DEFINITIONS,
    )
    con.commit()
    print(f"  Inserted {len(BADGE_DEFINITIONS)} badges.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if not DB_PATH.exists():
        print(f"ERROR: Database not found at {DB_PATH}")
        print("Start the server once to create the DB, then re-run migrate.py.")
        sys.exit(1)

    print(f"APXMIND Migration")
    print(f"Target DB : {DB_PATH}")
    print("=" * 60)

    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA foreign_keys=OFF")   # relax FK checks during migration

    try:
        step1_alter_tables(con)
        step2_create_tables()               # opens its own SQLAlchemy connection
        step3_backfill(con)
        step4_gamification_snapshots(con)
        step5_seed_levels(con)
        step6_seed_badges(con)
    finally:
        con.execute("PRAGMA foreign_keys=ON")
        con.close()

    print("\n" + "=" * 60)
    print("Migration complete. APXMIND.db is up to date.")


if __name__ == "__main__":
    main()
