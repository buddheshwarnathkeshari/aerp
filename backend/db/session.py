"""
backend/db/session.py

Database connection management.

Design Note: Async DATABASE?
  FastAPI is async. If you use a synchronous database driver in an async
  application, every DB query BLOCKS the event loop — no other requests
  can be served while waiting for the database.

  Synchronous (bad in async app):
    result = db.execute(query)  # Blocks for 50ms. Nothing else runs.

  Async (correct):
    result = await db.execute(query)  # Yields control. Other requests run.

  We use asyncpg (async PostgreSQL driver) via SQLAlchemy's async engine.

  Creating a new database connection is expensive (~30ms, TLS handshake).
  A connection pool maintains a set of open connections and reuses them.
  SQLAlchemy's async engine manages this automatically.
  pool_size=10 means: keep 10 connections open and ready.
  max_overflow=20 means: allow up to 30 total if burst traffic hits.
"""

import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool
from backend.config.settings import get_settings

settings = get_settings()

# ── Async Engine ──────────────────────────────────────────────────────────────
# Design Note: echo=False in production?
# echo=True logs every SQL query. Great for debugging. Terrible for production
# (logs fill up fast, sensitive data exposed).

is_celery = "celery" in sys.argv[0] or any("celery" in arg for arg in sys.argv)

engine_kwargs = {
    "echo": settings.is_development,
    "pool_pre_ping": True,
}

if is_celery:
    engine_kwargs["poolclass"] = NullPool
else:
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20

engine = create_async_engine(settings.database_url, **engine_kwargs)

# ── Session Factory ───────────────────────────────────────────────────────────
# async_sessionmaker creates AsyncSession objects.
# expire_on_commit=False: keep accessing attributes after commit
# (important for async: prevents extra queries after transaction ends)
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ── Base Model ────────────────────────────────────────────────────────────────
# All SQLAlchemy models inherit from this Base.
class Base(DeclarativeBase):
    pass


async def get_db():
    """
    FastAPI dependency that provides a database session per request.

      FastAPI calls this function for every request that needs a DB.
      `async with` guarantees the session is closed after the request,
      even if an exception occurs.

    USAGE IN ROUTE:
      @router.get("/reviews")
      async def list_reviews(db: AsyncSession = Depends(get_db)):
          ...

      Each request gets its own session (unit of work).
      All DB operations in that request are grouped together.
      If anything fails, the whole session rolls back atomically.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
