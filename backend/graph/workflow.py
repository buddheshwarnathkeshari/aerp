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
    # Phase 2.5
    orchestrator_node,
    # Phase 3 + 4 agents
    code_review_node,
    security_node,
    database_node,
    requirements_node,
    scalability_node,
    standards_node,
    architecture_node,
    blast_radius_node,
    # Phase 5
    consensus_node,
    # Phase 6
    hitl_node,
    output_node,
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


def route_agents(state: ReviewState) -> list[str]:
    """
    Conditional edge logic to route to selected agents.
    Returns a list of node names to execute in parallel.
    """
    selected = state.get("selected_agents")
    if not selected:
        # Fallback: run all agents
        return AGENT_NODES
    
    # Ensure we only route to valid agent nodes
    valid_agents = [agent for agent in selected if agent in AGENT_NODES]
    return valid_agents if valid_agents else AGENT_NODES

def route_after_consensus(state: ReviewState) -> str:
    """
    Conditional edge logic after the consensus agent finishes.
    If risk_score > 40, go to HITL. Otherwise, Auto-Approve (go to Output).
    """
    import structlog
    logger = structlog.get_logger()

    result = state.get("consensus_result", {})
    score = result.get("risk_score", 0)

    # In mock mode, we force the risk score to be 75, which triggers HITL
    if score > 40:
        logger.info("Routing to HITL (High Risk)", score=score)
        return "hitl"
    else:
        logger.info("Routing to Output (Auto-Approve)", score=score)
        return "output"


def create_workflow(checkpointer=None):
    """
    Builds and compiles the AERP LangGraph workflow.
    """
    builder = StateGraph(ReviewState)

    # ── Register nodes ────────────────────────────────────────────────────────
    builder.add_node("context_collector", context_collector_node)
    builder.add_node("repository_analyzer", repository_analyzer_node)
    builder.add_node("orchestrator", orchestrator_node)

    # Phase 3 + 4 agent nodes
    builder.add_node("code_review", code_review_node)
    builder.add_node("security", security_node)
    builder.add_node("database", database_node)
    builder.add_node("requirements", requirements_node)
    builder.add_node("scalability", scalability_node)
    builder.add_node("standards", standards_node)
    builder.add_node("architecture", architecture_node)
    builder.add_node("blast_radius", blast_radius_node)

    # Phase 5 Consensus
    builder.add_node("consensus", consensus_node)
    
    # Phase 6 HITL and Output
    builder.add_node("hitl", hitl_node)
    builder.add_node("output", output_node)

    # ── Define edges ──────────────────────────────────────────────────────────
    builder.add_edge(START, "context_collector")
    builder.add_edge("context_collector", "repository_analyzer")
    builder.add_edge("repository_analyzer", "orchestrator")

    # FAN-OUT: orchestrator → [selected agents]
    builder.add_conditional_edges(
        "orchestrator",
        route_agents,
        {node: node for node in AGENT_NODES}
    )

    # FAN-IN: [8 agents] → consensus
    for agent_node in AGENT_NODES:
        builder.add_edge(agent_node, "consensus")

    # Conditional Routing: consensus → hitl or output
    builder.add_conditional_edges(
        "consensus",
        route_after_consensus,
        {
            "hitl": "hitl",
            "output": "output",
        }
    )

    builder.add_edge("hitl", "output")
    builder.add_edge("output", END)

    # ── Compile ───────────────────────────────────────────────────────────────
    graph = builder.compile(checkpointer=checkpointer, interrupt_before=["hitl"])
    return graph


# Module-level compiled graph (without checkpointer, mainly for visualizer)
workflow = create_workflow(checkpointer=None)
