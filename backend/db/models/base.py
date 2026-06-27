"""
backend/db/models/base.py

Base class and TimestampMixin for all SQLAlchemy ORM models.

WHY A MIXIN?
  Instead of repeating created_at and updated_at in every table,
  we define them once here. Every model inherits from TimestampMixin
  and gets those columns for free.

  This is pure Python OOP — mixins have nothing to do with Django or FastAPI.
  They work the same way in any Python codebase.

WHY DeclarativeBase (SQLAlchemy 2.0 style)?
  SQLAlchemy 2.0 replaced the old `declarative_base()` function with
  the `DeclarativeBase` class. The new style provides better type hints
  and IDE support.
"""

from datetime import datetime
from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """
    The root base class for all SQLAlchemy ORM models.

    All models must inherit from this Base so that:
    - Alembic can discover them for migration generation
    - SQLAlchemy knows which engine to use for queries
    """
    pass


class TimestampMixin:
    """
    Mixin that adds created_at and updated_at to any model.

    USAGE:
        class User(Base, TimestampMixin):
            __tablename__ = "users"
            # created_at and updated_at are automatically included

    HOW onupdate WORKS:
        server_default=func.now()  → DB sets the value on INSERT
        onupdate=func.now()        → DB updates the value on every UPDATE
        This means you NEVER have to manually set these fields.

    WHY timezone=True?
        Always store timestamps in UTC with timezone info.
        Without this, you get "naive" datetimes that cause bugs
        when your app or DB runs in different timezones.
    """
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
