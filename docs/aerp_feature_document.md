# AI Engineering Review Platform (AERP)
## Complete Feature & Technology Document

**Version**: 1.0  
**Status**: Pre-Development  
**LLM**: Google Gemini 2.0 Flash  
**Framework**: LangGraph + LangChain

---

## Table of Contents

1. [Product Vision](#1-product-vision)
2. [Core Problem Being Solved](#2-core-problem)
3. [How the System Works — Overview](#3-overview)
4. [Inputs](#4-inputs)
5. [Outputs](#5-outputs)
6. [Agent Roster — Every Agent Explained](#6-agents)
7. [Consensus Protocol — How Agents Agree](#7-consensus)
8. [Human-in-the-Loop — When Humans Intervene](#8-hitl)
9. [RAG Pipeline — How Context is Retrieved](#9-rag)
10. [Risk Scoring Engine](#10-risk)
11. [Technology Stack — Every Tool Explained](#11-tech)
12. [Build Phases — MVP to Production](#12-phases)
13. [Future Capabilities](#13-future)

---

## 1. Product Vision

AERP is an **autonomous multi-agent engineering review system**.

It reviews a software change the way a **team of senior engineers** would — except it does it in minutes, at any time, with consistent depth.

> Traditional code review: One engineer, one perspective, after the code is written.
> AERP: Eight specialist agents, eight perspectives, simultaneously, the moment the PR is opened.

The system answers not just *"Is this code correct?"* but:

- Is this implementation aligned with what the ticket asked for?
- Does this code introduce security vulnerabilities?
- Will this query degrade at scale?
- Does this violate our architectural principles?
- What other services will this change break?
- Is this code readable and maintainable?
- Does this meet our logging and error handling standards?

And after answering all of that — it writes the review comments directly on your GitHub PR, generates missing documentation, and generates missing tests.

---

## 2. Core Problem Being Solved

| Problem | Without AERP | With AERP |
|---|---|---|
| Review bottleneck | Wait 1–3 days for reviewer | Review ready in ~5 minutes |
| Reviewer blind spots | Code reviewer misses security issues | 8 specialists each check their domain |
| Context silos | Reviewer only reads code, not ticket | All context unified: PR + Jira + Docs |
| Human fatigue | Late Friday reviews miss bugs | Consistent depth every time |
| Missing documentation | Engineers skip docs under deadline | Auto-generated and auto-PR'd |
| Missing tests | Engineers skip edge cases | Auto-generated, verified, and auto-PR'd |
| No impact awareness | No one checks what else breaks | Blast Radius Agent maps all affected modules |

---

## 3. How the System Works — Overview

```
YOU SUBMIT:
  GitHub PR URL  +  Jira Ticket URL  +  Google Doc URL
           │
           ▼
  ┌─────────────────────────────────┐
  │    Step 1: Context Collection   │
  │    GitHub MCP + Jira MCP        │
  │    + Google Docs MCP + RAG      │
  └─────────────┬───────────────────┘
                │
                ▼
  ┌─────────────────────────────────┐
  │   Step 2: Repository Analysis  │
  │   Impact graph of changed code  │
  └─────────────┬───────────────────┘
                │
         ┌──────┴──────┐
    8 agents run simultaneously (parallel)
         │
         ▼
  ┌─────────────────────────────────┐
  │   Step 3: Cross-Agent Critique  │
  │   Agents read each other's work │
  │   Withdraw false positives      │
  └─────────────┬───────────────────┘
                │
                ▼
  ┌─────────────────────────────────┐
  │   Step 4: Consensus Generation  │
  │   Merge + deduplicate + score   │
  │   Risk score 0–100              │
  │   Recommendation: APPROVE/BLOCK │
  └─────────────┬───────────────────┘
                │
         ┌──────┴──────────────┐
         │ CRITICAL/HIGH       │ LOW/MEDIUM
         ▼                     ▼
  ⏸️ PAUSE for human      Auto-route
  You approve/reject           │
         │                     │
         └──────────┬──────────┘
                    │
                    ▼
  ┌────────────────────────────────────────────────┐
  │  Step 5: Outputs (parallel)                    │
  │  • Comments posted on GitHub PR                │
  │  • Documentation PR created on GitHub          │
  │  • Test PR created on GitHub                   │
  │  • Final Engineering Report generated          │
  └────────────────────────────────────────────────┘
```

---

## 4. Inputs

### Mandatory

| Input | Source | What We Collect |
|---|---|---|
| **GitHub PR** | GitHub MCP | Diff, changed files, commit history, branch, author, PR description |
| **Jira Ticket** | Jira MCP | Story title, description, acceptance criteria, business rules, linked tickets |

### Optional (Strongly Recommended)

| Input | Source | What We Collect |
|---|---|---|
| **Feature/Design Doc** | Google Docs MCP | Feature spec, API contracts, business rules, design decisions |

### Future Inputs (Later Phases)

| Input | Phase |
|---|---|
| Screenshots (before/after) | Phase B |
| Screen recording | Phase B |
| Staging/QA environment URL | Phase A |
| Build logs | Phase A |
| Runtime logs | Phase A |

---

## 5. Outputs

### Immediate Outputs

**1. GitHub PR Review Comments**
Comments are posted directly on your GitHub PR — line-level and file-level.
Each comment includes:
```
🔴 [SECURITY - HIGH] Authorization validation missing
   before payment execution.

   Confidence: 96%
   Agent: Security Agent
   
   The payment endpoint at line 47 processes transactions
   without verifying the authenticated user owns the resource.
   This allows any authenticated user to pay for another
   user's invoice.
   
   Suggested fix: Add ownership check before transaction processing.
```

**2. Engineering Review Report**
A structured report containing:
- Per-agent findings (all raw findings before filtering)
- Validated findings (post cross-agent critique)
- Risk score per dimension (security, performance, etc.)
- Overall risk score (0–100)
- Approval recommendation with justification

**3. Documentation PR**
A GitHub Pull Request containing auto-generated documentation:
- **Product view**: What changed, why, user impact
- **Engineering view**: API changes, architecture changes, DB schema changes
- **Operations view**: Deployment notes, rollback plan, risks

**4. Test PR**
A GitHub Pull Request containing auto-generated tests:
- Unit tests for changed functions
- Integration tests for affected APIs
- Edge case tests derived from acceptance criteria
- Regression tests for impacted modules
- Tests verified to pass before PR is created

---

## 6. Agent Roster — Every Agent Explained

### 6.0 Context Collector (Not an AI Agent — a system node)

**What it is**: A LangGraph node that fetches and organizes all input data.
**What it does**:
- Calls GitHub MCP → fetches PR diff, changed files, commits
- Calls Jira MCP → fetches ticket content, acceptance criteria
- Calls Google Docs MCP → fetches feature specification
- Chunks all content → creates embeddings → stores in pgvector
- Builds the `ReviewState` that all agents share

**Output**: Fully populated `ReviewState` — the shared working memory for the entire workflow.

---

### 6.1 Repository Analyzer (Not an AI Agent — a system node)

**What it is**: A LangGraph node that maps code impact.
**What it does**:
- Identifies all changed files
- Traces dependencies (what imports this file? what does this file import?)
- Identifies impacted APIs, services, database entities
- Builds an impact graph

**Output**: `impact_graph` in ReviewState — a map of everything this change touches.

---

### 6.2 Requirements Agent

**Role**: Requirements compliance auditor.  
**System prompt identity**: "You are a senior product engineer who specializes in verifying that engineering implementations match their stated requirements."

**What it checks**:
- Was every acceptance criterion actually implemented?
- Are there edge cases in the requirements that the code ignores?
- Does the implementation match the business rules in the documentation?
- Are there requirements in the ticket that are entirely missing from the code?
- Does the PR description accurately describe what was implemented?

**Tools available**:
- `search_jira_context(query)` — RAG search over Jira content
- `search_doc_context(query)` — RAG search over feature doc
- `get_pr_diff()` — Read the code changes

**Output**:
```json
{
  "agent": "requirements_agent",
  "findings": [
    {
      "severity": "high",
      "confidence": 0.91,
      "title": "Acceptance criteria #3 not implemented",
      "description": "The ticket requires validation of partial payment minimum amount (10% of total). No such validation exists in PaymentService.",
      "file": "src/services/PaymentService.py",
      "line": null,
      "evidence": "AC #3: 'Partial payment must be minimum 10% of invoice total'"
    }
  ],
  "overall_compliance": 0.72,
  "recommendation": "request_changes"
}
```

---

### 6.3 Code Review Agent

**Role**: Senior software engineer.  
**System prompt identity**: "You are a senior software engineer with 10 years of experience reviewing Python/FastAPI codebases. You focus on code quality, readability, and maintainability."

**What it checks**:
- Method/function length (> 50 lines is a flag)
- Cyclomatic complexity (too many if/else branches)
- Code duplication (copy-paste patterns)
- Naming conventions (clear, descriptive names)
- Dead code (unreachable or unused code)
- Hard-coded values that should be constants or configs
- Missing docstrings on public methods
- Improper exception handling (bare `except:` clauses)
- Anti-patterns for the detected framework
- Readability (can a new engineer understand this in 5 minutes?)

**Tools available**:
- `search_repo_context(query)` — RAG search over codebase
- `get_pr_diff()` — Read the code changes
- `get_file_content(path)` — Read full file for context

**Output**: Structured list of findings with file paths, line numbers, severity, and suggested improvements.

---

### 6.4 Security Agent

**Role**: Application security engineer.  
**System prompt identity**: "You are an application security engineer specializing in OWASP Top 10 vulnerabilities and secure coding practices."

**What it checks**:

| Vulnerability | What it Looks For |
|---|---|
| **SQL Injection** | String concatenation in queries, unparameterized inputs |
| **XSS** | Unescaped user input rendered in responses |
| **CSRF** | Missing CSRF tokens on state-changing endpoints |
| **SSRF** | User-controlled URLs used in server-side requests |
| **Hardcoded Secrets** | API keys, passwords, tokens in source code |
| **Authentication** | Missing auth decorators, bypassed middleware |
| **Authorization** | Missing ownership checks, IDOR vulnerabilities |
| **Unsafe Deserialization** | `pickle.loads()`, `yaml.load()` without safe loader |
| **Path Traversal** | User input used in file paths |
| **Dependency Issues** | Known vulnerable packages in requirements |

**Tools available**:
- `get_pr_diff()` — Read code changes
- `search_repo_context(query)` — Find related auth/security code
- `get_file_content(path)` — Read security-relevant files

**Output**: Findings with OWASP category, CVE reference where applicable, severity (critical/high/medium/low), confidence score, and remediation guidance.

---

### 6.5 Database Agent

**Role**: Database engineer.  
**System prompt identity**: "You are a database engineer specializing in PostgreSQL query optimization, schema design, and data access patterns."

**What it checks**:

| Issue | Description |
|---|---|
| **N+1 Queries** | Loop that issues one DB query per iteration |
| **Missing Indexes** | Filter/sort columns without indexes |
| **Full Table Scans** | Queries with no WHERE clause or unindexed filters |
| **Expensive Joins** | Joining large tables without index support |
| **Missing Transactions** | Related writes not wrapped in a transaction |
| **Migration Safety** | Adding NOT NULL without default, dropping columns |
| **Connection Leaks** | DB connections opened but not closed |
| **Lock Contention** | Long-running transactions that block other queries |
| **Data Type Mismatches** | Comparing different types (forces casting = slow) |

**Tools available**:
- `get_pr_diff()` — Read migration files and query changes
- `search_repo_context(query)` — Find related DB models and repositories

**Output**: Findings with query examples, estimated performance impact, and optimized alternatives.

---

### 6.6 Scalability Agent

**Role**: Infrastructure and growth engineer.  
**System prompt identity**: "You are a platform engineer who evaluates code for future growth readiness — you think about what happens at 10x, 100x current load."

**What it checks**:
- Missing pagination on list endpoints (returns all records)
- Missing caching on expensive/repeated reads
- Synchronous operations that should be async/background
- In-memory data structures that should be database-backed
- Missing rate limiting on public endpoints
- Batch processing opportunities (processing one record at a time instead of bulk)
- Resource leak potential under high concurrency
- Tight coupling that prevents horizontal scaling

**Output**: Findings with load scenario descriptions and scaling recommendations.

---

### 6.7 Standards Agent

**Role**: Engineering standards enforcer.  
**System prompt identity**: "You are an engineering lead who ensures code adheres to team standards, consistency, and established project patterns."

**What it checks**:
- Logging standards (are logs structured? do they include request IDs? are log levels appropriate?)
- Error handling patterns (are errors propagated correctly? are custom exceptions used?)
- Project structure (is code in the right layer? service logic not in route handlers?)
- Configuration management (env vars used correctly? no magic numbers?)
- API response formats (consistent envelope structure?)
- Naming conventions consistent with the existing codebase
- Dependency injection patterns consistent with the project

**Note**: The Standards Agent uses RAG heavily to understand the project's existing patterns before judging new code against them.

**Output**: Findings referencing specific existing project patterns that the new code violates.

---

### 6.8 Architecture Agent

**Role**: Technical architect.  
**System prompt identity**: "You are a principal engineer who evaluates architectural integrity, layer separation, and design consistency."

**What it checks**:
- **Layer violations**: Controller directly calling repository (should go through service)
- **Coupling increases**: New hard dependency between previously independent modules
- **Circular dependencies**: A → B → A
- **Single Responsibility violations**: One class/function doing too many things
- **Abstraction leaks**: Implementation details exposed across boundaries
- **Design pattern violations**: Factory used as Singleton, etc.
- **Dependency direction**: Domain layer importing from infrastructure layer

**Output**: Architecture diagram annotations and findings with references to violated principles.

---

### 6.9 Blast Radius Agent

**Role**: Impact analyst.  
**System prompt identity**: "You are a senior engineer who specializes in understanding how a change propagates through a distributed system."

**What it does**:
- Uses the impact graph from Repository Analyzer
- Identifies all services that import or depend on changed modules
- Identifies all API consumers that may break
- Identifies all database tables touched and who else reads/writes them
- Estimates the "blast radius" if this change has a bug

**Output**:
```
BLAST RADIUS REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Changed: PaymentService.process_payment()

Direct Impact:
  • InvoiceService (calls process_payment)
  • RefundService (calls process_payment)

Indirect Impact:
  • ReportingService (reads payment records written by process_payment)
  • EmailService (triggered after payment completion)

Database Impact:
  • payments table (read by 4 other services)
  • invoices table (updated by this change)

API Impact:
  • POST /api/payments (changed endpoint)
  • GET /api/invoices/{id} (returns payment status)

Risk: HIGH — 4 services affected, 2 database tables, 2 APIs
```

---

### 6.10 Consensus Agent

**Role**: The judge and synthesizer.  
**System prompt identity**: "You are a staff engineer conducting a final review committee. You have received independent findings from 8 specialist engineers. Your job is to produce the definitive, unified review."

**What it does**:

**Round 1 — Deduplication**:
Finds findings from multiple agents that describe the same root issue. Merges them into one finding with all supporting evidence.

**Round 2 — Conflict Resolution**:
If Agent A says "approve" and Agent B says "block" for the same code, applies weighted resolution:
- CRITICAL security from high-confidence agent → always escalates
- Low-severity conflict → majority + confidence wins

**Round 3 — Confidence Filtering**:
Removes findings with confidence < 60%. These are included in the internal report but NOT posted as GitHub PR comments. (Avoid noisy false positives.)

**Round 4 — Risk Scoring**:
```
Security Risk:      Finding severity × confidence × weight(1.5)
Functional Risk:    Finding severity × confidence × weight(1.3)
Performance Risk:   Finding severity × confidence × weight(1.0)
Scalability Risk:   Finding severity × confidence × weight(0.8)
Standards Risk:     Finding severity × confidence × weight(0.6)
────────────────────────────────────────────────
Overall Risk Score: 0–100
```

**Round 5 — Recommendation**:
```
0–20:   APPROVE
21–40:  APPROVE WITH COMMENTS
41–60:  REQUEST CHANGES
61–80:  HIGH RISK — MANUAL REVIEW REQUIRED
81–100: BLOCK
```

**Output**: Master Review Report — the unified final output that drives all downstream actions.

---

### 6.11 Documentation Agent

**Role**: Technical writer.  
**System prompt identity**: "You are a technical writer who produces clear, accurate documentation for software changes."

**What it generates**:

**Product Documentation** (for non-engineers):
- What feature changed and why
- Business value delivered
- User-facing impact (what does the end user see differently?)

**Engineering Documentation** (for engineers):
- What APIs changed (new endpoints, changed request/response schemas)
- What architecture changed
- What database schema changed
- Known limitations

**Operations Documentation** (for DevOps/SRE):
- Deployment steps and considerations
- Environment variables added/changed
- Rollback procedure
- Monitoring alerts to check

**Action**: Creates a new branch on GitHub, commits the documentation, opens a PR for human review.

---

### 6.12 Test Agent

**Role**: QA engineer and test author.  
**System prompt identity**: "You are a senior QA engineer who writes comprehensive, realistic tests that catch real bugs."

**What it generates**:
- **Unit tests**: For each changed function, tests the function in isolation
- **Integration tests**: Tests the full API endpoint including DB interaction
- **Edge case tests**: Derived from acceptance criteria and business rules
- **Regression tests**: Tests that the existing behavior wasn't broken

**Verification Loop** (before PR creation):
```
Generate tests
    ↓
Run tests against the codebase
    ↓
Collect failures
    ↓
Analyze failure reason
    ↓
Fix incorrect test assertions or missing mocks
    ↓
Run again
    ↓
Repeat until 95% pass rate
    ↓
Create GitHub PR
```

Tests are **not blindly trusted** — they must actually pass before being submitted.

---

## 7. Consensus Protocol — How Agents Agree

### The Cross-Agent Discussion Round

After all 8 agents complete their independent reviews, each agent is shown the OTHER agents' findings and can respond:

**Withdrawal Example**:
```
Security Agent finding: "Potential SQL injection on line 47"

Database Agent responds: "The query on line 47 uses SQLAlchemy ORM 
with parameterized inputs. This is not SQL injection. The ORM 
escapes all parameters automatically."

Security Agent: "Database Agent is correct. I misread the ORM 
abstraction as raw SQL. Finding withdrawn. Confidence was only 0.52."
```

**Corroboration Example**:
```
Code Agent finding: "Missing error handling in payment processor"

QA Agent responds: "Corroborated. I also found no test exists for 
the error case, suggesting the author did not consider this path."

Code Agent: "Confidence updated from 0.78 to 0.91 due to corroboration."
```

This is called **"structured argumentation"** — agents arguing with evidence, not opinion.

---

## 8. Human-in-the-Loop — When Humans Intervene

### When HITL Triggers

```
CRITICAL or HIGH severity findings in final consensus → ALWAYS pause for human
Risk score > 60 → Pause for human
Any agent confidence < 60% was the deciding factor → Flag for human
```

### What the Human Sees

A review UI (React frontend) showing:
- Side-by-side: GitHub PR diff | Agent findings
- Per-finding: Severity badge, agent source, confidence score, evidence
- Overall risk score visualization
- Agent-by-agent breakdown

### Human Actions

| Action | Effect |
|---|---|
| **Approve** | Workflow resumes. Comments posted to PR. Doc/Test PRs created. |
| **Reject** | Review cancelled. No comments posted. Engineer notified. |
| **Approve with Override** | Specific findings marked as "acknowledged" — posted on PR but flagged as human-reviewed |
| **Request Re-review** | Specific agents re-run with additional context the human provides |

### How Pause/Resume Works Technically

```
LangGraph graph hits interrupt() node
    ↓
Complete state saved to Redis (like a save-game file)
    ↓
Graph PAUSES — no code running
    ↓
Notification sent to engineer (Slack webhook)
    ↓
Engineer clicks Approve in UI
    ↓
FastAPI receives POST /reviews/{id}/approve
    ↓
LangGraph resumes from exact pause point
    ↓
Human decision injected into ReviewState
    ↓
Workflow continues to output phase
```

The system can be paused for hours or days. State is safe.

---

## 9. RAG Pipeline — How Context is Retrieved

### Why RAG?

A large codebase + PR + Jira ticket + documentation might contain 200,000+ words. That exceeds any LLM context window and would be extremely expensive. RAG solves this by retrieving only the relevant pieces.

### The 5-Step RAG Pipeline

```
INDEXING (done once, at context collection time):
  Raw text (PR, Jira, Docs, Repo files)
      ↓
  Text Splitter — breaks into overlapping chunks (512 tokens, 50 overlap)
      ↓
  Embedder (Gemini embedding-001) — converts each chunk to a vector
      ↓
  pgvector Store — saves (chunk_text, vector, metadata) to PostgreSQL

RETRIEVAL (done when an agent needs information):
  Agent query: "What are the payment validation requirements?"
      ↓
  Query Embedder — converts query to a vector
      ↓
  Similarity Search — finds top 5 most similar chunks in pgvector
      ↓
  Retrieved chunks injected into agent's prompt
      ↓
  Agent reasons over relevant context only
```

### Chunking Strategy

| Content Type | Chunk Size | Overlap | Reason |
|---|---|---|---|
| Source code | 200 tokens | 50 tokens | Code has dense meaning per line |
| Documentation | 512 tokens | 100 tokens | Prose needs more context |
| Jira tickets | Full ticket | — | Usually small enough to fit entirely |
| PR diff | Per-file | — | Each file is its own semantic unit |

---

## 10. Risk Scoring Engine

### Dimensions

| Dimension | Weight | What Contributes |
|---|---|---|
| **Security Risk** | 1.5× | Security Agent findings (highest weight — production impact) |
| **Functional Risk** | 1.3× | Requirements Agent findings (broken features = broken product) |
| **Performance Risk** | 1.0× | Database + Scalability Agent findings |
| **Maintainability Risk** | 0.8× | Code Review + Architecture Agent findings |
| **Standards Risk** | 0.6× | Standards Agent findings |

### Score Calculation

```python
def calculate_risk_score(findings: list[Finding]) -> int:
    total = 0
    for finding in findings:
        severity_score = {"critical": 40, "high": 20, "medium": 8, "low": 2}
        dimension_weight = weights[finding.dimension]
        total += severity_score[finding.severity] * finding.confidence * dimension_weight
    return min(100, int(total))
```

### Risk Levels

| Score | Level | Recommendation | HITL? |
|---|---|---|---|
| 0–20 | Very Low | ✅ APPROVE | No — auto-approve |
| 21–40 | Low | ✅ APPROVE WITH COMMENTS | No — post comments |
| 41–60 | Medium | 🔶 REQUEST CHANGES | Yes — human reviews |
| 61–80 | High | 🔴 MANUAL REVIEW REQUIRED | Yes — human reviews |
| 81–100 | Critical | ⛔ BLOCK | Yes — human must approve to unblock |

---

## 11. Technology Stack — Every Tool Explained

### Core Language: Python 3.12

**What**: General-purpose programming language.  
**Why**: The entire AI/ML ecosystem is Python-first. LangChain, LangGraph, all AI libraries arrive in Python before any other language. Fighting this means maintaining custom ports.  
**Alternative**: JavaScript (LangChain.js exists but smaller ecosystem), Go (almost no AI libraries).

---

### Backend Framework: FastAPI

**What**: Modern async Python web framework.  
**Why**:
- Native async/await (essential for parallel agent calls taking 5-15 seconds each)
- Auto-generates OpenAPI documentation
- Pydantic-native (same models used for HTTP I/O and LLM structured outputs)
- Fastest Python framework (comparable to Node.js for async workloads)

**Endpoints AERP exposes**:
```
POST /reviews/start          → Submit a new review request
GET  /reviews/{id}/status    → Check review progress
GET  /reviews/{id}/report    → Get final report
POST /reviews/{id}/approve   → Human approval (resumes HITL)
POST /reviews/{id}/reject    → Human rejection
GET  /health                 → Docker health check
```

---

### Agent Orchestration: LangGraph

**What**: Graph-based workflow orchestration framework for AI agents (built on LangChain).  
**Why**: Enables non-linear agent workflows — parallel execution, conditional branching, loops, and pause/resume. The only framework that natively supports stateful, interruptible multi-agent systems.  
**Core concepts used**:
- `StateGraph` — the graph container
- `TypedDict State` — shared working memory (ReviewState)
- `add_node()` — register agent functions
- `add_edge()` — define execution order
- `add_conditional_edges()` — branching based on state
- `interrupt()` — pause for human input
- `MemorySaver` / `RedisSaver` — state persistence (checkpointing)

---

### LLM Framework: LangChain

**What**: Framework providing abstractions for LLM interactions.  
**Why**: Standardizes LLM provider access (swap Gemini → Claude with 1 config line), provides prompt templates, structured output parsers, document loaders, text splitters, and vector store integrations.  
**Components used**:
- `ChatGoogleGenerativeAI` — Gemini LLM wrapper
- `ChatPromptTemplate` — structured, reusable prompts
- `PydanticOutputParser` — force LLM to output Pydantic models
- `RecursiveCharacterTextSplitter` — chunk documents for RAG
- `GoogleGenerativeAIEmbeddings` — text → vectors
- `PGVector` — LangChain's pgvector integration

---

### Primary LLM: Google Gemini 2.0 Flash

**What**: Google's production LLM, optimized for speed and cost.  
**Why for AERP**:
- 1 million token context window (can fit an entire codebase)
- ~$0.02 per full AERP review (vs $0.90 for Claude Sonnet)
- Fast response times (lower latency = faster reviews)
- Excellent code understanding capabilities
- Free tier via Google AI Studio for development

**Model assignments**:
```
Gemini 2.0 Flash:
  • All 8 specialist agents (speed + cost)
  • Consensus Agent (cost at scale)
  • Documentation Agent

Gemini 1.5 Pro (optional, for complex reviews):
  • Architecture Agent (needs deeper reasoning)
  • Blast Radius Agent (complex dependency tracing)
```

---

### Database: PostgreSQL 16

**What**: Open-source relational database.  
**Why**:
- Industry standard — every company uses it
- Supports pgvector extension (no separate vector database service)
- ACID compliance (critical for audit trail integrity)
- JSON columns for flexible agent output storage

**Tables in AERP**:
```sql
reviews          — Review sessions (id, status, risk_score, created_at)
agent_findings   — Per-agent raw findings (agent, severity, confidence)
consensus_report — Final merged report per review
embeddings       — Document chunks with vector embeddings (pgvector)
human_decisions  — Audit trail of human approve/reject actions
```

---

### Vector Database: pgvector (PostgreSQL Extension)

**What**: PostgreSQL extension adding `vector` data type and similarity search.  
**Why**: No separate vector database service to manage. pgvector is inside PostgreSQL — same connection, same backups, same authentication. Good performance for this project's scale.  
**SQL it enables**:
```sql
-- Find top 5 most relevant chunks for a query
SELECT content, metadata
FROM embeddings
ORDER BY embedding <-> $1::vector  -- cosine distance
LIMIT 5;
```
**When to upgrade**: At ~5M+ vectors with sub-50ms latency requirements, consider Pinecone or Qdrant.

---

### Cache + Message Broker: Redis

**Dual role in AERP**:

**Role 1 — Celery Message Broker**:
Stores task queue entries. When FastAPI accepts a review request, it puts a Celery task in Redis. A Celery worker picks it up and runs the LangGraph workflow.

**Role 2 — LangGraph Checkpointer**:
Stores the complete LangGraph state when the workflow pauses for human review. Think of it as a save-game file — the workflow can be restored to the exact pause point.

**Why Redis for both**: Speed (in-memory), TTL support, and Celery's built-in Redis integration.

---

### Task Queue: Celery

**What**: Distributed task queue for Python.  
**Why**: A full AERP review takes 5-10 minutes. HTTP requests cannot wait that long (timeout). Celery allows:
- Immediate response: `{ "review_id": "abc123", "status": "queued" }`
- Background execution: LangGraph workflow runs on a worker
- Durability: Tasks survive server restarts (stored in Redis)
- Retry: Automatic retry on LLM API errors or rate limits
- Scaling: Run more workers = more parallel reviews

**Worker configuration**:
```
API Server (FastAPI) → enqueues tasks
Celery Worker → runs LangGraph workflows
Redis → stores the queue between them
```

---

### External Integrations: MCPs (Model Context Protocol)

**What is MCP**: An open standard for AI agents to communicate with external tools. Like USB-C — standardized connector, any tool can plug in.

**GitHub MCP** (`github/github-mcp-server` — Official):
```
Provides tools:
  get_pull_request(owner, repo, pr_number) → PR content, diff, files
  get_file_content(owner, repo, path) → Full file content
  create_pull_request(owner, repo, ...) → Create Doc/Test PRs
  create_review_comment(owner, repo, pr, ...) → Post PR comments
  list_commits(owner, repo, branch) → Commit history
```

**Jira MCP** (`atlassian-labs/mcp-atlassian` — Official):
```
Provides tools:
  get_issue(issue_key) → Ticket content, acceptance criteria
  search_issues(jql_query) → Find related tickets
  get_issue_comments(issue_key) → Discussion context
```

**Google Docs MCP** (Community stable):
```
Provides tools:
  get_document(document_id) → Full document content
  list_documents(folder_id) → Find related docs
```

---

### Containerization: Docker + Docker Compose

**What**: Docker packages the application and its dependencies into portable containers.  
**Why**: "Works on my machine" problem eliminated. One command starts all services.

**Services in docker-compose.yml**:
```yaml
services:
  api:          # FastAPI application
  worker:       # Celery worker (runs LangGraph)
  postgres:     # PostgreSQL + pgvector
  redis:        # Cache + message broker
  frontend:     # React UI (development)
```

---

### Frontend: React

**What**: JavaScript library for building user interfaces.  
**Why**: Widely known, component-based, sufficient for our review dashboard.  
**Pages**:
- `/` — Dashboard: list of all reviews with status
- `/reviews/new` — Submit new review (PR URL + Jira URL + Doc URL)
- `/reviews/{id}` — Review detail: per-agent findings, risk score
- `/reviews/{id}/approve` — Human approval interface (diff + findings side-by-side)

---

### Testing: Pytest

**What**: Python testing framework.  
**What we test**:
```
Unit tests:        Individual agent logic with mocked LLM responses
Integration tests: Full workflow end-to-end with test PRs
Evaluation tests:  Golden dataset — known PRs with known correct answers
```

---

## 12. Build Phases — MVP to Production

### Phase 1 — Architecture & Design ✅ COMPLETE
Teaching document. No code. Understanding every concept and decision before writing a line.

### Phase 2 — Project Foundation + Context Collection
**Goal**: Submit PR URL → system fetches everything and builds ReviewState.

What gets built:
- `docker-compose.yml` (all services running)
- FastAPI project skeleton
- GitHub MCP + Jira MCP + Google Docs MCP integration
- RAG pipeline (chunk → embed → pgvector)
- `ReviewState` TypedDict definition
- `context_collector_node` (first LangGraph node)
- `repository_analyzer_node`

✅ Deliverable: A system that can take a PR URL and produce a rich, structured context object.

---

### Phase 3 — First Agent (Code Review Agent)
**Goal**: Build one complete agent end-to-end. Understand the full agent lifecycle.

What gets built:
- `base_agent.py` (abstract class all agents inherit)
- Prompt engineering for code review
- Structured output (`CodeFindings` Pydantic model)
- `repo_search_tool` (RAG tool for codebase search)
- Wire into LangGraph as a single node
- Celery task wrapping the workflow

✅ Deliverable: PR → Code Review findings (structured, reliable JSON output)

---

### Phase 4 — All Parallel Agents
**Goal**: All 8 specialist agents running simultaneously.

What gets built:
- Security Agent
- Database Agent
- Requirements Agent
- Scalability Agent
- Standards Agent
- Architecture Agent
- Blast Radius Agent
- LangGraph parallel fan-out and fan-in pattern

✅ Deliverable: 8 agents run simultaneously, all findings in ReviewState

---

### Phase 5 — Consensus Agent + Risk Scoring
**Goal**: Turn 8 separate findings into one unified recommendation.

What gets built:
- Cross-agent critique round
- Consensus algorithm (deduplication, conflict resolution, confidence filtering)
- Risk scoring engine (0–100)
- Approval recommendation engine
- Conditional routing (CRITICAL → HITL, LOW → auto-approve)

✅ Deliverable: Unified recommendation with risk score

---

### Phase 6 — GitHub PR Comments + Human-in-the-Loop
**Goal**: System posts comments on the actual PR. Workflow pauses for human.

What gets built:
- GitHub MCP PR comment posting
- LangGraph `interrupt()` node
- Redis checkpointing (save/restore state)
- `POST /reviews/{id}/approve` endpoint (resumes workflow)
- Slack notification webhook

✅ Deliverable: Comments appear on real GitHub PRs. Workflow pauses and resumes.

---

### Phase 7 — Documentation + Test Agents
**Goal**: System auto-creates Doc PR and Test PR after approval.

What gets built:
- Documentation Agent (3 doc types)
- Test Agent with verification loop (generate → run → fix → re-run → PR)
- GitHub PR creation via GitHub MCP

✅ Deliverable: After approval, 2 auto-generated GitHub PRs are created

---

### Phase 8 — React Frontend
**Goal**: A real UI to submit reviews and approve them.

What gets built:
- Review submission form
- Live status tracking (polling)
- Per-agent findings viewer
- Human approval interface (diff + findings side-by-side)

✅ Deliverable: Fully demoable product with a real UI

---

### Phase 9 — Real-World Testing (Golden Dataset)
**Goal**: Validate the system against real PRs with known correct answers.

What gets built:
- Test GitHub repo with 6 pre-designed PRs
- Test Jira tickets linked to each PR
- Test Google Docs with feature specs
- Evaluation script (precision, recall, false positive rate)

✅ Deliverable: System validated. We know it actually works correctly.

---

### Phase 10 — Production Hardening
**Goal**: Portfolio-ready, production-quality codebase.

What gets built:
- Rate limiting and cost budgets
- Input sanitization (prompt injection prevention)
- Full Pytest suite
- Complete README with architecture diagram
- Demo video preparation

✅ Deliverable: Portfolio-ready project

---

## 13. Future Capabilities (Post-MVP)

### Phase A — Runtime Validation
- Launch the application in a Docker sandbox
- Monitor startup logs, exceptions, memory
- Detect runtime errors the static agents missed
- Log Analysis Agent: parse backend + browser console logs

### Phase B — Visual Validation
- Screenshot comparison (before vs after)
- Playwright browser automation (execute user flows end-to-end)
- UI regression detection

### Phase C — Multi-Platform Support
- Azure DevOps PR support
- GitLab Merge Request support
- ASP.NET Core, Spring Boot, Django project detection
- Framework-specific review rules

### Phase D — Learning & Autonomy
- Historical pattern learning (learn from past approved reviews)
- Team-specific standards adaptation
- Auto-fix suggestions (generate corrected code)
- Autonomous approval for very low risk changes (risk score < 10)
- Production incident correlation (does this change resemble a past incident?)

---

*Document Version: 1.0 | Status: Feature Specification Complete | Ready for Phase 2*
