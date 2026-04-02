"""
Exam Router
===========

Timed stamina drill APIs.

POST /api/exam/stamina/sessions
POST /api/exam/stamina/sessions/{session_id}/finish
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.middleware.auth import get_current_user
from ...api.schemas import (
    FinishStaminaSessionRequest,
    FinishStaminaSessionResponse,
    StartStaminaSessionRequest,
    StartStaminaSessionResponse,
    StaminaBlockPlanOut,
)
from ...db.gamification import append_event, award_xp_for_event
from ...db.models import ExamStaminaSession, User
from ...db.session import get_db

router = APIRouter()


def _build_block_plan(duration_minutes: int, planned_questions: int, block_count: int) -> list[dict]:
    plan: list[dict] = []
    base_minutes = duration_minutes // block_count
    minute_remainder = duration_minutes % block_count
    base_questions = planned_questions // block_count
    question_remainder = planned_questions % block_count

    for idx in range(block_count):
        plan.append(
            {
                "block_no": idx + 1,
                "planned_minutes": base_minutes + (1 if idx < minute_remainder else 0),
                "planned_questions": base_questions + (1 if idx < question_remainder else 0),
            }
        )

    return plan


def _accuracy(attempted_questions: int, correct_answers: int) -> float:
    if attempted_questions <= 0:
        return 0.0
    return round((correct_answers / attempted_questions) * 100.0, 2)


@router.post("/stamina/sessions", response_model=StartStaminaSessionResponse)
async def start_stamina_session(
    request: StartStaminaSessionRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if request.mode == "subject" and request.subject is None:
        raise HTTPException(status_code=400, detail="subject is required when mode=subject")

    block_plan = _build_block_plan(
        duration_minutes=request.duration_minutes,
        planned_questions=request.planned_questions,
        block_count=request.block_count,
    )

    session = ExamStaminaSession(
        user_id=user.id,
        mode=request.mode,
        subject=request.subject.value if request.subject else None,
        topic=request.topic,
        planned_duration_minutes=request.duration_minutes,
        planned_questions=request.planned_questions,
        block_count=request.block_count,
        block_plan=block_plan,
        status="active",
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    return StartStaminaSessionResponse(
        session_id=session.id,
        mode=session.mode,
        subject=session.subject,
        topic=session.topic,
        duration_minutes=session.planned_duration_minutes,
        planned_questions=session.planned_questions,
        started_at=session.started_at.isoformat(),
        block_plan=[StaminaBlockPlanOut(**row) for row in (session.block_plan or [])],
    )


@router.post("/stamina/sessions/{session_id}/finish", response_model=FinishStaminaSessionResponse)
async def finish_stamina_session(
    session_id: str,
    request: FinishStaminaSessionRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ExamStaminaSession).where(
            ExamStaminaSession.id == session_id,
            ExamStaminaSession.user_id == user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Stamina session not found")
    if session.status != "active":
        raise HTTPException(status_code=400, detail="Stamina session already closed")
    if not request.block_results:
        raise HTTPException(status_code=400, detail="block_results must be a non-empty list")

    total_questions = 0
    correct_answers = 0
    time_taken_sec = 0
    block_accuracies: list[float] = []
    error_clusters: dict[str, int] = {}

    for row in request.block_results:
        if row.correct_answers > row.attempted_questions:
            raise HTTPException(status_code=400, detail=f"block {row.block_no} has correct_answers > attempted_questions")

        total_questions += row.attempted_questions
        correct_answers += row.correct_answers
        time_taken_sec += row.elapsed_sec

        block_accuracy = _accuracy(row.attempted_questions, row.correct_answers)
        block_accuracies.append(block_accuracy)

        mistake_count = max(0, row.attempted_questions - row.correct_answers)
        if mistake_count > 0:
            key = row.dominant_error or "other"
            error_clusters[key] = error_clusters.get(key, 0) + mistake_count

    score_percent = _accuracy(total_questions, correct_answers)
    pacing_qph = round((total_questions / (time_taken_sec / 3600.0)), 2) if time_taken_sec > 0 else 0.0

    fatigue_accuracy_dip = 0.0
    fatigue_detected = False
    if len(block_accuracies) >= 2:
        split_idx = max(1, len(block_accuracies) // 2)
        early_slice = block_accuracies[:split_idx]
        late_slice = block_accuracies[split_idx:]
        if late_slice:
            early_avg = sum(early_slice) / len(early_slice)
            late_avg = sum(late_slice) / len(late_slice)
            fatigue_accuracy_dip = round(max(0.0, early_avg - late_avg), 2)
            fatigue_detected = fatigue_accuracy_dip >= 8.0

    now = datetime.utcnow()
    session.ended_at = now
    session.status = "completed"
    session.performance_summary = {
        "total_questions": total_questions,
        "correct_answers": correct_answers,
        "score_percent": score_percent,
        "time_taken_sec": time_taken_sec,
        "pacing_qph": pacing_qph,
        "fatigue_accuracy_dip": fatigue_accuracy_dip,
        "fatigue_detected": fatigue_detected,
        "error_clusters": error_clusters,
        "notes": request.notes,
    }
    session.updated_at = now

    await append_event(
        db,
        user_id=user.id,
        event_type="stamina_drill_completed",
        subject=session.subject,
        entity_type="stamina_session",
        entity_id=session.id,
        event_value=score_percent,
        payload={
            "mode": session.mode,
            "topic": session.topic,
            "planned_duration_minutes": session.planned_duration_minutes,
            "planned_questions": session.planned_questions,
            "total_questions": total_questions,
            "correct_answers": correct_answers,
            "score_percent": score_percent,
            "time_taken_sec": time_taken_sec,
            "pacing_qph": pacing_qph,
            "fatigue_accuracy_dip": fatigue_accuracy_dip,
            "fatigue_detected": fatigue_detected,
            "error_clusters": error_clusters,
        },
    )

    xp_awarded = await award_xp_for_event(
        db,
        user_id=user.id,
        event_type="study_session_recorded",
        subject=session.subject,
        minutes=max(1, round(time_taken_sec / 60)) if time_taken_sec > 0 else 1,
    )

    await db.commit()

    return FinishStaminaSessionResponse(
        session_id=session.id,
        completed_at=now.isoformat(),
        total_questions=total_questions,
        correct_answers=correct_answers,
        score_percent=score_percent,
        pacing_qph=pacing_qph,
        fatigue_accuracy_dip=fatigue_accuracy_dip,
        fatigue_detected=fatigue_detected,
        error_clusters=error_clusters,
        xp_awarded=xp_awarded,
    )
