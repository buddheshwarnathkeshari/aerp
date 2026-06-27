import asyncio
from sqlalchemy import select
from backend.db.session import AsyncSessionLocal
from backend.db.models import PullRequest, Comment, ReviewLog
import uuid

async def main():
    review_id = uuid.UUID("a678859b-2b2a-40ef-b51d-e47ae4628a60")
    async with AsyncSessionLocal() as session:
        # Get PR
        pr = (await session.execute(select(PullRequest).where(PullRequest.id == review_id))).scalar_one_or_none()
        print(f"PR Status: {pr.status}, Recommendation: {pr.recommendation}")
        
        # Get Logs
        print("\n--- LOGS ---")
        logs = (await session.execute(select(ReviewLog).where(ReviewLog.pull_request_id == review_id).order_by(ReviewLog.created_at))).scalars().all()
        for log in logs:
            print(f"{log.created_at} [{log.agent_name}] {log.status}: {log.message}")
            
        # Get Findings
        print("\n--- FINDINGS ---")
        comments = (await session.execute(select(Comment).where(Comment.pull_request_id == review_id))).scalars().all()
        for c in comments:
            print(f"[{c.severity}] {c.agent}: {c.title}")
            
asyncio.run(main())
