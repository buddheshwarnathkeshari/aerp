from backend.tasks.review_tasks import run_review
import sys

run_review.delay('a58dcf88-bccd-4e12-8754-a655d03fd084')
print("Triggered!")
