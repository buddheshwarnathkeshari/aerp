"""
backend/api/routes/reviews.py

FastAPI route handlers for the review API.

DESIGN: Routes only do 3 things:
  1. Validate the request (Pydantic does this automatically)
  2. Call the service/task layer
  3. Return a response
"""

import os
import uuid
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, case
from backend.api.schemas.review_schemas import (
    StartReviewRequest,
    StartReviewResponse,
    ReviewStatusResponse,
)
from backend.tasks.review_tasks import run_review_task
from backend.config.settings import get_settings
from backend.api.deps import get_db, get_current_user
from backend.db.models import PullRequest, Comment, User, ReviewLog
import structlog
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

router = APIRouter(prefix="/reviews", tags=["reviews"])
logger = structlog.get_logger()
settings = get_settings()


@router.post(
    "/start",
    response_model=StartReviewResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_review(
    request: StartReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    review_id = uuid.uuid4()
    logger.info(
        "Starting review",
        review_id=str(review_id),
        pr_url=request.pr_url,
        user_id=str(current_user.id),
    )

    provider = settings.llm_provider.lower() or "gemini"
    if provider == "openai":
        model = settings.openai_model
    elif provider == "anthropic":
        model = settings.anthropic_model
    elif provider == "ollama":
        model = os.getenv("OLLAMA_MODEL", "llama3.1")
    else:
        provider = "gemini"
        model = settings.gemini_model

    new_pr = PullRequest(
        id=review_id,
        user_id=current_user.id,
        pr_url=request.pr_url,
        jira_url=request.jira_url,
        doc_url=request.doc_url,
        status="queued",
        llm_provider=provider,
        llm_model=model,
    )
    db.add(new_pr)
    await db.commit()

    task = run_review_task.delay(
        review_id=str(review_id),
        pr_url=request.pr_url,
        jira_url=request.jira_url,
        doc_url=request.doc_url,
        user_id=str(current_user.id),
    )

    new_pr.task_id = task.id
    await db.commit()

    return StartReviewResponse(
        review_id=str(review_id),
        status="queued",
        message="Review started. Poll the status URL for updates.",
        status_url=f"/reviews/{review_id}/status",
    )


@router.get("/{review_id}/status", response_model=ReviewStatusResponse)
async def get_review_status(
    review_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(PullRequest).where(PullRequest.id == uuid.UUID(review_id))
    result = await db.execute(stmt)
    pr = result.scalar_one_or_none()

    if not pr:
        raise HTTPException(status_code=404, detail=f"Review {review_id} not found")

    if pr.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    return ReviewStatusResponse(
        review_id=str(pr.id),
        status=pr.status,
        created_at=pr.created_at,
        updated_at=pr.updated_at,
        completed_at=pr.completed_at,
        risk_score=pr.risk_score,
        recommendation=pr.recommendation,
        error=pr.error,
        llm_provider=pr.llm_provider,
        llm_model=pr.llm_model,
    )


@router.post("/{review_id}/cancel")
async def cancel_review(
    review_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(PullRequest).where(PullRequest.id == uuid.UUID(review_id))
    result = await db.execute(stmt)
    pr = result.scalar_one_or_none()

    if not pr:
        raise HTTPException(status_code=404, detail="Review not found")
    if pr.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    if pr.status in ["complete", "failed", "cancelled"]:
        return {"message": f"Review is already {pr.status}."}

    if pr.task_id:
        from backend.tasks.celery_app import celery_app

        logger.warning(
            "Revoking and terminating Celery task",
            task_id=pr.task_id,
            review_id=review_id,
        )
        celery_app.control.revoke(pr.task_id, terminate=True)

    pr.status = "cancelled"

    log_entry = ReviewLog(
        pull_request_id=uuid.UUID(review_id),
        agent_name="System",
        status="cancelled",
        message="Review was forcefully aborted by user.",
    )
    db.add(log_entry)
    await db.commit()

    from backend.utils.pubsub import get_redis_client

    client = get_redis_client()
    client.publish(f"review:{review_id}:progress", "SYSTEM: Review aborted by user.")

    return {"message": "Review successfully cancelled."}


@router.get("/health")
async def health_check():
    return {"status": "healthy", "service": "aerp-api"}


@router.get("/{review_id}/findings")
async def get_review_findings(
    review_id: str,
    severity: str = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    pr_stmt = select(PullRequest).where(PullRequest.id == uuid.UUID(review_id))
    pr = (await db.execute(pr_stmt)).scalar_one_or_none()
    if not pr or pr.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    stmt = select(Comment).where(Comment.pull_request_id == uuid.UUID(review_id))
    if severity:
        stmt = stmt.where(Comment.severity == severity)

    severity_order = case(
        (Comment.severity == "critical", 1),
        (Comment.severity == "high", 2),
        (Comment.severity == "medium", 3),
        (Comment.severity == "low", 4),
        else_=5,
    )
    stmt = stmt.order_by(severity_order, desc(Comment.confidence))

    result = await db.execute(stmt)
    comments = result.scalars().all()

    findings = [
        {
            "id": str(c.id),
            "agent": c.agent,
            "severity": c.severity,
            "confidence": c.confidence,
            "title": c.title,
            "description": c.description,
            "file_path": c.file_path,
            "line_number": c.line_number,
            "evidence": c.evidence,
            "suggested_fix": c.suggested_fix,
            "owasp_category": c.owasp_category,
            "included_in_pr": c.is_posted_to_github,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in comments
    ]
    return {
        "review_id": review_id,
        "total": len(findings),
        "findings": findings,
    }


@router.get("/{review_id}/logs")
async def get_review_logs(
    review_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    pr_stmt = select(PullRequest).where(PullRequest.id == uuid.UUID(review_id))
    pr = (await db.execute(pr_stmt)).scalar_one_or_none()
    if not pr or pr.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    stmt = (
        select(ReviewLog)
        .where(ReviewLog.pull_request_id == uuid.UUID(review_id))
        .order_by(ReviewLog.created_at)
    )
    result = await db.execute(stmt)
    logs = result.scalars().all()

    return {
        "logs": [
            {
                "agent_name": l.agent_name,
                "status": l.status,
                "message": l.message,
                "created_at": l.created_at,
            }
            for l in logs
        ]
    }


@router.get("")
async def list_reviews(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = (
        select(PullRequest)
        .where(PullRequest.user_id == current_user.id)
        .order_by(desc(PullRequest.created_at))
        .limit(limit)
    )
    result = await db.execute(stmt)
    prs = result.scalars().all()

    return {
        "reviews": [
            {
                "id": str(pr.id),
                "pr_url": pr.pr_url,
                "status": pr.status,
                "risk_score": pr.risk_score,
                "created_at": pr.created_at,
                "llm_provider": pr.llm_provider,
                "llm_model": pr.llm_model,
            }
            for pr in prs
        ]
    }


class PostFindingRequest(BaseModel):
    edited_message: Optional[str] = None


@router.post("/{review_id}/findings/{finding_id}/post")
async def post_finding_to_pr(
    review_id: str,
    finding_id: str,
    request: PostFindingRequest = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    pr_stmt = select(PullRequest).where(PullRequest.id == uuid.UUID(review_id))
    pr = (await db.execute(pr_stmt)).scalar_one_or_none()

    if not pr or pr.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Review not found")

    comment_stmt = select(Comment).where(
        Comment.id == uuid.UUID(finding_id),
        Comment.pull_request_id == uuid.UUID(review_id),
    )
    finding = (await db.execute(comment_stmt)).scalar_one_or_none()

    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")

    if finding.is_posted_to_github:
        return {"message": "Already posted"}

    from backend.db.models import ThirdPartyUserAccount, ThirdPartyIntegration

    token_stmt = (
        select(ThirdPartyUserAccount)
        .join(ThirdPartyIntegration)
        .where(
            ThirdPartyUserAccount.user_id == current_user.id,
            ThirdPartyIntegration.name == "github",
        )
    )
    github_account = (await db.execute(token_stmt)).scalar_one_or_none()
    if github_account and github_account.access_token_encrypted:
        from backend.utils.encryption import decrypt_token

        github_token = decrypt_token(github_account.access_token_encrypted)
    else:
        github_token = settings.github_token

    from backend.tools.github_tool import post_single_finding_comment

    finding_dict = {
        "title": finding.title,
        "severity": finding.severity,
        "description": finding.description,
        "file_path": finding.file_path,
        "evidence": finding.evidence,
        "included_in_pr": finding.is_posted_to_github,
    }
    if request and request.edited_message:
        finding_dict["edited_message"] = request.edited_message

    try:
        url = await post_single_finding_comment(pr.pr_url, finding_dict, github_token)
    except Exception as e:
        logger.error("Failed to post finding", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to post finding")

    finding.is_posted_to_github = True
    await db.commit()

    return {"message": "Successfully posted", "url": url}


class ApproveReviewRequest(BaseModel):
    comment: str = ""


@router.post("/{review_id}/approve")
async def approve_review(
    review_id: str,
    request: ApproveReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(PullRequest).where(PullRequest.id == uuid.UUID(review_id))
    pr = (await db.execute(stmt)).scalar_one_or_none()

    if not pr or pr.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Review not found")

    pr.status = "resuming"
    await db.commit()

    from backend.db.models import ThirdPartyUserAccount, ThirdPartyIntegration

    token_stmt = (
        select(ThirdPartyUserAccount)
        .join(ThirdPartyIntegration)
        .where(
            ThirdPartyUserAccount.user_id == current_user.id,
            ThirdPartyIntegration.name == "github",
        )
    )
    github_account = (await db.execute(token_stmt)).scalar_one_or_none()

    github_token = None
    if github_account and github_account.access_token_encrypted:
        from backend.utils.encryption import decrypt_token

        github_token = decrypt_token(github_account.access_token_encrypted)

    from backend.graph.workflow import create_workflow
    from langgraph.checkpoint.redis import AsyncRedisSaver

    config = {"configurable": {"thread_id": review_id, "github_token": github_token}}

    try:
        async with AsyncRedisSaver.from_conn_string(settings.redis_url) as checkpointer:
            wf = create_workflow(checkpointer)

            state = await wf.aget_state(config)
            if not state.next:
                raise HTTPException(status_code=400, detail="Workflow is not paused.")

            final_state = await wf.ainvoke(None, config=config)

            consensus_result = final_state.get("consensus_result") or {}
            recommendation = consensus_result.get(
                "recommendation", "approve_with_comments"
            )
            risk_score = consensus_result.get("risk_score", 0)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to resume workflow", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to resume workflow.")

    pr.status = "complete"
    pr.risk_score = risk_score
    pr.recommendation = recommendation
    pr.completed_at = datetime.now(timezone.utc)
    await db.commit()

    from backend.tasks.review_tasks import generate_artifacts_task

    generate_artifacts_task.delay(review_id)

    return {
        "message": "Review resumed and completed successfully. Artifact generation started.",
        "review_id": review_id,
    }


from fastapi import WebSocket, WebSocketDisconnect
import asyncio


@router.websocket("/{review_id}/ws")
async def review_progress_ws(websocket: WebSocket, review_id: str):
    await websocket.accept()
    from backend.utils.pubsub import get_redis_client

    client = get_redis_client()
    pubsub = client.pubsub()
    channel = f"review:{review_id}:progress"

    try:
        await pubsub.subscribe(channel)
        while True:
            message = await pubsub.get_message(
                ignore_subscribe_messages=True, timeout=1.0
            )
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
