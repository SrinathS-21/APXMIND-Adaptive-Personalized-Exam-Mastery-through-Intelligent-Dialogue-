"""
Admin Router
============

Admin dashboard, user management, moderation, tickets, feature flags, and settings.
"""

from datetime import datetime

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.middleware.auth import get_current_user
from ...db.models import (
    AdminUser,
    ContentReport,
    FeatureFlag,
    SupportTicket,
    SystemSetting,
    User,
    UserBan,
)
from ...db.session import get_db

router = APIRouter()


async def get_current_admin_user(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AdminUser:
    if not user.email:
        raise HTTPException(status_code=403, detail="Admin access denied")

    result = await db.execute(
        select(AdminUser).where(
            AdminUser.email == user.email,
            AdminUser.is_active.is_(True),
        )
    )
    admin = result.scalar_one_or_none()
    if not admin:
        raise HTTPException(status_code=403, detail="Admin access denied")
    return admin


@router.get("/dashboard")
async def admin_dashboard(
    _: AdminUser = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    total_users = (await db.execute(select(func.count(User.id)))).scalar_one()

    open_tickets = (
        await db.execute(
            select(func.count(SupportTicket.id)).where(
                SupportTicket.status.in_(["open", "in_progress", "waiting_user", "waiting_internal"])
            )
        )
    ).scalar_one()

    pending_reports = (
        await db.execute(
            select(func.count(ContentReport.id)).where(ContentReport.status.in_(["pending", "under_review"]))
        )
    ).scalar_one()

    active_bans = (
        await db.execute(
            select(func.count(UserBan.id)).where(UserBan.is_active.is_(True))
        )
    ).scalar_one()

    return {
        "success": True,
        "stats": {
            "total_users": total_users,
            "open_tickets": open_tickets,
            "pending_reports": pending_reports,
            "active_bans": active_bans,
        },
    }


@router.get("/users")
async def list_users(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None),
    _: AdminUser = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(User).order_by(User.created_at.desc()).offset(offset).limit(limit)
    if search:
        like = f"%{search}%"
        stmt = stmt.where((User.name.ilike(like)) | (User.email.ilike(like)) | (User.username.ilike(like)))

    result = await db.execute(stmt)
    users = result.scalars().all()

    return {
        "success": True,
        "users": [
            {
                "id": user.id,
                "name": user.name,
                "username": user.username,
                "email": user.email,
                "subscription_status": user.subscription_status,
                "target_score": user.target_score,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "last_active_at": user.last_active_at.isoformat() if user.last_active_at else None,
                "deleted_at": user.deleted_at.isoformat() if user.deleted_at else None,
            }
            for user in users
        ],
    }


@router.get("/users/{user_id}")
async def get_user_detail(
    user_id: int,
    _: AdminUser = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "success": True,
        "user": {
            "id": user.id,
            "name": user.name,
            "username": user.username,
            "email": user.email,
            "current_class": user.current_class,
            "attempt_number": user.attempt_number,
            "target_year": user.target_year,
            "target_score": user.target_score,
            "daily_study_target_hours": float(user.daily_study_target_hours) if user.daily_study_target_hours is not None else None,
            "preferred_language": user.preferred_language,
            "learning_level": user.learning_level,
            "subscription_status": user.subscription_status,
            "subscription_expires_at": user.subscription_expires_at.isoformat() if user.subscription_expires_at else None,
            "lifetime_value_inr": user.lifetime_value_inr,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_active_at": user.last_active_at.isoformat() if user.last_active_at else None,
            "deleted_at": user.deleted_at.isoformat() if user.deleted_at else None,
        },
    }


@router.patch("/users/{user_id}")
async def update_user(
    user_id: int,
    payload: dict = Body(...),
    _: AdminUser = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    editable_fields = {
        "name",
        "email",
        "username",
        "target_score",
        "current_class",
        "attempt_number",
        "target_year",
        "preferred_language",
        "learning_level",
        "subscription_status",
        "must_change_password",
        "marketing_consent",
        "deleted_at",
    }

    for key, value in payload.items():
        if key in editable_fields:
            setattr(user, key, value)

    user.updated_at = datetime.utcnow()
    await db.commit()
    return {"success": True, "message": "User updated"}


@router.post("/users/{user_id}/block")
async def block_user(
    user_id: int,
    reason: str = Body(default="admin_action", embed=True),
    duration_days: int | None = Body(default=None, embed=True),
    admin: AdminUser = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    existing_ban_result = await db.execute(
        select(UserBan).where(UserBan.user_id == user_id, UserBan.is_active.is_(True))
    )
    if existing_ban_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User already has an active ban")

    ends_at = None
    ban_type = "permanent"
    if duration_days and duration_days > 0:
        from datetime import timedelta

        ends_at = datetime.utcnow() + timedelta(days=duration_days)
        ban_type = "temporary"

    ban = UserBan(
        user_id=user_id,
        ban_type=ban_type,
        reason=reason,
        ends_at=ends_at,
        issued_by=admin.id,
        is_active=True,
    )
    db.add(ban)
    await db.commit()

    return {"success": True, "message": "User blocked", "ban_type": ban_type}


@router.get("/tickets")
async def list_tickets(
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    _: AdminUser = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(SupportTicket).order_by(SupportTicket.created_at.desc()).limit(limit)
    if status:
        stmt = stmt.where(SupportTicket.status == status)

    result = await db.execute(stmt)
    tickets = result.scalars().all()

    return {
        "success": True,
        "tickets": [
            {
                "id": ticket.id,
                "ticket_number": ticket.ticket_number,
                "user_id": ticket.user_id,
                "email": ticket.email,
                "subject": ticket.subject,
                "category": ticket.category,
                "priority": ticket.priority,
                "status": ticket.status,
                "assigned_to": ticket.assigned_to,
                "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
                "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None,
            }
            for ticket in tickets
        ],
    }


@router.patch("/tickets/{ticket_id}")
async def update_ticket(
    ticket_id: int,
    payload: dict = Body(...),
    _: AdminUser = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(SupportTicket).where(SupportTicket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    editable_fields = {
        "status",
        "priority",
        "category",
        "subcategory",
        "resolution_summary",
        "resolution_type",
        "first_response_sla_met",
        "resolution_sla_met",
    }

    for key, value in payload.items():
        if key in editable_fields:
            setattr(ticket, key, value)

    if payload.get("status") == "resolved":
        ticket.resolved_at = datetime.utcnow()
    if payload.get("status") == "closed":
        ticket.closed_at = datetime.utcnow()

    ticket.updated_at = datetime.utcnow()
    await db.commit()
    return {"success": True, "message": "Ticket updated"}


@router.post("/tickets/{ticket_id}/assign")
async def assign_ticket(
    ticket_id: int,
    assignee_admin_id: int = Body(..., embed=True),
    _: AdminUser = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    ticket_result = await db.execute(select(SupportTicket).where(SupportTicket.id == ticket_id))
    ticket = ticket_result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    admin_result = await db.execute(select(AdminUser).where(AdminUser.id == assignee_admin_id, AdminUser.is_active.is_(True)))
    assignee = admin_result.scalar_one_or_none()
    if not assignee:
        raise HTTPException(status_code=404, detail="Assignee admin not found")

    ticket.assigned_to = assignee.id
    ticket.assigned_at = datetime.utcnow()
    ticket.updated_at = datetime.utcnow()
    await db.commit()

    return {"success": True, "message": "Ticket assigned"}


@router.get("/reports")
async def list_reports(
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    _: AdminUser = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(ContentReport).order_by(ContentReport.created_at.desc()).limit(limit)
    if status:
        stmt = stmt.where(ContentReport.status == status)

    result = await db.execute(stmt)
    reports = result.scalars().all()

    return {
        "success": True,
        "reports": [
            {
                "id": report.id,
                "reporter_id": report.reporter_id,
                "content_type": report.content_type,
                "content_id": report.content_id,
                "reason": report.reason,
                "description": report.description,
                "status": report.status,
                "reviewed_by": report.reviewed_by,
                "reviewed_at": report.reviewed_at.isoformat() if report.reviewed_at else None,
                "action_taken": report.action_taken,
                "created_at": report.created_at.isoformat() if report.created_at else None,
            }
            for report in reports
        ],
    }


@router.patch("/reports/{report_id}")
async def update_report(
    report_id: int,
    status: str = Body(..., embed=True),
    action_taken: str | None = Body(default=None, embed=True),
    review_notes: str | None = Body(default=None, embed=True),
    admin: AdminUser = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ContentReport).where(ContentReport.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    report.status = status
    report.action_taken = action_taken
    report.review_notes = review_notes
    report.reviewed_by = admin.id
    report.reviewed_at = datetime.utcnow()
    await db.commit()

    return {"success": True, "message": "Report updated"}


@router.get("/feature-flags")
async def list_feature_flags(
    _: AdminUser = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(FeatureFlag).order_by(FeatureFlag.name.asc()))
    flags = result.scalars().all()

    return {
        "success": True,
        "feature_flags": [
            {
                "id": flag.id,
                "name": flag.name,
                "display_name": flag.display_name,
                "description": flag.description,
                "is_enabled": flag.is_enabled,
                "rollout_percentage": flag.rollout_percentage,
                "rollout_strategy": flag.rollout_strategy,
                "target_segments": flag.target_segments,
                "updated_at": flag.updated_at.isoformat() if flag.updated_at else None,
            }
            for flag in flags
        ],
    }


@router.patch("/feature-flags/{flag_id}")
async def update_feature_flag(
    flag_id: int,
    payload: dict = Body(...),
    admin: AdminUser = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(FeatureFlag).where(FeatureFlag.id == flag_id))
    flag = result.scalar_one_or_none()
    if not flag:
        raise HTTPException(status_code=404, detail="Feature flag not found")

    editable_fields = {
        "is_enabled",
        "rollout_percentage",
        "rollout_strategy",
        "target_user_ids",
        "target_segments",
        "exclude_user_ids",
        "enable_at",
        "disable_at",
        "has_variants",
        "variants",
        "owner",
        "jira_ticket",
    }

    for key, value in payload.items():
        if key in editable_fields:
            setattr(flag, key, value)

    flag.updated_by = admin.id
    flag.updated_at = datetime.utcnow()
    await db.commit()
    return {"success": True, "message": "Feature flag updated"}


@router.get("/settings")
async def list_settings(
    category: str | None = Query(default=None),
    _: AdminUser = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(SystemSetting).order_by(SystemSetting.category.asc(), SystemSetting.key.asc())
    if category:
        stmt = stmt.where(SystemSetting.category == category)

    result = await db.execute(stmt)
    settings = result.scalars().all()

    return {
        "success": True,
        "settings": [
            {
                "key": item.key,
                "value": item.value,
                "value_type": item.value_type,
                "description": item.description,
                "category": item.category,
                "is_sensitive": item.is_sensitive,
                "updated_by": item.updated_by,
                "updated_at": item.updated_at.isoformat() if item.updated_at else None,
            }
            for item in settings
        ],
    }


@router.put("/settings")
async def upsert_settings(
    settings_payload: list[dict] = Body(..., embed=True),
    admin: AdminUser = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    updated = 0
    for item in settings_payload:
        key = item.get("key")
        if not key:
            continue

        result = await db.execute(select(SystemSetting).where(SystemSetting.key == key))
        setting = result.scalar_one_or_none()

        if not setting:
            setting = SystemSetting(
                key=key,
                value=item.get("value"),
                value_type=item.get("value_type", "json"),
                description=item.get("description"),
                category=item.get("category", "general"),
                is_sensitive=bool(item.get("is_sensitive", False)),
                updated_by=admin.id,
                updated_at=datetime.utcnow(),
            )
            db.add(setting)
            updated += 1
            continue

        if "value" in item:
            setting.value = item["value"]
        if "value_type" in item:
            setting.value_type = item["value_type"]
        if "description" in item:
            setting.description = item["description"]
        if "category" in item:
            setting.category = item["category"]
        if "is_sensitive" in item:
            setting.is_sensitive = bool(item["is_sensitive"])

        setting.updated_by = admin.id
        setting.updated_at = datetime.utcnow()
        updated += 1

    await db.commit()
    return {"success": True, "updated": updated}
