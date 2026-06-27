"""
backend/tasks/review_tasks.py

Celery task that runs the LangGraph review workflow in the background.

THE ASYNC BRIDGE PROBLEM:
  Celery tasks are synchronous by default.
  LangGraph nodes are async (they use `await`).
  You cannot `await` inside a sync Celery task.

SOLUTION: asyncio.run()
  asyncio.run() creates a new event loop, runs the async function to
  completion, and returns the result — bridging sync Celery with async LangGraph.

INTERVIEW: "How do you run async code in a synchronous context?"
  Use asyncio.run() to create a new event loop and run until complete.
  Alternative: asyncio.get_event_loop().run_until_complete() (deprecated in 3.10+)
  In production, prefer dedicated async workers (e.g., Celery with gevent or
  eventlet) for heavy async workloads.
"""

import asyncio
import asyncpg
import json
from backend.tasks.celery_app import celery_app
from backend.graph.state import create_initial_state
from backend.graph.workflow import workflow
from backend.config.settings import get_settings
import structlog

logger = structlog.get_logger()
settings = get_settings()


@celery_app.task(
    bind=True,                  # `self` = the task instance (for retry/status)
    name="aerp.run_review",
    max_retries=3,              # Retry up to 3 times on failure
    default_retry_delay=30,     # Wait 30 seconds between retries
    soft_time_limit=600,        # Warn at 10 minutes
    time_limit=900,             # Hard kill at 15 minutes
)
def run_review_task(self, review_id: str, pr_url: str, jira_url: str = None, doc_url: str = None):
    """
    Celery task that runs the complete AERP review workflow.

    Called by FastAPI when a review is submitted.
    Runs asynchronously in a worker process.
    """
    logger.info("Review task started", review_id=review_id, task_id=self.request.id)

    # Update review status in DB
    asyncio.run(_update_review_status(review_id, "collecting"))

    try:
        # Create initial state
        initial_state = create_initial_state(
            review_id=review_id,
            pr_url=pr_url,
            jira_url=jira_url,
            doc_url=doc_url,
        )

        # Run the LangGraph workflow
        config = {"configurable": {"thread_id": review_id}}

        # asyncio.run bridges the sync Celery task and async LangGraph graph
        final_state = asyncio.run(
            workflow.ainvoke(initial_state, config=config)
        )

        # Check if workflow completed with an error
        if final_state.get("error"):
            asyncio.run(_update_review_status(review_id, "failed", error=final_state["error"]))
            return {"status": "failed", "error": final_state["error"]}

        # Persist agent findings to DB
        agent_findings = final_state.get("agent_findings", [])
        if agent_findings:
            asyncio.run(_persist_findings(review_id, agent_findings))

        # Build summary for the review row
        code_review_result = final_state.get("code_review_result") or {}
        recommendation = code_review_result.get("recommendation", "approve_with_comments")
        findings_count = len(agent_findings)
        risk_score = _compute_risk_score(agent_findings)

        # Update review to complete with risk score and recommendation
        asyncio.run(_update_review_complete(review_id, risk_score, recommendation))
        logger.info(
            "Review task complete",
            review_id=review_id,
            findings=findings_count,
            risk_score=risk_score,
            recommendation=recommendation,
        )

        return {
            "status": "complete",
            "review_id": review_id,
            "framework_detected": final_state.get("detected_framework"),
            "files_analyzed": len(final_state.get("changed_files_analysis") or {}),
            "findings_count": findings_count,
            "risk_score": risk_score,
            "recommendation": recommendation,
        }

    except Exception as exc:
        logger.error("Review task failed", review_id=review_id, error=str(exc))
        asyncio.run(_update_review_status(review_id, "failed", error=str(exc)))

        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=30 * (self.request.retries + 1))


def _compute_risk_score(findings: list) -> int:
    """
    Computes a 0-100 risk score from agent findings.

    WHY THIS FORMULA?
      Each severity level is weighted by impact:
        critical = 25 points  (one critical = 25% risk)
        high     = 10 points
        medium   =  3 points
        low      =  1 point

      Capped at 100. Score > 40 triggers Human-in-the-Loop in Phase 6.

    INTERVIEW: "How do you quantify code risk?"
      "We use a weighted severity scoring system. Critical findings contribute
      25 points each, high 10 points, medium 3 points, low 1 point.
      Scores above 40 trigger human review before the PR can merge."
    """
    weights = {"critical": 25, "high": 10, "medium": 3, "low": 1, "info": 0}
    score = sum(weights.get(f.get("severity", "info"), 0) for f in findings)
    return min(score, 100)


async def _persist_findings(review_id: str, findings: list):
    """Saves all agent findings to the agent_findings table."""
    if not findings:
        return

    conn_string = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(conn_string)
    try:
        for f in findings:
            await conn.execute(
                """
                INSERT INTO agent_findings
                  (review_id, agent, severity, confidence, title, description,
                   file_path, line_number, evidence, suggested_fix, owasp_category)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                """,
                review_id,
                f.get("agent", "unknown"),
                f.get("severity", "info"),
                float(f.get("confidence", 0.0)),
                f.get("title", ""),
                f.get("description", ""),
                f.get("file_path"),
                f.get("line_number"),
                f.get("evidence", ""),
                f.get("suggested_fix"),
                f.get("owasp_category"),
            )
        logger.info("Findings persisted", review_id=review_id, count=len(findings))
    finally:
        await conn.close()


async def _update_review_status(review_id: str, status: str, error: str = None):
    """Updates the review status in PostgreSQL."""
    conn_string = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(conn_string)
    try:
        if error:
            await conn.execute(
                "UPDATE reviews SET status=$1, error=$2, updated_at=NOW() WHERE id=$3",
                status, error, review_id,
            )
        else:
            await conn.execute(
                "UPDATE reviews SET status=$1, updated_at=NOW() WHERE id=$2",
                status, review_id,
            )
    finally:
        await conn.close()


async def _update_review_complete(review_id: str, risk_score: int, recommendation: str):
    """Marks a review complete with final risk score and recommendation."""
    conn_string = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(conn_string)
    try:
        await conn.execute(
            """
            UPDATE reviews
            SET status='complete', risk_score=$1, recommendation=$2,
                completed_at=NOW(), updated_at=NOW()
            WHERE id=$3
            """,
            risk_score, recommendation, review_id,
        )
    finally:
        await conn.close()
