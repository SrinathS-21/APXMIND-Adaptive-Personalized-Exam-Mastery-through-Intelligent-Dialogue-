"""
Adaptive Planner Router
=======================

Planner generation and execution tracking APIs.

GET   /api/planner/daily
POST  /api/planner/generate
PATCH /api/planner/tasks/{task_id}
"""

from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.middleware.auth import get_current_user
from ...api.schemas import (
    GenerateDailyPlanRequest,
    GenerateDailyPlanResponse,
    PlannerDailyResponse,
    PlannerTaskOut,
    StrategistPlanRequest,
    UpdatePlannerTaskRequest,
    UpdatePlannerTaskResponse,
)
from ...core.strategist import build_daily_plan, compute_available_minutes
from ...db.gamification import append_event
from ...db.models import PlannerTask, User
from ...db.session import get_db

router = APIRouter()


def _parse_date_or_400(value: str | None) -> date:
    if not value:
        return date.today()
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid date format, expected YYYY-MM-DD") from exc


def _to_task_out(task: PlannerTask) -> PlannerTaskOut:
    return PlannerTaskOut(
        id=task.id,
        task_date=task.task_date.isoformat(),
        task_type=task.task_type,
        subject=task.subject,
        topic=task.topic,
        recommended_minutes=task.recommended_minutes,
        priority_score=float(task.priority_score),
        status=task.status,
        completed_at=task.completed_at.isoformat() if task.completed_at else None,
        created_at=task.created_at.isoformat(),
        updated_at=task.updated_at.isoformat(),
    )


@router.post("/generate", response_model=GenerateDailyPlanResponse)
async def generate_daily_plan(
    request: GenerateDailyPlanRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    target_date = _parse_date_or_400(request.date)
    created_tasks, planned_minutes = await build_daily_plan(
        db,
        user,
        target_date,
        request.available_minutes,
        source="planner",
    )

    await db.commit()

    return GenerateDailyPlanResponse(
        date=target_date.isoformat(),
        generated_count=len(created_tasks),
        available_minutes=request.available_minutes,
        planned_minutes=planned_minutes,
        tasks=[_to_task_out(task) for task in created_tasks],
    )


@router.post("/strategist", response_model=GenerateDailyPlanResponse)
async def run_strategist_plan(
    request: StrategistPlanRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    target_date = _parse_date_or_400(request.date)
    available_minutes = compute_available_minutes(user)

    created_tasks, planned_minutes = await build_daily_plan(
        db,
        user,
        target_date,
        available_minutes,
        source="strategist",
    )

    await db.commit()

    return GenerateDailyPlanResponse(
        date=target_date.isoformat(),
        generated_count=len(created_tasks),
        available_minutes=available_minutes,
        planned_minutes=planned_minutes,
        tasks=[_to_task_out(task) for task in created_tasks],
    )


@router.get("/daily", response_model=PlannerDailyResponse)
async def get_daily_plan(
    plan_date: str | None = Query(default=None, alias="date"),
    autogenerate: bool = Query(default=True),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    target_date = _parse_date_or_400(plan_date)

    tasks_result = await db.execute(
        select(PlannerTask)
        .where(
            PlannerTask.user_id == user.id,
            PlannerTask.task_date == target_date,
        )
        .order_by(PlannerTask.priority_score.desc(), PlannerTask.created_at.asc())
    )
    tasks = tasks_result.scalars().all()

    # Ensure students always have a plan for today/future unless explicitly disabled.
    if autogenerate and not tasks and target_date >= date.today():
        available_minutes = compute_available_minutes(user)
        tasks, _ = await build_daily_plan(
            db,
            user,
            target_date,
            available_minutes,
            source="strategist_auto",
        )
        await db.commit()

    completed_count = sum(1 for task in tasks if task.status == "completed")
    skipped_count = sum(1 for task in tasks if task.status == "skipped")
    pending_count = sum(1 for task in tasks if task.status == "pending")
    day_closed = completed_count + skipped_count
    day_adherence = round((completed_count / day_closed) * 100, 2) if day_closed else 0.0

    weekly_since = target_date - timedelta(days=6)
    weekly_counts_result = await db.execute(
        select(PlannerTask.status, func.count())
        .where(
            PlannerTask.user_id == user.id,
            PlannerTask.task_date >= weekly_since,
            PlannerTask.task_date <= target_date,
        )
        .group_by(PlannerTask.status)
    )
    weekly_counts = {status: count for status, count in weekly_counts_result.all()}
    weekly_completed = int(weekly_counts.get("completed", 0))
    weekly_skipped = int(weekly_counts.get("skipped", 0))
    weekly_closed = weekly_completed + weekly_skipped
    weekly_adherence = round((weekly_completed / weekly_closed) * 100, 2) if weekly_closed else 0.0

    return PlannerDailyResponse(
        date=target_date.isoformat(),
        total=len(tasks),
        planned_minutes=sum(task.recommended_minutes for task in tasks),
        completed_count=completed_count,
        skipped_count=skipped_count,
        pending_count=pending_count,
        day_adherence_percent=day_adherence,
        weekly_adherence_percent=weekly_adherence,
        tasks=[_to_task_out(task) for task in tasks],
    )


@router.patch("/tasks/{task_id}", response_model=UpdatePlannerTaskResponse)
async def update_planner_task(
    task_id: str,
    request: UpdatePlannerTaskRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task_result = await db.execute(
        select(PlannerTask).where(
            PlannerTask.id == task_id,
            PlannerTask.user_id == user.id,
        )
    )
    task = task_result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Planner task not found")

    now = datetime.utcnow()
    task.status = request.status
    task.updated_at = now
    task.completed_at = now if request.status == "completed" else None

    rescheduled_task = None
    if request.status == "completed":
        await append_event(
            db,
            user_id=user.id,
            event_type="planner_task_completed",
            subject=task.subject,
            entity_type="planner_task",
            entity_id=task.id,
            event_value=float(task.recommended_minutes),
            payload={
                "task_type": task.task_type,
                "task_date": task.task_date.isoformat(),
                "topic": task.topic,
            },
        )
    elif request.status == "skipped":
        await append_event(
            db,
            user_id=user.id,
            event_type="planner_task_skipped",
            subject=task.subject,
            entity_type="planner_task",
            entity_id=task.id,
            payload={
                "task_type": task.task_type,
                "task_date": task.task_date.isoformat(),
                "topic": task.topic,
            },
        )

        next_date = task.task_date + timedelta(days=1)
        existing_result = await db.execute(
            select(PlannerTask).where(
                PlannerTask.user_id == user.id,
                PlannerTask.task_date == next_date,
                PlannerTask.task_type == task.task_type,
                PlannerTask.subject == task.subject,
                PlannerTask.topic == task.topic,
                PlannerTask.status == "pending",
            )
        )
        existing = existing_result.scalar_one_or_none()
        if not existing:
            rescheduled_task = PlannerTask(
                user_id=user.id,
                task_date=next_date,
                task_type=task.task_type,
                subject=task.subject,
                topic=task.topic,
                recommended_minutes=task.recommended_minutes,
                priority_score=float(task.priority_score) + 5.0,
                status="pending",
                source_recommendation_id=task.source_recommendation_id,
            )
            db.add(rescheduled_task)
            await db.flush()

    await db.commit()
    await db.refresh(task)
    if rescheduled_task is not None:
        await db.refresh(rescheduled_task)

    return UpdatePlannerTaskResponse(
        task=_to_task_out(task),
        rescheduled_task=_to_task_out(rescheduled_task) if rescheduled_task else None,
    )