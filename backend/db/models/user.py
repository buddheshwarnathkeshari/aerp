"""
backend/db/models/user.py

User ORM model — represents one registered account.

DESIGN DECISIONS:
  - password_hash is nullable: future OAuth-only users won't have a password
  - first/middle/last name all nullable: mononyms exist, some cultures differ
  - last_login_at: tracked for security audits and "active user" analytics
  - full_name: a Python @property, NOT a DB column (computed, not stored)

WHY @property instead of a column?
  full_name is always derivable from first/last name.
  Storing derived data violates 3NF (Third Normal Form) — you'd have
  to update two places (first_name + full_name) when a name changes.
  A @property computes it on demand, always consistent.

WHY NOT use @cached_property with SQLAlchemy?
  SQLAlchemy intercepts attribute access on model instances for lazy loading.
  @cached_property stores the result on the instance dict, which can conflict
  with SQLAlchemy's internal mechanisms. Plain @property is safe.
"""

import uuid
from sqlalchemy import Boolean, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.db.models.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    # ── Primary Key ────────────────────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="UUID v4 primary key — not guessable, safe to expose in URLs",
    )

    # ── Identity ───────────────────────────────────────────────────────────────
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="Primary login identifier. Indexed for fast lookup.",
    )
    password_hash: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="bcrypt hash of password. NULL for future OAuth-only accounts.",
    )

    # ── Name — separate columns for sorting, greeting, internationalization ────
    first_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    middle_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_name: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Nullable — mononyms exist (Adele, Madonna, Sukarno).",
    )

    # ── Profile ────────────────────────────────────────────────────────────────
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Account state ──────────────────────────────────────────────────────────
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="FALSE = soft-disabled account. Still exists in DB for audit trail.",
    )
    is_email_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Gate for email confirmation flow.",
    )

    # ── Audit ──────────────────────────────────────────────────────────────────
    last_login_at: Mapped[str | None] = mapped_column(
        nullable=True,
        comment="Updated on every successful login. Used for security auditing.",
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )
    integrations: Mapped[list["ThirdPartyUserAccount"]] = relationship(
        "ThirdPartyUserAccount", back_populates="user", cascade="all, delete-orphan"
    )
    pull_requests: Mapped[list["PullRequest"]] = relationship(
        "PullRequest", back_populates="user"
    )
    human_decisions: Mapped[list["HumanDecision"]] = relationship(
        "HumanDecision", back_populates="user"
    )

    # ── Computed Properties ────────────────────────────────────────────────────
    @property
    def full_name(self) -> str:
        """
        Computed from first/middle/last name. Not stored in DB.
        Skips None parts automatically.

        Examples:
          ("Buddheshwar", "Nath", "Keshari") → "Buddheshwar Nath Keshari"
          ("Adele", None, None)              → "Adele"
          (None, None, None)                 → ""
        """
        parts = [self.first_name, self.middle_name, self.last_name]
        return " ".join(p for p in parts if p)

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"
