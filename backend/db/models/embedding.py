"""
backend/db/models/embedding.py

Embedding ORM model — the RAG vector store.

WHY THIS IS DIFFERENT FROM ALL OTHER MODELS:
  Every other model uses standard SQL types (Text, Integer, UUID).
  This model uses the `vector` type from the pgvector extension —
  a PostgreSQL-specific type that doesn't exist in standard SQLAlchemy.

  The `pgvector` Python package provides a SQLAlchemy type adapter:
    from pgvector.sqlalchemy import Vector

  This lets us define vector columns in SQLAlchemy ORM just like any other column.

DIMENSION (768):
  Google's text-embedding-004 model outputs 768-dimensional vectors.
  The dimension MUST match your embedding model's output exactly.
  If you switch embedding models, you need a migration to change this.

  Common dimensions:
    text-embedding-004 (Google):     768
    text-embedding-3-small (OpenAI): 1536
    text-embedding-3-large (OpenAI): 3072

THE HNSW INDEX:
  We can't define the HNSW index via SQLAlchemy ORM column definition.
  It must be created in the Alembic migration using op.execute():

    op.execute(
        'CREATE INDEX idx_embeddings_vector '
        'ON embeddings USING hnsw (embedding vector_cosine_ops) '
        'WITH (m = 16, ef_construction = 64)'
    )

  HNSW = Hierarchical Navigable Small World
  - Approximate nearest-neighbor search
  - O(log n) instead of O(n) for exact search
  - ~99.5% recall accuracy with >100x speed improvement
  - m=16: each node connects to 16 neighbors
  - ef_construction=64: thoroughness of index build

SOURCE VALUES:
  'github_pr'   → Code chunks from the PR diff
  'jira'        → Jira ticket content (title, description, AC)
  'google_doc'  → Feature/design document content
  'repo_file'   → Codebase files for context (not diff, but full files)
"""

import uuid
from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.db.models.base import Base, TimestampMixin


class Embedding(Base, TimestampMixin):
    __tablename__ = "embeddings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # ── Foreign Key ────────────────────────────────────────────────────────────
    pull_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pull_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="All embeddings are scoped to a specific PR analysis.",
    )

    # ── Source ─────────────────────────────────────────────────────────────────
    source: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        index=True,
        comment="github_pr | jira | google_doc | repo_file",
    )

    # ── Content ────────────────────────────────────────────────────────────────
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="The raw text chunk that was embedded. What humans read.",
    )
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata",  # actual column name in DB (metadata is a reserved SQLAlchemy attr)
        JSONB,
        nullable=True,
        comment='{"file": "payments.py", "lines": "44-58", "chunk_index": 3}',
    )

    # ── Vector ─────────────────────────────────────────────────────────────────
    embedding: Mapped[list | None] = mapped_column(
        Vector(768),
        nullable=True,
        comment=(
            "768-dimensional float vector from Google text-embedding-004. "
            "The HNSW index on this column enables fast similarity search. "
            "NULL only transiently, while embedding is being computed."
        ),
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    pull_request: Mapped["PullRequest"] = relationship(
        "PullRequest", back_populates="embeddings"
    )

    def __repr__(self) -> str:
        return f"<Embedding pull_request_id={self.pull_request_id} source={self.source}>"
