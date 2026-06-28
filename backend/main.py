"""
backend/main.py

FastAPI application entry point.

This is the first file uvicorn loads. It creates the app,
registers all routes, and sets up startup/shutdown events.
"""

from contextlib import asynccontextmanager
import asyncpg
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from backend.api.routes.reviews import router as reviews_router
from backend.api.routes.auth import router as auth_router
from backend.api.routes.integrations import router as integrations_router
from backend.config.settings import get_settings
import structlog

logger = structlog.get_logger()
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Code before `yield` runs on startup.
    Code after `yield` runs on shutdown.

    Design Note: lifespan instead of @app.on_event("startup")
    on_event is deprecated in FastAPI 0.93+. lifespan is the modern approach.
    It uses async context managers — cleaner and more Pythonic.
    """
    # ── STARTUP ───────────────────────────────────────────────────────────────
    logger.info("AERP API starting up", env=settings.app_env)

    # Verify database connectivity on startup
    # If this fails, the app fails fast — better than failing on first request
    try:
        conn_string = settings.database_url.replace(
            "postgresql+asyncpg://", "postgresql://"
        )
        conn = await asyncpg.connect(conn_string)
        await conn.fetchval("SELECT 1")  # Simple connectivity test
        await conn.close()
        logger.info("Database connection verified")
    except Exception as e:
        logger.error("Database connection failed on startup", error=str(e))
        raise

    yield  # App runs here

    # ── SHUTDOWN ──────────────────────────────────────────────────────────────
    logger.info("AERP API shutting down")


# ── Create FastAPI app ────────────────────────────────────────────────────────
app = FastAPI(
    title="AI Engineering Review Platform",
    description="Multi-agent AI system for comprehensive engineering change reviews",
    version="0.1.0",
    lifespan=lifespan,
    # Auto-generated docs available at:
    #   /docs      → Swagger UI (interactive)
    #   /redoc     → ReDoc (cleaner reading)
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS Middleware ───────────────────────────────────────────────────────────
# Required so the React frontend (port 3000) can call the API (port 8000)
# Design Note: CORS?
# Browsers block cross-origin requests by default (security).
# CORS headers tell the browser: "this origin is allowed to call this API"
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"]
    if settings.is_development
    else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key or "super_secret_session_key",
    max_age=3600,  # 1 hour is plenty for OAuth flows
)

# ── Register routes ───────────────────────────────────────────────────────────
app.include_router(reviews_router)
app.include_router(auth_router, prefix="/api/v1")
app.include_router(integrations_router, prefix="/api/v1")


@app.get("/", tags=["root"])
async def root():
    return {
        "service": "AI Engineering Review Platform",
        "version": "0.1.0",
        "docs": "/docs",
        "status": "operational",
    }
