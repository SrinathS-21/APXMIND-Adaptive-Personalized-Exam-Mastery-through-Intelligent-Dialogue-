"""
Dashboard & Progress Router
============================

GET  /api/dashboard/summary          — XP, level, streak, today totals, badge count
GET  /api/progress/daily             — heatmap rows  ?days=7 | ?from=&to=
GET  /api/progress/gamification      — full snapshot row
POST /api/progress/study-minutes     — record manual study time
"""

import logging
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.middleware.auth import get_current_user
from ...api.schemas import (
    DailyProgressListResponse,
    DailyProgressResponse,
    DashboardSummaryResponse,
    GamificationSnapshotResponse,
    RecordStudyMinutesRequest,
)
from ...db.gamification import append_event, award_xp_for_event
from ...db.models import (
    DailyProgress,
    LevelDefinition,
    User,
    UserBadge,
    UserGamificationSnapshot,
)
from ...db.session import get_db

logger = logging.getLogger(__name__)
router = APIRouter()          # mounted at /api/dashboard
progress_router = APIRouter() # mounted at /api/progress


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _snap_to_schema(
    snap: UserGamificationSnapshot,
    level_label: str | None = None,
) -> GamificationSnapshotResponse:
    return GamificationSnapshotResponse(
        user_id=snap.user_id,
        total_xp=snap.total_xp,
        current_level=snap.current_level,
        level_label=level_label,
        xp_to_next_level=snap.xp_to_next_level,
        current_streak=snap.current_streak,
        longest_streak=snap.longest_streak,
        last_study_date=snap.last_study_date.isoformat() if snap.last_study_date else None,
    )


def _dp_to_schema(dp: DailyProgress | None, for_date: date) -> DailyProgressResponse:
    if dp is None:
        return DailyProgressResponse(date=for_date.isoformat())
    return DailyProgressResponse(
        date=dp.date.isoformat(),
        study_minutes=dp.study_minutes,
        lessons_completed=dp.lessons_completed,
        quizzes_taken=dp.quizzes_taken,
        xp_earned=dp.xp_earned,
        subjects_studied=dp.subjects_studied or [],
    )


async def _get_or_create_snapshot(
    db: AsyncSession, user_id: int
) -> UserGamificationSnapshot:
    result = await db.execute(
        select(UserGamificationSnapshot).where(UserGamificationSnapshot.user_id == user_id)
    )
    snap = result.scalar_one_or_none()
    if not snap:
        snap = UserGamificationSnapshot(user_id=user_id)
        db.add(snap)
        await db.commit()
        await db.refresh(snap)
    return snap


# ---------------------------------------------------------------------------
# GET /api/dashboard/summary
# ---------------------------------------------------------------------------

@router.get("/summary", response_model=DashboardSummaryResponse, summary="Dashboard summary")
async def get_dashboard_summary(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return XP, level, streak, today's progress, and earned badge count."""
    snap = await _get_or_create_snapshot(db, user.id)

    # Level label from level_definitions
    level_label = None
    lvl_result = await db.execute(
        select(LevelDefinition).where(LevelDefinition.level == snap.current_level)
    )
    lvl_def = lvl_result.scalar_one_or_none()
    if lvl_def:
        level_label = lvl_def.label

    # Today's progress
    today = date.today()
    dp_result = await db.execute(
        select(DailyProgress).where(
            DailyProgress.user_id == user.id,
            DailyProgress.date == today,
        )
    )
    dp = dp_result.scalar_one_or_none()

    # Badge count
    badge_result = await db.execute(
        select(UserBadge).where(UserBadge.user_id == user.id)
    )
    badges_count = len(badge_result.scalars().all())

    return DashboardSummaryResponse(
        gamification=_snap_to_schema(snap, level_label),
        today=_dp_to_schema(dp, today),
        badges_count=badges_count,
    )


# ---------------------------------------------------------------------------
# GET /api/progress/daily
# ---------------------------------------------------------------------------

@progress_router.get("/daily", response_model=DailyProgressListResponse, summary="Daily progress heatmap")
async def get_daily_progress(
    days: int = Query(default=7, ge=1, le=365),
    from_date: str = Query(default=None, alias="from"),
    to_date: str = Query(default=None, alias="to"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return per-day progress rows for heatmap / graph display."""
    if from_date and to_date:
        try:
            start = date.fromisoformat(from_date)
            end = date.fromisoformat(to_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format — use YYYY-MM-DD")
    else:
        end = date.today()
        start = end - timedelta(days=days - 1)

    result = await db.execute(
        select(DailyProgress).where(
            DailyProgress.user_id == user.id,
            DailyProgress.date >= start,
            DailyProgress.date <= end,
        ).order_by(DailyProgress.date)
    )
    rows = {dp.date: dp for dp in result.scalars().all()}

    # Fill in empty days so the frontend always gets a complete range
    current = start
    day_list = []
    while current <= end:
        day_list.append(_dp_to_schema(rows.get(current), current))
        current += timedelta(days=1)

    return DailyProgressListResponse(days=day_list)


# ---------------------------------------------------------------------------
# GET /api/progress/gamification
# ---------------------------------------------------------------------------

@progress_router.get(
    "/gamification",
    response_model=GamificationSnapshotResponse,
    summary="Full gamification snapshot",
)
async def get_gamification_snapshot(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    snap = await _get_or_create_snapshot(db, user.id)

    level_label = None
    lvl_result = await db.execute(
        select(LevelDefinition).where(LevelDefinition.level == snap.current_level)
    )
    lvl_def = lvl_result.scalar_one_or_none()
    if lvl_def:
        level_label = lvl_def.label

    return _snap_to_schema(snap, level_label)


# ---------------------------------------------------------------------------
# POST /api/progress/study-minutes
# ---------------------------------------------------------------------------

@progress_router.post("/study-minutes", summary="Record manual study time")
async def record_study_minutes(
    request: RecordStudyMinutesRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Append a study_session_recorded event and award XP (1 per minute, max 60)."""
    target_date = date.today()
    if request.date:
        try:
            target_date = date.fromisoformat(request.date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format — use YYYY-MM-DD")

    subject = request.subject.value
    minutes = request.minutes

    idempotency_key = f"study:{user.id}:{target_date.isoformat()}:{subject}:{minutes}"

    event = await append_event(
        db,
        user_id=user.id,
        event_type="study_session_recorded",
        subject=subject,
        entity_type="session",
        event_value=float(minutes),
        payload={"minutes": minutes, "date": target_date.isoformat()},
        idempotency_key=idempotency_key,
    )

    if event is None:
        return {"success": True, "message": "Duplicate — already recorded", "xp_awarded": 0}

    xp = await award_xp_for_event(
        db, user.id, "study_session_recorded", subject=subject, minutes=minutes
    )
    await db.commit()

    return {"success": True, "minutes_recorded": minutes, "xp_awarded": xp}
