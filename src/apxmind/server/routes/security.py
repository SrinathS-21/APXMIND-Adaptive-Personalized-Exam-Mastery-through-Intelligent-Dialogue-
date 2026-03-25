"""
Security Router
================

Password reset, session management, and security activity endpoints.
"""

import hashlib
import logging
import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.middleware.auth import get_current_user, hash_password
from ...db.models import (
    LoginHistory,
    PasswordResetToken,
    SecurityEvent,
    User,
)
from ...db.session import get_db

router = APIRouter()
logger = logging.getLogger(__name__)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _to_iso(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


async def _get_user_session_columns(db: AsyncSession) -> set[str]:
    result = await db.execute(text("PRAGMA table_info(user_sessions)"))
    rows = result.fetchall()
    return {str(row[1]) for row in rows}


@router.post("/password-reset/request")
async def request_password_reset(
    email: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        return {"success": True, "message": "If the email exists, reset instructions were sent."}

    raw_token = secrets.token_urlsafe(32)
    token_hash = _hash_token(raw_token)

    reset = PasswordResetToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime.utcnow() + timedelta(minutes=30),
    )
    db.add(reset)
    db.add(
        SecurityEvent(
            user_id=user.id,
            event_type="password_reset_requested",
            severity="info",
            description="Password reset requested",
        )
    )
    await db.commit()

    return {
        "success": True,
        "message": "Password reset token generated.",
        "reset_token": raw_token,
        "expires_in_minutes": 30,
    }


@router.post("/password-reset/confirm")
async def confirm_password_reset(
    token: str = Body(...),
    new_password: str = Body(...),
    db: AsyncSession = Depends(get_db),
):
    token_hash = _hash_token(token)
    now = datetime.utcnow()

    result = await db.execute(select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash))
    reset_token = result.scalar_one_or_none()

    if not reset_token or reset_token.used_at is not None or reset_token.expires_at < now:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    user_result = await db.execute(select(User).where(User.id == reset_token.user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.password_hash = hash_password(new_password)
    user.password_changed_at = now
    user.must_change_password = False
    reset_token.used_at = now

    db.add(
        SecurityEvent(
            user_id=user.id,
            event_type="password_reset_completed",
            severity="info",
            description="Password reset completed",
        )
    )
    await db.commit()

    return {"success": True, "message": "Password updated successfully"}


@router.get("/sessions")
async def list_sessions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        columns = await _get_user_session_columns(db)
        if not columns:
            return {
                "success": True,
                "sessions": [],
                "warning": "security_sessions_unavailable",
            }

        has_modern_columns = {"device_id", "location", "last_activity"}.issubset(columns)

        if has_modern_columns:
            result = await db.execute(
                text(
                    """
                    SELECT id, device_id, ip_address, location, is_revoked, expires_at, last_activity, created_at
                    FROM user_sessions
                    WHERE user_id = :user_id
                    ORDER BY last_activity DESC, created_at DESC
                    """
                ),
                {"user_id": user.id},
            )
            rows = result.mappings().all()
            sessions = [
                {
                    "id": row.get("id"),
                    "device_id": row.get("device_id"),
                    "ip_address": row.get("ip_address"),
                    "location": row.get("location"),
                    "is_revoked": bool(row.get("is_revoked")),
                    "expires_at": _to_iso(row.get("expires_at")),
                    "last_activity": _to_iso(row.get("last_activity")),
                    "created_at": _to_iso(row.get("created_at")),
                }
                for row in rows
            ]
        else:
            result = await db.execute(
                text(
                    """
                    SELECT id, ip_address, device_info, is_revoked, expires_at, last_activity, created_at
                    FROM user_sessions
                    WHERE user_id = :user_id
                    ORDER BY COALESCE(last_activity, created_at) DESC
                    """
                ),
                {"user_id": user.id},
            )
            rows = result.mappings().all()
            sessions = [
                {
                    "id": row.get("id"),
                    "device_id": None,
                    "ip_address": row.get("ip_address"),
                    "location": None,
                    "device_info": row.get("device_info"),
                    "is_revoked": bool(row.get("is_revoked")),
                    "expires_at": _to_iso(row.get("expires_at")),
                    "last_activity": _to_iso(row.get("last_activity")),
                    "created_at": _to_iso(row.get("created_at")),
                }
                for row in rows
            ]
    except Exception as exc:
        logger.exception("Failed to fetch sessions for user_id=%s", user.id, exc_info=exc)
        return {
            "success": True,
            "sessions": [],
            "warning": "security_sessions_unavailable",
        }

    return {
        "success": True,
        "sessions": sessions,
    }


@router.post("/sessions/{session_id}/revoke")
async def revoke_session(
    session_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        columns = await _get_user_session_columns(db)
        if not columns:
            raise HTTPException(status_code=404, detail="Session not found")

        exists_result = await db.execute(
            text("SELECT id FROM user_sessions WHERE id = :session_id AND user_id = :user_id LIMIT 1"),
            {"session_id": session_id, "user_id": user.id},
        )
        if not exists_result.first():
            raise HTTPException(status_code=404, detail="Session not found")

        set_clauses = ["is_revoked = 1"]
        params = {"session_id": session_id, "user_id": user.id}

        if "revoked_at" in columns:
            set_clauses.append("revoked_at = :revoked_at")
            params["revoked_at"] = datetime.utcnow()
        if "revoke_reason" in columns:
            set_clauses.append("revoke_reason = :revoke_reason")
            params["revoke_reason"] = "user_logout"

        await db.execute(
            text(
                f"UPDATE user_sessions SET {', '.join(set_clauses)} WHERE id = :session_id AND user_id = :user_id"
            ),
            params,
        )
        await db.commit()
        return {"success": True, "message": "Session revoked"}
    except SQLAlchemyError as exc:
        logger.exception("Failed to revoke session=%s for user_id=%s", session_id, user.id, exc_info=exc)
        raise HTTPException(status_code=500, detail="Unable to revoke session")


@router.post("/sessions/revoke-others")
async def revoke_other_sessions(
    payload: dict | str | None = Body(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_session_id: str | None = None
    if isinstance(payload, str):
        current_session_id = payload
    elif isinstance(payload, dict):
        value = payload.get("current_session_id")
        if isinstance(value, str):
            current_session_id = value

    try:
        columns = await _get_user_session_columns(db)
        if not columns:
            return {
                "success": True,
                "revoked_sessions": 0,
                "warning": "security_sessions_unavailable",
            }

        conditions = ["user_id = :user_id", "COALESCE(is_revoked, 0) = 0"]
        params: dict[str, object] = {"user_id": user.id}
        if current_session_id:
            conditions.append("id != :current_session_id")
            params["current_session_id"] = current_session_id

        set_clauses = ["is_revoked = 1"]
        if "revoked_at" in columns:
            set_clauses.append("revoked_at = :revoked_at")
            params["revoked_at"] = datetime.utcnow()
        if "revoke_reason" in columns:
            set_clauses.append("revoke_reason = :revoke_reason")
            params["revoke_reason"] = "logout_all"

        count_result = await db.execute(
            text(f"SELECT COUNT(1) AS total FROM user_sessions WHERE {' AND '.join(conditions)}"),
            params,
        )
        revoked_count = int(count_result.scalar() or 0)

        if revoked_count > 0:
            await db.execute(
                text(
                    f"UPDATE user_sessions SET {', '.join(set_clauses)} WHERE {' AND '.join(conditions)}"
                ),
                params,
            )

        await db.commit()
        return {"success": True, "revoked_sessions": revoked_count}
    except SQLAlchemyError as exc:
        logger.exception("Failed to revoke other sessions for user_id=%s", user.id, exc_info=exc)
        return {
            "success": True,
            "revoked_sessions": 0,
            "warning": "security_sessions_unavailable",
        }


@router.get("/login-history")
async def get_login_history(
    limit: int = Query(default=30, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(LoginHistory)
        .where(LoginHistory.user_id == user.id)
        .order_by(LoginHistory.created_at.desc())
        .limit(limit)
    )
    rows = result.scalars().all()

    return {
        "success": True,
        "history": [
            {
                "id": row.id,
                "success": row.success,
                "failure_reason": row.failure_reason,
                "ip_address": row.ip_address,
                "device_type": row.device_type,
                "browser": row.browser,
                "os": row.os,
                "location": {
                    "country": row.location_country,
                    "state": row.location_state,
                    "city": row.location_city,
                },
                "is_suspicious": row.is_suspicious,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ],
    }


@router.get("/events")
async def get_security_events(
    limit: int = Query(default=30, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SecurityEvent)
        .where(SecurityEvent.user_id == user.id)
        .order_by(SecurityEvent.created_at.desc())
        .limit(limit)
    )
    events = result.scalars().all()

    return {
        "success": True,
        "events": [
            {
                "id": event.id,
                "event_type": event.event_type,
                "severity": event.severity,
                "description": event.description,
                "ip_address": event.ip_address,
                "created_at": event.created_at.isoformat() if event.created_at else None,
            }
            for event in events
        ],
    }
