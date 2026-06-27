from backend.tasks.celery_app import celery_app
from backend.tasks.review_tasks import generate_artifacts_task

print("Triggering task...")
result = generate_artifacts_task.delay("12a223fe-a288-46f5-b58c-080570c1790b")
print(f"Task ID: {result.id}")
