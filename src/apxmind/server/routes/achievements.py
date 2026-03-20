"""
Achievements Router
====================

Badge catalog + earned badges (blueprint §5.5).

GET /api/achievements             — full catalog with earned status
GET /api/achievements/earned      — only earned badges
GET /api/achievements/{badge_id}  — single badge detail + earned status
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.middleware.auth import get_current_user
from ...api.schemas import AchievementsResponse, BadgeOut
from ...db.models import BadgeDefinition, User, UserBadge
from ...db.session import get_db

logger = logging.getLogger(__name__)
router = APIRouter()


def _badge_to_out(
    badge: BadgeDefinition,
    earned_map: dict,
) -> BadgeOut:
    ub = earned_map.get(badge.id)
    return BadgeOut(
        id=badge.id,
        name=badge.name,
        description=badge.description,
        icon=badge.icon,
        criteria=badge.criteria or {},
        earned=ub is not None,
        earned_at=ub.earned_at.isoformat() if ub else None,
    )


@router.get("", response_model=AchievementsResponse)
async def get_achievements(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return all badges with earned status for the current user."""
    badges_result = await db.execute(select(BadgeDefinition))
    all_badges = badges_result.scalars().all()

    earned_result = await db.execute(
        select(UserBadge).where(UserBadge.user_id == user.id)
    )
    earned_map = {ub.badge_id: ub for ub in earned_result.scalars().all()}

    badge_list = [_badge_to_out(b, earned_map) for b in all_badges]
    earned_count = sum(1 for b in badge_list if b.earned)

    return AchievementsResponse(
        badges=badge_list,
        earned_count=earned_count,
        total_count=len(badge_list),
    )


@router.get("/earned", response_model=AchievementsResponse)
async def get_earned_badges(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return only the badges the user has earned."""
    earned_result = await db.execute(
        select(UserBadge).where(UserBadge.user_id == user.id)
    )
    user_badges = earned_result.scalars().all()
    if not user_badges:
        return AchievementsResponse(badges=[], earned_count=0, total_count=0)

    badge_ids = [ub.badge_id for ub in user_badges]
    earned_map = {ub.badge_id: ub for ub in user_badges}

    badges_result = await db.execute(
        select(BadgeDefinition).where(BadgeDefinition.id.in_(badge_ids))
    )
    badges = badges_result.scalars().all()

    badge_list = [_badge_to_out(b, earned_map) for b in badges]
    return AchievementsResponse(
        badges=badge_list,
        earned_count=len(badge_list),
        total_count=len(badge_list),
    )


@router.get("/{badge_id}", response_model=BadgeOut)
async def get_badge_detail(
    badge_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return a single badge with earned status for the current user."""
    result = await db.execute(
        select(BadgeDefinition).where(BadgeDefinition.id == badge_id)
    )
    badge = result.scalar_one_or_none()
    if not badge:
        raise HTTPException(status_code=404, detail="Badge not found")

    earned_result = await db.execute(
        select(UserBadge).where(
            UserBadge.user_id == user.id,
            UserBadge.badge_id == badge_id,
        )
    )
    ub = earned_result.scalar_one_or_none()

    return BadgeOut(
        id=badge.id,
        name=badge.name,
        description=badge.description,
        icon=badge.icon,
        criteria=badge.criteria or {},
        earned=ub is not None,
        earned_at=ub.earned_at.isoformat() if ub else None,
    )
