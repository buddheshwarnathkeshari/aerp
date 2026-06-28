"""
backend/db/models/review_log.py

ReviewLog ORM model — the live execution feed for the dashboard.

PURPOSE:
  Each time an agent starts, completes, or fails, it writes a row here.
  The React frontend subscribes to these logs (via WebSocket + Redis pubsub)
  and displays them in real-time as a terminal-like feed.

  On page refresh, the frontend fetches all logs for the review from this
  table to restore the full history.

Design Note: Persist LOGS IN POSTGRES AND NOT JUST REDIS?
  Redis pubsub is fire-and-forget. If the user refreshes the browser,
  the live stream is gone. By persisting each log to PostgreSQL, we can
  restore the full execution history at any time.

  Redis → real-time push to connected clients
  PostgreSQL → persistent storage for history restoration
"""

import uuid
from sqlalchemy import ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.db.models.base import Base, TimestampMixin


class ReviewLog(Base, TimestampMixin):
    __tablename__ = "review_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # ── Foreign Key ────────────────────────────────────────────────────────────
    pull_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pull_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Log Content ────────────────────────────────────────────────────────────
    agent_name: Mapped[str] = mapped_column(
        Text, nullable=False, comment="Which agent or system component sent this log."
    )
    status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="running | complete | failed | skipped",
    )
    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="The log line displayed in the dashboard terminal feed.",
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    pull_request: Mapped["PullRequest"] = relationship(
        "PullRequest", back_populates="review_logs"
    )

    def __repr__(self) -> str:
        return f"<ReviewLog agent={self.agent_name} status={self.status}>"
