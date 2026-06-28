"""
backend/api/schemas/review_schemas.py

Pydantic models for HTTP request/response bodies.

Design Note: Separate SCHEMAS FROM DB MODELS?
  DB models (SQLAlchemy) define how data is stored.
  API schemas (Pydantic) define what the HTTP API accepts/returns.
  These are NOT the same thing:
  - DB model: has all fields including internal ones (created_at, error)
  - API response: exposes only what the client needs
  - API request: validates only what the client can send

  Mixing them creates security risks (exposing internal fields) and
  tight coupling (changing the DB schema breaks the API).
"""

from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime
from uuid import UUID


# ── Request schemas (what clients send to us) ─────────────────────────────────


class StartReviewRequest(BaseModel):
    """Request body for POST /reviews/start"""

    pr_url: str  # GitHub PR URL
    jira_url: Optional[str] = None
    doc_url: Optional[str] = None

    @field_validator("pr_url")
    @classmethod
    def validate_github_url(cls, v: str) -> str:
        if "github.com" not in v or "/pull/" not in v:
            raise ValueError(
                "pr_url must be a valid GitHub PR URL "
                "(e.g., https://github.com/owner/repo/pull/123)"
            )
        return v.strip()


class HumanDecisionRequest(BaseModel):
    """Request body for POST /reviews/{id}/decision"""

    decision: str  # "approve" | "reject" | "approve_with_override"
    reviewer: str  # Who is making the decision
    comment: Optional[str] = None

    @field_validator("decision")
    @classmethod
    def validate_decision(cls, v: str) -> str:
        valid = {"approve", "reject", "approve_with_override"}
        if v not in valid:
            raise ValueError(f"decision must be one of: {valid}")
        return v


# ── Response schemas (what we return to clients) ──────────────────────────────


class StartReviewResponse(BaseModel):
    """Response for POST /reviews/start"""

    review_id: UUID
    status: str  # "queued"
    message: str  # Human-readable message
    status_url: str  # URL to poll for status


class ReviewStatusResponse(BaseModel):
    """Response for GET /reviews/{id}/status"""

    review_id: UUID
    status: str
    # Status progression:
    # queued → collecting → analyzing → reviewing → consensus →
    # awaiting_human → complete | failed
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    risk_score: Optional[int] = None
    recommendation: Optional[str] = None
    error: Optional[str] = None
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
