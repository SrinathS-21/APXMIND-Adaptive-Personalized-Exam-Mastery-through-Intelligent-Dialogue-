"""
Profile Extensions Router
===========================

Subject preferences (blueprint §3.1 + §5.1).

GET    /api/profile/subjects                — list subject preferences
PUT    /api/profile/subjects/{subject}      — upsert preference
DELETE /api/profile/subjects/{subject}      — delete preference
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.middleware.auth import get_current_user
from ...api.schemas import (
    SubjectPreferenceOut,
    SubjectPreferenceRequest,
    SubjectPreferencesResponse,
)
from ...db.models import User, UserSubjectPreference
from ...db.session import get_db

logger = logging.getLogger(__name__)
router = APIRouter()

VALID_SUBJECTS = {"physics", "chemistry", "biology"}


def _pref_to_out(p: UserSubjectPreference) -> SubjectPreferenceOut:
    return SubjectPreferenceOut(
        subject=p.subject,
        strength=p.strength,
        priority_rank=p.priority_rank,
    )


@router.get("/subjects", response_model=SubjectPreferencesResponse)
async def get_subject_preferences(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserSubjectPreference)
        .where(UserSubjectPreference.user_id == user.id)
        .order_by(UserSubjectPreference.priority_rank.nullslast(), UserSubjectPreference.subject)
    )
    prefs = result.scalars().all()
    return SubjectPreferencesResponse(preferences=[_pref_to_out(p) for p in prefs])


@router.put("/subjects/{subject}", response_model=SubjectPreferenceOut)
async def upsert_subject_preference(
    subject: str = Path(..., description="physics | chemistry | biology"),
    request: SubjectPreferenceRequest = ...,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if subject not in VALID_SUBJECTS:
        raise HTTPException(status_code=400, detail=f"Subject must be one of {VALID_SUBJECTS}")

    result = await db.execute(
        select(UserSubjectPreference).where(
            UserSubjectPreference.user_id == user.id,
            UserSubjectPreference.subject == subject,
        )
    )
    pref = result.scalar_one_or_none()

    if pref:
        pref.strength = request.strength
        pref.priority_rank = request.priority_rank
    else:
        pref = UserSubjectPreference(
            user_id=user.id,
            subject=subject,
            strength=request.strength,
            priority_rank=request.priority_rank,
        )
        db.add(pref)

    await db.commit()
    await db.refresh(pref)
    return _pref_to_out(pref)


@router.delete("/subjects/{subject}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subject_preference(
    subject: str = Path(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserSubjectPreference).where(
            UserSubjectPreference.user_id == user.id,
            UserSubjectPreference.subject == subject,
        )
    )
    pref = result.scalar_one_or_none()
    if not pref:
        raise HTTPException(status_code=404, detail="Preference not found")
    await db.delete(pref)
    await db.commit()
