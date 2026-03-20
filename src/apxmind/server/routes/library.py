"""
Library Router
===============

Bookmarks + Study Notes (blueprint §3.7 + §5.6 + §5.7).

── Bookmarks ────────────────────────────────────────────────────────────────
GET    /api/library/bookmarks           — list (filterable)
GET    /api/library/bookmarks/{id}      — get one
POST   /api/library/bookmarks           — create
PATCH  /api/library/bookmarks/{id}      — partial update
DELETE /api/library/bookmarks/{id}      — delete one
DELETE /api/library/bookmarks           — bulk delete all

── Study Notes ──────────────────────────────────────────────────────────────
GET    /api/library/notes               — list (filterable + searchable)
GET    /api/library/notes/{id}          — get one
POST   /api/library/notes               — create
PUT    /api/library/notes/{id}          — full/partial update
DELETE /api/library/notes/{id}          — delete one
DELETE /api/library/notes               — bulk delete (body: {"ids": [...]})
"""

import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.middleware.auth import get_current_user
from ...api.schemas import (
    BookmarkListResponse,
    BookmarkOut,
    CreateBookmarkRequest,
    CreateNoteRequest,
    NoteListResponse,
    NoteOut,
    UpdateBookmarkRequest,
    UpdateNoteRequest,
)
from ...db.gamification import append_event, award_xp_for_event
from ...db.models import Bookmark, StudyNote, User
from ...db.session import get_db

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _bookmark_to_out(b: Bookmark) -> BookmarkOut:
    return BookmarkOut(
        id=b.id,
        title=b.title,
        subject=b.subject,
        lesson_id=b.lesson_id,
        path=b.path,
        saved_at=b.saved_at.isoformat(),
        updated_at=b.updated_at.isoformat(),
    )


def _note_to_out(n: StudyNote) -> NoteOut:
    return NoteOut(
        id=n.id,
        title=n.title,
        content=n.content,
        subject=n.subject,
        tags=n.tags or [],
        color=n.color,
        created_at=n.created_at.isoformat(),
        updated_at=n.updated_at.isoformat(),
    )


# ============================================================================
# BOOKMARKS
# ============================================================================

@router.get("/bookmarks", response_model=BookmarkListResponse)
async def list_bookmarks(
    subject: str = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Bookmark)
        .where(Bookmark.user_id == user.id)
        .order_by(Bookmark.saved_at.desc())
        .limit(limit)
    )
    if subject:
        stmt = stmt.where(Bookmark.subject == subject)
    result = await db.execute(stmt)
    bookmarks = result.scalars().all()
    return BookmarkListResponse(bookmarks=[_bookmark_to_out(b) for b in bookmarks], total=len(bookmarks))


@router.get("/bookmarks/{bookmark_id}", response_model=BookmarkOut)
async def get_bookmark(
    bookmark_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Bookmark).where(Bookmark.id == bookmark_id, Bookmark.user_id == user.id)
    )
    b = result.scalar_one_or_none()
    if not b:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    return _bookmark_to_out(b)


@router.post("/bookmarks", response_model=BookmarkOut, status_code=status.HTTP_201_CREATED)
async def create_bookmark(
    request: CreateBookmarkRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    b = Bookmark(
        id=str(uuid.uuid4()),
        user_id=user.id,
        title=request.title,
        subject=request.subject.value,
        lesson_id=request.lesson_id,
        path=request.path,
    )
    db.add(b)

    await append_event(
        db,
        user_id=user.id,
        event_type="bookmark_added",
        subject=request.subject.value,
        entity_type="bookmark",
        entity_id=b.id,
    )
    await award_xp_for_event(db, user.id, "bookmark_added", subject=request.subject.value)

    await db.commit()
    await db.refresh(b)
    return _bookmark_to_out(b)


@router.patch("/bookmarks/{bookmark_id}", response_model=BookmarkOut)
async def update_bookmark(
    bookmark_id: str,
    request: UpdateBookmarkRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Bookmark).where(Bookmark.id == bookmark_id, Bookmark.user_id == user.id)
    )
    b = result.scalar_one_or_none()
    if not b:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    if request.title is not None:
        b.title = request.title
    if request.subject is not None:
        b.subject = request.subject.value
    if request.lesson_id is not None:
        b.lesson_id = request.lesson_id
    if request.path is not None:
        b.path = request.path
    b.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(b)
    return _bookmark_to_out(b)


@router.delete("/bookmarks/{bookmark_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bookmark(
    bookmark_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Bookmark).where(Bookmark.id == bookmark_id, Bookmark.user_id == user.id)
    )
    b = result.scalar_one_or_none()
    if not b:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    await append_event(
        db,
        user_id=user.id,
        event_type="bookmark_removed",
        subject=b.subject,
        entity_type="bookmark",
        entity_id=bookmark_id,
    )
    await db.delete(b)
    await db.commit()


@router.delete("/bookmarks", status_code=status.HTTP_204_NO_CONTENT)
async def delete_all_bookmarks(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Bookmark).where(Bookmark.user_id == user.id))
    for b in result.scalars().all():
        await db.delete(b)
    await db.commit()


# ============================================================================
# STUDY NOTES
# ============================================================================

@router.get("/notes", response_model=NoteListResponse)
async def list_notes(
    subject: str = Query(default=None),
    color: str = Query(default=None),
    q: str = Query(default=None, description="Full-text search in title + content"),
    limit: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(StudyNote)
        .where(StudyNote.user_id == user.id)
        .order_by(StudyNote.updated_at.desc())
        .limit(limit)
    )
    if subject:
        stmt = stmt.where(StudyNote.subject == subject)
    if color:
        stmt = stmt.where(StudyNote.color == color)
    result = await db.execute(stmt)
    notes = result.scalars().all()

    # Simple in-process search (SQLite FTS is not set up)
    if q:
        q_lower = q.lower()
        notes = [
            n for n in notes
            if q_lower in n.title.lower() or q_lower in n.content.lower()
        ]

    return NoteListResponse(notes=[_note_to_out(n) for n in notes], total=len(notes))


@router.get("/notes/{note_id}", response_model=NoteOut)
async def get_note(
    note_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(StudyNote).where(StudyNote.id == note_id, StudyNote.user_id == user.id)
    )
    n = result.scalar_one_or_none()
    if not n:
        raise HTTPException(status_code=404, detail="Note not found")
    return _note_to_out(n)


@router.post("/notes", response_model=NoteOut, status_code=status.HTTP_201_CREATED)
async def create_note(
    request: CreateNoteRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    n = StudyNote(
        id=str(uuid.uuid4()),
        user_id=user.id,
        title=request.title,
        content=request.content,
        subject=request.subject.value if request.subject else None,
        tags=request.tags,
        color=request.color,
    )
    db.add(n)

    await append_event(
        db,
        user_id=user.id,
        event_type="note_created",
        subject=n.subject,
        entity_type="note",
        entity_id=n.id,
    )
    await award_xp_for_event(db, user.id, "note_created", subject=n.subject)

    await db.commit()
    await db.refresh(n)
    return _note_to_out(n)


@router.put("/notes/{note_id}", response_model=NoteOut)
async def update_note(
    note_id: str,
    request: UpdateNoteRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(StudyNote).where(StudyNote.id == note_id, StudyNote.user_id == user.id)
    )
    n = result.scalar_one_or_none()
    if not n:
        raise HTTPException(status_code=404, detail="Note not found")

    if request.title is not None:
        n.title = request.title
    if request.content is not None:
        n.content = request.content
    if request.subject is not None:
        n.subject = request.subject.value
    if request.tags is not None:
        n.tags = request.tags
    if request.color is not None:
        n.color = request.color
    n.updated_at = datetime.utcnow()

    await append_event(
        db,
        user_id=user.id,
        event_type="note_updated",
        entity_type="note",
        entity_id=note_id,
    )
    await db.commit()
    await db.refresh(n)
    return _note_to_out(n)


@router.delete("/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    note_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(StudyNote).where(StudyNote.id == note_id, StudyNote.user_id == user.id)
    )
    n = result.scalar_one_or_none()
    if not n:
        raise HTTPException(status_code=404, detail="Note not found")
    await append_event(db, user_id=user.id, event_type="note_deleted", entity_type="note", entity_id=note_id)
    await db.delete(n)
    await db.commit()


@router.delete("/notes", status_code=status.HTTP_204_NO_CONTENT)
async def bulk_delete_notes(
    ids: list[str] = Body(..., description="Array of note UUIDs to delete"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(StudyNote).where(StudyNote.id.in_(ids), StudyNote.user_id == user.id)
    )
    for n in result.scalars().all():
        await db.delete(n)
    await db.commit()
