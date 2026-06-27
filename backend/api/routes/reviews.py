"""
backend/api/routes/reviews.py

FastAPI route handlers for the review API.

DESIGN: Routes only do 3 things:
  1. Validate the request (Pydantic does this automatically)
  2. Call the service/task layer
  3. Return a response

NO business logic here. Routes don't talk to the database directly.
They don't run agents. They just orchestrate.
"""

import uuid
import asyncpg
from fastapi import APIRouter, HTTPException, status
from backend.api.schemas.review_schemas import (
    StartReviewRequest,
    StartReviewResponse,
    ReviewStatusResponse,
)
from backend.tasks.review_tasks import run_review_task
from backend.config.settings import get_settings
import structlog

router = APIRouter(prefix="/reviews", tags=["reviews"])
logger = structlog.get_logger()
settings = get_settings()


@router.post(
    "/start",
    response_model=StartReviewResponse,
    status_code=status.HTTP_202_ACCEPTED,  # 202 = Accepted (async processing started)
)
async def start_review(request: StartReviewRequest):
    """
    Submit a PR for AI review.

    Returns immediately with a review_id.
    The actual review runs asynchronously via Celery.
    Poll GET /reviews/{review_id}/status to track progress.

    WHY 202 ACCEPTED instead of 200 OK?
      200 OK implies the request is fully processed.
      202 ACCEPTED means: "I received your request and will process it."
      This is the correct HTTP status for async operations.
    """
    review_id = str(uuid.uuid4())
    logger.info("Starting review", review_id=review_id, pr_url=request.pr_url)

    # Create the review record in the database
    conn_string = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(conn_string)
    try:
        await conn.execute(
            """
            INSERT INTO reviews (id, pr_url, jira_url, doc_url, status)
            VALUES ($1, $2, $3, $4, 'queued')
            """,
            review_id,
            request.pr_url,
            request.jira_url,
            request.doc_url,
        )
    finally:
        await conn.close()

    # Enqueue the Celery task (non-blocking — returns immediately)
    run_review_task.delay(
        review_id=review_id,
        pr_url=request.pr_url,
        jira_url=request.jira_url,
        doc_url=request.doc_url,
    )

    return StartReviewResponse(
        review_id=review_id,
        status="queued",
        message="Review started. Poll the status URL for updates.",
        status_url=f"/reviews/{review_id}/status",
    )


@router.get("/{review_id}/status", response_model=ReviewStatusResponse)
async def get_review_status(review_id: str):
    """
    Check the status of an ongoing or completed review.

    Clients should poll this every 10-30 seconds until
    status is "complete", "awaiting_human", or "failed".
    """
    conn_string = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(conn_string)
    try:
        row = await conn.fetchrow(
            """
            SELECT id, status, created_at, updated_at,
                   completed_at, risk_score, recommendation, error
            FROM reviews WHERE id = $1
            """,
            review_id,
        )
    finally:
        await conn.close()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review {review_id} not found",
        )

    return ReviewStatusResponse(
        review_id=str(row["id"]),
        status=row["status"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        completed_at=row.get("completed_at"),
        risk_score=row.get("risk_score"),
        recommendation=row.get("recommendation"),
        error=row.get("error"),
    )


@router.get("/health")
async def health_check():
    """Simple health check endpoint for Docker."""
    return {"status": "healthy", "service": "aerp-api"}


@router.get("/{review_id}/findings")
async def get_review_findings(review_id: str, severity: str = None):
    """
    Fetch all agent findings for a completed review.

    Query params:
      ?severity=critical   -> filter by severity level

    WHY SEPARATE FROM /status?
      /status is lightweight -- just the review row.
      /findings can be large (many findings with full descriptions).
      Separating them lets the UI load status fast, then lazily
      fetch findings only when the user opens the detail view.
    """
    conn_string = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(conn_string)
    try:
        severity_order = """
          CASE severity
            WHEN 'critical' THEN 1
            WHEN 'high'     THEN 2
            WHEN 'medium'   THEN 3
            WHEN 'low'      THEN 4
            ELSE 5
          END, confidence DESC
        """
        if severity:
            rows = await conn.fetch(
                f"""
                SELECT agent, severity, confidence, title, description,
                       file_path, line_number, evidence, suggested_fix, owasp_category,
                       created_at
                FROM agent_findings
                WHERE review_id = $1 AND severity = $2
                ORDER BY {severity_order}
                """,
                review_id, severity,
            )
        else:
            rows = await conn.fetch(
                f"""
                SELECT agent, severity, confidence, title, description,
                       file_path, line_number, evidence, suggested_fix, owasp_category,
                       created_at
                FROM agent_findings
                WHERE review_id = $1
                ORDER BY {severity_order}
                """,
                review_id,
            )
    finally:
        await conn.close()

    findings = [dict(r) for r in rows]
    return {
        "review_id": review_id,
        "total": len(findings),
        "findings": findings,
    }
