"""
backend/rag/embedder.py + indexer.py + retriever.py

The complete RAG pipeline in one module.

EMBEDDER:  text → vector (768 numbers representing meaning)
INDEXER:   store (text + vector) in pgvector
RETRIEVER: given a query, find the most similar stored chunks
"""

# ── embedder.py logic ─────────────────────────────────────────────────────────
from backend.utils.llm_factory import get_embedder as get_llm_embedder
from langchain_core.embeddings import Embeddings


def get_embedder() -> Embeddings:
    """
    Returns the configured embedding model.
    """
    return get_llm_embedder()


def get_query_embedder() -> Embeddings:
    """Embedder optimized for query vectors."""
    return get_llm_embedder()
