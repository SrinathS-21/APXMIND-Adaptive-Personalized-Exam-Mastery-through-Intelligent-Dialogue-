"""
Gamification Utilities
======================

Award XP, update daily_progress, update user_gamification_snapshot,
and check simple badge criteria after any learning event.

XP award table (backend-only — never exposed to the frontend):

  lesson_completed          →  50 XP
  quiz_completed            →  correct_answers × 4 XP  (passed via xp arg)
  chat_query_sent           →  2 XP
  study_session_recorded    →  1 XP per minute, max 60 XP per call
  bookmark_added            →  1 XP
  note_created              →  2 XP
  badge_earned              →  25 XP bonus
"""

from datetime import date, datetime
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import (
    BadgeDefinition,
    Bookmark,
    DailyProgress,
    LearningEvent,
    QuizAttemptSummary,
    StudyNote,
    UserBadge,
    UserGamificationSnapshot,
)
from .sse_events import push as sse_push

XP_AWARDS = {
    "lesson_completed":       50,
    "chat_query_sent":        2,
    "bookmark_added":         1,
    "note_created":           2,
    "badge_earned":           25,
}


async def append_event(
    db: AsyncSession,
    user_id: int,
    event_type: str,
    subject: str = None,
    entity_type: str = None,
    entity_id: str = None,
    event_value: float = None,
    payload: dict = None,
    idempotency_key: str = None,
) -> LearningEvent | None:
    """Append one row to learning_events.

    If idempotency_key is provided and already exists, returns None silently.
    Call db.flush() / db.commit() after this in the calling code.
    """
    if idempotency_key:
        existing = await db.execute(
            select(LearningEvent).where(LearningEvent.idempotency_key == idempotency_key)
        )
        if existing.scalar_one_or_none():
            return None

    event = LearningEvent(
        user_id=user_id,
        idempotency_key=idempotency_key,
        event_type=event_type,
        subject=subject,
        entity_type=entity_type,
        entity_id=entity_id,
        event_value=event_value,
        payload=payload or {},
    )
    db.add(event)
    return event


async def award_xp(
    db: AsyncSession,
    user_id: int,
    event_type: str,
    xp: int,
    subject: str = None,
    minutes: int = 0,
) -> int:
    """
    Award XP to a user after a learning event.

    Updates daily_progress and user_gamification_snapshot.
    Returns the XP actually awarded.
    """
    if xp <= 0 and event_type != "quiz_completed":
        return 0

    today = date.today()

    # ── Upsert daily_progress ─────────────────────────────────────────────
    result = await db.execute(
        select(DailyProgress).where(
            DailyProgress.user_id == user_id,
            DailyProgress.date == today,
        )
    )
    dp = result.scalar_one_or_none()
    if not dp:
        dp = DailyProgress(user_id=user_id, date=today)
        db.add(dp)
        await db.flush()

    dp.xp_earned += xp

    if event_type == "lesson_completed":
        dp.lessons_completed += 1
    elif event_type == "quiz_completed":
        dp.quizzes_taken += 1
    elif event_type == "study_session_recorded" and minutes:
        dp.study_minutes += minutes

    if subject and subject not in (dp.subjects_studied or []):
        dp.subjects_studied = list(dp.subjects_studied or []) + [subject]

    # ── Upsert user_gamification_snapshot ─────────────────────────────────
    result = await db.execute(
        select(UserGamificationSnapshot).where(UserGamificationSnapshot.user_id == user_id)
    )
    snap = result.scalar_one_or_none()
    if not snap:
        snap = UserGamificationSnapshot(user_id=user_id)
        db.add(snap)
        await db.flush()

    snap.total_xp += xp

    # Recompute level from total XP (drive from level_definitions in a future pass)
    new_level = min(10, int(snap.total_xp // 500) + 1)
    snap.current_level = new_level
    snap.xp_to_next_level = max(0, new_level * 500 - snap.total_xp)

    # Streak update
    if snap.last_study_date:
        delta = (today - snap.last_study_date).days
        if delta == 1:
            snap.current_streak += 1
        elif delta > 1:
            snap.current_streak = 1
        # delta == 0: same day, no change
    else:
        snap.current_streak = 1

    snap.longest_streak = max(snap.longest_streak, snap.current_streak)
    snap.last_study_date = today
    snap.updated_at = datetime.utcnow()

    await db.flush()

    # ── Badge checks ──────────────────────────────────────────────────────
    await _check_badges(db, user_id, snap)

    # ── Push real-time event ──────────────────────────────────────────────
    await sse_push(user_id, "xp_awarded", {
        "xp": xp,
        "total_xp": snap.total_xp,
        "level": snap.current_level,
        "streak": snap.current_streak,
    })

    return xp


async def award_xp_for_event(
    db: AsyncSession,
    user_id: int,
    event_type: str,
    subject: str = None,
    minutes: int = 0,
    correct_answers: int = 0,
) -> int:
    """Convenience wrapper: look up XP from the award table, then call award_xp."""
    if event_type == "quiz_completed":
        xp = correct_answers * 4
    elif event_type == "study_session_recorded":
        xp = min(60, minutes)
    else:
        xp = XP_AWARDS.get(event_type, 0)

    return await award_xp(db, user_id, event_type, xp, subject=subject, minutes=minutes)


# ---------------------------------------------------------------------------
# Badge checking
# ---------------------------------------------------------------------------

async def _check_badges(
    db: AsyncSession,
    user_id: int,
    snap: UserGamificationSnapshot,
):
    """Check simple badge criteria and award any newly earned badges."""
    all_badges_result = await db.execute(select(BadgeDefinition))
    all_badges = all_badges_result.scalars().all()

    earned_result = await db.execute(
        select(UserBadge.badge_id).where(UserBadge.user_id == user_id)
    )
    earned_ids = {row[0] for row in earned_result.fetchall()}

    for badge in all_badges:
        if badge.id in earned_ids:
            continue

        earned = await _evaluate_badge(db, user_id, snap, badge)
        if not earned:
            continue

        db.add(UserBadge(user_id=user_id, badge_id=badge.id, earned_at=datetime.utcnow()))
        db.add(LearningEvent(
            user_id=user_id,
            event_type="badge_earned",
            payload={"badge_id": badge.id, "badge_name": badge.name},
        ))
        # Bonus XP for badge — don't recurse, just update snapshot directly
        snap.total_xp += XP_AWARDS["badge_earned"]

        # Push badge notification
        await sse_push(user_id, "badge_earned", {
            "badge_id": badge.id,
            "badge_name": badge.name,
        })

    await db.flush()


async def _evaluate_badge(
    db: AsyncSession,
    user_id: int,
    snap: UserGamificationSnapshot,
    badge: BadgeDefinition,
) -> bool:
    """Return True if the user now meets the badge criteria."""
    c = badge.criteria or {}

    if "total_xp" in c:
        return snap.total_xp >= c["total_xp"]

    if "streak_days" in c:
        return snap.current_streak >= c["streak_days"]

    if "quizzes_completed" in c:
        result = await db.execute(
            select(func.count()).where(QuizAttemptSummary.user_id == user_id)
        )
        return (result.scalar() or 0) >= c["quizzes_completed"]

    if "bookmarks_saved" in c:
        result = await db.execute(
            select(func.count()).where(Bookmark.user_id == user_id)
        )
        return (result.scalar() or 0) >= c["bookmarks_saved"]

    if "notes_created" in c:
        result = await db.execute(
            select(func.count()).where(StudyNote.user_id == user_id)
        )
        return (result.scalar() or 0) >= c["notes_created"]

    if "quiz_score_percent" in c:
        # checked at quiz finish time, not here
        return False

    if "lessons_completed" in c:
        result = await db.execute(
            select(func.count()).where(
                LearningEvent.user_id == user_id,
                LearningEvent.event_type == "lesson_completed",
            )
        )
        return (result.scalar() or 0) >= c["lessons_completed"]

    return False
