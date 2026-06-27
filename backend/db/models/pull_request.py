"""
backend/db/models/pull_request.py

PullRequest ORM model — replaces the old 'reviews' table.

WHY RENAMED FROM 'reviews' TO 'pull_requests'?
  'reviews' was ambiguous — is it a code review or a product review?
  'pull_requests' is precise: a row here represents one GitHub PR
  submitted for AI analysis. The "review" is what the AI DOES to it.

STATUS LIFECYCLE:
  queued → collecting → analyzing → consensus → awaiting_human
    → complete | failed | cancelled

  Each status represents a phase of the LangGraph workflow:
  - queued:         Celery task created, not started yet
  - collecting:     Context Collector fetching PR, Jira, Docs
  - analyzing:      8 specialist agents running in parallel
  - consensus:      Consensus Agent merging + scoring findings
  - awaiting_human: HITL pause — waiting for human decision
  - complete:       Finished successfully
  - failed:         An unrecoverable error occurred
  - cancelled:      User aborted via API

RISK SCORE:
  0-100, calculated by Consensus Agent.
  Drives the HITL decision and the GitHub comment content.
"""

import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.db.models.base import Base, TimestampMixin


class PullRequest(Base, TimestampMixin):
    __tablename__ = "pull_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # ── Owner ──────────────────────────────────────────────────────────────────
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment=(
            "SET NULL: if user deletes account, PRs remain for audit. "
            "NULL = submitted anonymously (before auth was implemented)."
        ),
    )

    # ── Input URLs ─────────────────────────────────────────────────────────────
    pr_url: Mapped[str] = mapped_column(
        Text, nullable=False, comment="The GitHub Pull Request URL."
    )
    jira_url: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Optional. Jira ticket for requirements context."
    )
    doc_url: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Optional. Google Doc for design/feature context."
    )

    # ── Status ─────────────────────────────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="queued",
        index=True,
        comment=(
            "queued | collecting | analyzing | consensus | "
            "awaiting_human | complete | failed | cancelled"
        ),
    )

    # ── Results ────────────────────────────────────────────────────────────────
    risk_score: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="0–100. Set by Consensus Agent. NULL until consensus completes.",
    )
    recommendation: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="approve | approve_with_comments | request_changes | block",
    )

    # ── LLM tracking ──────────────────────────────────────────────────────────
    llm_provider: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="gemini | openai | ollama | anthropic"
    )
    llm_model: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="e.g. 'gemini-2.5-flash', 'gpt-4o', 'llama3.1'"
    )

    # ── Task management (for abort feature) ───────────────────────────────────
    task_id: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Celery task ID. Used to terminate the task via celery.control.revoke().",
    )

    # ── Error handling ─────────────────────────────────────────────────────────
    error: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Full error message if status='failed'."
    )

    # ── Completion timestamp ───────────────────────────────────────────────────
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    user: Mapped["User"] = relationship("User", back_populates="pull_requests")
    comments: Mapped[list["Comment"]] = relationship(
        "Comment", back_populates="pull_request", cascade="all, delete-orphan"
    )
    human_decisions: Mapped[list["HumanDecision"]] = relationship(
        "HumanDecision", back_populates="pull_request", cascade="all, delete-orphan"
    )
    review_logs: Mapped[list["ReviewLog"]] = relationship(
        "ReviewLog", back_populates="pull_request", cascade="all, delete-orphan"
    )
    embeddings: Mapped[list["Embedding"]] = relationship(
        "Embedding", back_populates="pull_request", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<PullRequest id={self.id} status={self.status}>"
