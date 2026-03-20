"""
Learn Sessions & Chat Router
==============================

DB-persisted learning sessions + chat messages (blueprint §3.6 + §5.3).

POST   /api/learn/sessions                          — start session
GET    /api/learn/sessions                          — list sessions
GET    /api/learn/sessions/{id}                     — get session
PATCH  /api/learn/sessions/{id}/end                 — end session
DELETE /api/learn/sessions/{id}                     — delete session + messages

POST   /api/learn/sessions/{id}/messages            — send message (triggers AI)
GET    /api/learn/sessions/{id}/messages            — list messages
DELETE /api/learn/sessions/{id}/messages/{msg_id}   — delete single message
DELETE /api/learn/sessions/{id}/messages            — clear all messages
"""

import logging
import time
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.middleware.auth import get_current_user
from ...api.schemas import (
    MessageListResponse,
    MessageOut,
    SendMessageRequest,
    SessionListResponse,
    SessionOut,
    StartSessionRequest,
)
from ...db.gamification import append_event, award_xp_for_event
from ...db.models import ChatMessage, LearningSession, QueryEvent, User
from ...db.session import get_db

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _session_to_out(s: LearningSession) -> SessionOut:
    duration = None
    if s.started_at and s.ended_at:
        duration = round((s.ended_at - s.started_at).total_seconds() / 60, 2)
    return SessionOut(
        id=s.id,
        subject=s.subject,
        lesson_id=s.lesson_id,
        started_at=s.started_at.isoformat(),
        ended_at=s.ended_at.isoformat() if s.ended_at else None,
        duration_minutes=duration,
    )


def _msg_to_out(m: ChatMessage) -> MessageOut:
    return MessageOut(
        id=m.id,
        session_id=m.session_id,
        role=m.role,
        content=m.content,
        tier=m.tier,
        created_at=m.created_at.isoformat(),
    )


async def _get_session_or_404(db: AsyncSession, session_id: str, user_id: int) -> LearningSession:
    result = await db.execute(
        select(LearningSession).where(
            LearningSession.id == session_id, LearningSession.user_id == user_id
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


def _run_ai(query: str, subject: str) -> tuple[str, str, float]:
    """Run the tiered AI pipeline. Returns (answer, tier, latency_ms)."""
    start = time.time()
    try:
        from ...api.agents import classify_intent, retriever_agent, orchestrator_agent
        from ...core.dependencies import get_llm, get_vectorstore

        llm = get_llm()
        intent_result = classify_intent(query, subject)
        intent = intent_result.get("intent", "complex")
        detected_subject = intent_result.get("subject", subject)

        if intent in ("simple", "retrieval"):
            vs = get_vectorstore(detected_subject)
            result = retriever_agent(query=query, vectorstore=vs, llm=llm, subject=detected_subject)
            tier = "tier-1"
        else:
            vectorstores = {
                "biology": get_vectorstore("biology"),
                "chemistry": get_vectorstore("chemistry"),
                "physics": get_vectorstore("physics"),
            }
            result = orchestrator_agent(query=query, vectorstores=vectorstores, llm=llm, subject=detected_subject)
            tier = "tier-2"

        answer = result.get("answer", "")
    except Exception as exc:
        logger.warning(f"AI pipeline error: {exc}")
        answer = "I'm unable to process that right now. Please try again."
        tier = "tier-0"

    latency_ms = round((time.time() - start) * 1000, 2)
    return answer, tier, latency_ms


# ---------------------------------------------------------------------------
# POST /api/learn/sessions
# ---------------------------------------------------------------------------

@router.post("/sessions", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
async def start_session(
    request: StartSessionRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = LearningSession(
        id=str(uuid.uuid4()),
        user_id=user.id,
        subject=request.subject.value,
        lesson_id=request.lesson_id,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return _session_to_out(session)


# ---------------------------------------------------------------------------
# GET /api/learn/sessions
# ---------------------------------------------------------------------------

@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    subject: str = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(LearningSession)
        .where(LearningSession.user_id == user.id)
        .order_by(LearningSession.started_at.desc())
        .limit(limit)
    )
    if subject:
        stmt = stmt.where(LearningSession.subject == subject)
    result = await db.execute(stmt)
    sessions = result.scalars().all()
    return SessionListResponse(sessions=[_session_to_out(s) for s in sessions], total=len(sessions))


# ---------------------------------------------------------------------------
# GET /api/learn/sessions/{id}
# ---------------------------------------------------------------------------

@router.get("/sessions/{session_id}", response_model=SessionOut)
async def get_session(
    session_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await _get_session_or_404(db, session_id, user.id)
    return _session_to_out(session)


# ---------------------------------------------------------------------------
# PATCH /api/learn/sessions/{id}/end
# ---------------------------------------------------------------------------

@router.patch("/sessions/{session_id}/end", response_model=SessionOut)
async def end_session(
    session_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await _get_session_or_404(db, session_id, user.id)
    if session.ended_at:
        return _session_to_out(session)
    session.ended_at = datetime.utcnow()

    # Award study XP based on session duration
    duration_minutes = round((session.ended_at - session.started_at).total_seconds() / 60)
    if duration_minutes > 0:
        await append_event(
            db,
            user_id=user.id,
            event_type="study_session_recorded",
            subject=session.subject,
            entity_type="session",
            entity_id=session.id,
            event_value=float(duration_minutes),
            payload={"minutes": duration_minutes},
        )
        await award_xp_for_event(
            db, user.id, "study_session_recorded",
            subject=session.subject, minutes=duration_minutes
        )

    await db.commit()
    await db.refresh(session)
    return _session_to_out(session)


# ---------------------------------------------------------------------------
# DELETE /api/learn/sessions/{id}
# ---------------------------------------------------------------------------

@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await _get_session_or_404(db, session_id, user.id)
    await db.delete(session)
    await db.commit()


# ---------------------------------------------------------------------------
# POST /api/learn/sessions/{id}/messages  — send message + get AI reply
# ---------------------------------------------------------------------------

@router.post("/sessions/{session_id}/messages", response_model=MessageOut)
async def send_message(
    session_id: str,
    request: SendMessageRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await _get_session_or_404(db, session_id, user.id)

    # Persist user message
    user_msg = ChatMessage(
        session_id=session_id,
        role="user",
        content=request.content,
    )
    db.add(user_msg)
    await db.flush()

    # Append query event
    await append_event(
        db,
        user_id=user.id,
        event_type="chat_query_sent",
        subject=session.subject,
        entity_type="session",
        entity_id=session_id,
    )
    await award_xp_for_event(db, user.id, "chat_query_sent", subject=session.subject)

    # Run AI pipeline in a thread to avoid blocking the event loop
    import asyncio
    answer, tier, latency_ms = await asyncio.get_event_loop().run_in_executor(
        None, _run_ai, request.content, session.subject
    )

    # Persist assistant message
    assistant_msg = ChatMessage(
        session_id=session_id,
        role="assistant",
        content=answer,
        tier=tier,
        msg_metadata={"latency_ms": latency_ms},
    )
    db.add(assistant_msg)

    # Persist query event analytics
    db.add(QueryEvent(
        user_id=user.id,
        session_id=session_id,
        query_text=request.content,
        subject=session.subject,
        tier=tier,
        latency_ms=int(latency_ms),
    ))

    await db.commit()
    await db.refresh(assistant_msg)
    return _msg_to_out(assistant_msg)


# ---------------------------------------------------------------------------
# GET /api/learn/sessions/{id}/messages
# ---------------------------------------------------------------------------

@router.get("/sessions/{session_id}/messages", response_model=MessageListResponse)
async def get_messages(
    session_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_session_or_404(db, session_id, user.id)
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
        .limit(limit)
    )
    msgs = result.scalars().all()
    return MessageListResponse(messages=[_msg_to_out(m) for m in msgs], total=len(msgs))


# ---------------------------------------------------------------------------
# DELETE /api/learn/sessions/{id}/messages/{msg_id}
# ---------------------------------------------------------------------------

@router.delete(
    "/sessions/{session_id}/messages/{msg_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_message(
    session_id: str,
    msg_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_session_or_404(db, session_id, user.id)
    result = await db.execute(
        select(ChatMessage).where(
            ChatMessage.id == msg_id, ChatMessage.session_id == session_id
        )
    )
    msg = result.scalar_one_or_none()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    await db.delete(msg)
    await db.commit()


# ---------------------------------------------------------------------------
# DELETE /api/learn/sessions/{id}/messages  — clear all
# ---------------------------------------------------------------------------

@router.delete(
    "/sessions/{session_id}/messages",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def clear_messages(
    session_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_session_or_404(db, session_id, user.id)
    result = await db.execute(
        select(ChatMessage).where(ChatMessage.session_id == session_id)
    )
    for msg in result.scalars().all():
        await db.delete(msg)
    await db.commit()
