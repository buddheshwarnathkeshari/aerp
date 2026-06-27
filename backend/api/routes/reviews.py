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

    provider = settings.llm_provider.lower() or "gemini"
    if provider == "openai":
        model = settings.openai_model
    elif provider == "anthropic":
        model = settings.anthropic_model
    elif provider == "ollama":
        import os
        model = os.getenv("OLLAMA_MODEL", "llama3.1")
    else:
        provider = "gemini"
        model = settings.gemini_model

    # Create the review record in the database
    conn_string = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(conn_string)
    try:
        await conn.execute(
            """
            INSERT INTO reviews (id, pr_url, jira_url, doc_url, status, llm_provider, llm_model)
            VALUES ($1, $2, $3, $4, 'queued', $5, $6)
            """,
            review_id,
            request.pr_url,
            request.jira_url,
            request.doc_url,
            provider,
            model,
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
                SELECT id, agent, severity, confidence, title, description,
                       file_path, line_number, evidence, suggested_fix, owasp_category,
                       included_in_pr, created_at
                FROM agent_findings
                WHERE review_id = $1 AND severity = $2
                ORDER BY {severity_order}
                """,
                review_id, severity,
            )
        else:
            rows = await conn.fetch(
                f"""
                SELECT id, agent, severity, confidence, title, description,
                       file_path, line_number, evidence, suggested_fix, owasp_category,
                       included_in_pr, created_at
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


@router.get("/{review_id}/logs")
async def get_review_logs(review_id: str):
    """
    Fetch historical execution logs for a review.
    Used by the UI to restore log state on refresh.
    """
    conn_string = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(conn_string)
    try:
        rows = await conn.fetch(
            """
            SELECT agent_name, status, message, created_at
            FROM review_logs
            WHERE review_id = $1
            ORDER BY created_at ASC
            """,
            review_id,
        )
    finally:
        await conn.close()
        
    return {"logs": [dict(r) for r in rows]}

@router.get("")
async def list_reviews(limit: int = 20):
    """
    List recent reviews for the homepage dashboard.
    """
    conn_string = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(conn_string)
    try:
        rows = await conn.fetch(
            """
            SELECT id, pr_url, status, risk_score, created_at
            FROM reviews
            ORDER BY created_at DESC
            LIMIT $1
            """,
            limit,
        )
    finally:
        await conn.close()
        
    return {"reviews": [dict(r) for r in rows]}

from pydantic import BaseModel
from typing import Optional

class PostFindingRequest(BaseModel):
    edited_message: Optional[str] = None

@router.post("/{review_id}/findings/{finding_id}/post")
async def post_finding_to_pr(review_id: str, finding_id: str, request: PostFindingRequest = None):
    """
    Posts a specific finding directly to the PR as a comment.
    Accepts an optional edited_message.
    """
    conn_string = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(conn_string)
    try:
        # Get the review to find the PR URL
        review = await conn.fetchrow("SELECT pr_url FROM reviews WHERE id = $1", review_id)
        if not review:
            raise HTTPException(status_code=404, detail="Review not found")
            
        # Get the specific finding
        finding = await conn.fetchrow(
            """
            SELECT title, severity, description, file_path, evidence, included_in_pr 
            FROM agent_findings 
            WHERE id = $1 AND review_id = $2
            """, 
            finding_id, review_id
        )
        if not finding:
            raise HTTPException(status_code=404, detail="Finding not found")
            
        if finding["included_in_pr"]:
            return {"message": "Already posted"}
            
        # Call the GitHub tool
        from backend.tools.github_tool import post_single_finding_comment
        finding_dict = dict(finding)
        if request and request.edited_message:
            finding_dict["edited_message"] = request.edited_message
        url = await post_single_finding_comment(review["pr_url"], finding_dict)
        
        # Mark as posted
        await conn.execute("UPDATE agent_findings SET included_in_pr = TRUE WHERE id = $1", finding_id)
        
        return {"message": "Successfully posted", "url": url}
    finally:
        await conn.close()


from pydantic import BaseModel
class ApproveReviewRequest(BaseModel):
    comment: str = ""

@router.post("/{review_id}/approve")
async def approve_review(review_id: str, request: ApproveReviewRequest):
    """
    Resume a paused workflow (HITL) by explicitly approving it.
    This routes the graph to the output node.
    """
    from backend.graph.workflow import create_workflow
    from langgraph.checkpoint.redis import AsyncRedisSaver
    
    # Update DB status
    conn_string = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(conn_string)
    try:
        await conn.execute(
            "UPDATE reviews SET status=$1, updated_at=NOW() WHERE id=$2",
            "resuming", review_id,
        )
    finally:
        await conn.close()
        
    config = {"configurable": {"thread_id": review_id}}
    
    try:
        async with AsyncRedisSaver.from_conn_string(settings.redis_url) as checkpointer:
            wf = create_workflow(checkpointer)
            
            state = await wf.aget_state(config)
            if not state.next:
                raise HTTPException(status_code=400, detail="Workflow is not paused.")
                
            # Resume execution
            final_state = await wf.ainvoke(None, config=config)
            
            consensus_result = final_state.get("consensus_result") or {}
            recommendation = consensus_result.get("recommendation", "approve_with_comments")
            risk_score = consensus_result.get("risk_score", 0)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to resume workflow", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to resume workflow.")
        
    # Update status to complete
    conn = await asyncpg.connect(conn_string)
    try:
        await conn.execute(
            "UPDATE reviews SET status=$1, updated_at=NOW(), completed_at=NOW(), risk_score=$2, recommendation=$3 WHERE id=$4",
            "complete", risk_score, recommendation, review_id,
        )
    finally:
        await conn.close()
        
    # Trigger Phase 7 Documentation and Test Agent generation
    from backend.tasks.review_tasks import generate_artifacts_task
    generate_artifacts_task.delay(review_id)
    
    return {"message": "Review resumed and completed successfully. Artifact generation started.", "review_id": review_id}

from fastapi import WebSocket, WebSocketDisconnect
import asyncio

@router.websocket("/{review_id}/ws")
async def review_progress_ws(websocket: WebSocket, review_id: str):
    """
    WebSocket endpoint to stream real-time execution progress of the agents
    for a specific review.
    """
    await websocket.accept()
    from backend.utils.pubsub import get_redis_client
    client = get_redis_client()
    pubsub = client.pubsub()
    channel = f"review:{review_id}:progress"
    
    try:
        await pubsub.subscribe(channel)
        while True:
            # timeout=1.0 ensures we don't block forever if the client disconnects
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message:
                await websocket.send_text(message["data"])
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected", review_id=review_id)
    except Exception as e:
        logger.error("WebSocket error", error=str(e), review_id=review_id)
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.close()
