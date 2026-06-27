"""
backend/db/models/third_party_user_account.py

ThirdPartyUserAccount — One user's connection to one external service.

DESIGN: Hybrid approach for credentials storage.
  - access_token_encrypted: explicit required column (every provider needs this)
  - credentials: JSONB for provider-specific optional fields

WHY HYBRID (NOT FULL JSONB)?
  The access token is the one field we ALWAYS need. Making it an explicit
  column gives us a DB-level NOT NULL guarantee. You can't accidentally
  insert a row without it. A JSONB blob could have {"typo_token": "..."} and
  the DB would accept it silently.

  Everything else (refresh_token, expiry, Jira site URL, Google workspace domain)
  goes in `credentials` JSONB because:
  - Not every provider has refresh tokens (GitHub doesn't)
  - Provider-specific extras differ wildly
  - JSONB is queryable: credentials->>'site_url' works in SQL

CREDENTIAL ENCRYPTION:
  NEVER store raw OAuth tokens. Before inserting, encrypt with AES-256.
  The encryption key lives only in the .env file (never in the DB).
  If the DB is compromised, encrypted tokens are useless.

  access_token_encrypted: AES256(raw_access_token, ENCRYPTION_KEY)
  credentials.refresh_token: AES256(raw_refresh_token, ENCRYPTION_KEY)

EXAMPLES of `credentials` JSONB per provider:
  GitHub:  {}   (no refresh token, tokens don't expire)
  Jira:    {"refresh_token": "enc_...", "expires_at": "2026-...", 
             "site_url": "mycompany.atlassian.net", "cloud_id": "abc123"}
  Google:  {"refresh_token": "enc_...", "expires_at": "2026-..."}
"""

import uuid
from sqlalchemy import Boolean, ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.db.models.base import Base, TimestampMixin


class ThirdPartyUserAccount(Base, TimestampMixin):
    __tablename__ = "third_party_user_accounts"

    # ── Unique constraint: one connection per provider per user ────────────────
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "integration_id",
            name="uq_user_integration",
            comment="A user can only connect one account per integration.",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # ── Foreign Keys ───────────────────────────────────────────────────────────
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    integration_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("third_party_integrations.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ── Credentials (Hybrid approach) ──────────────────────────────────────────
    access_token_encrypted: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment=(
            "AES-256 encrypted access token. "
            "NOT NULL — every integration always needs this."
        ),
    )
    credentials: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment=(
            "Provider-specific optional credentials as JSONB. "
            "Keys: refresh_token (encrypted), expires_at, site_url (Jira), cloud_id (Jira)."
        ),
    )

    # ── Provider Identity ──────────────────────────────────────────────────────
    provider_user_id: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Their ID on that platform. GitHub numeric ID, Google 'sub', Atlassian account ID.",
    )
    provider_email: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Email on that platform (may differ from AERP email)."
    )
    provider_username: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Display name on platform, e.g. GitHub username."
    )
    granted_scopes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Scopes the user actually approved. May be subset of required_scopes.",
    )

    # ── State ──────────────────────────────────────────────────────────────────
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="FALSE = user disconnected this integration. Row kept for audit.",
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    user: Mapped["User"] = relationship("User", back_populates="integrations")
    integration: Mapped["ThirdPartyIntegration"] = relationship(
        "ThirdPartyIntegration", back_populates="user_accounts"
    )

    def get_credential(self, key: str):
        """Safely retrieve a key from the credentials JSONB field."""
        return self.credentials.get(key) if self.credentials else None

    def __repr__(self) -> str:
        return f"<ThirdPartyUserAccount user_id={self.user_id} integration_id={self.integration_id}>"
