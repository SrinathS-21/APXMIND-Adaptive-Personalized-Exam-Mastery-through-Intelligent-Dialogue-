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
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.middleware.auth import get_current_user
from ...api.schemas import (
    DailyProgressListResponse,
    DailyProgressResponse,
    DashboardSummaryResponse,
    GamificationSnapshotResponse,
    NextBestActionOut,
    NextBestActionsResponse,
    RecordStudyMinutesRequest,
)
from ...db.gamification import append_event, award_xp_for_event
from ...db.models import (
    DailyProgress,
    LevelDefinition,
    LearningRecommendation,
    LearningSession,
    PlannerTask,
    SpacedReview,
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


def _subject_label(subject: str | None) -> str:
    if not subject:
        return "your subject"
    return subject.strip().capitalize()


def _recommendation_route(rec_type: str | None, subject: str | None) -> str:
    kind = (rec_type or "").strip().lower()
    sub = (subject or "").strip().lower()

    if kind in {"lesson", "new_learning"}:
        return f"/subject/{sub}" if sub else "/books"
    if kind == "mini_set":
        return "/mini-set"
    if kind in {"stamina", "stamina_drill"}:
        return "/exam/stamina"
    if kind == "quiz":
        return f"/subject/{sub}/quiz" if sub else "/learn-sessions"
    if kind in {"revision", "spaced_review"}:
        return "/study-plan"
    if kind in {"daily_plan_task", "planner", "routine"}:
        return "/study-plan"
    return "/learn-sessions"


def _target_minutes(user: User) -> int:
    if user.daily_study_target_hours and user.daily_study_target_hours > 0:
        return int(user.daily_study_target_hours * 60)
    if user.daily_study_target and user.daily_study_target > 0:
        return int(user.daily_study_target * 60)
    return 240


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


@router.get(
    "/next-actions",
    response_model=NextBestActionsResponse,
    summary="Dynamic next best actions for Home dashboard",
)
async def get_next_best_actions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.utcnow()
    today = date.today()

    progress_result = await db.execute(
        select(DailyProgress).where(
            DailyProgress.user_id == user.id,
            DailyProgress.date == today,
        )
    )
    today_progress = progress_result.scalar_one_or_none()
    studied_minutes_today = today_progress.study_minutes if today_progress else 0

    active_session_result = await db.execute(
        select(LearningSession)
        .where(
            LearningSession.user_id == user.id,
            LearningSession.ended_at.is_(None),
        )
        .order_by(LearningSession.started_at.desc())
        .limit(1)
    )
    active_session = active_session_result.scalar_one_or_none()

    latest_session_result = await db.execute(
        select(LearningSession)
        .where(LearningSession.user_id == user.id)
        .order_by(LearningSession.started_at.desc())
        .limit(1)
    )
    latest_session = latest_session_result.scalar_one_or_none()

    due_reviews_count_result = await db.execute(
        select(func.count())
        .select_from(SpacedReview)
        .where(
            SpacedReview.user_id == user.id,
            SpacedReview.status == "active",
            SpacedReview.due_at <= now,
        )
    )
    due_reviews_count = int(due_reviews_count_result.scalar() or 0)

    next_due_review_result = await db.execute(
        select(SpacedReview)
        .where(
            SpacedReview.user_id == user.id,
            SpacedReview.status == "active",
            SpacedReview.due_at <= now,
        )
        .order_by(SpacedReview.due_at.asc())
        .limit(1)
    )
    next_due_review = next_due_review_result.scalar_one_or_none()

    planner_result = await db.execute(
        select(
            func.count().label("pending_count"),
            func.coalesce(func.sum(PlannerTask.recommended_minutes), 0).label("pending_minutes"),
        ).where(
            PlannerTask.user_id == user.id,
            PlannerTask.task_date == today,
            PlannerTask.status == "pending",
        )
    )
    planner_row = planner_result.one()
    pending_today_count = int(planner_row.pending_count or 0)
    pending_today_minutes = int(planner_row.pending_minutes or 0)

    recommendation_result = await db.execute(
        select(LearningRecommendation)
        .where(
            LearningRecommendation.user_id == user.id,
            LearningRecommendation.status == "active",
        )
        .order_by(
            LearningRecommendation.priority_score.desc(),
            LearningRecommendation.generated_at.desc(),
        )
        .limit(1)
    )
    top_recommendation = recommendation_result.scalar_one_or_none()

    actions: list[NextBestActionOut] = []

    if active_session:
        subject = _subject_label(active_session.subject)
        actions.append(
            NextBestActionOut(
                key="continue_learning",
                title="Continue Learning",
                description=f"Resume your active {subject} session and keep your momentum.",
                cta_label="Resume Session",
                cta_route="/learn-sessions",
                accent="accent",
                action_kind="learning",
                priority=100,
                metric_label="Status",
                metric_value="In progress",
            )
        )
    elif latest_session:
        subject = _subject_label(latest_session.subject)
        actions.append(
            NextBestActionOut(
                key="continue_learning",
                title="Continue Learning",
                description=f"Pick up from your latest {subject} session in one click.",
                cta_label="Resume Chapter",
                cta_route="/learn-sessions",
                accent="accent",
                action_kind="learning",
                priority=95,
                metric_label="Last subject",
                metric_value=subject,
            )
        )
    else:
        actions.append(
            NextBestActionOut(
                key="continue_learning",
                title="Continue Learning",
                description="Start a focused chapter now and build your daily streak.",
                cta_label="Start Learning",
                cta_route="/books",
                accent="accent",
                action_kind="learning",
                priority=85,
            )
        )

    if due_reviews_count > 0:
        minutes = max(10, min(30, due_reviews_count * 5))
        if next_due_review and next_due_review.topic:
            due_desc = (
                f"{due_reviews_count} review items are due. Start with {next_due_review.topic} "
                f"({_subject_label(next_due_review.subject)})."
            )
        else:
            due_desc = f"{due_reviews_count} review items are due. Complete a short revision sprint now."

        actions.append(
            NextBestActionOut(
                key="smart_revision",
                title="Smart Revision",
                description=due_desc,
                cta_label=f"Revise {minutes} Minutes",
                cta_route="/study-plan",
                accent="purple",
                action_kind="revision",
                priority=90,
                metric_label="Due now",
                metric_value=str(due_reviews_count),
            )
        )
    elif top_recommendation and (top_recommendation.rec_type or "").lower() in {
        "revision",
        "mini_set",
        "quiz",
        "spaced_review",
    }:
        actions.append(
            NextBestActionOut(
                key="smart_revision",
                title="Smart Revision",
                description=top_recommendation.reason,
                cta_label="Start Practice",
                cta_route=_recommendation_route(top_recommendation.rec_type, top_recommendation.subject),
                accent="purple",
                action_kind="revision",
                priority=80,
                metric_label="Focus",
                metric_value=_subject_label(top_recommendation.subject),
            )
        )
    else:
        actions.append(
            NextBestActionOut(
                key="smart_revision",
                title="Smart Revision",
                description="Take a short weak-area quiz to improve retention consistency.",
                cta_label="Revise 15 Minutes",
                cta_route="/study-plan",
                accent="purple",
                action_kind="revision",
                priority=70,
            )
        )

    target_minutes = _target_minutes(user)
    remaining_minutes = max(0, target_minutes - studied_minutes_today)

    if pending_today_count > 0:
        actions.append(
            NextBestActionOut(
                key="plan_ahead",
                title="Plan Ahead",
                description=(
                    f"You still have {pending_today_count} planned tasks pending today "
                    f"(~{pending_today_minutes} min)."
                ),
                cta_label="Open Study Plan",
                cta_route="/study-plan",
                accent="amber",
                action_kind="planning",
                priority=85,
                metric_label="Pending",
                metric_value=str(pending_today_count),
            )
        )
    elif top_recommendation and (top_recommendation.rec_type or "").lower() in {
        "daily_plan_task",
        "planner",
        "routine",
    }:
        actions.append(
            NextBestActionOut(
                key="plan_ahead",
                title="Plan Ahead",
                description=top_recommendation.reason,
                cta_label="Open Study Plan",
                cta_route=_recommendation_route(top_recommendation.rec_type, top_recommendation.subject),
                accent="amber",
                action_kind="planning",
                priority=75,
            )
        )
    else:
        if remaining_minutes > 0:
            description = f"Block {remaining_minutes} more minutes to hit today's study target."
        else:
            description = "You are on pace today. Schedule your first deep-focus block for tomorrow."
        actions.append(
            NextBestActionOut(
                key="plan_ahead",
                title="Plan Ahead",
                description=description,
                cta_label="Open Study Plan",
                cta_route="/study-plan",
                accent="amber",
                action_kind="planning",
                priority=65,
            )
        )

    return NextBestActionsResponse(
        generated_at=now.isoformat(),
        actions=actions,
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
