"""
Books API — serves NCERT PDF files
====================================

Serves PDF chapter files from  data/raw/NCRTBooks/ with
path-traversal protection.
"""

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

logger = logging.getLogger(__name__)

router = APIRouter()

# Resolve once at import time
_PROJECT_ROOT = Path(__file__).resolve().parents[4]  # src/APXMIND/server/routes → project root
_BOOKS_DIR = _PROJECT_ROOT / "data" / "raw" / "NCRTBooks"


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
