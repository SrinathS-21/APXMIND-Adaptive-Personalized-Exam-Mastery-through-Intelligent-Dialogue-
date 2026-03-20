"""
Learning Recommendations Router
================================

GET    /api/recommendations            — list recommendations (filterable by status/subject)
PATCH  /api/recommendations/{id}       — update status (accepted | dismissed | completed)
DELETE /api/recommendations/{id}       — delete one
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.middleware.auth import get_current_user
from ...api.schemas import (
    RecommendationOut,
    RecommendationsListResponse,
    UpdateRecommendationRequest,
)
from ...db.models import LearningRecommendation, User
from ...db.session import get_db

logger = logging.getLogger(__name__)
router = APIRouter()


def _to_out(r: LearningRecommendation) -> RecommendationOut:
    return RecommendationOut(
        id=r.id,
        rec_type=r.rec_type,
        subject=r.subject,
        topic=r.topic,
        title=r.title,
        reason=r.reason,
        priority_score=float(r.priority_score),
        status=r.status,
        generated_at=r.generated_at.isoformat(),
        expires_at=r.expires_at.isoformat() if r.expires_at else None,
    )


@router.get("", response_model=RecommendationsListResponse, summary="List recommendations")
async def list_recommendations(
    status: str = Query(default="active", description="Filter by status"),
    subject: str = Query(default=None),
    limit: int = Query(default=10, ge=1, le=50),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(LearningRecommendation)
        .where(LearningRecommendation.user_id == user.id)
        .order_by(LearningRecommendation.priority_score.desc())
        .limit(limit)
    )
    if status:
        stmt = stmt.where(LearningRecommendation.status == status)
    if subject:
        stmt = stmt.where(LearningRecommendation.subject == subject)

    result = await db.execute(stmt)
    recs = result.scalars().all()
    return RecommendationsListResponse(
        recommendations=[_to_out(r) for r in recs],
        total=len(recs),
    )


@router.patch("/{rec_id}", response_model=RecommendationOut, summary="Update recommendation status")
async def update_recommendation(
    rec_id: int,
    request: UpdateRecommendationRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(LearningRecommendation).where(
            LearningRecommendation.id == rec_id,
            LearningRecommendation.user_id == user.id,
        )
    )
    rec = result.scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    rec.status = request.status
    await db.commit()
    await db.refresh(rec)
    return _to_out(rec)


@router.delete("/{rec_id}", status_code=204, summary="Delete recommendation")
async def delete_recommendation(
    rec_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(LearningRecommendation).where(
            LearningRecommendation.id == rec_id,
            LearningRecommendation.user_id == user.id,
        )
    )
    rec = result.scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    await db.delete(rec)
    await db.commit()
