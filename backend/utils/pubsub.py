import json
import uuid
import redis.asyncio as redis
from backend.config.settings import get_settings

settings = get_settings()

_redis_pool = None

def get_redis_client() -> redis.Redis:
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = redis.ConnectionPool.from_url(settings.redis_url, decode_responses=True)
    return redis.Redis(connection_pool=_redis_pool)

async def publish_progress(review_id: str, message: str):
    """
    Publishes a progress message for a specific review to a Redis channel.
    The channel is specific to the review: review:{review_id}:progress
    """
    client = get_redis_client()
    channel = f"review:{review_id}:progress"
    try:
        await client.publish(channel, message)
    except Exception as e:
        import structlog
        logger = structlog.get_logger()
        logger.error("Failed to publish progress", error=str(e), review_id=review_id)

async def publish_agent_status(review_id: str, agent: str, status: str, message: str):
    """
    Helper to publish structured agent status updates (running, complete, failed).
    """
    payload = json.dumps({
        "agent": agent,
        "status": status,
        "message": message
    })
    await publish_progress(review_id, payload)
    
    # Also write to PostgreSQL for persistence
    import asyncpg
    conn_string = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    try:
        conn = await asyncpg.connect(conn_string)
        await conn.execute(
            "INSERT INTO review_logs (id, pull_request_id, agent_name, status, message) VALUES ($1, $2, $3, $4, $5)",
            uuid.uuid4(), review_id, agent, status, message
        )
        await conn.close()
    except Exception as e:
        import structlog
        structlog.get_logger().error("Failed to insert log into DB", error=str(e), review_id=review_id)
