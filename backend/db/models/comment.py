"""
backend/db/models/comment.py

Comment ORM model — replaces the old 'agent_findings' table.

Design Note: Renamed FROM 'agent_findings' TO 'comments'?
  'Comments' is the exact term GitHub uses. When we post findings to GitHub,
  they become PR review comments. The name 'comments' makes this mapping
  obvious and aligns with domain language.

STATUS FIELD — How the Consensus Agent soft-filters:
  We NEVER delete rows. Instead we use `status` to track each comment's
  disposition. This preserves a complete audit trail.

  'pending'                → Just created by an agent, not yet processed
  'included'               → Consensus approved, will be posted to GitHub
  'filtered_low_confidence'→ confidence < threshold, excluded from GitHub
  'merged_duplicate'       → Same issue found by another agent; see merged_into_id
  'false_positive'         → Human explicitly marked as not a real issue

SELF-REFERENTIAL FOREIGN KEY (merged_into_id):
  When two agents find the same bug, Consensus Agent picks the better one
  as "canonical" and marks the duplicate with status='merged_duplicate'
  and merged_into_id pointing to the canonical comment's id.

  This creates a self-join on the comments table — a comment can reference
  another comment in the same table. This is called a self-referential FK.
"""

import uuid
from sqlalchemy import Boolean, Float, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.db.models.base import Base, TimestampMixin


class Comment(Base, TimestampMixin):
    __tablename__ = "comments"

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
    merged_into_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("comments.id", ondelete="SET NULL"),
        nullable=True,
        comment=(
            "Self-referential FK. When status='merged_duplicate', this points "
            "to the canonical comment that absorbed this one."
        ),
    )

    # ── Source ─────────────────────────────────────────────────────────────────
    agent: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Which agent generated this. e.g. 'security_agent', 'code_review_agent'",
    )

    # ── Severity & Confidence ─────────────────────────────────────────────────
    severity: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="critical | high | medium | low | info",
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="0.0–1.0. Findings below threshold get status='filtered_low_confidence'.",
    )

    # ── Content ────────────────────────────────────────────────────────────────
    title: Mapped[str] = mapped_column(
        Text, nullable=False, comment="Short, specific issue title (max ~80 chars)."
    )
    description: Mapped[str] = mapped_column(
        Text, nullable=False, comment="Full explanation: what, why, impact."
    )
    evidence: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="The exact code snippet that triggered this finding.",
    )
    suggested_fix: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Corrected code snippet or remediation steps."
    )

    # ── Location ───────────────────────────────────────────────────────────────
    file_path: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="e.g. 'backend/api/routes/payments.py'"
    )
    line_number: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Specific line in the file."
    )

    # ── Security-specific ──────────────────────────────────────────────────────
    owasp_category: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="For security findings only. e.g. 'A03:2021 - Injection'",
    )

    # ── Consensus status ───────────────────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="pending",
        index=True,
        comment=(
            "pending | included | filtered_low_confidence | "
            "merged_duplicate | false_positive"
        ),
    )
    is_posted_to_github: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="TRUE only after the GitHub API call succeeds.",
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    pull_request: Mapped["PullRequest"] = relationship(
        "PullRequest", back_populates="comments"
    )
    # Self-referential: the comment this was merged into
    merged_into: Mapped["Comment | None"] = relationship(
        "Comment", remote_side="Comment.id", foreign_keys=[merged_into_id]
    )

    def __repr__(self) -> str:
        return f"<Comment agent={self.agent} severity={self.severity} status={self.status}>"
