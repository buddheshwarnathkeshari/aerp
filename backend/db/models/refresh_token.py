"""
backend/db/models/refresh_token.py

RefreshToken ORM model.

HOW JWT REFRESH TOKENS WORK:
  1. On login, we issue TWO tokens:
     - Access token (JWT): short-lived (15 min), contains user claims
     - Refresh token: long-lived (30 days), stored in DB as a hash

  2. When access token expires, client sends the refresh token to
     POST /auth/refresh. We look up the hash in this table.
     If found and not revoked: issue a new access token pair.

  3. On logout: set revoked_at = NOW() on the refresh token.

WHY STORE THE HASH, NOT THE RAW TOKEN?
  The raw refresh token is equivalent to a password — whoever has it
  can impersonate the user. If an attacker dumps the database,
  they would get all active sessions.

  By storing only the SHA-256 hash:
  - Raw token lives ONLY on the user's device (httpOnly cookie or localStorage)
  - Database has only the hash — useless to an attacker without the raw token
  - Same principle as password hashing

WHY NOT STORE IN REDIS INSTEAD?
  Redis is valid for short-lived access tokens. But for refresh tokens
  (30 days), PostgreSQL is better: ACID guarantees, survives restarts,
  proper audit trail of every session ever created.
"""

import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.db.models.base import Base, TimestampMixin


class RefreshToken(Base, TimestampMixin):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # ── Foreign Key ────────────────────────────────────────────────────────────
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="CASCADE: deleting a user deletes all their sessions.",
    )

    # ── Token ──────────────────────────────────────────────────────────────────
    token_hash: Mapped[str] = mapped_column(
        Text,
        unique=True,
        nullable=False,
        comment="SHA-256 hash of the raw refresh token. Never store the raw token.",
    )

    # ── Validity ───────────────────────────────────────────────────────────────
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="30 days from creation. Token invalid after this.",
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="NULL = still valid. Set on logout or suspicious activity.",
    )

    # ── Audit / Security ───────────────────────────────────────────────────────
    device_info: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment='e.g. "Chrome 125 on macOS 15". For session management UI.',
    )
    ip_address: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="IP at time of login. For security alerts.",
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")

    # ── Helper ─────────────────────────────────────────────────────────────────
    @property
    def is_valid(self) -> bool:
        """True if this token can be used to issue a new access token."""
        from datetime import timezone
        now = datetime.now(tz=timezone.utc)
        return self.revoked_at is None and self.expires_at > now

    def __repr__(self) -> str:
        return f"<RefreshToken user_id={self.user_id} revoked={self.revoked_at is not None}>"
