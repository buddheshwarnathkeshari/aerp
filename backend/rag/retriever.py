"""
backend/rag/retriever.py

Given a query string, finds the most semantically similar chunks
stored in pgvector for a specific review session.

This is the "R" in RAG — Retrieval.

HOW SIMILARITY SEARCH WORKS:
  1. Convert query text to a vector using the query embedder
  2. Use pgvector's "<->" operator (cosine distance) to find nearest vectors
  3. Return the top-K most similar chunks

  Cosine distance: 0 = identical, 1 = completely different.
  We ORDER BY distance ASC and take the smallest (most similar).

INTERVIEW: "What is the difference between cosine similarity and L2 distance?"
  Cosine similarity measures the ANGLE between vectors (direction).
  L2 distance measures the MAGNITUDE (Euclidean distance).
  For text embeddings, cosine is preferred because:
  - It's length-normalized (a long document and short document about the
    same topic will still be "close")
  - L2 distance is biased toward shorter texts
"""

import asyncpg
from langchain_core.tools import tool
from backend.rag.embedder import get_query_embedder
from backend.config.settings import get_settings
import structlog

logger = structlog.get_logger()
settings = get_settings()


async def retrieve_similar_chunks(
    query: str,
    review_id: str,
    top_k: int = 5,
    source_filter: str | None = None,
) -> list[dict]:
    """
    Retrieves the top-K most semantically similar chunks for a query.

    Args:
        query: The search query (e.g., "authentication middleware")
        review_id: Only search chunks from this review
        top_k: Number of results to return (5 is a good default)
        source_filter: Optional — restrict to "github_pr", "jira", or "google_doc"

    Returns:
        List of dicts with 'content', 'source', 'metadata', 'distance'
    """
    embedder = get_query_embedder()

    # Embed the query
    query_vector = await embedder.aembed_query(query)

    conn_string = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(conn_string)

    try:
        if source_filter:
            rows = await conn.fetch(
                """
                SELECT content, source, metadata,
                       embedding <-> $1::vector AS distance
                FROM embeddings
                WHERE pull_request_id = $2 AND source = $3
                ORDER BY distance ASC
                LIMIT $4
                """,
                str(query_vector),
                review_id,
                source_filter,
                top_k,
            )
        else:
            rows = await conn.fetch(
                """
                SELECT content, source, metadata,
                       embedding <-> $1::vector AS distance
                FROM embeddings
                WHERE pull_request_id = $2
                ORDER BY distance ASC
                LIMIT $3
                """,
                str(query_vector),
                review_id,
                top_k,
            )

        return [
            {
                "content": row["content"],
                "source": row["source"],
                "metadata": row["metadata"],
                "distance": float(row["distance"]),
            }
            for row in rows
        ]
    finally:
        await conn.close()


def build_rag_tool(review_id: str):
    """
    Creates a LangChain Tool for RAG search, bound to a specific review_id.

    WHY BIND review_id?
      The @tool decorator creates a function without review_id context.
      We need the tool to only search chunks from the CURRENT review.
      By creating the tool dynamically per review, we "close over" the
      review_id — this is called a closure.

    INTERVIEW: "What is a closure?"
      A closure is a function that "remembers" variables from its enclosing scope.
      Here, the inner function remembers `review_id` even after `build_rag_tool` returns.
    """
    async def search_context(query: str, source: str | None = None) -> str:
        """
        Search the review context (PR, Jira, docs) for relevant information.
        Use when you need to find specific details about requirements, code patterns,
        or documentation that aren't directly in the diff.

        Args:
            query: What you're looking for (e.g., "authentication requirements")
            source: Optional filter: "github_pr", "jira", or "google_doc"

        Returns:
            Top 5 most relevant text chunks with their sources.
        """
        results = await retrieve_similar_chunks(
            query=query,
            review_id=review_id,
            top_k=5,
            source_filter=source,
        )

        if not results:
            return f"No relevant context found for: '{query}'"

        output = [f"Found {len(results)} relevant chunks for '{query}':\n"]
        for i, r in enumerate(results, 1):
            source_label = r["source"].replace("_", " ").title()
            distance = r["distance"]
            output.append(
                f"\n[{i}] Source: {source_label} (similarity: {1 - distance:.2f})\n"
                f"{r['content'][:800]}"  # Limit each chunk to 800 chars
            )

        return "\n".join(output)

    # Wrap as LangChain tool so agents can call it
    return tool(search_context)
