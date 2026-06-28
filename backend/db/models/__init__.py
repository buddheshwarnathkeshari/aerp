"""
backend/db/models/__init__.py

Re-exports all ORM models so that:
  1. Alembic's env.py can import Base and see ALL models for autogenerate
  2. Application code can do: from backend.db.models import User, PullRequest

IMPORTANT: Every model must be imported here, otherwise Alembic
won't know it exists and won't generate migrations for it.
"""

from backend.db.models.base import Base, TimestampMixin
from backend.db.models.user import User
from backend.db.models.refresh_token import RefreshToken
from backend.db.models.third_party_integration import ThirdPartyIntegration
from backend.db.models.third_party_user_account import ThirdPartyUserAccount
from backend.db.models.pull_request import PullRequest
from backend.db.models.comment import Comment
from backend.db.models.human_decision import HumanDecision
from backend.db.models.review_log import ReviewLog
from backend.db.models.embedding import Embedding

__all__ = [
    "Base",
    "TimestampMixin",
    "User",
    "RefreshToken",
    "ThirdPartyIntegration",
    "ThirdPartyUserAccount",
    "PullRequest",
    "Comment",
    "HumanDecision",
    "ReviewLog",
    "Embedding",
]
