"""
Support Router
==============

User support tickets and content reporting.
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.middleware.auth import get_current_user
from ...db.models import ContentReport, SupportTicket, TicketResponse, User
from ...db.session import get_db

router = APIRouter()
reports_router = APIRouter()


def _generate_ticket_number() -> str:
    return f"TKT-{datetime.utcnow().strftime('%Y')}-{uuid.uuid4().hex[:5].upper()}"


@router.get("/tickets")
async def list_tickets(
    limit: int = Query(default=30, ge=1, le=200),
    status: str | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(SupportTicket)
        .where(SupportTicket.user_id == user.id)
        .order_by(SupportTicket.created_at.desc())
        .limit(limit)
    )
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
                "subject": ticket.subject,
                "description": ticket.description,
                "category": ticket.category,
                "subcategory": ticket.subcategory,
                "priority": ticket.priority,
                "status": ticket.status,
                "assigned_to": ticket.assigned_to,
                "resolution_summary": ticket.resolution_summary,
                "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
                "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None,
                "closed_at": ticket.closed_at.isoformat() if ticket.closed_at else None,
            }
            for ticket in tickets
        ],
    }


@router.post("/tickets")
async def create_ticket(
    subject: str = Body(...),
    description: str = Body(...),
    category: str = Body(default="other"),
    subcategory: str | None = Body(default=None),
    priority: str = Body(default="normal"),
    attachments: list[str] | None = Body(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.utcnow()
    ticket = SupportTicket(
        ticket_number=_generate_ticket_number(),
        user_id=user.id,
        email=user.email or "",
        name=user.name,
        subject=subject,
        description=description,
        category=category,
        subcategory=subcategory,
        priority=priority,
        status="open",
        source="app",
        attachments=attachments,
        created_at=now,
        updated_at=now,
    )
    db.add(ticket)
    await db.flush()

    response = TicketResponse(
        ticket_id=ticket.id,
        responder_type="user",
        responder_id=user.id,
        responder_name=user.name,
        message=description,
        is_internal=False,
        is_automated=False,
    )
    db.add(response)

    await db.commit()
    await db.refresh(ticket)

    return {
        "success": True,
        "ticket": {
            "id": ticket.id,
            "ticket_number": ticket.ticket_number,
            "status": ticket.status,
            "priority": ticket.priority,
            "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
        },
    }


@router.get("/tickets/{ticket_id}")
async def get_ticket(
    ticket_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SupportTicket).where(SupportTicket.id == ticket_id, SupportTicket.user_id == user.id)
    )
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    response_result = await db.execute(
        select(TicketResponse)
        .where(TicketResponse.ticket_id == ticket.id)
        .order_by(TicketResponse.created_at.asc())
    )
    responses = response_result.scalars().all()

    return {
        "success": True,
        "ticket": {
            "id": ticket.id,
            "ticket_number": ticket.ticket_number,
            "subject": ticket.subject,
            "description": ticket.description,
            "category": ticket.category,
            "subcategory": ticket.subcategory,
            "priority": ticket.priority,
            "status": ticket.status,
            "assigned_to": ticket.assigned_to,
            "resolution_summary": ticket.resolution_summary,
            "resolution_type": ticket.resolution_type,
            "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
            "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None,
            "closed_at": ticket.closed_at.isoformat() if ticket.closed_at else None,
            "responses": [
                {
                    "id": response.id,
                    "responder_type": response.responder_type,
                    "responder_id": response.responder_id,
                    "responder_name": response.responder_name,
                    "message": response.message,
                    "is_internal": response.is_internal,
                    "attachments": response.attachments,
                    "is_automated": response.is_automated,
                    "created_at": response.created_at.isoformat() if response.created_at else None,
                }
                for response in responses
                if not response.is_internal
            ],
        },
    }


@router.post("/tickets/{ticket_id}/reply")
async def reply_ticket(
    ticket_id: int,
    message: str = Body(...),
    attachments: list[str] | None = Body(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SupportTicket).where(SupportTicket.id == ticket_id, SupportTicket.user_id == user.id)
    )
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    response = TicketResponse(
        ticket_id=ticket.id,
        responder_type="user",
        responder_id=user.id,
        responder_name=user.name,
        message=message,
        attachments=attachments,
        is_internal=False,
        is_automated=False,
    )
    db.add(response)

    ticket.updated_at = datetime.utcnow()
    if ticket.status in {"resolved", "closed"}:
        ticket.status = "waiting_internal"

    await db.commit()
    return {"success": True, "message": "Reply added"}


@router.post("/reports")
@reports_router.post("/reports")
async def create_report(
    content_type: str = Body(...),
    content_id: str = Body(...),
    reason: str = Body(...),
    description: str | None = Body(default=None),
    content_preview: str | None = Body(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    report = ContentReport(
        reporter_id=user.id,
        content_type=content_type,
        content_id=content_id,
        content_preview=content_preview,
        reason=reason,
        description=description,
        status="pending",
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    return {
        "success": True,
        "report": {
            "id": report.id,
            "content_type": report.content_type,
            "content_id": report.content_id,
            "reason": report.reason,
            "status": report.status,
            "created_at": report.created_at.isoformat() if report.created_at else None,
        },
    }
