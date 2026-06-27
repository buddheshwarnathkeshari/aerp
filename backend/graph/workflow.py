"""
backend/graph/workflow.py

Assembles the LangGraph StateGraph — the complete workflow.

PHASE 3 GRAPH (context collection + code review agent):

  START
    │
    ▼
  [context_collector_node]   ← Fetch PR + Jira + Docs + RAG index
    │
    ▼
  [repository_analyzer_node] ← Analyze changed files, detect framework
    │
    ▼
  [code_review_node]         ← AI code review (Gemini structured output)
    │
    ▼
  END

PHASE 4 UPGRADE (parallel agents — only workflow.py changes):
  After repo_analyzer, we will fan out to 8 agents simultaneously
  using LangGraph's Send() API, then fan in to consensus.

LANGGRAPH KEY CONCEPTS USED HERE:
  StateGraph   → The graph container (holds nodes + edges + state type)
  add_node     → Register a function as a node
  add_edge     → Connect nodes (always-run edge)
  START        → Special node: the entry point
  END          → Special node: the exit point
  compile()    → Validates the graph and returns a runnable

WHY compile()?
  compile() checks for issues:
  - Unreachable nodes
  - Missing edges
  - Invalid state references
  It's like a type-check for your graph.
"""

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.redis import RedisSaver
from backend.graph.state import ReviewState
from backend.graph.nodes import (
    context_collector_node,
    repository_analyzer_node,
    code_review_node,
)
from backend.config.settings import get_settings

settings = get_settings()


def create_workflow(checkpointer=None):
    """
    Builds and compiles the AERP LangGraph workflow.

    Args:
        checkpointer: Optional checkpointer for state persistence.
                      Required for HITL (pause/resume).
                      In Phase 3, we pass None (no HITL yet).

    Returns:
        A compiled LangGraph graph ready to run.

    DESIGN: Why a factory function instead of module-level graph?
      Creating the graph at module level means it's created at import time.
      If the checkpointer connection fails at startup, the import fails.
      A factory function creates the graph on demand, after all services
      are confirmed healthy.
    """
    # Create the graph with ReviewState as shared state type
    builder = StateGraph(ReviewState)

    # ── Register nodes ────────────────────────────────────────────────────────
    # node name → function that implements the node
    builder.add_node("context_collector", context_collector_node)
    builder.add_node("repository_analyzer", repository_analyzer_node)
    builder.add_node("code_review", code_review_node)   # ← NEW in Phase 3

    # ── Define edges (execution order) ────────────────────────────────────────
    # START is a special LangGraph constant representing the entry point
    builder.add_edge(START, "context_collector")
    builder.add_edge("context_collector", "repository_analyzer")
    builder.add_edge("repository_analyzer", "code_review")   # ← NEW in Phase 3
    builder.add_edge("code_review", END)                      # ← NEW in Phase 3

    # ── Compile ───────────────────────────────────────────────────────────────
    # checkpointer=None in Phase 3
    # checkpointer=RedisSaver in Phase 6 (enables HITL pause/resume)
    graph = builder.compile(checkpointer=checkpointer)

    return graph


def get_redis_checkpointer():
    """
    Creates a Redis-backed checkpointer for HITL state persistence.
    Used in Phase 6 when we add human-in-the-loop.

    NOT USED IN PHASE 3 — here for reference.
    """
    return RedisSaver.from_conn_string(settings.redis_url)


# Module-level compiled graph (no HITL yet)
# Agents and Celery worker import this directly
workflow = create_workflow(checkpointer=None)
