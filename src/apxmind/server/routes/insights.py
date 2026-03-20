"""
Insights Router
================

Topic mastery, exam readiness snapshots, and daily habit signals.

GET /api/insights/mastery              — all topic mastery (filterable by subject)
GET /api/insights/mastery/{subject}    — mastery for a single subject
GET /api/insights/readiness            — exam readiness snapshots (?days=30)
GET /api/insights/habits               — daily habit signals  (?days=7)
"""

import logging
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.middleware.auth import get_current_user
from ...api.schemas import (
    ExamReadinessListResponse,
    ExamReadinessOut,
    HabitSignalOut,
    HabitSignalsResponse,
    TopicMasteryListResponse,
    TopicMasteryOut,
)
from ...db.models import ExamReadinessSnapshot, HabitSignal, TopicMastery, User
from ...db.session import get_db

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Topic Mastery
# ---------------------------------------------------------------------------

def _mastery_to_out(r: TopicMastery) -> TopicMasteryOut:
    return TopicMasteryOut(
        subject=r.subject,
        topic=r.topic,
        mastery_score=float(r.mastery_score),
        confidence=float(r.confidence),
        last_assessed_at=r.last_assessed_at.isoformat() if r.last_assessed_at else None,
    )


@router.get("/mastery", response_model=TopicMasteryListResponse, summary="All topic mastery")
async def get_topic_mastery(
    subject: str = Query(default=None),
    min_score: float = Query(default=0.0, ge=0.0, le=100.0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return topic mastery scores, sorted highest first."""
    stmt = (
        select(TopicMastery)
        .where(TopicMastery.user_id == user.id)
        .order_by(TopicMastery.mastery_score.desc())
    )
    if subject:
        stmt = stmt.where(TopicMastery.subject == subject.lower())
    if min_score > 0:
        stmt = stmt.where(TopicMastery.mastery_score >= min_score)

    result = await db.execute(stmt)
    rows = result.scalars().all()
    return TopicMasteryListResponse(mastery=[_mastery_to_out(r) for r in rows], total=len(rows))


@router.get("/mastery/{subject}", response_model=TopicMasteryListResponse, summary="Subject topic mastery")
async def get_topic_mastery_by_subject(
    subject: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TopicMastery)
        .where(TopicMastery.user_id == user.id, TopicMastery.subject == subject.lower())
        .order_by(TopicMastery.mastery_score.desc())
    )
    rows = result.scalars().all()
    return TopicMasteryListResponse(mastery=[_mastery_to_out(r) for r in rows], total=len(rows))


# ---------------------------------------------------------------------------
# Exam Readiness
# ---------------------------------------------------------------------------

@router.get("/readiness", response_model=ExamReadinessListResponse, summary="Exam readiness snapshots")
async def get_readiness(
    days: int = Query(default=30, ge=1, le=365),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    since = date.today() - timedelta(days=days - 1)
    result = await db.execute(
        select(ExamReadinessSnapshot)
        .where(
            ExamReadinessSnapshot.user_id == user.id,
            ExamReadinessSnapshot.snapshot_date >= since,
        )
        .order_by(ExamReadinessSnapshot.snapshot_date.desc())
    )
    rows = result.scalars().all()

    def _row(r: ExamReadinessSnapshot) -> ExamReadinessOut:
        return ExamReadinessOut(
            snapshot_date=r.snapshot_date.isoformat(),
            projected_score=float(r.projected_score) if r.projected_score is not None else None,
            syllabus_coverage_percent=float(r.syllabus_coverage_percent) if r.syllabus_coverage_percent is not None else None,
            accuracy_percent=float(r.accuracy_percent) if r.accuracy_percent is not None else None,
            speed_qph=float(r.speed_qph) if r.speed_qph is not None else None,
            consistency_score=float(r.consistency_score) if r.consistency_score is not None else None,
            risk_band=r.risk_band,
        )

    snapshots = [_row(r) for r in rows]
    return ExamReadinessListResponse(
        latest=snapshots[0] if snapshots else None,
        history=snapshots,
    )


# ---------------------------------------------------------------------------
# Habit Signals
# ---------------------------------------------------------------------------

@router.get("/habits", response_model=HabitSignalsResponse, summary="Daily habit signals")
async def get_habits(
    days: int = Query(default=7, ge=1, le=90),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    since = date.today() - timedelta(days=days - 1)
    result = await db.execute(
        select(HabitSignal)
        .where(HabitSignal.user_id == user.id, HabitSignal.date >= since)
        .order_by(HabitSignal.date.desc())
    )
    rows = result.scalars().all()
    return HabitSignalsResponse(
        signals=[
            HabitSignalOut(
                date=r.date.isoformat(),
                session_count=r.session_count,
                deep_focus_minutes=r.deep_focus_minutes,
                interruptions_count=r.interruptions_count,
                first_activity_at=r.first_activity_at.isoformat() if r.first_activity_at else None,
                last_activity_at=r.last_activity_at.isoformat() if r.last_activity_at else None,
            )
            for r in rows
        ]
    )
