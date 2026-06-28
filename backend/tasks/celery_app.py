"""
backend/tasks/celery_app.py + review_tasks.py
"""

# ─── celery_app.py ────────────────────────────────────────────────────────────
from celery import Celery
from backend.config.settings import get_settings

settings = get_settings()

# Create Celery app
# First arg = module name (used for task naming)
# broker = where tasks are queued (Redis)
# backend = where task results are stored (also Redis)
celery_app = Celery(
    "aerp",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["backend.tasks.review_tasks"],  # Auto-discover tasks
)

celery_app.conf.update(
    # ── Task settings ─────────────────────────────────────────────────────────
    task_serializer="json",  # Use JSON (not pickle — security risk)
    result_serializer="json",
    accept_content=["json"],
    # ── Retry settings ────────────────────────────────────────────────────────
    task_acks_late=True,  # Acknowledge AFTER task completes (not before)
    # Design Note: task_acks_late=True?
    # Default: Celery removes task from queue BEFORE running it.
    # If the worker crashes mid-task, the task is LOST.
    # With acks_late=True: task stays in queue until worker confirms completion.
    # If worker crashes, another worker picks it up and retries.
    task_reject_on_worker_lost=True,  # Re-queue if worker dies
    # ── Result expiry ─────────────────────────────────────────────────────────
    result_expires=3600,  # Results expire after 1 hour (86400 = 1 day)
    # ── Concurrency ───────────────────────────────────────────────────────────
    worker_prefetch_multiplier=1,  # Each worker takes 1 task at a time
    # Design Note: 1? LangGraph workflows are long-running (5-10 min).
    # Prefetching more would cause one worker to hoard multiple reviews
    # while others sit idle.
    # ── Timezone ──────────────────────────────────────────────────────────────
    timezone="UTC",
    enable_utc=True,
)
