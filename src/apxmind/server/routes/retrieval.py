"""
Retrieval Router
================

Offline-first retrieval and spaced revision flows.

POST /api/retrieval/lesson-recall
GET  /api/retrieval/spaced-queue
POST /api/retrieval/spaced-queue/{review_id}/complete
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.middleware.auth import get_current_user
from ...api.schemas import (
    CompleteSpacedReviewRequest,
    CompleteSpacedReviewResponse,
    LessonRecallRequest,
    LessonRecallResponse,
    SpacedQueueResponse,
    SpacedReviewItemOut,
)
from ...db.gamification import append_event
from ...db.models import SpacedReview, TopicMastery, User
from ...db.session import get_db

router = APIRouter()

_INTERVAL_SEQUENCE = [1, 3, 7, 14, 21, 30, 45]


def _parse_due_before(raw_value: str) -> datetime:
    value = (raw_value or "").strip()
    if not value:
        raise ValueError("empty due_before")

    normalized = value
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"

    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def _score_band(score: int) -> str:
    if score >= 80:
        return "Strong"
    if score >= 50:
        return "Needs Review"
    return "Retry"


def _build_gaps(score: int) -> list[str]:
    if score >= 80:
        return []
    if score >= 50:
        return [
            "Revisit key definitions and one worked example.",
            "Do one memory-only recap before next session.",
        ]
    return [
        "Relearn core concept from summary notes.",
        "Attempt a short recall again in 24 hours.",
    ]


def _next_interval(current_step: int, result: str) -> int:
    if result == "incorrect":
        return 1
    if result == "partial":
        return current_step
    try:
        idx = _INTERVAL_SEQUENCE.index(current_step)
    except ValueError:
        return 3
    return _INTERVAL_SEQUENCE[min(idx + 1, len(_INTERVAL_SEQUENCE) - 1)]


async def _upsert_topic_mastery(
    db: AsyncSession,
    user_id: int,
    subject: str | None,
    topic: str | None,
    observed_score: float,
    confidence: float,
):
    if not subject:
        return

    topic_key = (topic or "").strip() or "general"
    now = datetime.utcnow()
    result = await db.execute(
        select(TopicMastery).where(
            TopicMastery.user_id == user_id,
            TopicMastery.subject == subject,
            TopicMastery.topic == topic_key,
        )
    )
    row = result.scalar_one_or_none()

    if row:
        row.mastery_score = round(float(row.mastery_score) * 0.7 + observed_score * 0.3, 2)
        row.confidence = round(float(row.confidence) * 0.6 + confidence * 0.4, 2)
        row.last_assessed_at = now
        return

    db.add(
        TopicMastery(
            user_id=user_id,
            subject=subject,
            topic=topic_key,
            mastery_score=round(observed_score, 2),
            confidence=round(confidence, 2),
            last_assessed_at=now,
        )
    )


@router.post("/lesson-recall", response_model=LessonRecallResponse)
async def submit_lesson_recall(
    request: LessonRecallRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.utcnow()
    topic_key = request.topic.strip()
    source_id = str(request.lesson_id) if request.lesson_id is not None else topic_key.lower()

    result = await db.execute(
        select(SpacedReview).where(
            SpacedReview.user_id == user.id,
            SpacedReview.source_type == "lesson_recall",
            SpacedReview.source_id == source_id,
        )
    )
    review = result.scalar_one_or_none()

    if review:
        review.topic = topic_key
        review.subject = request.subject.value if request.subject else review.subject
        review.interval_step = 1
        review.due_at = now + timedelta(days=1)
        review.last_result = "correct" if request.self_score >= 80 else "partial"
        review.status = "active"
        review.updated_at = now
    else:
        review = SpacedReview(
            user_id=user.id,
            topic=topic_key,
            subject=request.subject.value if request.subject else None,
            source_type="lesson_recall",
            source_id=source_id,
            interval_step=1,
            due_at=now + timedelta(days=1),
            last_result="correct" if request.self_score >= 80 else "partial",
            status="active",
        )
        db.add(review)
        await db.flush()

    await append_event(
        db,
        user_id=user.id,
        event_type="recall_completed",
        subject=request.subject.value if request.subject else None,
        entity_type="lesson_recall",
        entity_id=review.id,
        event_value=float(request.self_score),
        payload={
            "topic": topic_key,
            "lesson_id": request.lesson_id,
            "time_taken_sec": request.time_taken_sec,
            "self_score": request.self_score,
        },
    )

    await _upsert_topic_mastery(
        db,
        user_id=user.id,
        subject=request.subject.value if request.subject else None,
        topic=topic_key,
        observed_score=float(request.self_score),
        confidence=max(20.0, float(request.self_score) * 0.9),
    )

    await db.commit()

    return LessonRecallResponse(
        score_band=_score_band(request.self_score),
        next_review_due=review.due_at.isoformat(),
        spaced_review_id=review.id,
        gaps=_build_gaps(request.self_score),
    )


@router.get("/spaced-queue", response_model=SpacedQueueResponse)
async def get_spaced_queue(
    limit: int = Query(default=50, ge=1, le=200),
    due_before: str | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cutoff = datetime.utcnow()
    if due_before:
        try:
            cutoff = _parse_due_before(due_before)
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail="Invalid due_before datetime. Use ISO 8601, e.g. 2026-04-12T23:59:59Z",
            ) from exc

    result = await db.execute(
        select(SpacedReview)
        .where(
            SpacedReview.user_id == user.id,
            SpacedReview.status == "active",
            SpacedReview.due_at <= cutoff,
        )
        .order_by(SpacedReview.due_at.asc())
        .limit(limit)
    )
    rows = result.scalars().all()

    return SpacedQueueResponse(
        due_items=[
            SpacedReviewItemOut(
                id=row.id,
                topic=row.topic,
                subject=row.subject,
                source_type=row.source_type,
                source_id=row.source_id,
                interval_step=row.interval_step,
                due_at=row.due_at.isoformat(),
                last_result=row.last_result,
                streak=row.streak,
            )
            for row in rows
        ],
        total=len(rows),
    )


@router.post("/spaced-queue/{review_id}/complete", response_model=CompleteSpacedReviewResponse)
async def complete_spaced_review(
    review_id: str,
    request: CompleteSpacedReviewRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SpacedReview).where(
            SpacedReview.id == review_id,
            SpacedReview.user_id == user.id,
        )
    )
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="Spaced review item not found")

    now = datetime.utcnow()
    next_step = _next_interval(review.interval_step, request.result)
    review.interval_step = next_step
    review.last_result = request.result
    review.last_reviewed_at = now
    review.streak = review.streak + 1 if request.result == "correct" else 0
    review.due_at = now + timedelta(days=next_step)
    review.updated_at = now

    await append_event(
        db,
        user_id=user.id,
        event_type="spaced_review_completed",
        subject=review.subject,
        entity_type="spaced_review",
        entity_id=review.id,
        payload={
            "result": request.result,
            "confidence_level": request.confidence_level,
            "topic": review.topic,
            "interval_step": next_step,
        },
    )

    result_score = {
        "correct": 85.0,
        "partial": 60.0,
        "incorrect": 30.0,
    }.get(request.result, 50.0)
    confidence_score = float(request.confidence_level * 20) if request.confidence_level else 50.0
    await _upsert_topic_mastery(
        db,
        user_id=user.id,
        subject=review.subject,
        topic=review.topic,
        observed_score=result_score,
        confidence=confidence_score,
    )

    await db.commit()

    return CompleteSpacedReviewResponse(
        review_id=review.id,
        interval_step=review.interval_step,
        next_due_at=review.due_at.isoformat(),
        streak=review.streak,
    )
