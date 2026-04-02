"""
Error Notebook Router
=====================

Mistake-card APIs for repeated-error reduction.

GET   /api/errors/mistake-cards
PATCH /api/errors/mistake-cards/{card_id}
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.middleware.auth import get_current_user
from ...api.schemas import (
    MistakeCardListResponse,
    MistakeCardOut,
    UpdateMistakeCardRequest,
    UpdateMistakeCardResponse,
)
from ...db.models import MistakeCard, User
from ...db.session import get_db

router = APIRouter()


def _to_out(card: MistakeCard) -> MistakeCardOut:
    return MistakeCardOut(
        id=card.id,
        subject=card.subject,
        topic=card.topic,
        source_type=card.source_type,
        source_id=card.source_id,
        error_reason_code=card.error_reason_code,
        prompt_snapshot=card.prompt_snapshot,
        correct_explanation=card.correct_explanation,
        times_seen=card.times_seen,
        times_repeated=card.times_repeated,
        last_seen_at=card.last_seen_at.isoformat(),
        next_due_at=card.next_due_at.isoformat() if card.next_due_at else None,
        status=card.status,
        created_at=card.created_at.isoformat(),
        updated_at=card.updated_at.isoformat(),
    )


@router.get("/mistake-cards", response_model=MistakeCardListResponse)
async def list_mistake_cards(
    status: str | None = Query(default=None, pattern=r"^(active|resolved)$"),
    subject: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(MistakeCard)
        .where(MistakeCard.user_id == user.id)
        .order_by(MistakeCard.next_due_at.asc(), MistakeCard.updated_at.desc())
        .limit(limit)
    )
    if status:
        stmt = stmt.where(MistakeCard.status == status)
    if subject:
        stmt = stmt.where(MistakeCard.subject == subject.lower())

    result = await db.execute(stmt)
    cards = result.scalars().all()
    return MistakeCardListResponse(cards=[_to_out(c) for c in cards], total=len(cards))


@router.patch("/mistake-cards/{card_id}", response_model=UpdateMistakeCardResponse)
async def update_mistake_card(
    card_id: str,
    request: UpdateMistakeCardRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MistakeCard).where(MistakeCard.id == card_id, MistakeCard.user_id == user.id)
    )
    card = result.scalar_one_or_none()
    if not card:
        raise HTTPException(status_code=404, detail="Mistake card not found")

    if request.status is not None:
        card.status = request.status
    if request.error_reason_code is not None:
        card.error_reason_code = request.error_reason_code
    if request.correct_explanation is not None:
        card.correct_explanation = request.correct_explanation
    if request.next_due_at is not None:
        try:
            card.next_due_at = datetime.fromisoformat(request.next_due_at)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid next_due_at datetime") from exc

    card.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(card)

    return UpdateMistakeCardResponse(card=_to_out(card))
