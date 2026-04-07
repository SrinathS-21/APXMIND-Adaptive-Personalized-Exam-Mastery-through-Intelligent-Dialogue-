"""
APXMIND Database Migration & Improvement Script
================================================

This script helps migrate existing data and populate missing tables.

Usage:
    python migrate_database.py --action <action_name>

Actions:
    - migrate_subjects: Migrate strong/weak subjects to user_subject_preferences
    - populate_topics: Populate topics table with NEET syllabus
    - link_lessons: Link lessons to topics
    - calculate_mastery: Calculate initial topic mastery
    - seed_badges: Add enhanced badge definitions
    - expand_levels: Expand level system to 50 levels
    - init_snapshots: Initialize gamification snapshots for all users
    - all: Run all migrations
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker


# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from apxmind.db.models import (
    User,
    UserSubjectPreference,
    Subject,
    Topic,
    Lesson,
    LevelDefinition,
    BadgeDefinition,
    UserGamificationSnapshot,
    TopicMastery,
    ExamReadinessSnapshot,
)


DATABASE_URL = "sqlite+aiosqlite:///APXMIND.db"


# ============================================================================
# NEET Syllabus Data
# ============================================================================

NEET_SYLLABUS = {
    "biology": [
        {"name": "Diversity in Living World", "weight": 7.0},
        {"name": "Structural Organisation in Animals and Plants", "weight": 5.0},
        {"name": "Cell Structure and Function", "weight": 9.0},
        {"name": "Plant Physiology", "weight": 8.0},
        {"name": "Human Physiology", "weight": 20.0},
        {"name": "Reproduction", "weight": 9.0},
        {"name": "Genetics and Evolution", "weight": 18.0},
        {"name": "Biology and Human Welfare", "weight": 9.0},
        {"name": "Biotechnology and Its Applications", "weight": 5.0},
        {"name": "Ecology and Environment", "weight": 10.0},
    ],
    "chemistry": [
        {"name": "Some Basic Concepts of Chemistry", "weight": 3.0},
        {"name": "Structure of Atom", "weight": 4.0},
        {"name": "Classification of Elements and Periodicity", "weight": 3.0},
        {"name": "Chemical Bonding and Molecular Structure", "weight": 5.0},
        {"name": "States of Matter", "weight": 3.0},
        {"name": "Thermodynamics", "weight": 8.0},
        {"name": "Equilibrium", "weight": 7.0},
        {"name": "Redox Reactions", "weight": 4.0},
        {"name": "Hydrogen and s-Block Elements", "weight": 4.0},
        {"name": "p-Block Elements", "weight": 8.0},
        {"name": "d and f Block Elements", "weight": 5.0},
        {"name": "Coordination Compounds", "weight": 5.0},
        {"name": "Environmental Chemistry", "weight": 2.0},
        {"name": "Solid State", "weight": 3.0},
        {"name": "Solutions", "weight": 5.0},
        {"name": "Electrochemistry", "weight": 6.0},
        {"name": "Chemical Kinetics", "weight": 5.0},
        {"name": "Surface Chemistry", "weight": 3.0},
        {"name": "General Principles of Metallurgy", "weight": 3.0},
        {"name": "Organic Chemistry Basics", "weight": 10.0},
        {"name": "Hydrocarbons", "weight": 6.0},
        {"name": "Organic Compounds with Functional Groups", "weight": 12.0},
    ],
    "physics": [
        {"name": "Physical World and Measurement", "weight": 2.0},
        {"name": "Kinematics", "weight": 6.0},
        {"name": "Laws of Motion", "weight": 6.0},
        {"name": "Work, Energy and Power", "weight": 6.0},
        {"name": "Motion of System of Particles and Rigid Body", "weight": 5.0},
        {"name": "Gravitation", "weight": 4.0},
        {"name": "Properties of Bulk Matter", "weight": 7.0},
        {"name": "Thermodynamics", "weight": 8.0},
        {"name": "Kinetic Theory of Gases", "weight": 3.0},
        {"name": "Oscillations and Waves", "weight": 7.0},
        {"name": "Electrostatics", "weight": 8.0},
        {"name": "Current Electricity", "weight": 7.0},
        {"name": "Magnetic Effects of Current and Magnetism", "weight": 8.0},
        {"name": "Electromagnetic Induction and AC", "weight": 8.0},
        {"name": "Electromagnetic Waves", "weight": 2.0},
        {"name": "Optics", "weight": 9.0},
        {"name": "Dual Nature of Matter and Radiation", "weight": 4.0},
        {"name": "Atoms and Nuclei", "weight": 6.0},
        {"name": "Electronic Devices", "weight": 5.0},
    ],
}


EXTENDED_LEVELS = [
    (11, 6000, "Advanced Scholar"),
    (12, 7500, "Expert"),
    (13, 9500, "Master"),
    (14, 12000, "Grand Master"),
    (15, 15000, "Champion"),
    (16, 18500, "Elite"),
    (17, 22500, "Legend"),
    (18, 27000, "Prodigy"),
    (19, 32000, "Virtuoso"),
    (20, 38000, "Genius"),
    (21, 45000, "Sage"),
    (22, 53000, "Enlightened"),
    (23, 62000, "Transcendent"),
    (24, 72000, "Immortal"),
    (25, 83000, "Deity"),
    (26, 95000, "Supreme"),
    (27, 108000, "Omniscient"),
    (28, 122000, "Cosmic"),
    (29, 137000, "Celestial"),
    (30, 153000, "Eternal"),
    (31, 170000, "Infinite"),
    (32, 188000, "Ultimate"),
    (33, 207000, "Absolute"),
    (34, 227000, "Divine"),
    (35, 248000, "Transcendent Master"),
    (36, 270000, "Universal"),
    (37, 293000, "Omnipotent"),
    (38, 317000, "Boundless"),
    (39, 342000, "Supreme Being"),
    (40, 368000, "Apex"),
    (41, 395000, "Zenith"),
    (42, 423000, "Pinnacle"),
    (43, 452000, "Sovereign"),
    (44, 482000, "Emperor"),
    (45, 513000, "God Tier"),
    (46, 545000, "Mythic"),
    (47, 578000, "Legendary Master"),
    (48, 612000, "Omega"),
    (49, 647000, "Alpha Omega"),
    (50, 683000, "NEET Conqueror"),
]


ENHANCED_BADGES = [
    {
        "id": "perfect_quiz_5",
        "name": "Perfect Pentad",
        "description": "Score 100% in 5 quizzes",
        "icon": "🎯",
        "criteria": {"perfect_quizzes": 5},
        "rarity": "rare",
        "category": "mastery",
    },
    {
        "id": "perfect_quiz_10",
        "name": "Perfect 10",
        "description": "Score 100% in 10 quizzes",
        "icon": "💯",
        "criteria": {"perfect_quizzes": 10},
        "rarity": "epic",
        "category": "mastery",
    },
    {
        "id": "study_streak_30",
        "name": "30-Day Warrior",
        "description": "Study for 30 days straight",
        "icon": "⚡",
        "criteria": {"streak_days": 30},
        "rarity": "legendary",
        "category": "streak",
    },
    {
        "id": "study_streak_60",
        "name": "Unstoppable",
        "description": "Study for 60 days straight",
        "icon": "🔥",
        "criteria": {"streak_days": 60},
        "rarity": "legendary",
        "category": "streak",
    },
    {
        "id": "neet_ready",
        "name": "NEET Ready",
        "description": "Complete 100% syllabus coverage",
        "icon": "🎓",
        "criteria": {"syllabus_coverage": 100},
        "rarity": "legendary",
        "category": "milestone",
    },
    {
        "id": "bio_master",
        "name": "Biology Master",
        "description": "90%+ mastery in all Biology topics",
        "icon": "🧬",
        "criteria": {"subject_mastery": "biology", "threshold": 90},
        "rarity": "epic",
        "category": "mastery",
    },
    {
        "id": "chem_master",
        "name": "Chemistry Master",
        "description": "90%+ mastery in all Chemistry topics",
        "icon": "🧪",
        "criteria": {"subject_mastery": "chemistry", "threshold": 90},
        "rarity": "epic",
        "category": "mastery",
    },
    {
        "id": "physics_master",
        "name": "Physics Master",
        "description": "90%+ mastery in all Physics topics",
        "icon": "⚛️",
        "criteria": {"subject_mastery": "physics", "threshold": 90},
        "rarity": "epic",
        "category": "mastery",
    },
    {
        "id": "speed_demon",
        "name": "Speed Demon",
        "description": "Solve 100 questions in 1 hour",
        "icon": "🏃",
        "criteria": {"questions_per_hour": 100},
        "rarity": "rare",
        "category": "speed",
    },
    {
        "id": "night_owl",
        "name": "Night Owl",
        "description": "Study after 11 PM for 7 days",
        "icon": "🦉",
        "criteria": {"late_night_days": 7},
        "rarity": "common",
        "category": "habit",
    },
    {
        "id": "early_bird",
        "name": "Early Bird",
        "description": "Study before 6 AM for 7 days",
        "icon": "🐦",
        "criteria": {"early_morning_days": 7},
        "rarity": "common",
        "category": "habit",
    },
    {
        "id": "marathon",
        "name": "Marathon Runner",
        "description": "Study for 8+ hours in a single day",
        "icon": "🏃‍♂️",
        "criteria": {"single_day_minutes": 480},
        "rarity": "rare",
        "category": "dedication",
    },
]


# ============================================================================
# Migration Functions
# ============================================================================


async def migrate_subjects(db: AsyncSession):
    """Migrate strong/weak subjects from JSON to user_subject_preferences table."""
    print("[MIGRATING] Migrating user subject preferences...")

    result = await db.execute(select(User))
    users = result.scalars().all()

    migrated_count = 0

    for user in users:
        # Migrate strong subjects
        for subject in user.strong_subjects or []:
            preference = UserSubjectPreference(
                user_id=user.id,
                subject=subject.lower(),
                strength="strong",
                priority_rank=None,
            )
            db.add(preference)
            migrated_count += 1

        # Migrate weak subjects
        for subject in user.weak_subjects or []:
            preference = UserSubjectPreference(
                user_id=user.id,
                subject=subject.lower(),
                strength="weak",
                priority_rank=None,
            )
            db.add(preference)
            migrated_count += 1

    await db.commit()
    print(f"[SUCCESS] Migrated {migrated_count} subject preferences")


async def populate_topics(db: AsyncSession):
    """Populate topics table with NEET syllabus."""
    print("[MIGRATING] Populating NEET syllabus topics...")

    # Get subject IDs
    result = await db.execute(select(Subject))
    subjects = {s.name.lower(): s for s in result.scalars().all()}

    total_topics = 0

    for subject_name, topics in NEET_SYLLABUS.items():
        subject = subjects.get(subject_name)
        if not subject:
            print(f"[WARNING]  Subject '{subject_name}' not found in database")
            continue

        for topic_data in topics:
            # Check if topic already exists
            result = await db.execute(
                select(Topic).where(
                    Topic.subject_id == subject.id, Topic.name == topic_data["name"]
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                # Update weight if different
                if existing.syllabus_weight != topic_data["weight"]:
                    existing.syllabus_weight = topic_data["weight"]
                    print(f"   Updated: {topic_data['name']} -> {topic_data['weight']}%")
            else:
                # Create new topic
                topic = Topic(
                    subject_id=subject.id,
                    name=topic_data["name"],
                    syllabus_weight=topic_data["weight"],
                )
                db.add(topic)
                total_topics += 1
                print(f"   Added: {topic_data['name']} -> {topic_data['weight']}%")

    await db.commit()
    print(f"[SUCCESS] Added {total_topics} new topics to database")


async def link_lessons(db: AsyncSession):
    """Link lessons to topics based on lesson.topics JSON field."""
    print("[MIGRATING] Linking lessons to topics...")

    # Get all subjects and their topics
    result = await db.execute(select(Subject.id, Subject.name))
    subjects = [(row[0], row[1]) for row in result.all()]

    for subject_id, subject_name in subjects:
        result = await db.execute(
            select(Topic).where(Topic.subject_id == subject_id)
        )
        topics = {t.name.lower(): t for t in result.scalars().all()}

        result = await db.execute(
            select(Lesson).where(Lesson.subject_id == subject_id)
        )
        lessons = result.scalars().all()

        linked_count = 0

        for lesson in lessons:
            if lesson.topic_id:
                continue  # Already linked

            # Try to match lesson topics JSON to actual topics
            lesson_topics = lesson.topics or []
            if not lesson_topics:
                print(f"   [WARNING]  No topics for lesson: {lesson.title}")
                continue

            # Try to find best matching topic
            for topic_name in lesson_topics:
                topic_key = topic_name.lower().strip()
                if topic_key in topics:
                    lesson.topic_id = topics[topic_key].id
                    linked_count += 1
                    print(f"   [OK] Linked '{lesson.title}' -> '{topic_name}'")
                    break

        await db.commit()
        # Use cached name to avoid async lazy-load after commit.
        print(f"[SUCCESS] Linked {linked_count} lessons for {subject_name}")


async def calculate_mastery(db: AsyncSession):
    """Calculate initial topic mastery based on existing quiz performance."""
    print("[MIGRATING] Calculating initial topic mastery...")

    # This is a placeholder - actual implementation needs quiz analysis
    print("[WARNING]  Topic mastery calculation requires quiz performance data")
    print("   This will be implemented as a background job")
    print("   For now, initializing with 0 mastery for all users and topics")

    result = await db.execute(select(User))
    users = result.scalars().all()

    result = await db.execute(select(Topic))
    topics = result.scalars().all()

    mastery_records = 0

    for user in users:
        for topic in topics:
            # Check if mastery already exists
            result = await db.execute(
                select(TopicMastery).where(
                    TopicMastery.user_id == user.id,
                    TopicMastery.subject == topic.subject.name.lower(),
                    TopicMastery.topic == topic.name,
                )
            )
            existing = result.scalar_one_or_none()

            if not existing:
                mastery = TopicMastery(
                    user_id=user.id,
                    subject=topic.subject.name.lower(),
                    topic=topic.name,
                    mastery_score=0,
                    confidence=0,
                    last_assessed_at=None,
                )
                db.add(mastery)
                mastery_records += 1

    await db.commit()
    print(f"[SUCCESS] Initialized {mastery_records} topic mastery records")


async def seed_badges(db: AsyncSession):
    """Add enhanced badge definitions."""
    print("[MIGRATING] Seeding enhanced badges...")

    added_count = 0

    for badge_data in ENHANCED_BADGES:
        result = await db.execute(
            select(BadgeDefinition).where(BadgeDefinition.id == badge_data["id"])
        )
        existing = result.scalar_one_or_none()

        if not existing:
            badge = BadgeDefinition(**badge_data)
            db.add(badge)
            added_count += 1
            print(f"   Added: {badge_data['name']} ({badge_data['rarity']})")

    await db.commit()
    print(f"[SUCCESS] Added {added_count} new badges")


async def expand_levels(db: AsyncSession):
    """Expand level system from 10 to 50 levels."""
    print("[MIGRATING] Expanding level system to 50 levels...")

    added_count = 0

    for level, xp, label in EXTENDED_LEVELS:
        result = await db.execute(
            select(LevelDefinition).where(LevelDefinition.level == level)
        )
        existing = result.scalar_one_or_none()

        if not existing:
            level_def = LevelDefinition(level=level, xp_required=xp, label=label)
            db.add(level_def)
            added_count += 1
            print(f"   Level {level}: {xp:,} XP -> {label}")

    await db.commit()
    print(f"[SUCCESS] Added {added_count} new levels")


async def init_snapshots(db: AsyncSession):
    """Initialize gamification snapshots for users who don't have one."""
    print("[MIGRATING] Initializing gamification snapshots...")

    result = await db.execute(select(User))
    users = result.scalars().all()

    added_count = 0

    for user in users:
        result = await db.execute(
            select(UserGamificationSnapshot).where(
                UserGamificationSnapshot.user_id == user.id
            )
        )
        existing = result.scalar_one_or_none()

        if not existing:
            snapshot = UserGamificationSnapshot(
                user_id=user.id,
                total_xp=0,
                current_level=1,
                xp_to_next_level=500,
                current_streak=0,
                longest_streak=0,
                last_study_date=None,
            )
            db.add(snapshot)
            added_count += 1
            print(f"   Created snapshot for user: {user.name}")

    await db.commit()
    print(f"[SUCCESS] Created {added_count} gamification snapshots")


async def run_all_migrations(db: AsyncSession):
    """Run all migrations in sequence."""
    print("=" * 70)
    print("APXMIND Database Migration - Running All Migrations")
    print("=" * 70)

    await populate_topics(db)
    await migrate_subjects(db)
    await link_lessons(db)
    await expand_levels(db)
    await seed_badges(db)
    await init_snapshots(db)
    await calculate_mastery(db)

    print("=" * 70)
    print("[SUCCESS] All migrations completed successfully!")
    print("=" * 70)


# ============================================================================
# Main Execution
# ============================================================================


async def main():
    import argparse

    parser = argparse.ArgumentParser(description="APXMIND Database Migrations")
    parser.add_argument(
        "--action",
        type=str,
        required=True,
        choices=[
            "migrate_subjects",
            "populate_topics",
            "link_lessons",
            "calculate_mastery",
            "seed_badges",
            "expand_levels",
            "init_snapshots",
            "all",
        ],
        help="Migration action to perform",
    )

    args = parser.parse_args()

    # Create async engine
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session_factory = async_sessionmaker(engine, class_=AsyncSession)

    async with async_session_factory() as db:
        if args.action == "migrate_subjects":
            await migrate_subjects(db)
        elif args.action == "populate_topics":
            await populate_topics(db)
        elif args.action == "link_lessons":
            await link_lessons(db)
        elif args.action == "calculate_mastery":
            await calculate_mastery(db)
        elif args.action == "seed_badges":
            await seed_badges(db)
        elif args.action == "expand_levels":
            await expand_levels(db)
        elif args.action == "init_snapshots":
            await init_snapshots(db)
        elif args.action == "all":
            await run_all_migrations(db)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
