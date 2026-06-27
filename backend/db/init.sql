-- backend/db/init.sql
-- This script runs automatically when PostgreSQL starts for the first time.
-- It sets up the pgvector extension and creates our schema.

-- Enable pgvector extension
-- WHY: pgvector adds the vector data type and similarity search operators.
-- Without this, we can't store or search embeddings.
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable uuid-ossp for UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ─────────────────────────────────────────────────────────────────────────────
-- Reviews table
-- Stores one row per review session. This is the "audit trail".
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS reviews (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pr_url          TEXT NOT NULL,
    jira_url        TEXT,
    doc_url         TEXT,
    status          TEXT NOT NULL DEFAULT 'pending',
    -- Status values: pending | collecting | reviewing | consensus |
    --                awaiting_human | approved | rejected | complete | failed
    risk_score      INTEGER,
    recommendation  TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ,
    error           TEXT,
    llm_provider    TEXT,
    llm_model       TEXT
);

-- ─────────────────────────────────────────────────────────────────────────────
-- Agent findings table
-- Stores individual findings from each agent. One row per finding.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS agent_findings (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    review_id       UUID NOT NULL REFERENCES reviews(id) ON DELETE CASCADE,
    agent           TEXT NOT NULL,          -- which agent produced this
    severity        TEXT NOT NULL,          -- critical|high|medium|low|info
    confidence      FLOAT NOT NULL,
    title           TEXT NOT NULL,
    description     TEXT NOT NULL,
    file_path       TEXT,
    line_number     INTEGER,
    evidence        TEXT NOT NULL,
    suggested_fix   TEXT,
    owasp_category  TEXT,                   -- for security findings
    included_in_pr  BOOLEAN DEFAULT FALSE,  -- was this posted on the PR?
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────────────────────
-- Human decisions table
-- Audit trail of every human approval/rejection. Critical for compliance.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS human_decisions (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    review_id   UUID NOT NULL REFERENCES reviews(id) ON DELETE CASCADE,
    decision    TEXT NOT NULL,          -- approve|reject|approve_with_override
    reviewer    TEXT NOT NULL,
    comment     TEXT,
    decided_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────────────────────
-- Review execution logs
-- Persistent storage for agent status updates (used for UI history and auditing).
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS review_logs (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    review_id   UUID NOT NULL REFERENCES reviews(id) ON DELETE CASCADE,
    agent_name  TEXT NOT NULL,
    status      TEXT NOT NULL,          -- running|complete|failed|skipped
    message     TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────────────────────
-- Embeddings table (pgvector)
-- Stores document chunks with their vector embeddings for RAG search.
--
-- WHY vector(768)?
-- Google's text-embedding-004 model outputs 768-dimensional vectors.
-- Different embedding models have different dimensions:
--   text-embedding-004:     768 dimensions
--   text-embedding-3-small: 1536 dimensions
--   text-embedding-3-large: 3072 dimensions
-- The dimension MUST match your embedding model's output.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS embeddings (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    review_id   UUID NOT NULL REFERENCES reviews(id) ON DELETE CASCADE,
    source      TEXT NOT NULL,      -- "github_pr" | "jira" | "google_doc" | "repo_file"
    content     TEXT NOT NULL,      -- The actual text chunk
    metadata    JSONB,              -- File path, page number, section, etc.
    embedding   vector,             -- Variable dimension vector
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────────────────────
-- Indexes
-- ─────────────────────────────────────────────────────────────────────────────

-- Standard indexes for frequent query patterns
CREATE INDEX IF NOT EXISTS idx_reviews_status ON reviews(status);
CREATE INDEX IF NOT EXISTS idx_findings_review_id ON agent_findings(review_id);
CREATE INDEX IF NOT EXISTS idx_findings_severity ON agent_findings(severity);
CREATE INDEX IF NOT EXISTS idx_embeddings_review_id ON embeddings(review_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_source ON embeddings(source);

-- Vector similarity search index (HNSW)
-- WHY HNSW instead of exact search?
-- Exact nearest-neighbor search is O(n) — checks every vector.
-- HNSW (Hierarchical Navigable Small World) is approximate but O(log n).
-- For 10K vectors, HNSW is ~100x faster with <1% accuracy loss.
-- "ef_construction=64, m=16" are standard production settings.
CREATE INDEX IF NOT EXISTS idx_embeddings_vector
    ON embeddings USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
