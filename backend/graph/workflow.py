"""
backend/graph/workflow.py

Assembles the LangGraph StateGraph — the complete Phase 4 workflow.

PHASE 4 GRAPH (parallel agents):

  START
    │
    ▼
  [context_collector_node]   ← Fetch PR + Jira + Docs + RAG index
    │
    ▼
  [repository_analyzer_node] ← Analyze changed files, detect framework
    │
    ▼ fan-out via conditional_edges + Send()
    ├──► [code_review_node]     ┐
    ├──► [security_node]        │
    ├──► [database_node]        │ All 8 agents run SIMULTANEOUSLY
    ├──► [requirements_node]    │ Total time = slowest single agent
    ├──► [scalability_node]     │ NOT sum of all agents (~8x speedup)
    ├──► [standards_node]       │
    ├──► [architecture_node]    │
    └──► [blast_radius_node]    ┘
              │ (all 8 write to agent_findings via Annotated[list, add] reducer)
              ▼ fan-in to collector
    [collector_node]           ← Waits for all agents, merges findings
              │
              ▼
           END

HOW PARALLEL EXECUTION WORKS IN LANGGRAPH:
  The key is the Annotated[list, add] reducer in ReviewState.

  Each agent node returns: {"agent_findings": [their findings...]}
  LangGraph sees 8 concurrent writes to "agent_findings".
  Instead of overwriting, the "add" reducer APPENDS all lists together.
  When all 8 agents finish, agent_findings contains ALL findings.

  This is "fan-out + reducer fan-in" pattern:
    fan-out:  repo_analyzer → [8 simultaneous agent nodes]
    reducer:  each agent appends to agent_findings
    fan-in:   collector_node reads the merged agent_findings

INTERVIEW: "How do you run LangGraph nodes in parallel?"
  "LangGraph supports parallel execution by adding multiple edges from
  one node to multiple destination nodes. When a node has parallel
  outgoing edges, LangGraph runs all destinations concurrently.
  For state merging, we use Annotated[list, add] reducers — this tells
  LangGraph to APPEND list writes from concurrent nodes instead of
  overwriting. The result is that all 8 agents run simultaneously,
  each appending their findings to the shared list."
"""

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.redis import RedisSaver
from backend.graph.state import ReviewState
from backend.graph.nodes import (
    # Phase 2
    context_collector_node,
    repository_analyzer_node,
    # Phase 3 + 4 agents
    code_review_node,
    security_node,
    database_node,
    requirements_node,
    scalability_node,
    standards_node,
    architecture_node,
    blast_radius_node,
)
from backend.config.settings import get_settings

settings = get_settings()

# All 8 agent node names — used for fan-out edges
AGENT_NODES = [
    "code_review",
    "security",
    "database",
    "requirements",
    "scalability",
    "standards",
    "architecture",
    "blast_radius",
]


async def collector_node(state: ReviewState) -> dict:
    """
    Fan-in node that runs after all parallel agents complete.

    WHY IS THIS NEEDED?
      After fanning out to 8 agents, we need a single "join" point
      where all findings are consolidated before the workflow ends.
      This node is where Phase 5 (Consensus Agent) will be plugged in.

    For Phase 4, it just logs a summary and returns nothing new
    (the agent_findings reducer has already merged everything).
    """
    from backend.config.settings import get_settings
    import structlog
    logger = structlog.get_logger()

    all_findings = state.get("agent_findings", [])
    logger.info(
        "All agents complete — findings collected",
        review_id=state["review_id"],
        total_findings=len(all_findings),
        agents_run=len([
            k for k in [
                state.get("code_review_result"),
                state.get("security_result"),
                state.get("database_result"),
                state.get("requirements_result"),
                state.get("scalability_result"),
                state.get("standards_result"),
                state.get("architecture_result"),
                state.get("blast_radius_result"),
            ] if k is not None
        ])
    )
    # Phase 5: Consensus Agent will run here
    # For now, just return empty (findings are already in state via reducer)
    return {}


def create_workflow(checkpointer=None):
    """
    Builds and compiles the AERP LangGraph workflow.

    Phase 4: parallel fan-out to 8 agents, then collector fan-in.

    Args:
        checkpointer: Optional checkpointer for state persistence.
                      Required for HITL (pause/resume).
                      In Phase 4, we pass None (no HITL yet).

    Returns:
        A compiled LangGraph graph ready to run.
    """
    builder = StateGraph(ReviewState)

    # ── Register nodes ────────────────────────────────────────────────────────
    builder.add_node("context_collector", context_collector_node)
    builder.add_node("repository_analyzer", repository_analyzer_node)

    # Phase 3 + 4 agent nodes
    builder.add_node("code_review", code_review_node)
    builder.add_node("security", security_node)
    builder.add_node("database", database_node)
    builder.add_node("requirements", requirements_node)
    builder.add_node("scalability", scalability_node)
    builder.add_node("standards", standards_node)
    builder.add_node("architecture", architecture_node)
    builder.add_node("blast_radius", blast_radius_node)

    # Collector (fan-in)
    builder.add_node("collector", collector_node)

    # ── Define edges ──────────────────────────────────────────────────────────
    # Phase 1 → 2 (sequential)
    builder.add_edge(START, "context_collector")
    builder.add_edge("context_collector", "repository_analyzer")

    # Phase 4: FAN-OUT — repository_analyzer → all 8 agents simultaneously
    # Adding parallel edges from one source node to multiple targets
    # causes LangGraph to execute them concurrently (asyncio gather)
    for agent_node in AGENT_NODES:
        builder.add_edge("repository_analyzer", agent_node)

    # Phase 4: FAN-IN — all 8 agents → collector
    # Each agent's findings are merged via the Annotated[list, add] reducer
    # collector_node runs only after ALL 8 agents have finished
    for agent_node in AGENT_NODES:
        builder.add_edge(agent_node, "collector")

    builder.add_edge("collector", END)

    # ── Compile ───────────────────────────────────────────────────────────────
    graph = builder.compile(checkpointer=checkpointer)
    return graph


def get_redis_checkpointer():
    """
    Creates a Redis-backed checkpointer for HITL state persistence.
    Used in Phase 6 when we add human-in-the-loop.
    """
    return RedisSaver.from_conn_string(settings.redis_url)


# Module-level compiled graph
workflow = create_workflow(checkpointer=None)
