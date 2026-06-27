"""
backend/rag/indexer.py

Stores document chunks + their embeddings into pgvector.
Called during context collection — before any agents run.

RESILIENCE:
  If the embedding API fails (e.g., 403 billing not set up, rate limit),
  we log a warning and continue WITHOUT embeddings.
  The Code Review Agent can still run using the raw context string.
  RAG search will return empty results, but the agent will still produce findings.
  This avoids a single API error killing the entire review.
"""

import asyncpg
import uuid
from backend.rag.chunker import DocumentChunk
from backend.rag.embedder import get_embedder
from backend.config.settings import get_settings
import structlog

logger = structlog.get_logger()
settings = get_settings()


async def index_chunks(
    chunks: list[DocumentChunk],
    review_id: str,
    db_conn_string: str | None = None,
) -> int:
    """
    Embeds a list of chunks and stores them in pgvector.

    Args:
        chunks: List of DocumentChunk objects from the chunker
        review_id: Associates chunks with this review session
        db_conn_string: PostgreSQL connection string (defaults to settings)

    Returns:
        Number of chunks successfully indexed (0 if embedding unavailable)

    BATCH PROCESSING:
      We embed in batches of 100 to avoid hitting Gemini API rate limits.
      Batching reduces API calls from N to N/100.

    FAILURE HANDLING:
      If embedding fails (403, quota exceeded, network error), we:
      1. Log a warning with the reason
      2. Return 0 (no chunks indexed)
      3. Let the workflow continue — agents will use raw_context instead
    """
    if not chunks:
        return 0

    conn_string = db_conn_string or settings.database_url.replace(
        "postgresql+asyncpg://", "postgresql://"
    )

    embedder = get_embedder()
    batch_size = 100
    total_indexed = 0

    conn = await asyncpg.connect(conn_string)

    try:
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            texts = [chunk.content for chunk in batch]

            logger.info(
                "Embedding batch",
                batch_num=i // batch_size + 1,
                batch_size=len(batch),
            )

            try:
                embeddings = await embedder.aembed_documents(texts)
            except Exception as embed_err:
                # Embedding failed (billing not set up, quota, etc.)
                # Log a warning and skip — the review continues without RAG
                logger.warning(
                    "Embedding API unavailable — skipping RAG indexing",
                    error=str(embed_err),
                    review_id=review_id,
                    hint="Enable billing at console.cloud.google.com to activate RAG search",
                )
                return 0  # No chunks indexed, but workflow continues

            # Store each chunk + embedding in PostgreSQL
            for chunk, embedding in zip(batch, embeddings):
                await conn.execute(
                    """
                    INSERT INTO embeddings (id, pull_request_id, source, content, metadata, embedding)
                    VALUES ($1, $2, $3, $4, $5::jsonb, $6::vector)
                    """,
                    uuid.uuid4(),
                    review_id,
                    chunk.source,
                    chunk.content,
                    str(chunk.metadata).replace("'", '"'),
                    str(embedding),
                )

            total_indexed += len(batch)

    finally:
        await conn.close()

    logger.info("Indexing complete", total_chunks=total_indexed, review_id=review_id)
    return total_indexed
