"""
Async Database Session
=======================

SQLAlchemy async engine and session factory for the APXMIND application.
Uses aiosqlite for async SQLite support.
"""

import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from ..core.config import Settings

logger = logging.getLogger(__name__)

# Module-level engine and session factory (initialized at startup)
_engine = None
_async_session_factory = None


def init_db_engine(settings: Settings):
    """
    Initialize the async database engine and session factory.
    Called once during FastAPI app startup.
    """
    global _engine, _async_session_factory

    db_url = settings.database_url
    # Ensure the URL uses the async driver
    if db_url.startswith("sqlite:///") and "aiosqlite" not in db_url:
        db_url = db_url.replace("sqlite:///", "sqlite+aiosqlite:///")

    _engine = create_async_engine(db_url, echo=settings.debug)
    _async_session_factory = async_sessionmaker(
        _engine, class_=AsyncSession, expire_on_commit=False
    )
    logger.info(f"Database engine initialized: {db_url.split('?')[0]}")


async def create_tables():
    """Create all database tables (run once at startup)."""
    from .models import Base

    if _engine is None:
        raise RuntimeError("Database engine not initialized. Call init_db_engine() first.")

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created successfully")


async def get_db() -> AsyncSession:
    """
    FastAPI dependency — yields an async database session.

    Usage:
        @router.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    if _async_session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db_engine() first.")

    async with _async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def close_db():
    """Close the database engine (called at shutdown)."""
    global _engine
    if _engine:
        await _engine.dispose()
        logger.info("Database engine closed")
