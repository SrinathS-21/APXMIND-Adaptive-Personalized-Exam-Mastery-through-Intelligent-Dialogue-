file_path = 'src/apxmind/server/routes/auth.py'

new_auth_content = '''"""
Auth Router
============

GET  /api/auth/users — get list of available local users
POST /api/auth/register — create new local user (Profile Setup)
POST /api/auth/login — authenticate local user (by name)
GET  /api/auth/me — get current user profile
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.schemas import (
    OfflineProfileRequest,
    LoginRequest,
    AuthResponse,
    UserResponse,
    LocalDropdownResponse,
    LocalUserDropdown,
    ErrorResponse,
)
from ...api.middleware.auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
)
from ...core.dependencies import get_settings
from ...core.config import Settings
from ...db.models import User
from ...db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/users", response_model=LocalDropdownResponse, summary="Get list of local users")
async def get_local_users(db: AsyncSession = Depends(get_db)):
    """Fetch all users on this local machine for the login dropdown."""
    result = await db.execute(select(User.id, User.name))
    users = result.fetchall()
    
    return LocalDropdownResponse(
        success=True,
        users=[LocalUserDropdown(id=row.id, name=row.name) for row in users]
    )


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new local user"
)
async def register(
    request: OfflineProfileRequest,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Create a new local user account with profile details."""
    # Check if a user with this name already exists
    result = await db.execute(select(User).where(User.name == request.name))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this name already exists on this device. Please choose a different name or login."
        )

    # Create new user
    user = User(
        name=request.name,
        password_hash=hash_password(request.password),
        dob=request.dob,
        current_class=request.current_class,
        attempt_number=request.attempt_number,
        target_year=request.target_year,
        target_score=request.target_score,
        strong_subjects=request.strong_subjects,
        weak_subjects=request.weak_subjects,
        daily_study_target=request.daily_study_target,
        preferred_language=request.preferred_language,
        learning_level="beginner"
    )
    db.add(user)
    await db.flush()  # Get user.id before commit
    await db.commit()
    await db.refresh(user)

    # Generate token
    token = create_access_token(user.id, settings)

    return AuthResponse(
        success=True,
        token=token,
        user=UserResponse(
            id=user.id,
            name=user.name,
            dob=user.dob,
            current_class=user.current_class,
            target_year=user.target_year,
            target_score=user.target_score,
            learning_level=user.learning_level or "beginner",
            created_at=user.created_at.isoformat() if user.created_at else None,
        )
    )


@router.post("/login", response_model=AuthResponse, summary="Login local user")
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Authenticate a local user by name and return a JWT token."""
    result = await db.execute(select(User).where(User.name == request.name))
    user = result.scalar_one_or_none()

    if not user or not user.password_hash:
        raise HTTPException(status_code=401, detail="Invalid name or password")

    if not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid name or password")

    token = create_access_token(user.id, settings)

    return AuthResponse(
        success=True,
        token=token,
        user=UserResponse(
            id=user.id,
            name=user.name,
            dob=user.dob,
            current_class=user.current_class,
            target_year=user.target_year,
            target_score=user.target_score,
            learning_level=user.learning_level or "beginner",
            created_at=user.created_at.isoformat() if user.created_at else None,
        )
    )


@router.get("/me", response_model=UserResponse, summary="Get current user")
async def get_me(user: User = Depends(get_current_user)):
    """Get the authenticated user's profile."""
    return UserResponse(
        id=user.id,
        name=user.name,
        dob=user.dob,
        current_class=user.current_class,
        target_year=user.target_year,
        target_score=user.target_score,
        learning_level=user.learning_level or "beginner",
        created_at=user.created_at.isoformat() if user.created_at else None,
    )
'''

with open(file_path, 'w') as f:
    f.write(new_auth_content)

print("Auth routes rewritten successfully.")
