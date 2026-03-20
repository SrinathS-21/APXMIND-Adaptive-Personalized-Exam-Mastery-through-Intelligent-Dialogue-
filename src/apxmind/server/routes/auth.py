"""
Auth Router
============

POST /api/auth/register — create new user
POST /api/auth/login    — authenticate and get JWT token
GET  /api/auth/me       — get current user profile
PUT  /api/auth/profile  — update profile
GET  /api/auth/users    — list local users (for offline selector)
POST /api/auth/profile  — setup offline profile (upsert)
"""

import logging
import re
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.middleware.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from ...api.schemas import (
    AuthResponse,
    LocalDropdownResponse,
    LocalUserDropdown,
    LoginRequest,
    OfflineProfileRequest,
    UpdateProfileRequest,
    UserResponse,
)
from ...core.config import Settings
from ...core.dependencies import get_settings
from ...db.models import User, UserGamificationSnapshot
from ...db.session import get_db

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _slugify(name: str) -> str:
    """Convert a display name to a valid username slug."""
    return re.sub(r"[^a-z0-9_]", "", name.lower().replace(" ", "_"))


def _to_user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        name=user.name,
        username=user.username,
        email=user.email,
        avatar_url=user.avatar_url,
        dob=user.dob,
        current_class=user.current_class,
        attempt_number=user.attempt_number,
        target_year=user.target_year,
        target_score=user.target_score,
        strong_subjects=user.strong_subjects or [],
        weak_subjects=user.weak_subjects or [],
        daily_study_target=user.daily_study_target,
        daily_study_target_hours=user.daily_study_target_hours,
        preferred_language=user.preferred_language,
        learning_level=user.learning_level or "beginner",
        timezone=user.timezone,
        created_at=user.created_at.isoformat() if user.created_at else None,
        updated_at=user.updated_at.isoformat() if user.updated_at else None,
    )


async def _ensure_gamification_snapshot(db: AsyncSession, user_id: int) -> None:
    """Create a UserGamificationSnapshot row if one doesn't exist yet."""
    result = await db.execute(
        select(UserGamificationSnapshot).where(UserGamificationSnapshot.user_id == user_id)
    )
    if result.scalar_one_or_none() is None:
        db.add(UserGamificationSnapshot(user_id=user_id))


# ---------------------------------------------------------------------------
# POST /api/auth/register
# ---------------------------------------------------------------------------

@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(
    request: OfflineProfileRequest,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Create a new user account and return a JWT token."""
    # Check name uniqueness
    result = await db.execute(select(User).where(User.name == request.name))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this name already exists",
        )

    # Determine username
    username = request.username
    if username:
        # Validate uniqueness of explicitly provided username
        u_result = await db.execute(select(User).where(User.username == username))
        if u_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already taken",
            )
    else:
        # Auto-generate from name; will de-duplicate after we know the new user's id
        username = _slugify(request.name) or "user"

    now = datetime.utcnow()
    user = User(
        name=request.name,
        username=username,
        email=request.email,
        password_hash=hash_password(request.password),
        dob=request.dob,
        current_class=request.current_class,
        attempt_number=request.attempt_number,
        target_year=request.target_year,
        target_score=request.target_score,
        strong_subjects=request.strong_subjects,
        weak_subjects=request.weak_subjects,
        daily_study_target=request.daily_study_target,
        daily_study_target_hours=request.daily_study_target_hours,
        preferred_language=request.preferred_language,
        learning_level=request.learning_level,
        timezone=request.timezone,
        updated_at=now,
        last_active_at=now,
    )
    db.add(user)
    await db.flush()  # get user.id without committing yet

    # De-duplicate auto-generated username: append "_<id>" if slug already taken
    if not request.username:
        u2 = await db.execute(
            select(User).where(User.username == user.username, User.id != user.id)
        )
        if u2.scalar_one_or_none():
            user.username = f"{username}_{user.id}"

    await _ensure_gamification_snapshot(db, user.id)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(user.id, settings)
    return AuthResponse(success=True, token=token, user=_to_user_response(user))


# ---------------------------------------------------------------------------
# POST /api/auth/login
# ---------------------------------------------------------------------------

@router.post("/login", response_model=AuthResponse, summary="Login")
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Authenticate a user by name or username and return a JWT token."""
    if not request.name and not request.username:
        raise HTTPException(status_code=400, detail="Provide 'name' or 'username'")

    if request.name:
        result = await db.execute(select(User).where(User.name == request.name))
    else:
        result = await db.execute(select(User).where(User.username == request.username))
    user = result.scalar_one_or_none()

    if not user or not user.password_hash:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    now = datetime.utcnow()
    user.last_active = now
    user.last_active_at = now
    user.updated_at = now
    await db.commit()
    await db.refresh(user)

    token = create_access_token(user.id, settings)
    return AuthResponse(success=True, token=token, user=_to_user_response(user))


# ---------------------------------------------------------------------------
# GET /api/auth/me
# ---------------------------------------------------------------------------

@router.get("/me", response_model=UserResponse, summary="Get current user")
async def get_me(user: User = Depends(get_current_user)):
    """Return the authenticated user's profile."""
    return _to_user_response(user)


# ---------------------------------------------------------------------------
# PUT /api/auth/profile
# ---------------------------------------------------------------------------

@router.put("/profile", response_model=UserResponse, summary="Update current user profile")
async def update_profile(
    request: UpdateProfileRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the authenticated user's profile (only provided fields are changed)."""
    if request.name is not None:
        user.name = request.name
    if request.username is not None:
        # Check uniqueness against other users
        u_result = await db.execute(
            select(User).where(User.username == request.username, User.id != user.id)
        )
        if u_result.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Username already taken")
        user.username = request.username
    if request.email is not None:
        user.email = request.email
    if request.avatar_url is not None:
        user.avatar_url = request.avatar_url
    if request.dob is not None:
        user.dob = request.dob
    if request.current_class is not None:
        user.current_class = request.current_class
    if request.attempt_number is not None:
        user.attempt_number = request.attempt_number
    if request.target_year is not None:
        user.target_year = request.target_year
    if request.target_score is not None:
        user.target_score = request.target_score
    if request.strong_subjects is not None:
        user.strong_subjects = request.strong_subjects
    if request.weak_subjects is not None:
        user.weak_subjects = request.weak_subjects
    if request.daily_study_target is not None:
        user.daily_study_target = request.daily_study_target
    if request.daily_study_target_hours is not None:
        user.daily_study_target_hours = request.daily_study_target_hours
    if request.preferred_language is not None:
        user.preferred_language = request.preferred_language
    if request.learning_level is not None:
        user.learning_level = request.learning_level
    if request.timezone is not None:
        user.timezone = request.timezone

    user.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(user)
    return _to_user_response(user)


# ---------------------------------------------------------------------------
# GET /api/auth/users  (offline user selector)
# ---------------------------------------------------------------------------

@router.get("/users", response_model=LocalDropdownResponse, summary="List local users")
async def list_local_users(db: AsyncSession = Depends(get_db)):
    """Return available local users for the login selector."""
    result = await db.execute(
        select(User).order_by(User.last_active.desc(), User.created_at.desc())
    )
    users = result.scalars().all()
    return LocalDropdownResponse(
        success=True,
        users=[LocalUserDropdown(id=u.id, name=u.name) for u in users],
    )


# ---------------------------------------------------------------------------
# POST /api/auth/profile  (offline single-user setup)
# ---------------------------------------------------------------------------

@router.post(
    "/profile",
    response_model=AuthResponse,
    summary="Save local user profile setup",
)
async def setup_local_profile(
    request: OfflineProfileRequest,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Create or update the single local offline user profile."""
    existing_user = None

    if request.username:
        by_username = await db.execute(select(User).where(User.username == request.username))
        existing_user = by_username.scalar_one_or_none()

    if not existing_user:
        by_name = await db.execute(select(User).where(User.name == request.name))
        existing_user = by_name.scalar_one_or_none()

    now = datetime.utcnow()

    if existing_user:
        user = existing_user

        if request.name != user.name:
            name_conflict = await db.execute(
                select(User).where(User.name == request.name, User.id != user.id)
            )
            if name_conflict.scalar_one_or_none():
                raise HTTPException(status_code=409, detail="User with this name already exists")

        if request.username and request.username != user.username:
            username_conflict = await db.execute(
                select(User).where(User.username == request.username, User.id != user.id)
            )
            if username_conflict.scalar_one_or_none():
                raise HTTPException(status_code=409, detail="Username already taken")

        user.name = request.name
        if request.username:
            user.username = request.username
        if request.email:
            user.email = request.email
        if request.password:
            user.password_hash = hash_password(request.password)
        user.dob = request.dob
        user.current_class = request.current_class
        user.attempt_number = request.attempt_number
        user.target_year = request.target_year
        user.target_score = request.target_score
        user.strong_subjects = request.strong_subjects
        user.weak_subjects = request.weak_subjects
        user.daily_study_target = request.daily_study_target
        if request.daily_study_target_hours is not None:
            user.daily_study_target_hours = request.daily_study_target_hours
        user.preferred_language = request.preferred_language
        if request.learning_level:
            user.learning_level = request.learning_level
        if request.timezone:
            user.timezone = request.timezone
        user.updated_at = now
    else:
        username = request.username or _slugify(request.name) or "user"

        if request.username:
            username_exists = await db.execute(select(User).where(User.username == username))
            if username_exists.scalar_one_or_none():
                raise HTTPException(status_code=409, detail="Username already taken")

        name_exists = await db.execute(select(User).where(User.name == request.name))
        if name_exists.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="User with this name already exists")

        user = User(
            name=request.name,
            username=username,
            email=request.email,
            password_hash=hash_password(request.password) if request.password else None,
            dob=request.dob,
            current_class=request.current_class,
            attempt_number=request.attempt_number,
            target_year=request.target_year,
            target_score=request.target_score,
            strong_subjects=request.strong_subjects,
            weak_subjects=request.weak_subjects,
            daily_study_target=request.daily_study_target,
            daily_study_target_hours=request.daily_study_target_hours,
            preferred_language=request.preferred_language,
            learning_level=request.learning_level,
            timezone=request.timezone,
            updated_at=now,
            last_active_at=now,
        )
        db.add(user)
        await db.flush()
        await _ensure_gamification_snapshot(db, user.id)

    await db.commit()
    await db.refresh(user)

    token = create_access_token(user.id, settings)
    return AuthResponse(success=True, token=token, user=_to_user_response(user))
