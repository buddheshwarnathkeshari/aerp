"""
backend/db/models/third_party_integration.py

ThirdPartyIntegration — The integration catalog table.

This is a LOOKUP / CATALOG table. It has a fixed, small number of rows
that are seeded at application startup. Think of it as config-as-data.

CURRENT ROWS (3):
  name='github'  display_name='GitHub'         auth_type='oauth2'
  name='jira'    display_name='Jira Cloud'      auth_type='oauth2'
  name='google'  display_name='Google Workspace' auth_type='oauth2'

Design Note: A SEPARATE TABLE INSTEAD OF HARDCODING IN CODE?
  - Adding Slack/Linear/Confluence in the future = one INSERT, zero code change
  - Integration metadata (logo URL, docs URL, scopes) lives in one place
  - Can disable an integration platform-wide: SET is_enabled = FALSE

COMPARISON WITH POD CODEBASE:
  Your POD codebase has ThirdPartyIntegration with name, class_path, logo.
  This is the same concept — a master list of supported integrations.
  We add oauth-specific fields (authorize_url, token_url, required_scopes).
"""

import uuid
from sqlalchemy import Boolean, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.db.models.base import Base, TimestampMixin


class ThirdPartyIntegration(Base, TimestampMixin):
    __tablename__ = "third_party_integrations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # ── Identity ───────────────────────────────────────────────────────────────
    name: Mapped[str] = mapped_column(
        Text,
        unique=True,
        nullable=False,
        index=True,
        comment="Slug: 'github' | 'jira' | 'google'. Used as identifier in code.",
    )
    display_name: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Human-readable name shown in UI: 'GitHub', 'Jira Cloud'.",
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Short description shown in the connect UI."
    )
    logo_url: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="URL to the service's logo. Shown in connect UI."
    )

    # ── OAuth 2.0 Configuration ────────────────────────────────────────────────
    auth_type: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="oauth2",
        comment="'oauth2' or 'pat' (Personal Access Token). Determines the connect flow.",
    )
    oauth_authorize_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment=(
            "Where to redirect the user to start OAuth. "
            "GitHub: 'https://github.com/login/oauth/authorize'"
        ),
    )
    oauth_token_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Where to exchange the OAuth code for an access token.",
    )
    required_scopes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment=(
            "Space or comma-separated OAuth scopes we request. "
            "GitHub: 'repo read:user', Google: 'drive.readonly'"
        ),
    )

    # ── Meta ───────────────────────────────────────────────────────────────────
    docs_url: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Link to our setup guide for this integration."
    )
    is_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="FALSE = integration hidden from UI. Useful for maintenance.",
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    user_accounts: Mapped[list["ThirdPartyUserAccount"]] = relationship(
        "ThirdPartyUserAccount",
        back_populates="integration",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<ThirdPartyIntegration name={self.name}>"
