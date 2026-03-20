"""
Subjects Router
================

GET  /api/subjects                                         — list all NEET subjects
GET  /api/subjects/{subject}/lessons                      — get lessons for a subject
POST /api/subjects/{subject}/lessons/{lesson_id}/complete — mark lesson completed
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.middleware.auth import get_current_user
from ...api.schemas import (
    LessonListResponse,
    LessonResponse,
    SubjectListResponse,
    SubjectResponse,
)
from ...db.gamification import append_event, award_xp_for_event
from ...db.models import Lesson, Progress, Subject, User
from ...db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=SubjectListResponse, summary="List all subjects")
async def get_subjects(db: AsyncSession = Depends(get_db)):
    """Get all NEET subjects."""
    try:
        result = await db.execute(select(Subject))
        subjects = result.scalars().all()
        data = [
            SubjectResponse(
                id=s.id,
                name=s.name,
                display_name=s.display_name,
                description=s.description,
                icon=s.icon,
                color=s.color,
                total_lessons=s.total_lessons,
            )
            for s in subjects
        ]
        return SubjectListResponse(success=True, data=data, count=len(data))
    except Exception as e:
        logger.error(f"Error getting subjects: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{subject_name}/lessons",
    response_model=LessonListResponse,
    summary="Get lessons for a subject",
)
async def get_lessons(subject_name: str, db: AsyncSession = Depends(get_db)):
    """Get all lessons for a specific subject."""
    try:
        subject_name = subject_name.lower()

        result = await db.execute(select(Subject).where(Subject.name == subject_name))
        subject = result.scalar_one_or_none()
        if not subject:
            raise HTTPException(status_code=404, detail=f"Subject not found: {subject_name}")

        result = await db.execute(
            select(Lesson).where(Lesson.subject_id == subject.id).order_by(Lesson.order)
        )
        lessons = result.scalars().all()

        subject_resp = SubjectResponse(
            id=subject.id,
            name=subject.name,
            display_name=subject.display_name,
            description=subject.description,
            icon=subject.icon,
            color=subject.color,
            total_lessons=subject.total_lessons,
        )
        lesson_list = [
            LessonResponse(
                id=l.id,
                subject_id=l.subject_id,
                subject_name=subject.name,
                title=l.title,
                description=l.description,
                difficulty=l.difficulty,
                order=l.order,
                estimated_time=l.estimated_time,
                topics=l.topics or [],
            )
            for l in lessons
        ]
        return LessonListResponse(
            success=True, subject=subject_resp, lessons=lesson_list, count=len(lesson_list)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting lessons for {subject_name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# POST /api/subjects/{subject_name}/lessons/{lesson_id}/complete
# ---------------------------------------------------------------------------

@router.post(
    "/{subject_name}/lessons/{lesson_id}/complete",
    summary="Mark a lesson as completed",
)
async def complete_lesson(
    subject_name: str,
    lesson_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Record that the authenticated user completed a lesson; awards XP once."""
    subject_name = subject_name.lower()

    sub_result = await db.execute(select(Subject).where(Subject.name == subject_name))
    subject = sub_result.scalar_one_or_none()
    if not subject:
        raise HTTPException(status_code=404, detail=f"Subject not found: {subject_name}")

    les_result = await db.execute(
        select(Lesson).where(Lesson.id == lesson_id, Lesson.subject_id == subject.id)
    )
    lesson = les_result.scalar_one_or_none()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    idempotency_key = f"lesson_completed:{user.id}:{lesson_id}"
    event = await append_event(
        db,
        user_id=user.id,
        event_type="lesson_completed",
        subject=subject_name,
        entity_type="lesson",
        entity_id=str(lesson_id),
        idempotency_key=idempotency_key,
    )

    if event is None:
        return {"success": True, "message": "Already completed", "xp_awarded": 0}

    # Upsert progress row
    prog_result = await db.execute(
        select(Progress).where(
            Progress.user_id == user.id,
            Progress.lesson_id == lesson_id,
        )
    )
    prog = prog_result.scalar_one_or_none()
    if prog is None:
        prog = Progress(user_id=user.id, lesson_id=lesson_id, completed=True)
        db.add(prog)
    else:
        prog.completed = True

    xp = await award_xp_for_event(db, user.id, "lesson_completed", subject=subject_name)
    await db.commit()

    return {"success": True, "lesson_id": lesson_id, "xp_awarded": xp}
