"""
backend/db/models/human_decision.py

HumanDecision ORM model — the HITL audit trail.

PURPOSE:
  When the Consensus Agent calculates a high risk score (> threshold),
  the LangGraph workflow PAUSES. A human reviews the findings in the UI
  and clicks Approve or Reject. This table records that decision.

WHY THIS TABLE EXISTS (compliance):
  Enterprise companies require proof that a human explicitly reviewed
  every high-risk AI decision before code was shipped to production.
  This is required for SOC2 compliance, ISO 27001, etc.
  Without this table, there is no verifiable audit trail.

WHY reviewer_name is a snapshot:
  We store the name at the time of decision (not a JOIN to users.full_name).
  If the user later changes their name, the historical record still shows
  exactly who made the decision. Audit trails must be immutable snapshots.
"""

import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.db.models.base import Base, TimestampMixin


class HumanDecision(Base, TimestampMixin):
    __tablename__ = "human_decisions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # ── Foreign Keys ───────────────────────────────────────────────────────────
    pull_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pull_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="SET NULL: record preserved even if user account is deleted.",
    )

    # ── Decision ───────────────────────────────────────────────────────────────
    decision: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="approve | reject | approve_with_override",
    )
    reviewer_name: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment=(
            "Immutable snapshot of the reviewer's name at decision time. "
            "NOT a FK join — audit records must not change if user renames."
        ),
    )
    comment: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Optional human reasoning for the decision."
    )

    # ── Timestamp (separate from TimestampMixin's created_at for semantics) ────
    decided_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Exact moment the human clicked Approve or Reject.",
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    pull_request: Mapped["PullRequest"] = relationship(
        "PullRequest", back_populates="human_decisions"
    )
    user: Mapped["User"] = relationship("User", back_populates="human_decisions")

    def __repr__(self) -> str:
        return f"<HumanDecision decision={self.decision} pr={self.pull_request_id}>"
