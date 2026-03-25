"""
Notifications Router
====================

User notifications, preferences, and push token management.
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.middleware.auth import get_current_user
from ...db.models import (
    NotificationPreference,
    NotificationSetting,
    PushToken,
    User,
    UserNotification,
)
from ...db.session import get_db

router = APIRouter()


@router.get("")
async def list_notifications(
    limit: int = Query(default=30, ge=1, le=200),
    unread_only: bool = Query(default=False),
    category: str | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(UserNotification)
        .where(UserNotification.user_id == user.id)
        .order_by(UserNotification.created_at.desc())
        .limit(limit)
    )
    if unread_only:
        stmt = stmt.where(UserNotification.is_read.is_(False))
    if category:
        stmt = stmt.where(UserNotification.category == category)

    result = await db.execute(stmt)
    notifications = result.scalars().all()

    return {
        "success": True,
        "notifications": [
            {
                "id": item.id,
                "title": item.title,
                "body": item.body,
                "category": item.category,
                "subcategory": item.subcategory,
                "priority": item.priority,
                "action_type": item.action_type,
                "action_data": item.action_data,
                "is_read": item.is_read,
                "read_at": item.read_at.isoformat() if item.read_at else None,
                "is_seen": item.is_seen,
                "seen_at": item.seen_at.isoformat() if item.seen_at else None,
                "is_dismissed": item.is_dismissed,
                "dismissed_at": item.dismissed_at.isoformat() if item.dismissed_at else None,
                "created_at": item.created_at.isoformat() if item.created_at else None,
                "expires_at": item.expires_at.isoformat() if item.expires_at else None,
            }
            for item in notifications
        ],
    }


@router.get("/unread-count")
async def get_unread_count(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(func.count(UserNotification.id)).where(
            UserNotification.user_id == user.id,
            UserNotification.is_read.is_(False),
        )
    )
    unread_count = result.scalar_one()
    return {"success": True, "unread_count": unread_count}


@router.patch("/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    read: bool = Body(default=True, embed=True),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserNotification).where(
            UserNotification.id == notification_id,
            UserNotification.user_id == user.id,
        )
    )
    notification = result.scalar_one_or_none()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    notification.is_read = read
    notification.read_at = datetime.utcnow() if read else None
    notification.is_seen = True
    notification.seen_at = datetime.utcnow()
    await db.commit()

    return {"success": True, "message": "Notification updated"}


@router.post("/read-all")
async def mark_all_read(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserNotification).where(
            UserNotification.user_id == user.id,
            UserNotification.is_read.is_(False),
        )
    )
    notifications = result.scalars().all()

    now = datetime.utcnow()
    for item in notifications:
        item.is_read = True
        item.read_at = now
        item.is_seen = True
        item.seen_at = now

    await db.commit()
    return {"success": True, "updated": len(notifications)}


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserNotification).where(
            UserNotification.id == notification_id,
            UserNotification.user_id == user.id,
        )
    )
    notification = result.scalar_one_or_none()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    await db.delete(notification)
    await db.commit()
    return {"success": True, "message": "Notification deleted"}


@router.get("/preferences")
async def get_preferences(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pref_result = await db.execute(
        select(NotificationPreference)
        .where(NotificationPreference.user_id == user.id)
        .order_by(NotificationPreference.category.asc())
    )
    prefs = pref_result.scalars().all()

    settings_result = await db.execute(
        select(NotificationSetting).where(NotificationSetting.user_id == user.id)
    )
    settings = settings_result.scalar_one_or_none()

    if not settings:
        settings = NotificationSetting(user_id=user.id)
        db.add(settings)
        await db.commit()
        await db.refresh(settings)

    return {
        "success": True,
        "settings": {
            "all_notifications_enabled": settings.all_notifications_enabled,
            "push_enabled": settings.push_enabled,
            "email_enabled": settings.email_enabled,
            "sms_enabled": settings.sms_enabled,
            "quiet_hours_enabled": settings.quiet_hours_enabled,
            "quiet_hours_start": settings.quiet_hours_start,
            "quiet_hours_end": settings.quiet_hours_end,
            "quiet_hours_timezone": settings.quiet_hours_timezone,
            "email_digest_enabled": settings.email_digest_enabled,
            "email_digest_frequency": settings.email_digest_frequency,
            "email_digest_time": settings.email_digest_time,
            "preferred_language": settings.preferred_language,
        },
        "categories": [
            {
                "id": pref.id,
                "category": pref.category,
                "in_app": pref.in_app,
                "push": pref.push,
                "email": pref.email,
                "sms": pref.sms,
                "max_per_day": pref.max_per_day,
                "digest_mode": pref.digest_mode,
            }
            for pref in prefs
        ],
    }


@router.put("/preferences")
async def update_preferences(
    payload: dict = Body(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    settings_result = await db.execute(
        select(NotificationSetting).where(NotificationSetting.user_id == user.id)
    )
    settings = settings_result.scalar_one_or_none()
    if not settings:
        settings = NotificationSetting(user_id=user.id)
        db.add(settings)

    settings_fields = {
        "all_notifications_enabled",
        "push_enabled",
        "email_enabled",
        "sms_enabled",
        "quiet_hours_enabled",
        "quiet_hours_start",
        "quiet_hours_end",
        "quiet_hours_timezone",
        "email_digest_enabled",
        "email_digest_frequency",
        "email_digest_time",
        "preferred_language",
    }

    for key, value in payload.items():
        if key in settings_fields:
            setattr(settings, key, value)

    category_updates = payload.get("categories", [])
    for update in category_updates:
        category = update.get("category")
        if not category:
            continue

        pref_result = await db.execute(
            select(NotificationPreference).where(
                NotificationPreference.user_id == user.id,
                NotificationPreference.category == category,
            )
        )
        pref = pref_result.scalar_one_or_none()
        if not pref:
            pref = NotificationPreference(user_id=user.id, category=category)
            db.add(pref)

        for field in ["in_app", "push", "email", "sms", "max_per_day", "digest_mode"]:
            if field in update:
                setattr(pref, field, update[field])

    settings.updated_at = datetime.utcnow()
    await db.commit()
    return {"success": True, "message": "Preferences updated"}


@router.post("/push-tokens")
async def register_push_token(
    token: str = Body(...),
    token_type: str = Body(default="fcm"),
    platform: str = Body(default="web"),
    device_id: str | None = Body(default=None),
    device_name: str | None = Body(default=None),
    app_version: str | None = Body(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    existing_result = await db.execute(
        select(PushToken).where(PushToken.user_id == user.id, PushToken.token == token)
    )
    existing = existing_result.scalar_one_or_none()

    now = datetime.utcnow()
    if existing:
        existing.token_type = token_type
        existing.platform = platform
        existing.device_id = device_id
        existing.device_name = device_name
        existing.app_version = app_version
        existing.is_active = True
        existing.last_used_at = now
        existing.updated_at = now
        await db.commit()
        return {"success": True, "token_id": existing.id, "updated": True}

    push_token = PushToken(
        user_id=user.id,
        token=token,
        token_type=token_type,
        platform=platform,
        device_id=device_id,
        device_name=device_name,
        app_version=app_version,
        is_active=True,
        last_used_at=now,
    )
    db.add(push_token)
    await db.commit()
    await db.refresh(push_token)

    return {"success": True, "token_id": push_token.id, "created": True}


@router.delete("/push-tokens/{token_id}")
async def delete_push_token(
    token_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PushToken).where(PushToken.id == token_id, PushToken.user_id == user.id)
    )
    push_token = result.scalar_one_or_none()
    if not push_token:
        raise HTTPException(status_code=404, detail="Push token not found")

    await db.delete(push_token)
    await db.commit()
    return {"success": True, "message": "Push token removed"}
