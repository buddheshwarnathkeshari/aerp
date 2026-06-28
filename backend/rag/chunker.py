"""
backend/rag/chunker.py

Splits documents into chunks for embedding and storage in pgvector.

Design Note: Chunking?
  Embedding models have input limits (e.g., 2048 tokens max).
  A PR diff or feature doc might be 50,000 tokens.
  We split into smaller, overlapping chunks so:
    1. Each chunk fits within embedding model limits
    2. Semantic meaning is preserved per chunk
    3. Retrieval returns focused, relevant context

Design Note: Overlap?
  A sentence at the END of chunk 1 may be contextually connected
  to the sentence at the START of chunk 2.
  Without overlap, these get split and lose their connection.
  50-token overlap ensures boundary context is preserved.

  [──── chunk 1 ────][overlap][──── chunk 2 ────]
                     [overlap] = same content in both chunks

  We use RecursiveCharacterTextSplitter because it tries to split on
  natural boundaries first (paragraphs → sentences → words → characters).
  This preserves semantic coherence better than fixed-size splitting.
"""

from langchain_text_splitters import RecursiveCharacterTextSplitter
from typing import NamedTuple


class DocumentChunk(NamedTuple):
    """A single chunk ready for embedding."""

    content: str  # The text content
    source: str  # Where it came from: "github_pr" | "jira" | "google_doc"
    metadata: dict  # Extra info: file_path, section, page, etc.


# Chunking configs per document type
# Different content types have different optimal chunk sizes:
#   - Code diffs: smaller chunks (code is dense with meaning)
#   - Documentation: larger chunks (prose needs more context)
#   - Jira tickets: usually small enough to embed whole

CHUNK_CONFIGS = {
    "github_pr": {
        "chunk_size": 800,  # ~600 words — code is dense
        "chunk_overlap": 100,
    },
    "jira": {
        "chunk_size": 1500,  # Jira tickets are prose, need more context
        "chunk_overlap": 150,
    },
    "google_doc": {
        "chunk_size": 1500,  # Feature docs are prose
        "chunk_overlap": 150,
    },
    "repo_file": {
        "chunk_size": 600,  # Individual files — smaller for precision
        "chunk_overlap": 80,
    },
}


def chunk_document(
    content: str,
    source: str,
    metadata: dict | None = None,
) -> list[DocumentChunk]:
    """
    Splits a document into chunks using source-appropriate settings.

    Args:
        content: The raw text to chunk
        source: Type of document ("github_pr", "jira", "google_doc", "repo_file")
        metadata: Additional context to attach to each chunk

    Returns:
        List of DocumentChunk objects ready for embedding
    """
    if not content or not content.strip():
        return []

    config = CHUNK_CONFIGS.get(source, CHUNK_CONFIGS["google_doc"])

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config["chunk_size"],
        chunk_overlap=config["chunk_overlap"],
        # Separators tried in order — falls back to next if previous produces too-large chunks
        # This is the "recursive" in RecursiveCharacterTextSplitter
        separators=[
            "\n\n",  # Try paragraph break first
            "\n",  # Then line break
            ". ",  # Then sentence
            ", ",  # Then clause
            " ",  # Then word
            "",  # Last resort: character split
        ],
        length_function=len,
    )

    texts = splitter.split_text(content)

    chunks = []
    for i, text in enumerate(texts):
        chunk_metadata = {
            "chunk_index": i,
            "total_chunks": len(texts),
            "source": source,
            **(metadata or {}),
        }
        chunks.append(
            DocumentChunk(
                content=text.strip(),
                source=source,
                metadata=chunk_metadata,
            )
        )

    return chunks


def chunk_pr_diff(diff: str, pr_metadata: dict) -> list[DocumentChunk]:
    """
    Special chunking for PR diffs — splits per file.

    Design Note: Per FILE?
      A PR diff might touch 20 files. Chunking randomly across the whole diff
      would mix context from different files. Splitting per file means each
      chunk is semantically coherent (all from one file).
    """
    chunks = []

    # Split diff into per-file sections (each starts with "diff --git")
    file_diffs = diff.split("diff --git ")
    file_diffs = [d for d in file_diffs if d.strip()]  # Remove empty

    for file_diff in file_diffs:
        # Extract filename from diff header: "a/src/file.py b/src/file.py"
        lines = file_diff.split("\n")
        filename = lines[0].split(" b/")[-1] if " b/" in lines[0] else "unknown"

        file_chunks = chunk_document(
            content=f"diff --git {file_diff}",
            source="github_pr",
            metadata={
                "file_path": filename,
                "pr_number": pr_metadata.get("pr_number"),
                "repo": pr_metadata.get("repo_name"),
            },
        )
        chunks.extend(file_chunks)

    return chunks
