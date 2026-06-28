"""
backend/db/migrations/env.py

Alembic environment configuration.

This file is the bridge between Alembic and our SQLAlchemy models.
Alembic calls run_migrations_online() which:
  1. Connects to PostgreSQL (using sync psycopg2)
  2. Reads our Base.metadata (which knows about all models)
  3. Compares metadata to the actual DB schema
  4. Generates or applies migrations

KEY SETUP:
  - target_metadata = Base.metadata → tells Alembic about our models
  - We import ALL models via 'from backend.db.models import *' to ensure
    every model is registered on Base.metadata before autogenerate runs.
  - We use include_schemas=True and render_as_batch=False (PostgreSQL-safe)
"""

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# ── Import Base and ALL models ────────────────────────────────────────────────
# CRITICAL: Every model must be imported here, or Alembic won't know it exists.
# The models/__init__.py imports everything, so one import is sufficient.
from backend.db.models.base import Base
import backend.db.models  # noqa: F401 — side-effect import registers all models

# ── Alembic Config ────────────────────────────────────────────────────────────
config = context.config

# Setup Python logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── This is what tells Alembic about our schema ───────────────────────────────
# Base.metadata knows about every table defined in our ORM models.
# Alembic diffs this against the actual DB to generate migrations.
target_metadata = Base.metadata


def get_url() -> str:
    """
    Get the database URL for Alembic (synchronous psycopg2 driver).

    Design Note: Not asyncpg?
      Alembic's migration runner is synchronous — it uses standard
      SQLAlchemy sessions, not AsyncSession. asyncpg only works with
      async code. We use psycopg2 for migrations only.

    The app uses: postgresql+asyncpg://...  (async, for FastAPI/Celery)
    Alembic uses: postgresql+psycopg2://... (sync, for migrations only)
    """
    # Allow DATABASE_URL override from environment (for Docker)
    url = os.getenv("DATABASE_URL", config.get_main_option("sqlalchemy.url"))
    # App uses asyncpg dialect — convert to psycopg2 for Alembic
    return url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode — connected to a live database.
    This is the standard mode used in production.
    """
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # No connection pooling for migrations
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # Include the schema in comparisons
            compare_type=True,  # Detect column type changes
            compare_server_default=True,  # Detect default value changes
        )
        with context.begin_transaction():
            context.run_migrations()


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode — generates SQL without a DB connection.
    Useful for reviewing what SQL will be executed before running it.
    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
