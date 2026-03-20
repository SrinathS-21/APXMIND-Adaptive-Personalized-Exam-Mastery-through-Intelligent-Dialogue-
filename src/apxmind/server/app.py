"""
APXMIND FastAPI Application
===========================

Main FastAPI application entry point.
Serves both the API and the React SPA (monolith architecture).
"""

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from ..core.config import Settings
from ..core.dependencies import get_settings, init_resources, cleanup_resources

logger = logging.getLogger(__name__)

# ── Resolve client/dist path relative to project root ──────────────────
# Project layout: <root>/src/APXMIND/server/app.py → 4 levels up = <root>
PROJECT_ROOT = Path(__file__).resolve().parents[3]
CLIENT_DIST = PROJECT_ROOT / "client" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load LLM, vectorstores, and DB on startup; clean up on shutdown."""
    settings = get_settings()
    setup_logging(settings)

    logger.info("=" * 60)
    logger.info("APXMIND API Starting...")
    logger.info("=" * 60)

    await init_resources(settings)

    logger.info(f"Server ready at http://{settings.host}:{settings.port}")
    logger.info("=" * 60)

    yield  # Application runs here

    logger.info("Shutting down...")
    await cleanup_resources()
    logger.info("APXMIND API stopped.")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="APXMIND API",
        description="AI-powered NEET Exam Preparation Tutor",
        version="2.0.0",
        lifespan=lifespan,
    )

    # ── CORS ────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Register routers ────────────────────────────────────────────────
    from .routes.query import router as query_router
    from .routes.subjects import router as subjects_router
    from .routes.trainer import router as trainer_router
    from .routes.auth import router as auth_router
    from .routes.ws import router as ws_router
    from .routes.books import router as books_router
    # New real-time routes
    from .routes.dashboard import router as dashboard_router, progress_router
    from .routes.quiz_v2 import router as quiz_v2_router
    from .routes.learn import router as learn_router
    from .routes.library import router as library_router
    from .routes.achievements import router as achievements_router
    from .routes.profile_ext import router as profile_ext_router
    from .routes.sse import router as sse_router
    from .routes.recommendations import router as recommendations_router
    from .routes.insights import router as insights_router

    app.include_router(query_router,        prefix="/api/query",        tags=["Query"])
    app.include_router(subjects_router,     prefix="/api/subjects",     tags=["Subjects"])
    app.include_router(trainer_router,      prefix="/api/trainer",      tags=["Trainer (legacy)"])
    app.include_router(auth_router,         prefix="/api/auth",         tags=["Auth"])
    app.include_router(books_router,        prefix="/api/books",        tags=["Books"])
    app.include_router(ws_router,           prefix="/ws",               tags=["WebSocket"])
    # Real-time routes
    app.include_router(dashboard_router,    prefix="/api/dashboard",    tags=["Dashboard"])
    app.include_router(progress_router,     prefix="/api/progress",     tags=["Progress"])
    app.include_router(quiz_v2_router,      prefix="/api/quiz",         tags=["Quiz"])
    app.include_router(learn_router,        prefix="/api/learn",        tags=["Learn"])
    app.include_router(library_router,      prefix="/api/library",      tags=["Library"])
    app.include_router(achievements_router, prefix="/api/achievements", tags=["Achievements"])
    app.include_router(profile_ext_router,  prefix="/api/profile",      tags=["Profile"])
    app.include_router(sse_router,           prefix="/api/events",       tags=["Events"])
    app.include_router(recommendations_router, prefix="/api/recommendations", tags=["Recommendations"])
    app.include_router(insights_router,      prefix="/api/insights",     tags=["Insights"])

    # ── Health check ────────────────────────────────────────────────────
    @app.get("/health", tags=["System"])
    async def health_check():
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "2.0.0",
            "components": {
                "api": "healthy",
            },
        }

    # ── API info ────────────────────────────────────────────────────────
    @app.get("/api", tags=["System"])
    async def api_info():
        return {
            "name": "APXMIND API",
            "version": "2.0.0",
            "description": "AI-powered NEET exam preparation assistant",
            "documentation": "/docs",
            "endpoints": {
                "auth": {
                    "register":       "POST /api/auth/register",
                    "login":          "POST /api/auth/login",
                    "me":             "GET  /api/auth/me",
                    "update_profile": "PUT  /api/auth/profile",
                    "setup_profile":  "POST /api/auth/profile",
                    "list_users":     "GET  /api/auth/users",
                },
                "subjects": {
                    "list":            "GET  /api/subjects",
                    "lessons":         "GET  /api/subjects/{subject}/lessons",
                    "complete_lesson": "POST /api/subjects/{subject}/lessons/{id}/complete",
                },
                "query": {"ask": "POST /api/query"},
                "trainer": {
                    "generate_quiz": "POST /api/trainer/generate-quiz",
                    "submit_answer": "POST /api/trainer/submit-answer",
                },
                "dashboard": {"summary": "GET /api/dashboard/summary"},
                "progress": {
                    "daily":         "GET  /api/progress/daily",
                    "gamification":  "GET  /api/progress/gamification",
                    "study_minutes": "POST /api/progress/study-minutes",
                },
                "quiz": {
                    "start":         "POST   /api/quiz/start",
                    "list":          "GET    /api/quiz",
                    "get":           "GET    /api/quiz/{id}",
                    "questions":     "GET    /api/quiz/{id}/questions",
                    "submit_answer": "POST   /api/quiz/{id}/answers/{qid}",
                    "update_answer": "PATCH  /api/quiz/{id}/answers/{qid}",
                    "finish":        "POST   /api/quiz/{id}/finish",
                    "abandon":       "POST   /api/quiz/{id}/abandon",
                    "results":       "GET    /api/quiz/{id}/results",
                    "delete":        "DELETE /api/quiz/{id}",
                },
                "learn": {
                    "start_session": "POST /api/learn/sessions",
                    "list_sessions": "GET  /api/learn/sessions",
                    "get_session":   "GET  /api/learn/sessions/{id}",
                    "end_session":   "POST /api/learn/sessions/{id}/end",
                    "send_message":  "POST /api/learn/sessions/{id}/messages",
                    "list_messages": "GET  /api/learn/sessions/{id}/messages",
                },
                "library": {
                    "list_bookmarks":    "GET    /api/library/bookmarks",
                    "get_bookmark":      "GET    /api/library/bookmarks/{id}",
                    "create_bookmark":   "POST   /api/library/bookmarks",
                    "update_bookmark":   "PATCH  /api/library/bookmarks/{id}",
                    "delete_bookmark":   "DELETE /api/library/bookmarks/{id}",
                    "delete_all_bmarks": "DELETE /api/library/bookmarks",
                    "list_notes":        "GET    /api/library/notes",
                    "get_note":          "GET    /api/library/notes/{id}",
                    "create_note":       "POST   /api/library/notes",
                    "update_note":       "PUT    /api/library/notes/{id}",
                    "delete_note":       "DELETE /api/library/notes/{id}",
                    "bulk_delete_notes": "DELETE /api/library/notes",
                },
                "achievements": {
                    "all":    "GET /api/achievements",
                    "earned": "GET /api/achievements/earned",
                    "detail": "GET /api/achievements/{badge_id}",
                },
                "profile": {
                    "list_preferences":   "GET    /api/profile/subjects",
                    "upsert_preference":  "PUT    /api/profile/subjects/{subject}",
                    "delete_preference":  "DELETE /api/profile/subjects/{subject}",
                },
                "websocket": {"chat": "WS /ws/chat"},
                "events": {
                    "stream": "GET /api/events/stream",
                },
                "recommendations": {
                    "list":   "GET    /api/recommendations",
                    "update": "PATCH  /api/recommendations/{id}",
                    "delete": "DELETE /api/recommendations/{id}",
                },
                "insights": {
                    "mastery":          "GET /api/insights/mastery",
                    "mastery_subject":  "GET /api/insights/mastery/{subject}",
                    "readiness":        "GET /api/insights/readiness",
                    "habits":           "GET /api/insights/habits",
                },
            },
            "status": "operational",
            "timestamp": datetime.utcnow().isoformat(),
        }

    # ── Global exception handler ────────────────────────────────────────
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Internal Server Error",
                "message": str(exc) if settings.debug else "An unexpected error occurred.",
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    # ── Serve React SPA (production) ───────────────────────────────────
    if CLIENT_DIST.exists() and (CLIENT_DIST / "index.html").exists():
        # Mount static assets (JS/CSS bundles)
        assets_dir = CLIENT_DIST / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

        # Serve other static files from dist root (favicon, etc.)
        @app.get("/vite.svg", include_in_schema=False)
        async def vite_svg():
            svg = CLIENT_DIST / "vite.svg"
            if svg.exists():
                return FileResponse(str(svg))
            return JSONResponse(status_code=404, content={"error": "not found"})

        # SPA catch-all: any GET that doesn't match API/ws/health/docs → index.html
        @app.get("/{full_path:path}", include_in_schema=False)
        async def serve_spa(request: Request, full_path: str):
            # Don't intercept API, WebSocket, docs, or health routes
            if full_path.startswith(("api/", "ws/", "docs", "redoc", "openapi.json", "health")):
                return JSONResponse(status_code=404, content={"error": "not found"})
            # Try to serve a static file from dist first
            file_path = CLIENT_DIST / full_path
            if full_path and file_path.exists() and file_path.is_file():
                return FileResponse(str(file_path))
            # Otherwise serve index.html (SPA routing)
            return FileResponse(str(CLIENT_DIST / "index.html"))

        logger.info(f"Serving React SPA from {CLIENT_DIST}")
    else:
        logger.warning(f"Client build not found at {CLIENT_DIST}. Run 'cd client && npm run build'")

    return app


def setup_logging(settings: Settings):
    """Configure application logging."""
    os.makedirs(os.path.dirname(settings.log_file) or "logs", exist_ok=True)

    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(settings.log_file),
            logging.StreamHandler(),
        ],
    )


# Convenience: create app at module level for uvicorn
app = create_app()
