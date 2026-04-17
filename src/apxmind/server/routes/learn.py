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

import asyncio
import io
import json
import logging
import re
import shutil
import time
import uuid
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from sqlalchemy import desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.middleware.auth import get_current_user
from ...api.schemas import (
    ChapterBriefOut,
    GenerateChapterBriefRequest,
    GenerateRevisionSheetRequest,
    GenerateSessionNotesRequest,
    CheckpointOut,
    LessonMissionContextOut,
    LearnSessionSummaryOut,
    MessageListResponse,
    MessageOut,
    NotebookSourceListOut,
    NotebookSourceOut,
    NotebookUploadSourceOut,
    RevisionSheetItemOut,
    RevisionSheetOut,
    SessionNotesOut,
    SetSourceLockRequest,
    SessionModeOut,
    SourceCitationOut,
    SourceLockOut,
    SendMessageRequest,
    SubmitCheckpointRequest,
    SetSessionModeRequest,
    SessionListResponse,
    SessionOut,
    StartSessionRequest,
)
from ...db.gamification import append_event, award_xp_for_event
from ...core.dependencies import get_llm, get_settings, get_vectorstore
from ...core.language import language_name, normalize_language, resolve_request_language
from ...db.models import ChatMessage, LearningEvent, LearningSession, Lesson, Progress, QueryEvent, StudyNote, Subject, User
from ...db.session import get_db

logger = logging.getLogger(__name__)
router = APIRouter()

VALID_TUTOR_MODES = {"guided", "revision", "drill"}
SUPPORTED_NOTE_OUTPUT_LANGUAGES = ["en", "ta"]
NOTEBOOK_UPLOAD_MODES = {"quick", "full"}

_PROJECT_ROOT = Path(__file__).resolve().parents[4]
_NOTEBOOK_UPLOAD_ROOT = _PROJECT_ROOT / "data" / "uploads" / "notebook"
_NOTEBOOK_MAX_FILE_BYTES = 15 * 1024 * 1024
_NOTEBOOK_MAX_CONTEXT_CHARS = 12000
_NOTEBOOK_CHUNK_SIZE = 1200
_NOTEBOOK_CHUNK_OVERLAP = 180
_NOTEBOOK_RETRIEVAL_K = 6
_STOPWORDS = {
    "the", "and", "for", "that", "with", "from", "into", "this", "what", "when",
    "where", "which", "about", "have", "your", "their", "were", "been", "will",
    "would", "could", "should", "explain", "please", "give", "show",
}


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
        msg_metadata=m.msg_metadata,
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


def _build_mode_instruction(mode: str | None) -> str:
    if mode == "revision":
        return (
            "Tutor mode: revision. Keep responses concise and high-yield. "
            "Prioritize key formulas, memory hooks, and exam traps."
        )
    if mode == "drill":
        return (
            "Tutor mode: drill. Use exam-oriented questioning style. "
            "Give short checks and challenge prompts before full explanations."
        )
    if mode == "guided":
        return (
            "Tutor mode: guided. Teach step-by-step with beginner-friendly progression."
        )
    return ""


def _normalize_tutor_mode(mode: str | None) -> str:
    candidate = (mode or "").strip().lower()
    if candidate not in VALID_TUTOR_MODES:
        raise HTTPException(status_code=422, detail="Invalid tutor mode")
    return candidate


def _normalize_output_language(language: str | None) -> str:
    normalized = normalize_language(language)
    return normalized if normalized in SUPPORTED_NOTE_OUTPUT_LANGUAGES else "en"


def _normalize_notebook_upload_mode(mode: str | None) -> str:
    candidate = (mode or "quick").strip().lower()
    if candidate not in NOTEBOOK_UPLOAD_MODES:
        raise HTTPException(status_code=422, detail="Invalid upload mode. Use 'quick' or 'full'.")
    return candidate


def _sanitize_filename(filename: str | None) -> str:
    raw = (filename or "uploaded.pdf").strip()
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", raw).strip("._")
    if not cleaned:
        cleaned = "uploaded.pdf"
    if not cleaned.lower().endswith(".pdf"):
        cleaned = f"{cleaned}.pdf"
    return cleaned


def _session_upload_dir(user_id: int, session_id: str) -> Path:
    return _NOTEBOOK_UPLOAD_ROOT / f"user_{user_id}" / f"session_{session_id}"


def _source_upload_dir(user_id: int, session_id: str, source_id: str) -> Path:
    return _session_upload_dir(user_id, session_id) / source_id


def _source_meta_path(user_id: int, session_id: str, source_id: str) -> Path:
    return _source_upload_dir(user_id, session_id, source_id) / "meta.json"


def _source_chunks_path(user_id: int, session_id: str, source_id: str) -> Path:
    return _source_upload_dir(user_id, session_id, source_id) / "chunks.json"


def _load_pdf_pages(pdf_bytes: bytes) -> tuple[list[dict], int]:
    try:
        from pypdf import PdfReader
    except Exception as exc:  # pragma: no cover - import guard
        raise HTTPException(status_code=500, detail=f"PDF reader dependency missing: {exc}")

    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid or unreadable PDF file: {exc}")

    page_total = len(reader.pages)
    pages: list[dict] = []
    for idx, page in enumerate(reader.pages, start=1):
        try:
            text = (page.extract_text() or "").replace("\x00", " ")
        except Exception:
            text = ""
        normalized = re.sub(r"[ \t]+", " ", text).strip()
        if normalized:
            pages.append({"page": idx, "text": normalized})

    return pages, page_total


def _chunk_text(text: str, chunk_size: int = _NOTEBOOK_CHUNK_SIZE, overlap: int = _NOTEBOOK_CHUNK_OVERLAP) -> list[str]:
    if not text:
        return []

    safe_overlap = min(max(overlap, 0), max(chunk_size // 2, 1))
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = end - safe_overlap
    return chunks


def _build_page_chunks(pages: list[dict]) -> list[dict]:
    rows: list[dict] = []
    for page_item in pages:
        page_no = int(page_item.get("page") or 0)
        page_text = str(page_item.get("text") or "")
        if not page_no or not page_text:
            continue

        for idx, chunk in enumerate(_chunk_text(page_text), start=1):
            rows.append({
                "page": page_no,
                "chunk_index": idx,
                "text": chunk,
            })
    return rows


def _notebook_collection_name(user_id: int, session_id: str) -> str:
    session_token = re.sub(r"[^a-z0-9]", "", session_id.lower())[:20] or "session"
    return f"APXMIND_notebook_u{user_id}_{session_token}"


def _get_notebook_collection(user_id: int, session_id: str):
    try:
        import chromadb
        from chromadb.config import Settings as ChromaSettings
        from chromadb.utils import embedding_functions
    except Exception as exc:  # pragma: no cover - import guard
        raise HTTPException(status_code=500, detail=f"Notebook retrieval dependencies missing: {exc}")

    settings = get_settings()
    persist_dir = Path(settings.chroma_persist_dir)
    persist_dir.mkdir(parents=True, exist_ok=True)

    client = chromadb.PersistentClient(
        path=str(persist_dir),
        settings=ChromaSettings(anonymized_telemetry=False, allow_reset=True),
    )

    embed_fn = embedding_functions.OllamaEmbeddingFunction(
        url=f"{settings.ollama_base_url.rstrip('/')}/api/embeddings",
        model_name=settings.embedding_model,
    )

    collection_name = _notebook_collection_name(user_id, session_id)
    return client.get_or_create_collection(
        name=collection_name,
        embedding_function=embed_fn,
        metadata={"scope": "notebook_upload", "session_id": session_id, "user_id": str(user_id)},
    )


def _save_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_notebook_sources(user_id: int, session_id: str) -> list[dict]:
    session_dir = _session_upload_dir(user_id, session_id)
    if not session_dir.exists():
        return []

    items: list[dict] = []
    for source_dir in session_dir.iterdir():
        if not source_dir.is_dir():
            continue

        meta_path = source_dir / "meta.json"
        if not meta_path.exists():
            continue

        try:
            raw = _load_json(meta_path)
        except Exception:
            continue

        if not isinstance(raw, dict):
            continue

        source_id = str(raw.get("source_id") or source_dir.name)
        raw_mode = str(raw.get("index_mode") or "quick").strip().lower()
        index_mode = raw_mode if raw_mode in NOTEBOOK_UPLOAD_MODES else "quick"

        items.append({
            "source_id": source_id,
            "file_name": str(raw.get("file_name") or "uploaded.pdf"),
            "file_size_bytes": int(raw.get("file_size_bytes") or 0),
            "page_count": int(raw.get("page_count") or 0),
            "text_characters": int(raw.get("text_characters") or 0),
            "index_mode": index_mode,
            "indexed": bool(raw.get("indexed")),
            "chunk_count": int(raw.get("chunk_count") or 0),
            "uploaded_at": str(raw.get("uploaded_at") or datetime.utcnow().isoformat()),
        })

    items.sort(key=lambda row: row.get("uploaded_at", ""), reverse=True)
    return items


def _tokenize_query(text: str) -> list[str]:
    tokens = [token.lower() for token in re.findall(r"[A-Za-z0-9]{3,}", text)]
    filtered = [token for token in tokens if token not in _STOPWORDS]
    return filtered[:20]


def _score_chunk_against_query(chunk_text: str, query_tokens: list[str], query_raw: str) -> float:
    lowered = chunk_text.lower()
    score = 0.0
    for token in query_tokens:
        if token in lowered:
            score += 3.0

    query_phrase = query_raw.strip().lower()
    if query_phrase and len(query_phrase) > 6 and query_phrase in lowered:
        score += 5.0

    score += min(len(chunk_text) / 400.0, 2.0)
    return score


def _quick_context_from_chunks(chunks: list[dict], query: str, max_chunks: int = _NOTEBOOK_RETRIEVAL_K) -> tuple[str, list[dict]]:
    if not chunks:
        return "", []

    query_tokens = _tokenize_query(query)
    scored = []
    for idx, chunk in enumerate(chunks):
        text = str(chunk.get("text") or "").strip()
        if not text:
            continue
        scored.append((
            _score_chunk_against_query(text, query_tokens, query),
            idx,
            chunk,
        ))

    if not scored:
        return "", []

    scored.sort(key=lambda row: (row[0], -row[1]), reverse=True)
    selected = [row[2] for row in scored[:max_chunks]]

    context_blocks: list[str] = []
    citations: list[dict] = []
    total_chars = 0

    for index, row in enumerate(selected, start=1):
        snippet = str(row.get("text") or "").strip()
        if not snippet:
            continue

        title = str(row.get("file_name") or "Uploaded PDF")
        page_raw = row.get("page")
        page = int(page_raw) if isinstance(page_raw, int) else None
        source_id = str(row.get("source_id") or f"upload-{index}")

        context_piece = f"[{title}{f' p.{page}' if page else ''}] {snippet}"
        if total_chars + len(context_piece) > _NOTEBOOK_MAX_CONTEXT_CHARS:
            break
        context_blocks.append(context_piece)
        total_chars += len(context_piece)

        citations.append({
            "source_id": f"{source_id}:{page if page is not None else index}:{index}",
            "title": title,
            "page": page,
            "snippet": snippet[:260] + ("..." if len(snippet) > 260 else ""),
            "source": f"uploaded://{title}",
        })

    return "\n\n".join(context_blocks), citations


def _compose_uploaded_chunks(user_id: int, session_id: str) -> list[dict]:
    chunks: list[dict] = []
    for source in _read_notebook_sources(user_id, session_id):
        chunk_path = _source_chunks_path(user_id, session_id, source["source_id"])
        if not chunk_path.exists():
            continue

        try:
            raw = _load_json(chunk_path)
        except Exception:
            continue

        if not isinstance(raw, list):
            continue

        for row in raw:
            if not isinstance(row, dict):
                continue
            text = str(row.get("text") or "").strip()
            if not text:
                continue
            page_raw = row.get("page")
            page = int(page_raw) if isinstance(page_raw, int) else None
            chunks.append({
                "source_id": source["source_id"],
                "file_name": source["file_name"],
                "page": page,
                "text": text,
            })
    return chunks


async def _query_uploaded_collection(query: str, user_id: int, session_id: str, subject: str) -> tuple[str, list[dict]]:
    try:
        collection = _get_notebook_collection(user_id, session_id)
    except HTTPException:
        return "", []

    try:
        result = await asyncio.to_thread(
            collection.query,
            query_texts=[query],
            n_results=_NOTEBOOK_RETRIEVAL_K,
            include=["documents", "metadatas", "distances"],
        )
    except Exception as exc:
        logger.warning(f"Notebook Chroma retrieval failed: {exc}")
        return "", []

    docs_raw = result.get("documents") if isinstance(result, dict) else None
    metas_raw = result.get("metadatas") if isinstance(result, dict) else None

    docs = docs_raw[0] if isinstance(docs_raw, list) and docs_raw else []
    metas = metas_raw[0] if isinstance(metas_raw, list) and metas_raw else []

    context_rows: list[str] = []
    citations: list[dict] = []
    used_keys: set[str] = set()
    total_chars = 0

    for idx, doc in enumerate(docs):
        text = str(doc or "").strip()
        if not text:
            continue

        meta = metas[idx] if idx < len(metas) and isinstance(metas[idx], dict) else {}
        title = str(meta.get("file_name") or "Uploaded PDF")
        source_id = str(meta.get("source_id") or f"upload-{idx + 1}")
        page_raw = meta.get("page")
        page = int(page_raw) if isinstance(page_raw, int) else None
        key = f"{source_id}:{page if page is not None else idx}"
        if key in used_keys:
            continue
        used_keys.add(key)

        context_piece = f"[{title}{f' p.{page}' if page else ''}] {text}"
        if total_chars + len(context_piece) > _NOTEBOOK_MAX_CONTEXT_CHARS:
            break
        context_rows.append(context_piece)
        total_chars += len(context_piece)

        citations.append({
            "source_id": key,
            "title": title,
            "page": page,
            "subject": subject,
            "snippet": text[:260] + ("..." if len(text) > 260 else ""),
            "source": f"uploaded://{title}",
        })

    return "\n\n".join(context_rows), citations


async def _upsert_uploaded_chunks_to_chroma(
    user_id: int,
    session_id: str,
    source_id: str,
    file_name: str,
    uploaded_at: str,
    chunks: list[dict],
) -> int:
    if not chunks:
        return 0

    collection = _get_notebook_collection(user_id, session_id)

    ids: list[str] = []
    docs: list[str] = []
    metas: list[dict] = []

    for idx, row in enumerate(chunks, start=1):
        text = str(row.get("text") or "").strip()
        if not text:
            continue
        page_raw = row.get("page")
        page = int(page_raw) if isinstance(page_raw, int) else None

        ids.append(f"{source_id}:{idx}")
        docs.append(text)

        meta = {
            "source_id": source_id,
            "file_name": file_name,
            "uploaded_at": uploaded_at,
            "session_id": session_id,
            "user_id": str(user_id),
            "chunk_index": idx,
        }
        if page is not None:
            meta["page"] = page
        metas.append(meta)

    if not ids:
        return 0

    await asyncio.to_thread(collection.upsert, ids=ids, documents=docs, metadatas=metas)
    return len(ids)


async def _answer_from_uploaded_context(
    query: str,
    language: str,
    mode: str | None,
    source_locked: bool,
    context: str,
    source_scope_hint: str,
) -> str:
    if not context.strip():
        if source_locked:
            return _not_found_in_source(language)
        return ""

    mode_instruction = _build_mode_instruction(mode)
    source_rule = (
        "You MUST answer only from the source context. "
        "If evidence is missing, say exactly: Not found in source."
        if source_locked
        else "Use the source context as primary evidence. If context is partial, clearly label assumptions."
    )

    prompt_text = f"""You are APXMIND Notebook Tutor.
Write the answer in {language_name(language)}.
{source_rule}
{mode_instruction}

Question:
{query}

Session Scope:
{source_scope_hint}

Source Context:
{context}
"""

    return (await _generate_markdown_with_llm(prompt_text)).strip()


def _summary_context_from_chunks(chunks: list[dict], max_chunks: int = 10, max_chars: int = 6000) -> str:
    blocks: list[str] = []
    total_chars = 0

    for row in chunks[:max_chunks]:
        text = str(row.get("text") or "").strip()
        if not text:
            continue

        page_raw = row.get("page")
        page = int(page_raw) if isinstance(page_raw, int) else None
        prefix = f"[Page {page}] " if page is not None else ""
        piece = f"{prefix}{text}"

        if total_chars + len(piece) > max_chars:
            break

        blocks.append(piece)
        total_chars += len(piece)

    return "\n\n".join(blocks)


async def _summarize_uploaded_pdf(file_name: str, chunks: list[dict], language: str) -> str:
    context = _summary_context_from_chunks(chunks)
    if not context.strip():
        return (
            f"## Uploaded PDF Summary\n"
            f"File: {file_name}\n\n"
            "- I could not extract readable text from this PDF yet."
        )

    prompt_text = f"""Create a concise study summary of this uploaded PDF.
Write the summary in {language_name(language)}.

File: {file_name}
Extracted Context:
{context}

Return markdown with exactly these sections:
## What This PDF Covers
## Key Concepts
## How To Study This

Keep it brief and practical (6-10 bullets total).
"""

    summary = ""
    try:
        summary = (await asyncio.wait_for(_generate_markdown_with_llm(prompt_text), timeout=35)).strip()
    except asyncio.TimeoutError:
        logger.warning("Uploaded PDF summary generation timed out")
    except Exception as exc:
        logger.warning(f"Uploaded PDF summary generation failed: {exc}")

    if summary:
        return summary

    fallback_points: list[str] = []
    for row in chunks[:4]:
        text = str(row.get("text") or "").strip()
        if not text:
            continue
        page_raw = row.get("page")
        page = int(page_raw) if isinstance(page_raw, int) else None
        snippet = text[:180] + ("..." if len(text) > 180 else "")
        page_label = f"p.{page}" if page is not None else "source"
        fallback_points.append(f"- {page_label}: {snippet}")

    if not fallback_points:
        fallback_points.append("- Text was extracted, but summary generation needs a follow-up question.")

    return (
        f"## Uploaded PDF Summary\n"
        f"File: {file_name}\n\n"
        "## What This PDF Covers\n"
        + "\n".join(fallback_points)
    )


@router.post("/sessions/{session_id}/notebook/sources", response_model=NotebookUploadSourceOut)
async def upload_notebook_source(
    session_id: str,
    index_mode: str = Form("quick"),
    language: str | None = Form(None),
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await _get_session_or_404(db, session_id, user.id)
    normalized_mode = _normalize_notebook_upload_mode(index_mode)
    selected_language = _normalize_output_language(
        resolve_request_language(
            explicit=language,
            user_preference=user.preferred_language,
        )
    )

    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing PDF filename")

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF uploads are supported")

    safe_name = _sanitize_filename(file.filename)

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Uploaded PDF is empty")
    if len(raw) > _NOTEBOOK_MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="PDF is too large. Limit is 15 MB per file")

    pages, page_count = _load_pdf_pages(raw)
    page_chunks = _build_page_chunks(pages)
    if not page_chunks:
        raise HTTPException(
            status_code=400,
            detail="Could not extract readable text from this PDF. Try a digital-text PDF.",
        )

    source_id = str(uuid.uuid4())
    uploaded_at = datetime.utcnow().isoformat()
    source_dir = _source_upload_dir(user.id, session.id, source_id)
    source_dir.mkdir(parents=True, exist_ok=True)

    file_path = source_dir / safe_name
    file_path.write_bytes(raw)
    _save_json(_source_chunks_path(user.id, session.id, source_id), page_chunks)

    indexed = False
    chunk_count = len(page_chunks)
    if normalized_mode == "full":
        try:
            chunk_count = await _upsert_uploaded_chunks_to_chroma(
                user_id=user.id,
                session_id=session.id,
                source_id=source_id,
                file_name=safe_name,
                uploaded_at=uploaded_at,
                chunks=page_chunks,
            )
            indexed = True
        except HTTPException:
            raise
        except Exception as exc:
            logger.error(f"Notebook source indexing failed: {exc}", exc_info=True)
            raise HTTPException(
                status_code=503,
                detail="Uploaded PDF text was saved, but embedding/indexing failed. Verify embedding service and retry full mode.",
            )

    text_characters = sum(len(str(item.get("text") or "")) for item in page_chunks)
    upload_summary_markdown = await _summarize_uploaded_pdf(
        file_name=safe_name,
        chunks=page_chunks,
        language=selected_language,
    )

    meta_payload = {
        "source_id": source_id,
        "file_name": safe_name,
        "file_size_bytes": len(raw),
        "page_count": page_count,
        "text_characters": text_characters,
        "index_mode": normalized_mode,
        "indexed": indexed,
        "chunk_count": chunk_count,
        "uploaded_at": uploaded_at,
    }
    _save_json(_source_meta_path(user.id, session.id, source_id), meta_payload)

    db.add(
        ChatMessage(
            session_id=session.id,
            role="assistant",
            content=upload_summary_markdown,
            tier="upload-summary",
            msg_metadata={
                "event": "notebook_upload_summary",
                "source_id": source_id,
                "file_name": safe_name,
                "upload_mode": normalized_mode,
                "output_language": selected_language,
                "indexed": indexed,
            },
        )
    )

    await append_event(
        db,
        user_id=user.id,
        event_type="learn_notebook_source_uploaded",
        subject=session.subject,
        entity_type="session",
        entity_id=session.id,
        payload={
            "source_id": source_id,
            "file_name": safe_name,
            "index_mode": normalized_mode,
            "indexed": indexed,
            "chunk_count": chunk_count,
            "summary_generated": bool(upload_summary_markdown.strip()),
        },
    )
    await db.commit()

    return NotebookUploadSourceOut(
        session_id=session.id,
        upload_summary_markdown=upload_summary_markdown,
        **meta_payload,
    )


@router.get("/sessions/{session_id}/notebook/sources", response_model=NotebookSourceListOut)
async def list_notebook_sources(
    session_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await _get_session_or_404(db, session_id, user.id)
    sources = [NotebookSourceOut(**row) for row in _read_notebook_sources(user.id, session.id)]
    return NotebookSourceListOut(session_id=session.id, sources=sources)


@router.delete("/sessions/{session_id}/notebook/sources/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notebook_source(
    session_id: str,
    source_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await _get_session_or_404(db, session_id, user.id)
    source_dir = _source_upload_dir(user.id, session.id, source_id)
    if not source_dir.exists() or not source_dir.is_dir():
        raise HTTPException(status_code=404, detail="Notebook source not found")

    meta_path = _source_meta_path(user.id, session.id, source_id)
    indexed = False
    if meta_path.exists():
        try:
            raw = _load_json(meta_path)
            if isinstance(raw, dict):
                indexed = bool(raw.get("indexed"))
        except Exception:
            indexed = False

    if indexed:
        try:
            collection = _get_notebook_collection(user.id, session.id)
            await asyncio.to_thread(collection.delete, where={"source_id": source_id})
        except Exception as exc:
            logger.warning(f"Notebook source vector cleanup failed for {source_id}: {exc}")

    shutil.rmtree(source_dir, ignore_errors=True)

    await append_event(
        db,
        user_id=user.id,
        event_type="learn_notebook_source_deleted",
        subject=session.subject,
        entity_type="session",
        entity_id=session.id,
        payload={"source_id": source_id},
    )
    await db.commit()


def _not_found_in_source(language: str) -> str:
    if normalize_language(language) == "ta":
        return "தேர்ந்தெடுக்கப்பட்ட மூலத்தில் இந்த கேள்விக்கு ஆதாரம் கிடைக்கவில்லை."
    return "Not found in source."


def _safe_float(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _citation_payload_from_doc(doc: object, fallback_subject: str, index: int) -> dict:
    metadata = getattr(doc, "metadata", {}) or {}
    title = metadata.get("title") or metadata.get("chapter") or metadata.get("source") or f"Source {index}"
    page_raw = metadata.get("page")
    page = int(page_raw) if isinstance(page_raw, int) else None
    content = str(getattr(doc, "page_content", "") or "").strip().replace("\n", " ")
    snippet = content[:260] + ("..." if len(content) > 260 else "")
    source_ref = metadata.get("source") or metadata.get("path")

    return {
        "source_id": f"{title}:{page if page is not None else index}",
        "title": str(title),
        "page": page,
        "subject": str(metadata.get("subject") or fallback_subject),
        "snippet": snippet,
        "source": str(source_ref) if source_ref else None,
    }


async def _retrieve_subject_docs(subject: str, query: str, k: int = 5) -> list[object]:
    store = get_vectorstore(subject)
    if store is None:
        return []

    try:
        retriever = store.as_retriever(search_kwargs={"k": k})
        docs = await asyncio.to_thread(retriever.invoke, query)
        return list(docs or [])
    except Exception as exc:
        logger.warning(f"Source retrieval failed for subject={subject}: {exc}")
        return []


def _coerce_citation(raw: object, index: int) -> SourceCitationOut | None:
    if not isinstance(raw, dict):
        return None

    title = str(raw.get("title") or raw.get("source") or f"Source {index}")
    page_raw = raw.get("page")
    page = int(page_raw) if isinstance(page_raw, int) else None
    snippet = str(raw.get("snippet") or "").strip()
    source_id = str(raw.get("source_id") or f"{title}:{page if page is not None else index}")

    return SourceCitationOut(
        source_id=source_id,
        title=title,
        page=page,
        subject=str(raw.get("subject")) if raw.get("subject") else None,
        snippet=snippet,
        source=str(raw.get("source")) if raw.get("source") else None,
    )


def _coerce_citations(raw_sources: object) -> list[SourceCitationOut]:
    if not isinstance(raw_sources, list):
        return []

    citations: list[SourceCitationOut] = []
    for index, row in enumerate(raw_sources, start=1):
        citation = _coerce_citation(row, index)
        if citation:
            citations.append(citation)
    return citations


def _default_brief_markdown(subject: str, lesson_title: str, language: str) -> str:
    if language == "ta":
        return (
            f"## அத்தியாய சுருக்கம்\n"
            f"பாடம்: {lesson_title or subject}\n\n"
            "இந்த அத்தியாயத்திற்கான நம்பகமான மூல குறிப்புகள் கிடைக்கவில்லை. "
            "அரட்டை உரையாடலை தொடர்ந்து உருவாக்குங்கள்; பிறகு சுருக்கத்தை மீண்டும் உருவாக்கலாம்."
        )

    return (
        f"## Chapter Brief\n"
        f"Lesson: {lesson_title or subject}\n\n"
        "Reliable source snippets are not available yet for this lesson. "
        "Continue a few evidence-backed chat turns and generate the brief again."
    )


async def _resolve_source_lock_state(session_id: str, user_id: int, db: AsyncSession) -> tuple[bool, str]:
    event_result = await db.execute(
        select(LearningEvent)
        .where(
            LearningEvent.user_id == user_id,
            LearningEvent.event_type == "learn_source_lock_set",
            LearningEvent.entity_type == "session",
            LearningEvent.entity_id == session_id,
        )
        .order_by(desc(LearningEvent.occurred_at))
        .limit(1)
    )
    latest_event = event_result.scalar_one_or_none()
    if latest_event and isinstance(latest_event.payload, dict):
        enabled = bool(latest_event.payload.get("enabled"))
        return enabled, latest_event.occurred_at.isoformat()

    return False, datetime.utcnow().isoformat()


async def _load_source_scope_hint(db: AsyncSession, session: LearningSession) -> str:
    if not session.lesson_id:
        return f"Subject scope: {session.subject}"

    lesson_result = await db.execute(select(Lesson).where(Lesson.id == session.lesson_id))
    lesson = lesson_result.scalar_one_or_none()
    if not lesson:
        return f"Subject scope: {session.subject}"

    parts: list[str] = [f"Lesson: {lesson.title}"]
    if lesson.description:
        parts.append(f"Description: {lesson.description}")
    if isinstance(lesson.topics, list) and lesson.topics:
        topic_list = ", ".join(str(topic) for topic in lesson.topics[:8])
        parts.append(f"Focus topics: {topic_list}")

    return " | ".join(parts)


async def _collect_checkpoint_events(session_id: str, user_id: int, db: AsyncSession) -> list[LearningEvent]:
    result = await db.execute(
        select(LearningEvent)
        .where(
            LearningEvent.user_id == user_id,
            LearningEvent.event_type == "learn_checkpoint_submitted",
            LearningEvent.entity_type == "session",
            LearningEvent.entity_id == session_id,
        )
        .order_by(desc(LearningEvent.occurred_at))
        .limit(100)
    )
    return list(result.scalars().all())


def _checkpoint_items_from_events(events: list[LearningEvent]) -> list[RevisionSheetItemOut]:
    items: list[RevisionSheetItemOut] = []
    for event in events:
        payload = event.payload if isinstance(event.payload, dict) else {}
        concept_key = str(payload.get("concept_key") or "Current concept")
        score_raw = payload.get("score_percent")
        score = int(score_raw) if isinstance(score_raw, int) else int(_safe_float(score_raw) or 0)
        confidence_raw = payload.get("confidence")
        confidence = int(confidence_raw) if isinstance(confidence_raw, int) else None

        if score >= 80:
            priority = "low"
        elif score >= 60:
            priority = "medium"
        else:
            priority = "high"

        items.append(
            RevisionSheetItemOut(
                concept_key=concept_key,
                score_percent=max(0, min(100, score)),
                confidence=confidence,
                priority=priority,
            )
        )
    return items


async def _generate_markdown_with_llm(prompt_text: str) -> str:
    try:
        from langchain_core.output_parsers import StrOutputParser
        from langchain_core.prompts import PromptTemplate

        llm = get_llm()
        chain = PromptTemplate.from_template("{prompt_text}") | llm | StrOutputParser()
        return await asyncio.to_thread(chain.invoke, {"prompt_text": prompt_text})
    except Exception as exc:
        logger.warning(f"LLM markdown generation failed: {exc}")
        return ""


def _score_checkpoint_response(concept_key: str, response_text: str, confidence: int | None) -> int:
    score = 35
    normalized = response_text.strip().lower()

    if len(response_text.strip()) >= 40:
        score += 20
    if len(response_text.strip()) >= 90:
        score += 10

    concept_terms = [
        token.strip().lower()
        for token in concept_key.replace("/", " ").replace("-", " ").split()
        if len(token.strip()) > 2
    ]
    if concept_terms and any(term in normalized for term in concept_terms):
        score += 20

    if any(marker in normalized for marker in ["because", "therefore", "hence", "so"]):
        score += 10

    if confidence is not None:
        if confidence >= 70:
            score += 5
        elif confidence <= 30:
            score -= 5

    return max(0, min(100, score))


def _checkpoint_feedback(score_percent: int, concept_key: str) -> str:
    if score_percent >= 80:
        return f"Great checkpoint. Your understanding of {concept_key} looks strong."
    if score_percent >= 60:
        return f"Good attempt. Revisit one more worked example on {concept_key} to lock it in."
    return f"Needs reinforcement. Review {concept_key} basics and try one guided question now."


def _run_ai(
    query: str,
    subject: str,
    language: str,
    mode: str | None = None,
    source_locked: bool = False,
    source_scope_hint: str | None = None,
) -> tuple[str, str, float, list[dict], str]:
    """Run the tiered AI pipeline. Returns (answer, tier, latency_ms, citations, method)."""
    start = time.time()
    try:
        from ...api.agents import classify_intent, retriever_agent, orchestrator_agent

        llm = get_llm()
        intent_result = classify_intent(query, subject)
        intent = intent_result.get("intent", "complex")
        detected_subject = intent_result.get("subject", subject)

        mode_instruction = _build_mode_instruction(mode)
        effective_query = query
        if mode_instruction:
            effective_query = f"{query}\n\n{mode_instruction}"
        if source_scope_hint:
            effective_query = f"{effective_query}\n\nSource scope: {source_scope_hint}"

        if source_locked:
            vs = get_vectorstore(subject)
            result = retriever_agent(
                query=effective_query,
                vectorstore=vs,
                llm=llm,
                subject=subject,
                language=language,
                source_locked=True,
            )
            tier = "tier-1"
        elif intent in ("simple", "retrieval"):
            vs = get_vectorstore(detected_subject)
            result = retriever_agent(
                query=effective_query,
                vectorstore=vs,
                llm=llm,
                subject=detected_subject,
                language=language,
                source_locked=False,
            )
            tier = "tier-1"
        else:
            vectorstores = {
                "biology": get_vectorstore("biology"),
                "chemistry": get_vectorstore("chemistry"),
                "physics": get_vectorstore("physics"),
            }
            result = orchestrator_agent(
                query=effective_query,
                vectorstores=vectorstores,
                llm=llm,
                subject=detected_subject,
                language=language,
            )
            tier = "tier-2"

        answer = result.get("answer", "")
        citations = result.get("sources", []) if isinstance(result, dict) else []
        method = str(result.get("method", "unknown")) if isinstance(result, dict) else "unknown"
    except Exception as exc:
        logger.warning(f"AI pipeline error: {exc}")
        answer = "I'm unable to process that right now. Please try again."
        tier = "tier-0"
        citations = []
        method = "error"

    latency_ms = round((time.time() - start) * 1000, 2)
    return answer, tier, latency_ms, citations, method


@router.get("/lessons/{lesson_id}/context", response_model=LessonMissionContextOut)
async def get_lesson_context(
    lesson_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    lesson_result = await db.execute(select(Lesson).where(Lesson.id == lesson_id))
    lesson = lesson_result.scalar_one_or_none()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    subject_result = await db.execute(select(Subject).where(Subject.id == lesson.subject_id))
    subject = subject_result.scalar_one_or_none()
    subject_code = subject.name if subject else ""
    subject_display_name = subject.display_name if subject else "Subject"

    topics: list[str] = []
    if isinstance(lesson.topics, list):
        for raw in lesson.topics:
            value = str(raw).strip()
            if value and value not in topics:
                topics.append(value)

    if not topics:
        for chunk in (lesson.description or "").replace(";", ",").split(","):
            value = chunk.strip()
            if value and value not in topics:
                topics.append(value)
            if len(topics) >= 6:
                break

    focus_topics = topics[:6] or [lesson.title]
    estimated_minutes = lesson.estimated_minutes or lesson.estimated_time or 30
    difficulty = (lesson.difficulty or "medium").lower()

    progress_result = await db.execute(
        select(Progress).where(
            Progress.user_id == user.id,
            Progress.lesson_id == lesson_id,
        )
    )
    progress = progress_result.scalar_one_or_none()
    is_completed = bool(progress and progress.completed)

    mission_objectives = [
        f"Understand the core idea behind {lesson.title}.",
        f"Apply {focus_topics[0]} in a NEET-style question.",
        "Identify one mistake pattern to avoid in this topic.",
    ]

    starter_prompts = {
        "guided": f"Teach me {lesson.title} from basics step-by-step.",
        "revision": f"Give me a quick high-yield revision of {lesson.title} with key exam points.",
        "drill": f"Give me 3 NEET-style drill questions on {focus_topics[0]} and check my answers.",
    }

    return LessonMissionContextOut(
        lesson_id=lesson.id,
        subject=subject_code,
        subject_display_name=subject_display_name,
        lesson_title=lesson.title,
        lesson_description=lesson.description,
        difficulty=difficulty,
        estimated_minutes=int(estimated_minutes),
        focus_topics=focus_topics,
        mission_title=f"{subject_display_name} Mission: {lesson.title}",
        mission_objectives=mission_objectives,
        starter_prompts=starter_prompts,
        is_completed=is_completed,
    )


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
# POST /api/learn/sessions/{id}/mode
# ---------------------------------------------------------------------------

@router.post("/sessions/{session_id}/mode", response_model=SessionModeOut)
async def set_session_mode(
    session_id: str,
    request: SetSessionModeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await _get_session_or_404(db, session_id, user.id)
    selected_mode = _normalize_tutor_mode(request.mode)

    await append_event(
        db,
        user_id=user.id,
        event_type="learn_tutor_mode_set",
        subject=session.subject,
        entity_type="session",
        entity_id=session.id,
        payload={"mode": selected_mode},
    )
    await db.commit()

    return SessionModeOut(
        session_id=session.id,
        mode=selected_mode,
        updated_at=datetime.utcnow().isoformat(),
    )


# ---------------------------------------------------------------------------
# GET /api/learn/sessions/{id}/mode
# ---------------------------------------------------------------------------

@router.get("/sessions/{session_id}/mode", response_model=SessionModeOut)
async def get_session_mode(
    session_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await _get_session_or_404(db, session_id, user.id)

    event_result = await db.execute(
        select(LearningEvent)
        .where(
            LearningEvent.user_id == user.id,
            LearningEvent.event_type == "learn_tutor_mode_set",
            LearningEvent.entity_type == "session",
            LearningEvent.entity_id == session.id,
        )
        .order_by(desc(LearningEvent.occurred_at))
        .limit(1)
    )
    latest_event = event_result.scalar_one_or_none()
    if latest_event and isinstance(latest_event.payload, dict):
        event_mode = latest_event.payload.get("mode")
        if isinstance(event_mode, str) and event_mode in VALID_TUTOR_MODES:
            return SessionModeOut(
                session_id=session.id,
                mode=event_mode,
                updated_at=latest_event.occurred_at.isoformat(),
            )

    msg_result = await db.execute(
        select(ChatMessage)
        .where(
            ChatMessage.session_id == session.id,
            ChatMessage.role == "assistant",
        )
        .order_by(desc(ChatMessage.created_at))
        .limit(1)
    )
    latest_msg = msg_result.scalar_one_or_none()
    if latest_msg and isinstance(latest_msg.msg_metadata, dict):
        msg_mode = latest_msg.msg_metadata.get("mode")
        if isinstance(msg_mode, str) and msg_mode in VALID_TUTOR_MODES:
            return SessionModeOut(
                session_id=session.id,
                mode=msg_mode,
                updated_at=latest_msg.created_at.isoformat(),
            )

    return SessionModeOut(
        session_id=session.id,
        mode="guided",
        updated_at=datetime.utcnow().isoformat(),
    )


# ---------------------------------------------------------------------------
# POST/GET /api/learn/sessions/{id}/source-lock
# ---------------------------------------------------------------------------

@router.post("/sessions/{session_id}/source-lock", response_model=SourceLockOut)
async def set_session_source_lock(
    session_id: str,
    request: SetSourceLockRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await _get_session_or_404(db, session_id, user.id)

    await append_event(
        db,
        user_id=user.id,
        event_type="learn_source_lock_set",
        subject=session.subject,
        entity_type="session",
        entity_id=session.id,
        payload={"enabled": bool(request.enabled)},
    )
    await db.commit()

    return SourceLockOut(
        session_id=session.id,
        enabled=bool(request.enabled),
        updated_at=datetime.utcnow().isoformat(),
    )


@router.get("/sessions/{session_id}/source-lock", response_model=SourceLockOut)
async def get_session_source_lock(
    session_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await _get_session_or_404(db, session_id, user.id)
    enabled, updated_at = await _resolve_source_lock_state(session.id, user.id, db)

    return SourceLockOut(
        session_id=session.id,
        enabled=enabled,
        updated_at=updated_at,
    )


# ---------------------------------------------------------------------------
# POST /api/learn/sessions/{id}/checkpoint
# ---------------------------------------------------------------------------

@router.post("/sessions/{session_id}/checkpoint", response_model=CheckpointOut)
async def submit_checkpoint(
    session_id: str,
    request: SubmitCheckpointRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await _get_session_or_404(db, session_id, user.id)

    concept_key = request.concept_key.strip()
    response_text = request.response_text.strip()
    score_percent = _score_checkpoint_response(concept_key, response_text, request.confidence)
    feedback = _checkpoint_feedback(score_percent, concept_key)
    created_at = datetime.utcnow().isoformat()

    await append_event(
        db,
        user_id=user.id,
        event_type="learn_checkpoint_submitted",
        subject=session.subject,
        entity_type="session",
        entity_id=session.id,
        event_value=float(score_percent),
        payload={
            "concept_key": concept_key,
            "prompt": request.prompt,
            "response_text": response_text,
            "confidence": request.confidence,
            "score_percent": score_percent,
            "feedback": feedback,
        },
    )
    await db.commit()

    return CheckpointOut(
        session_id=session.id,
        concept_key=concept_key,
        score_percent=score_percent,
        feedback=feedback,
        created_at=created_at,
    )


# ---------------------------------------------------------------------------
# POST /api/learn/sessions/{id}/chapter-brief
# ---------------------------------------------------------------------------

@router.post("/sessions/{session_id}/chapter-brief", response_model=ChapterBriefOut)
async def generate_chapter_brief(
    session_id: str,
    request: GenerateChapterBriefRequest,
    http_request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await _get_session_or_404(db, session_id, user.id)
    selected_language = _normalize_output_language(
        resolve_request_language(
            explicit=request.language,
            header=http_request.headers.get("X-APXMIND-Language"),
            user_preference=user.preferred_language,
        )
    )

    lesson_title = f"{session.subject.title()} Lesson"
    if session.lesson_id:
        lesson_result = await db.execute(select(Lesson).where(Lesson.id == session.lesson_id))
        lesson = lesson_result.scalar_one_or_none()
        if lesson:
            lesson_title = lesson.title

    source_scope_hint = await _load_source_scope_hint(db, session)
    retrieval_query = (
        f"{source_scope_hint}. Generate evidence for key ideas, formulas, common mistakes, "
        "NEET traps, and rapid revision points."
    )
    docs = await _retrieve_subject_docs(session.subject, retrieval_query, 6)
    citations_raw = [_citation_payload_from_doc(doc, session.subject, idx) for idx, doc in enumerate(docs, start=1)]
    citations = _coerce_citations(citations_raw)

    if request.source_locked and not citations:
        markdown = _default_brief_markdown(session.subject, lesson_title, selected_language)
    else:
        context = "\n\n".join(
            f"[{c.title}] {c.snippet}" for c in citations[:6] if c.snippet.strip()
        )
        if not context:
            context = source_scope_hint

        prompt_text = f"""You are creating a NEET chapter brief.
Use ONLY the provided source context.
Write the output in {language_name(selected_language)}.

Lesson: {lesson_title}
Subject: {session.subject}
Source Context:
{context}

Return markdown with exactly these sections:
## Key Ideas
## Formulas
## Common Mistakes
## NEET Traps
## Rapid Revision (10 Points)
"""

        markdown = (await _generate_markdown_with_llm(prompt_text)).strip()
        if not markdown:
            if selected_language == "ta":
                markdown = (
                    f"## அத்தியாய சுருக்கம்\n"
                    f"பாடம்: {lesson_title}\n\n"
                    "## முக்கிய கருத்துகள்\n"
                    + "\n".join(f"- {c.snippet}" for c in citations[:5] if c.snippet)
                )
            else:
                markdown = (
                    f"## Chapter Brief\n"
                    f"Lesson: {lesson_title}\n\n"
                    "## Key Ideas\n"
                    + "\n".join(f"- {c.snippet}" for c in citations[:5] if c.snippet)
                )

    await append_event(
        db,
        user_id=user.id,
        event_type="learn_chapter_brief_generated",
        subject=session.subject,
        entity_type="session",
        entity_id=session.id,
        payload={"language": selected_language, "citations": len(citations)},
    )
    await db.commit()

    return ChapterBriefOut(
        session_id=session.id,
        language=selected_language,
        markdown=markdown,
        citations=citations,
        generated_at=datetime.utcnow().isoformat(),
    )


# ---------------------------------------------------------------------------
# POST /api/learn/sessions/{id}/notes
# ---------------------------------------------------------------------------

@router.post("/sessions/{session_id}/notes", response_model=SessionNotesOut)
async def convert_session_to_notes(
    session_id: str,
    request: GenerateSessionNotesRequest,
    http_request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await _get_session_or_404(db, session_id, user.id)
    selected_language = _normalize_output_language(
        resolve_request_language(
            explicit=request.language,
            header=http_request.headers.get("X-APXMIND-Language"),
            user_preference=user.preferred_language,
        )
    )

    msg_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at)
        .limit(240)
    )
    rows = list(msg_result.scalars().all())
    if not rows:
        raise HTTPException(status_code=400, detail="No messages available to convert into notes")

    checkpoints = await _collect_checkpoint_events(session.id, user.id, db)
    conversation_text = "\n".join(
        f"{'Student' if row.role == 'user' else 'Tutor'}: {row.content.strip()[:700]}"
        for row in rows[-80:]
        if row.content and row.content.strip()
    )
    checkpoint_text = "\n".join(
        f"- {str((event.payload or {}).get('concept_key') or 'Concept')}: "
        f"score {int(((event.payload or {}).get('score_percent') or 0))}%"
        for event in checkpoints[:12]
    )

    notes_prompt = f"""Create structured NEET study notes from this tutoring session.
Write in {language_name(selected_language)}.
Use only this transcript and checkpoint summary.

Transcript:
{conversation_text}

Checkpoint Summary:
{checkpoint_text or '- No checkpoints yet'}

Return markdown with these sections:
## Concepts Learned
## Worked Examples
## Mistakes To Avoid
## Revision Checklist
"""

    markdown = (await _generate_markdown_with_llm(notes_prompt)).strip()
    if not markdown:
        if selected_language == "ta":
            markdown = "## Concepts Learned\n- உரையாடலில் இருந்து குறிப்புகள் உருவாக்கப்படவில்லை."
        else:
            markdown = "## Concepts Learned\n- Notes could not be auto-generated from this session yet."

    note_title = (request.title or f"{session.subject.title()} Session Notes").strip()[:255]
    note = StudyNote(
        id=str(uuid.uuid4()),
        user_id=user.id,
        title=note_title,
        content=markdown,
        subject=session.subject,
        tags=["learn-session", "auto-generated", f"lang:{selected_language}"],
        color="amber",
    )
    db.add(note)

    await append_event(
        db,
        user_id=user.id,
        event_type="learn_session_notes_generated",
        subject=session.subject,
        entity_type="session",
        entity_id=session.id,
        payload={"note_id": note.id, "language": selected_language},
    )
    await award_xp_for_event(db, user.id, "note_created", subject=session.subject)

    await db.commit()

    return SessionNotesOut(
        session_id=session.id,
        note_id=note.id,
        title=note.title,
        language=selected_language,
        markdown=note.content,
        created_at=datetime.utcnow().isoformat(),
    )


# ---------------------------------------------------------------------------
# POST /api/learn/sessions/{id}/revision-sheet
# ---------------------------------------------------------------------------

@router.post("/sessions/{session_id}/revision-sheet", response_model=RevisionSheetOut)
async def generate_revision_sheet(
    session_id: str,
    request: GenerateRevisionSheetRequest,
    http_request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await _get_session_or_404(db, session_id, user.id)
    selected_language = _normalize_output_language(
        resolve_request_language(
            explicit=request.language,
            header=http_request.headers.get("X-APXMIND-Language"),
            user_preference=user.preferred_language,
        )
    )

    checkpoint_events = await _collect_checkpoint_events(session.id, user.id, db)
    raw_items = _checkpoint_items_from_events(checkpoint_events)

    concept_map: dict[str, list[RevisionSheetItemOut]] = {}
    for item in raw_items:
        concept_map.setdefault(item.concept_key, []).append(item)

    aggregated_items: list[RevisionSheetItemOut] = []
    for concept_key, entries in concept_map.items():
        avg_score = round(sum(entry.score_percent for entry in entries) / len(entries))
        latest_confidence = next((entry.confidence for entry in entries if entry.confidence is not None), None)

        if avg_score >= 80:
            priority = "low"
        elif avg_score >= 60:
            priority = "medium"
        else:
            priority = "high"

        aggregated_items.append(
            RevisionSheetItemOut(
                concept_key=concept_key,
                score_percent=int(avg_score),
                confidence=latest_confidence,
                priority=priority,
            )
        )

    priority_rank = {"high": 0, "medium": 1, "low": 2}
    aggregated_items.sort(key=lambda item: (priority_rank.get(item.priority, 3), item.score_percent))

    if not aggregated_items:
        if selected_language == "ta":
            markdown = "## Revision Sheet\nசரிபார்ப்பு தரவு இல்லை. முதலில் Checkpoint Pulse ஐ முடிக்கவும்."
        else:
            markdown = "## Revision Sheet\nNo checkpoint data yet. Complete checkpoint pulses first."
    else:
        item_text = "\n".join(
            f"- {item.concept_key}: score {item.score_percent}%, confidence {item.confidence if item.confidence is not None else 'n/a'}, priority {item.priority}"
            for item in aggregated_items[:12]
        )
        revision_prompt = f"""Create an actionable NEET revision sheet from checkpoint analytics.
Write in {language_name(selected_language)}.

Checkpoint Analytics:
{item_text}

Return markdown sections:
## Revise First
## Quick Fix Actions
## Exam Trap Alerts
## 20-Minute Revision Plan
"""
        markdown = (await _generate_markdown_with_llm(revision_prompt)).strip()
        if not markdown:
            if selected_language == "ta":
                markdown = "## Revise First\n" + "\n".join(
                    f"- {item.concept_key} ({item.score_percent}%, {item.priority})" for item in aggregated_items[:8]
                )
            else:
                markdown = "## Revise First\n" + "\n".join(
                    f"- {item.concept_key} ({item.score_percent}%, {item.priority})" for item in aggregated_items[:8]
                )

    await append_event(
        db,
        user_id=user.id,
        event_type="learn_revision_sheet_generated",
        subject=session.subject,
        entity_type="session",
        entity_id=session.id,
        payload={"language": selected_language, "items": len(aggregated_items)},
    )
    await db.commit()

    return RevisionSheetOut(
        session_id=session.id,
        language=selected_language,
        markdown=markdown,
        items=aggregated_items,
        generated_at=datetime.utcnow().isoformat(),
    )


# ---------------------------------------------------------------------------
# GET /api/learn/sessions/{id}/summary
# ---------------------------------------------------------------------------

@router.get("/sessions/{session_id}/summary", response_model=LearnSessionSummaryOut)
async def get_session_summary(
    session_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await _get_session_or_404(db, session_id, user.id)

    mode_state = await get_session_mode(session_id, user, db)
    source_locked, source_updated_at = await _resolve_source_lock_state(session.id, user.id, db)

    message_count_result = await db.execute(
        select(func.count())
        .select_from(ChatMessage)
        .where(ChatMessage.session_id == session.id)
    )
    message_count = int(message_count_result.scalar_one() or 0)

    checkpoints = await _collect_checkpoint_events(session.id, user.id, db)
    checkpoint_items = _checkpoint_items_from_events(checkpoints)
    checkpoint_scores = [item.score_percent for item in checkpoint_items]

    avg_checkpoint_score = (
        round(sum(checkpoint_scores) / len(checkpoint_scores), 2)
        if checkpoint_scores else None
    )
    latest_checkpoint_score = checkpoint_items[0].score_percent if checkpoint_items else None
    latest_checkpoint_feedback = None
    if checkpoints and isinstance(checkpoints[0].payload, dict):
        latest_checkpoint_feedback = checkpoints[0].payload.get("feedback")

    return LearnSessionSummaryOut(
        session_id=session.id,
        mode=mode_state.mode,
        source_locked=source_locked,
        message_count=message_count,
        checkpoint_count=len(checkpoint_items),
        avg_checkpoint_score=avg_checkpoint_score,
        latest_checkpoint_score=latest_checkpoint_score,
        latest_checkpoint_feedback=str(latest_checkpoint_feedback) if latest_checkpoint_feedback else None,
        supported_output_languages=SUPPORTED_NOTE_OUTPUT_LANGUAGES,
        updated_at=source_updated_at,
    )


# ---------------------------------------------------------------------------
# GET /api/learn/sessions
# ---------------------------------------------------------------------------

@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    subject: str = Query(default=None),
    session_status: str = Query(default=None, alias="status"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    filters = [LearningSession.user_id == user.id]
    if subject:
        filters.append(LearningSession.subject == subject)
    if session_status == "active":
        filters.append(LearningSession.ended_at.is_(None))
    elif session_status == "completed":
        filters.append(LearningSession.ended_at.is_not(None))

    total_result = await db.execute(
        select(func.count()).select_from(LearningSession).where(*filters)
    )
    total = int(total_result.scalar_one() or 0)

    stmt = (
        select(LearningSession)
        .where(*filters)
        .order_by(LearningSession.started_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(stmt)
    sessions = result.scalars().all()
    return SessionListResponse(sessions=[_session_to_out(s) for s in sessions], total=total)


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

    # Keep analytics rows but detach them from this session so FK constraints
    # do not block session deletion.
    await db.execute(
        update(QueryEvent)
        .where(
            QueryEvent.session_id == session_id,
            QueryEvent.user_id == user.id,
        )
        .values(session_id=None)
    )

    await db.delete(session)
    await db.commit()


# ---------------------------------------------------------------------------
# POST /api/learn/sessions/{id}/messages  — send message + get AI reply
# ---------------------------------------------------------------------------

@router.post("/sessions/{session_id}/messages", response_model=MessageOut)
async def send_message(
    session_id: str,
    request: SendMessageRequest,
    http_request: Request,
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
    selected_language = resolve_request_language(
        explicit=request.language,
        header=http_request.headers.get("X-APXMIND-Language"),
        user_preference=user.preferred_language,
    )
    source_scope_hint = await _load_source_scope_hint(db, session)

    use_uploaded_sources = bool(request.use_uploaded_sources)
    upload_mode = _normalize_notebook_upload_mode(request.upload_mode or "quick")

    if use_uploaded_sources:
        started = time.time()
        if upload_mode == "full":
            uploaded_context, uploaded_citations = await _query_uploaded_collection(
                query=request.content,
                user_id=user.id,
                session_id=session.id,
                subject=session.subject,
            )
            retrieval_method = "uploaded_full_chroma"
        else:
            upload_chunks = _compose_uploaded_chunks(user.id, session.id)
            uploaded_context, uploaded_citations = _quick_context_from_chunks(
                chunks=upload_chunks,
                query=request.content,
                max_chunks=_NOTEBOOK_RETRIEVAL_K,
            )
            retrieval_method = "uploaded_quick_context"

        if request.source_locked and not uploaded_citations:
            answer = _not_found_in_source(selected_language)
            tier = "tier-1"
            latency_ms = round((time.time() - started) * 1000, 2)
            citations = uploaded_citations
            retrieval_method = f"{retrieval_method}:empty"
        elif uploaded_context.strip():
            answer = await _answer_from_uploaded_context(
                query=request.content,
                language=selected_language,
                mode=request.mode,
                source_locked=request.source_locked,
                context=uploaded_context,
                source_scope_hint=source_scope_hint,
            )
            if not answer:
                answer, tier, latency_ms, citations, retrieval_method = await asyncio.get_event_loop().run_in_executor(
                    None,
                    _run_ai,
                    request.content,
                    session.subject,
                    selected_language,
                    request.mode,
                    request.source_locked,
                    source_scope_hint,
                )
            else:
                tier = "tier-1"
                latency_ms = round((time.time() - started) * 1000, 2)
                citations = uploaded_citations
        else:
            answer, tier, latency_ms, citations, retrieval_method = await asyncio.get_event_loop().run_in_executor(
                None,
                _run_ai,
                request.content,
                session.subject,
                selected_language,
                request.mode,
                request.source_locked,
                source_scope_hint,
            )
    else:
        answer, tier, latency_ms, citations, retrieval_method = await asyncio.get_event_loop().run_in_executor(
            None,
            _run_ai,
            request.content,
            session.subject,
            selected_language,
            request.mode,
            request.source_locked,
            source_scope_hint,
        )

    normalized_citations = [citation.model_dump() for citation in _coerce_citations(citations)]

    # Persist assistant message
    assistant_msg = ChatMessage(
        session_id=session_id,
        role="assistant",
        content=answer,
        tier=tier,
        msg_metadata={
            "latency_ms": latency_ms,
            "mode": request.mode,
            "source_locked": request.source_locked,
            "citations": normalized_citations,
            "retrieval_method": retrieval_method,
            "output_language": selected_language,
            "uploaded_sources_enabled": use_uploaded_sources,
            "upload_mode": upload_mode if use_uploaded_sources else None,
        },
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
        sources=normalized_citations,
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
