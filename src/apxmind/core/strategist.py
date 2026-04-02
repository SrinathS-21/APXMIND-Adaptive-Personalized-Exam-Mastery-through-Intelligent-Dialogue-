"""
Daily strategist planning utilities.

Creates adaptive plans based on mastery, spaced reviews, and error signals.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import List, Tuple

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.gamification import append_event
from ..db.models import (
    LearningRecommendation,
    MistakeCard,
    PlannerTask,
    SpacedReview,
    TopicMastery,
    User,
)


def compute_available_minutes(user: User, default_minutes: int = 120) -> int:
    if user.daily_study_target_hours is not None:
        minutes = int(float(user.daily_study_target_hours) * 60)
    elif user.daily_study_target is not None:
        minutes = int(user.daily_study_target) * 60
    else:
        minutes = default_minutes
    return max(30, min(960, minutes))


def _normalize_topic(topic: str | None) -> str | None:
    if not topic:
        return None
    normalized = topic.strip()
    return normalized or None


def _task_title(task_type: str, topic: str | None) -> str:
    if task_type == "revision":
        return f"Revision: {topic or 'Due items'}"
    if task_type == "mini_set":
        return f"Mixed mini-set: {topic or 'Cross-subject'}"
    if task_type == "stamina":
        return f"Stamina drill: {topic or 'Timed section'}"
    return f"Concept build: {topic or 'Weak area'}"


def _task_reason(task_type: str, priority_score: float) -> str:
    if task_type == "revision":
        return "Due now in your spaced revision queue."
    if task_type == "mini_set":
        return "Interleaved mixed practice to improve transfer."
    if task_type == "stamina":
        return "Timed practice to improve speed consistency."
    if priority_score >= 80:
        return "High-priority weak topic based on recent mastery."
    return "Personalized topic reinforcement."


async def select_plan_items(
    db: AsyncSession,
    user: User,
    target_date: date,
    available_minutes: int,
) -> Tuple[List[dict], datetime]:
    day_end = datetime.combine(target_date + timedelta(days=1), time.min)

    due_reviews_result = await db.execute(
        select(SpacedReview)
        .where(
            SpacedReview.user_id == user.id,
            SpacedReview.status == "active",
            SpacedReview.due_at <= day_end,
        )
        .order_by(SpacedReview.due_at.asc())
        .limit(8)
    )
    due_reviews = due_reviews_result.scalars().all()

    mistake_cards_result = await db.execute(
        select(MistakeCard)
        .where(
            MistakeCard.user_id == user.id,
            MistakeCard.status == "active",
        )
        .order_by(MistakeCard.next_due_at.asc(), MistakeCard.updated_at.desc())
        .limit(8)
    )
    mistake_cards = mistake_cards_result.scalars().all()

    weak_topics_result = await db.execute(
        select(TopicMastery)
        .where(TopicMastery.user_id == user.id)
        .order_by(TopicMastery.mastery_score.asc(), TopicMastery.last_assessed_at.asc())
        .limit(10)
    )
    weak_topics = weak_topics_result.scalars().all()

    candidates: list[dict] = []
    for item in due_reviews:
        candidates.append(
            {
                "task_type": "revision",
                "subject": item.subject,
                "topic": _normalize_topic(item.topic) or "Spaced review",
                "recommended_minutes": 15,
                "priority_score": 100.0,
            }
        )

    for card in mistake_cards:
        candidates.append(
            {
                "task_type": "revision",
                "subject": card.subject,
                "topic": _normalize_topic(card.topic) or "Error notebook",
                "recommended_minutes": 10,
                "priority_score": 90.0,
            }
        )

    for mastery in weak_topics:
        score = float(mastery.mastery_score)
        candidates.append(
            {
                "task_type": "new_learning" if score < 50 else "mini_set",
                "subject": mastery.subject,
                "topic": _normalize_topic(mastery.topic),
                "recommended_minutes": 20 if score < 50 else 15,
                "priority_score": max(55.0, 95.0 - score),
            }
        )

    candidates.append(
        {
            "task_type": "mini_set",
            "subject": None,
            "topic": "Daily mixed mini-set",
            "recommended_minutes": 15,
            "priority_score": 70.0,
        }
    )

    deduped: dict[tuple[str, str, str], dict] = {}
    for item in candidates:
        key = (
            item["task_type"],
            (item["subject"] or "").lower(),
            (item["topic"] or "").lower(),
        )
        current = deduped.get(key)
        if not current or item["priority_score"] > current["priority_score"]:
            deduped[key] = item

    selected: list[dict] = []
    remaining = max(30, min(960, available_minutes))
    for item in sorted(deduped.values(), key=lambda x: x["priority_score"], reverse=True):
        if remaining < 10:
            break
        minutes = min(item["recommended_minutes"], remaining)
        if minutes < 10:
            continue
        selected.append({**item, "recommended_minutes": minutes})
        remaining -= minutes

    if not selected:
        selected.append(
            {
                "task_type": "mini_set",
                "subject": None,
                "topic": "Daily mixed mini-set",
                "recommended_minutes": min(15, remaining or 15),
                "priority_score": 60.0,
            }
        )

    return selected, day_end


async def build_daily_plan(
    db: AsyncSession,
    user: User,
    target_date: date,
    available_minutes: int,
    *,
    source: str = "strategist",
) -> Tuple[List[PlannerTask], int]:
    selected, day_end = await select_plan_items(db, user, target_date, available_minutes)

    await db.execute(
        delete(PlannerTask).where(
            PlannerTask.user_id == user.id,
            PlannerTask.task_date == target_date,
            PlannerTask.status == "pending",
        )
    )

    created_tasks: list[PlannerTask] = []
    for item in selected:
        rec = LearningRecommendation(
            user_id=user.id,
            rec_type="daily_plan_task",
            subject=item["subject"],
            topic=item["topic"],
            title=_task_title(item["task_type"], item["topic"]),
            reason=_task_reason(item["task_type"], float(item["priority_score"])),
            priority_score=float(item["priority_score"]),
            status="active",
            expires_at=day_end,
        )
        db.add(rec)
        await db.flush()

        task = PlannerTask(
            user_id=user.id,
            task_date=target_date,
            task_type=item["task_type"],
            subject=item["subject"],
            topic=item["topic"],
            recommended_minutes=int(item["recommended_minutes"]),
            priority_score=float(item["priority_score"]),
            status="pending",
            source_recommendation_id=rec.id,
        )
        db.add(task)
        created_tasks.append(task)

    await db.flush()

    planned_minutes = sum(task.recommended_minutes for task in created_tasks)
    await append_event(
        db,
        user_id=user.id,
        event_type="planner_generated",
        entity_type="planner",
        entity_id=target_date.isoformat(),
        payload={
            "task_count": len(created_tasks),
            "available_minutes": available_minutes,
            "planned_minutes": planned_minutes,
            "source": source,
        },
    )

    return created_tasks, planned_minutes
