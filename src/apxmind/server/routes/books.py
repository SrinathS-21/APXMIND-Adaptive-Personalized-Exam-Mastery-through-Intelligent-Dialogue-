"""
Books API — serves NCERT PDF files
====================================

Serves PDF chapter files from  data/raw/NCRTBooks/ with
path-traversal protection.

Also provides a textbook-context tutor endpoint for the book reader.
"""

import logging
from pathlib import Path
from enum import Enum
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from ...core.dependencies import get_llm

try:
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser
except ImportError:
    ChatPromptTemplate = None
    StrOutputParser = None

logger = logging.getLogger(__name__)

router = APIRouter()

# Resolve once at import time
_PROJECT_ROOT = Path(__file__).resolve().parents[4]  # src/APXMIND/server/routes → project root
_BOOKS_DIR = _PROJECT_ROOT / "data" / "raw" / "NCRTBooks"


class TutorTaskMode(str, Enum):
    summary = "summary"
    simple_explain = "simple_explain"
    detailed_explain = "detailed_explain"
    examples = "examples"
    key_points = "key_points"
    questions = "questions"
    follow_up = "follow_up"


class TutorChatTurn(BaseModel):
    role: str = Field(..., pattern=r"^(user|assistant)$")
    content: str = Field(..., min_length=1, max_length=5000)
    task: Optional[TutorTaskMode] = None


class TextbookTutorRequest(BaseModel):
    context: str = Field(..., min_length=1, max_length=15000)
    task: TutorTaskMode
    page_number: Optional[int] = Field(default=None, ge=1, le=5000)
    chat_history: List[TutorChatTurn] = Field(default_factory=list)
    user_query: str = Field(default="", max_length=2000)
    source_type: str = Field(default="selected_text", max_length=32)


class TextbookTutorResponse(BaseModel):
    success: bool = True
    mode: TutorTaskMode
    response: str
    topic: str = ""
    caution: Optional[str] = None
    timestamp: str


def _extract_topic(context: str) -> str:
    for raw in context.splitlines():
        line = raw.strip()
        if not line:
            continue
        if len(line) > 120:
            line = line[:120].rstrip() + "..."
        return line
    return "Provided textbook section"


def _task_mode_guide(task: TutorTaskMode) -> str:
    guides = {
        TutorTaskMode.summary: (
            "SUMMARY:\n"
            "- Give a concise overview.\n"
            "- Use bullet points.\n"
            "- Highlight key ideas only."
        ),
        TutorTaskMode.simple_explain: (
            "SIMPLE EXPLANATION:\n"
            "- Explain in easy beginner-friendly language.\n"
            "- Avoid jargon where possible.\n"
            "- Use a simple analogy if helpful."
        ),
        TutorTaskMode.detailed_explain: (
            "DETAILED EXPLANATION:\n"
            "- Explain step by step.\n"
            "- Cover definitions, relationships, and why concepts matter.\n"
            "- Add clear examples tied to the provided text."
        ),
        TutorTaskMode.examples: (
            "EXAMPLES:\n"
            "- Provide 2 to 4 relevant examples.\n"
            "- Prefer practical or real-world examples.\n"
            "- Explicitly connect each example to the context."
        ),
        TutorTaskMode.key_points: (
            "KEY POINTS:\n"
            "- Extract the most important points only.\n"
            "- Use concise bullet points.\n"
            "- Keep it short and revision-friendly."
        ),
        TutorTaskMode.questions: (
            "QUESTION GENERATION:\n"
            "- Generate conceptual and exam-style questions.\n"
            "- Mix short and long answer prompts.\n"
            "- Do not include answers unless explicitly asked."
        ),
        TutorTaskMode.follow_up: (
            "FOLLOW-UP Q&A:\n"
            "- Use both current context and recent conversation.\n"
            "- Answer the current user query directly.\n"
            "- Avoid repeating earlier points unless needed."
        ),
    }
    return guides[task]


@router.post(
    "/tutor",
    response_model=TextbookTutorResponse,
    summary="Context-grounded AI tutor for textbook reader",
)
async def textbook_tutor(request: TextbookTutorRequest):
    context = request.context.strip()
    if len(context) < 20:
        raise HTTPException(
            status_code=400,
            detail="Please provide more textbook context (at least ~20 characters).",
        )

    if ChatPromptTemplate is None or StrOutputParser is None:
        raise HTTPException(
            status_code=500,
            detail="LangChain prompt components are unavailable.",
        )

    try:
        llm = get_llm()
    except Exception as exc:
        logger.error(f"Tutor LLM unavailable: {exc}")
        raise HTTPException(status_code=503, detail="Tutor model is not available right now.")

    history_rows = request.chat_history[-8:]
    if history_rows:
        history_text = "\n".join(f"{row.role.upper()}: {row.content}" for row in history_rows)
    else:
        history_text = "(No previous conversation)"

    user_query = request.user_query.strip() or "(No explicit user question provided)"
    source_type = (request.source_type or "selected_text").strip().lower()
    page_hint = str(request.page_number) if request.page_number else "not provided"

    system_prompt = """You are an advanced AI Tutor embedded inside an interactive textbook reader application.

Your primary goal is to help students deeply understand academic content using provided textbook context.

CORE RULES:
1. CONTEXT FIRST: Base your response primarily on the provided context.
2. NO HALLUCINATION: Do not invent facts, formulas, or definitions.
3. If context is insufficient, explicitly say: "The provided text does not contain enough information..." and then ask a clarifying question.
4. External information is allowed only when clearly labeled: "Additional Explanation (beyond provided text)".
5. Be student-friendly: clear headings, short paragraphs, bullet points, teaching style.
6. For OCR-derived text, interpret cautiously and avoid overconfidence.

OUTPUT STYLE:
- Use headings and bullets where useful.
- Keep it clear and educational.
- Avoid long dense paragraphs.
"""

    human_prompt = """Task mode: {task}
Task behavior:
{task_guide}

Page number: {page_number}
Input source type: {source_type}
Current user request: {user_query}

Previous conversation:
{chat_history}

Textbook context (primary source of truth):
<context>
{context}
</context>

Respond now according to the task mode and rules.
"""

    try:
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", human_prompt),
        ])
        chain = prompt | llm | StrOutputParser()
        answer = chain.invoke(
            {
                "task": request.task.value,
                "task_guide": _task_mode_guide(request.task),
                "page_number": page_hint,
                "source_type": source_type,
                "user_query": user_query,
                "chat_history": history_text,
                "context": context,
            }
        ).strip()

        if not answer:
            answer = "The provided text does not contain enough information to generate a reliable response. Could you share a little more context from the textbook?"

        caution = None
        if source_type == "ocr":
            caution = "OCR text may contain recognition errors. The explanation was generated cautiously from the provided extract."

        return TextbookTutorResponse(
            success=True,
            mode=request.task,
            response=answer,
            topic=_extract_topic(context),
            caution=caution,
            timestamp=datetime.utcnow().isoformat(),
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Textbook tutor failed: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Tutor request failed: {exc}")


@router.get("/{file_path:path}", summary="Serve an NCERT PDF chapter")
async def serve_book(file_path: str):
    """
    Return the requested PDF from the NCERT books directory.

    ``file_path`` is relative to ``data/raw/NCRTBooks/``, e.g.
    ``Physics/11Physics1/keph101.pdf``.
    """
    if not file_path or ".." in file_path:
        raise HTTPException(status_code=400, detail="Invalid path")

    target = (_BOOKS_DIR / file_path).resolve()

    # Security: ensure the resolved path is still inside the books dir
    if not str(target).startswith(str(_BOOKS_DIR)):
        raise HTTPException(status_code=403, detail="Access denied")

    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail=f"Book not found: {file_path}")

    media = "application/pdf" if target.suffix.lower() == ".pdf" else "application/octet-stream"
    return FileResponse(
        path=str(target),
        media_type=media,
        # No filename= so the browser displays inline instead of downloading
        headers={"Content-Disposition": "inline"},
    )
