"""
backend/graph/nodes.py

LangGraph node functions for Phase 2, 3, and 4.

WHAT IS A NODE?
  A node is a regular Python function that:
  1. Receives the current ReviewState
  2. Does work (API calls, LLM calls, computation)
  3. Returns a PARTIAL state update (only the keys it changed)

  LangGraph calls your node, merges its return value into state,
  then moves to the next node.

PHASE 2 NODES:
  - context_collector_node: Fetches PR, Jira, Docs → builds ReviewState
  - repository_analyzer_node: Analyzes changed files → builds impact graph

PHASE 3 NODES:
  - code_review_node: Runs the CodeReviewAgent on the PR diff

PHASE 4 NODES (NEW — PARALLEL EXECUTION):
  - security_node, database_node, requirements_node
  - scalability_node, standards_node, architecture_node, blast_radius_node
  - All 8 agents are fanned out simultaneously via LangGraph Send()

PHASE 5+ NODES (not yet):
  - consensus_node
  - hitl_node
"""

import uuid
from datetime import datetime, timezone
from typing import Any

from backend.graph.state import ReviewState, PRMetadata, JiraTicket
from backend.tools.github_tool import fetch_pr_data
from backend.tools.jira_tool import fetch_jira_ticket
from backend.rag.chunker import chunk_pr_diff, chunk_document
from backend.rag.indexer import index_chunks
from backend.config.settings import get_settings

# Phase 3 — Code Review Agent
from backend.agents.code_review_agent import code_review_agent
from backend.prompts.code_review import build_human_message as build_code_review_msg

# Phase 4 — All parallel agents
from backend.agents.security_agent import security_agent
from backend.agents.database_agent import database_agent
from backend.agents.requirements_agent import requirements_agent
from backend.agents.scalability_agent import scalability_agent
from backend.agents.standards_agent import standards_agent
from backend.agents.architecture_agent import architecture_agent
from backend.agents.blast_radius_agent import blast_radius_agent
from backend.prompts.security import build_human_message as build_security_msg
from backend.prompts.database import build_human_message as build_database_msg
from backend.prompts.requirements import build_human_message as build_requirements_msg
from backend.prompts.scalability import build_human_message as build_scalability_msg
from backend.prompts.standards import build_human_message as build_standards_msg
from backend.prompts.architecture import build_human_message as build_architecture_msg
from backend.prompts.blast_radius import build_human_message as build_blast_radius_msg

import structlog

logger = structlog.get_logger()
settings = get_settings()


# ─────────────────────────────────────────────────────────────────────────────
# NODE 1: Context Collector
# ─────────────────────────────────────────────────────────────────────────────

async def context_collector_node(state: ReviewState) -> dict:
    """
    Fetches all external context needed for the review.

    INPUTS (reads from state):
      - pr_url
      - jira_url (optional)
      - doc_url (optional)
      - review_id

    OUTPUTS (writes to state):
      - pr_metadata
      - jira_ticket
      - doc_content
      - raw_context

    ALSO DOES:
      - Chunks all content
      - Embeds chunks using Gemini
      - Stores in pgvector for RAG retrieval by agents

    ERROR HANDLING STRATEGY:
      If GitHub fails → we cannot continue (PR is mandatory) → re-raise
      If Jira fails → log warning, continue without it (optional)
      If Google Docs fails → log warning, continue without it (optional)
    """
    review_id = state["review_id"]
    logger.info("Starting context collection", review_id=review_id)

    result = {
        "started_at": datetime.now(timezone.utc).isoformat(),
    }

    # ── Step 1: Fetch GitHub PR (MANDATORY) ───────────────────────────────────
    try:
        logger.info("Fetching GitHub PR", url=state["pr_url"])
        pr_data = await fetch_pr_data(state["pr_url"])
        result["pr_metadata"] = pr_data
        logger.info(
            "GitHub PR fetched",
            title=pr_data["title"],
            changed_files=len(pr_data["changed_files"]),
        )
    except Exception as e:
        logger.error("Failed to fetch GitHub PR", error=str(e))
        # This is fatal — we need the PR to do a review
        return {"error": f"Cannot fetch GitHub PR: {str(e)}"}

    # ── Step 2: Fetch Jira Ticket (OPTIONAL) ──────────────────────────────────
    jira_ticket = None
    if state.get("jira_url"):
        try:
            logger.info("Fetching Jira ticket", url=state["jira_url"])
            jira_data = await fetch_jira_ticket(state["jira_url"])
            jira_ticket = jira_data
            result["jira_ticket"] = jira_ticket
            logger.info("Jira ticket fetched", ticket=jira_data["ticket_id"])
        except Exception as e:
            logger.warning("Failed to fetch Jira ticket", error=str(e))
            # Non-fatal — continue without Jira context

    # ── Step 3: Fetch Google Doc (OPTIONAL) ───────────────────────────────────
    doc_content = None
    if state.get("doc_url"):
        try:
            logger.info("Fetching Google Doc", url=state["doc_url"])
            doc_content = await _fetch_google_doc(state["doc_url"])
            result["doc_content"] = doc_content
            logger.info("Google Doc fetched", chars=len(doc_content))
        except Exception as e:
            logger.warning("Failed to fetch Google Doc", error=str(e))
            # Non-fatal — continue without doc context

    # ── Step 4: Build raw_context string ──────────────────────────────────────
    raw_context_parts = [
        f"=== PULL REQUEST: {pr_data['title']} ===",
        f"Author: {pr_data['author']} | Branch: {pr_data['branch']}",
        f"Changed files: {', '.join(pr_data['changed_files'][:10])}",
        f"\nDescription:\n{pr_data['description']}",
    ]

    if jira_ticket:
        raw_context_parts.extend([
            f"\n=== JIRA TICKET: {jira_ticket['ticket_id']} ===",
            f"{jira_ticket['title']}",
            f"\nAcceptance Criteria:",
            *[f"  - {ac}" for ac in jira_ticket["acceptance_criteria"]],
        ])

    if doc_content:
        raw_context_parts.extend([
            "\n=== FEATURE DOCUMENTATION ===",
            doc_content[:3000],
        ])

    result["raw_context"] = "\n".join(raw_context_parts)

    # ── Step 5: Chunk + Embed + Index for RAG ─────────────────────────────────
    all_chunks = []

    if pr_data.get("diff"):
        pr_chunks = chunk_pr_diff(pr_data["diff"], pr_data)
        all_chunks.extend(pr_chunks)
        logger.info("PR chunked", num_chunks=len(pr_chunks))

    if jira_ticket:
        jira_text = _jira_to_text(jira_ticket)
        jira_chunks = chunk_document(
            content=jira_text,
            source="jira",
            metadata={"ticket_id": jira_ticket["ticket_id"]},
        )
        all_chunks.extend(jira_chunks)
        logger.info("Jira chunked", num_chunks=len(jira_chunks))

    if doc_content:
        doc_chunks = chunk_document(
            content=doc_content,
            source="google_doc",
            metadata={"url": state.get("doc_url", "")},
        )
        all_chunks.extend(doc_chunks)
        logger.info("Doc chunked", num_chunks=len(doc_chunks))

    if all_chunks:
        total_indexed = await index_chunks(all_chunks, review_id)
        logger.info("RAG indexing complete", total_chunks=total_indexed)

    logger.info("Context collection complete", review_id=review_id)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# NODE 2: Repository Analyzer
# ─────────────────────────────────────────────────────────────────────────────

async def repository_analyzer_node(state: ReviewState) -> dict:
    """
    Analyzes changed files to build an impact graph.
    """
    pr_metadata = state.get("pr_metadata")
    if not pr_metadata:
        return {"error": "Cannot analyze repository: no PR metadata"}

    changed_files = pr_metadata.get("changed_files", [])
    logger.info("Analyzing repository", num_files=len(changed_files))

    files_analysis = {}
    for filepath in changed_files:
        files_analysis[filepath] = {
            "type": _classify_file_type(filepath),
            "layer": _detect_layer(filepath),
            "is_test": _is_test_file(filepath),
            "is_migration": _is_migration(filepath),
            "is_config": _is_config_file(filepath),
        }

    detected_framework = _detect_framework(changed_files)

    impact_graph = {
        "changed_layers": list({f["layer"] for f in files_analysis.values() if f["layer"]}),
        "has_migrations": any(f["is_migration"] for f in files_analysis.values()),
        "has_config_changes": any(f["is_config"] for f in files_analysis.values()),
        "test_files_changed": [fp for fp, f in files_analysis.items() if f["is_test"]],
        "non_test_files": [fp for fp, f in files_analysis.items() if not f["is_test"]],
        "framework": detected_framework,
    }

    logger.info(
        "Repository analysis complete",
        framework=detected_framework,
        layers_changed=impact_graph["changed_layers"],
        has_migrations=impact_graph["has_migrations"],
    )

    return {
        "changed_files_analysis": files_analysis,
        "impact_graph": impact_graph,
        "detected_framework": detected_framework,
    }


# ─────────────────────────────────────────────────────────────────────────────
# PHASE 3 NODE: Code Review Agent
# ─────────────────────────────────────────────────────────────────────────────

async def code_review_node(state: ReviewState) -> dict:
    """Runs the Code Review Agent on the PR diff."""
    pr_metadata = state.get("pr_metadata")
    if not pr_metadata:
        return _empty_agent_result("code_review_agent", "code_review_result")

    raw_context = state.get("raw_context", "")
    human_message = build_code_review_msg(raw_context, pr_metadata)
    logger.info("Running Code Review Agent", review_id=state["review_id"])
    return await code_review_agent.run(state=state, human_message=human_message)


# ─────────────────────────────────────────────────────────────────────────────
# PHASE 4 NODES: All parallel specialist agents
# ─────────────────────────────────────────────────────────────────────────────

async def security_node(state: ReviewState) -> dict:
    """Runs the Security Agent — OWASP Top 10 and vulnerability detection."""
    pr_metadata = state.get("pr_metadata")
    if not pr_metadata:
        return _empty_agent_result("security_agent", "security_result")
    human_message = build_security_msg(state.get("raw_context", ""), pr_metadata)
    logger.info("Running Security Agent", review_id=state["review_id"])
    return await security_agent.run(state=state, human_message=human_message)


async def database_node(state: ReviewState) -> dict:
    """Runs the Database Agent — N+1, migrations, query safety."""
    pr_metadata = state.get("pr_metadata")
    if not pr_metadata:
        return _empty_agent_result("database_agent", "database_result")
    human_message = build_database_msg(state.get("raw_context", ""), pr_metadata)
    logger.info("Running Database Agent", review_id=state["review_id"])
    return await database_agent.run(state=state, human_message=human_message)


async def requirements_node(state: ReviewState) -> dict:
    """Runs the Requirements Agent — Jira acceptance criteria compliance."""
    pr_metadata = state.get("pr_metadata")
    if not pr_metadata:
        return _empty_agent_result("requirements_agent", "requirements_result")
    human_message = build_requirements_msg(state.get("raw_context", ""), pr_metadata)
    logger.info("Running Requirements Agent", review_id=state["review_id"])
    return await requirements_agent.run(state=state, human_message=human_message)


async def scalability_node(state: ReviewState) -> dict:
    """Runs the Scalability Agent — performance under load."""
    pr_metadata = state.get("pr_metadata")
    if not pr_metadata:
        return _empty_agent_result("scalability_agent", "scalability_result")
    human_message = build_scalability_msg(state.get("raw_context", ""), pr_metadata)
    logger.info("Running Scalability Agent", review_id=state["review_id"])
    return await scalability_agent.run(state=state, human_message=human_message)


async def standards_node(state: ReviewState) -> dict:
    """Runs the Standards Agent — logging, error handling, maintainability."""
    pr_metadata = state.get("pr_metadata")
    if not pr_metadata:
        return _empty_agent_result("standards_agent", "standards_result")
    human_message = build_standards_msg(state.get("raw_context", ""), pr_metadata)
    logger.info("Running Standards Agent", review_id=state["review_id"])
    return await standards_agent.run(state=state, human_message=human_message)


async def architecture_node(state: ReviewState) -> dict:
    """Runs the Architecture Agent — SOLID, coupling, design patterns."""
    pr_metadata = state.get("pr_metadata")
    if not pr_metadata:
        return _empty_agent_result("architecture_agent", "architecture_result")
    human_message = build_architecture_msg(state.get("raw_context", ""), pr_metadata)
    logger.info("Running Architecture Agent", review_id=state["review_id"])
    return await architecture_agent.run(state=state, human_message=human_message)


async def blast_radius_node(state: ReviewState) -> dict:
    """Runs the Blast Radius Agent — downstream failure impact analysis."""
    pr_metadata = state.get("pr_metadata")
    if not pr_metadata:
        return _empty_agent_result("blast_radius_agent", "blast_radius_result")
    human_message = build_blast_radius_msg(state.get("raw_context", ""), pr_metadata)
    logger.info("Running Blast Radius Agent", review_id=state["review_id"])
    return await blast_radius_agent.run(state=state, human_message=human_message)


# ─────────────────────────────────────────────────────────────────────────────
# Helper: Empty agent result (used when PR metadata is missing)
# ─────────────────────────────────────────────────────────────────────────────

def _empty_agent_result(agent_name: str, result_key: str) -> dict:
    """Returns an empty result dict when an agent cannot run."""
    return {
        result_key: {
            "agent": agent_name,
            "findings": [],
            "overall_assessment": "Skipped: no PR metadata available",
            "recommendation": "approve_with_comments",
            "confidence": 0.0,
            "tokens_used": None,
        },
        "agent_findings": [],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Helper functions
# ─────────────────────────────────────────────────────────────────────────────

def _classify_file_type(filepath: str) -> str:
    """Classify file by extension."""
    ext = filepath.split(".")[-1].lower() if "." in filepath else ""
    type_map = {
        "py": "python", "ts": "typescript", "tsx": "typescript",
        "js": "javascript", "jsx": "javascript", "java": "java",
        "cs": "csharp", "go": "go", "sql": "sql", "json": "config",
        "yaml": "config", "yml": "config", "env": "config",
        "md": "docs", "txt": "docs", "html": "template", "css": "style",
    }
    return type_map.get(ext, "unknown")


def _detect_layer(filepath: str) -> str | None:
    """Detect architectural layer from file path."""
    path = filepath.lower()
    if any(x in path for x in ["/routes/", "/controllers/", "/api/"]):
        return "presentation"
    if any(x in path for x in ["/services/", "/use_cases/", "/domain/"]):
        return "business_logic"
    if any(x in path for x in ["/models/", "/schemas/", "/entities/"]):
        return "domain_model"
    if any(x in path for x in ["/repositories/", "/db/", "/database/", "/migrations/"]):
        return "data_access"
    if any(x in path for x in ["/utils/", "/helpers/", "/common/"]):
        return "utility"
    return None


def _is_test_file(filepath: str) -> bool:
    return "test" in filepath.lower() or "spec" in filepath.lower()


def _is_migration(filepath: str) -> bool:
    return "migration" in filepath.lower() or "migrate" in filepath.lower()


def _is_config_file(filepath: str) -> bool:
    return filepath.endswith((".yml", ".yaml", ".json", ".env", ".toml", ".cfg"))


def _detect_framework(changed_files: list[str]) -> str:
    """Detect the primary framework from file patterns."""
    all_paths = " ".join(changed_files).lower()
    if "fastapi" in all_paths or "uvicorn" in all_paths:
        return "fastapi"
    if "django" in all_paths or "settings.py" in all_paths:
        return "django"
    if "spring" in all_paths or ".java" in all_paths:
        return "spring_boot"
    if "aspnet" in all_paths or ".cs" in all_paths:
        return "aspnet_core"
    if any(f.endswith(".py") for f in changed_files):
        return "python"
    return "unknown"


def _jira_to_text(ticket: dict) -> str:
    """Converts a JiraTicket dict to a flat text string for chunking."""
    return f"""
JIRA TICKET: {ticket['ticket_id']}
Title: {ticket['title']}
Status: {ticket['status']}
Priority: {ticket['priority']}

Description:
{ticket['description']}

Acceptance Criteria:
{chr(10).join(f"- {ac}" for ac in ticket['acceptance_criteria'])}

Business Rules:
{chr(10).join(f"- {br}" for br in ticket.get('business_rules', []))}
""".strip()


async def _fetch_google_doc(doc_url: str) -> str:
    """
    Fetches content from a Google Doc.
    NOTE: Requires Google Service Account credentials.
    """
    import re
    match = re.search(r"/document/d/([a-zA-Z0-9_-]+)", doc_url)
    if not match:
        return "Could not extract Google Doc ID from URL"

    doc_id = match.group(1)

    try:
        from googleapiclient.discovery import build
        from google.oauth2 import service_account

        credentials = service_account.Credentials.from_service_account_file(
            settings.google_service_account_file,
            scopes=["https://www.googleapis.com/auth/documents.readonly"],
        )
        service = build("docs", "v1", credentials=credentials)
        doc = service.documents().get(documentId=doc_id).execute()

        content_parts = []
        for element in doc.get("body", {}).get("content", []):
            if "paragraph" in element:
                for para_elem in element["paragraph"].get("elements", []):
                    if "textRun" in para_elem:
                        content_parts.append(para_elem["textRun"].get("content", ""))

        return "".join(content_parts)

    except Exception as e:
        logger.warning("Google Docs fetch failed", error=str(e))
        return f"Google Doc content unavailable: {str(e)}"
