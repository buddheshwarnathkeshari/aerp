"""
backend/graph/state.py

THE MOST IMPORTANT FILE IN THE PROJECT.

WHAT IS ReviewState?
  This TypedDict defines the "shared working memory" of the entire
  LangGraph workflow. Every agent reads from it. Every agent writes to it.
  Think of it as a whiteboard that all agents can see.

Design Note: TypedDict INSTEAD OF A REGULAR DICT?
  TypedDict gives us type hints without runtime overhead.
  - dict           → no type hints, runtime bugs
  - Pydantic model → validates on every write (too slow for state)
  - TypedDict      → type hints + no runtime cost (perfect for LangGraph state)

HOW STATE UPDATES WORK IN LANGGRAPH:
  Nodes return a PARTIAL state update — only the keys they changed.
  LangGraph merges it into the full state automatically.

  Example:
    security_node returns: {"security_findings": [...]}
    LangGraph merges this with the existing state.
    All other keys remain unchanged.

  You NEVER return the full state from a node — just your changes.

  LangGraph uses "reducers" — functions that define how to merge updates
  for a specific key. The default reducer replaces the value.
  You can define custom reducers (e.g., list append) with Annotated types.
"""

from typing import TypedDict, Optional, Annotated
from operator import add  # used as a reducer for list fields


# ─────────────────────────────────────────────────────────────────────────────
# Sub-types used within ReviewState
# ─────────────────────────────────────────────────────────────────────────────


class PRMetadata(TypedDict):
    """Structured data about the GitHub Pull Request."""

    pr_number: int
    title: str
    description: str
    author: str
    branch: str
    base_branch: str
    repo_owner: str
    repo_name: str
    changed_files: list[str]  # List of file paths that changed
    diff: str  # Full unified diff string
    commit_messages: list[str]


class JiraTicket(TypedDict):
    """Structured data from the Jira ticket."""

    ticket_id: str
    title: str
    description: str
    acceptance_criteria: list[str]  # Each criterion as a separate string
    business_rules: list[str]
    story_points: Optional[int]
    priority: str
    status: str
    reporter: str
    linked_tickets: list[str]


class AgentFinding(TypedDict):
    """
    A single finding from any agent.

    DESIGN DECISION: Why a shared finding format?
    Every agent outputs the same structure. This lets the Consensus Agent
    process all findings uniformly — it doesn't need to know which
    agent produced a finding to work with it.
    """

    agent: str  # e.g. "security_agent", "code_review_agent"
    severity: str  # "critical" | "high" | "medium" | "low" | "info"
    confidence: float  # 0.0 to 1.0
    title: str  # Short, human-readable title
    description: str  # Full explanation
    file_path: Optional[str]  # Which file has this issue (None for general findings)
    line_number: Optional[int]  # Which line (None if not applicable)
    evidence: str  # What the agent observed that led to this finding
    suggested_fix: Optional[str]  # How to fix it (if agent can suggest)
    owasp_category: Optional[str]  # For security findings: OWASP category


class AgentResult(TypedDict):
    """Complete output from a single agent run."""

    agent: str
    findings: list[AgentFinding]
    overall_assessment: str  # A brief paragraph summary
    recommendation: (
        str  # "approve" | "approve_with_comments" | "request_changes" | "block"
    )
    confidence: float  # Overall confidence in this agent's assessment
    tokens_used: Optional[int]  # Track cost


class ConsensusResult(TypedDict):
    """The final unified report produced by the Consensus Agent."""

    validated_findings: list[AgentFinding]  # After dedup + confidence filtering
    all_findings: list[AgentFinding]  # Everything including low confidence
    risk_score: int  # 0–100
    risk_breakdown: dict  # Per-dimension scores
    recommendation: str  # Final: approve/block/etc
    recommendation_rationale: str  # Why this recommendation
    findings_for_pr: list[AgentFinding]  # Only findings above confidence threshold


class HumanDecision(TypedDict):
    """Records what the human decided during HITL."""

    decision: str  # "approve" | "reject" | "approve_with_override"
    reviewer: str  # Who made the decision
    comment: Optional[str]  # Optional explanation
    overridden_findings: list[str]  # Finding IDs the human acknowledged/dismissed
    decided_at: str  # ISO timestamp


# ─────────────────────────────────────────────────────────────────────────────
# The Main State Object
# ─────────────────────────────────────────────────────────────────────────────


class ReviewState(TypedDict):
    """
    The complete shared state for the AERP review workflow.

    LIFECYCLE:
      1. Created empty when a review starts.
      2. context_collector_node fills: pr_metadata, jira_ticket, doc_content, raw_context
      3. repo_analyzer_node fills: impact_graph, changed_files_analysis
      4. Agent nodes fill: *_result fields (run in parallel)
      5. consensus_node fills: consensus_result
      6. human_decision_node fills: human_decision
      7. output_node fills: github_comments_posted, doc_pr_url, test_pr_url

    ANNOTATED LIST FIELDS:
      Fields marked with Annotated[list, add] use the "add" reducer.
      This means when two parallel agents both write to agent_findings,
      LangGraph appends both lists instead of one overwriting the other.
      This is critical for parallel execution correctness.
    """

    # ── Input data ────────────────────────────────────────────────────────────
    review_id: str  # Unique ID for this review session
    pr_url: str  # The original PR URL submitted by user
    jira_url: Optional[str]  # The original Jira URL
    doc_url: Optional[str]  # The original Google Doc URL

    # ── Collected context (filled by context_collector_node) ──────────────────
    pr_metadata: Optional[PRMetadata]  # Structured PR data from GitHub
    jira_ticket: Optional[JiraTicket]  # Structured ticket data from Jira
    doc_content: Optional[str]  # Raw text from Google Doc
    raw_context: Optional[str]  # Combined context string for RAG indexing

    # ── Repository analysis (filled by repo_analyzer_node) ───────────────────
    changed_files_analysis: Optional[dict]  # Per-file metadata
    impact_graph: Optional[dict]  # What else does this change affect?
    detected_framework: Optional[str]  # "fastapi" | "django" | "spring_boot" | etc

    # ── Agent results — filled in PARALLEL by each agent ─────────────────────
    # Annotated[list, add] means these lists are APPENDED when parallel
    # agents write to them simultaneously (not overwritten).
    selected_agents: Optional[list[str]]  # List of agents chosen by orchestrator
    agent_findings: Annotated[list[AgentFinding], add]  # All findings from all agents

    # Individual agent results (each agent writes its own key)
    requirements_result: Optional[AgentResult]
    code_review_result: Optional[AgentResult]
    security_result: Optional[AgentResult]
    database_result: Optional[AgentResult]
    scalability_result: Optional[AgentResult]
    standards_result: Optional[AgentResult]
    architecture_result: Optional[AgentResult]
    blast_radius_result: Optional[AgentResult]

    # ── Cross-agent critique (filled after all agents complete) ───────────────
    critique_complete: bool  # Has cross-agent discussion happened?

    # ── Consensus (filled by consensus_node) ─────────────────────────────────
    consensus_result: Optional[ConsensusResult]

    # ── Human-in-the-Loop ────────────────────────────────────────────────────
    hitl_required: bool  # Does this review need human approval?
    human_decision: Optional[HumanDecision]

    # ── Outputs ───────────────────────────────────────────────────────────────
    github_comments_posted: bool
    doc_pr_url: Optional[str]  # URL of generated documentation PR
    test_pr_url: Optional[str]  # URL of generated test PR
    final_report: Optional[dict]  # Complete final report

    # ── Metadata ──────────────────────────────────────────────────────────────
    error: Optional[str]  # If something fails, store error here
    started_at: Optional[str]  # ISO timestamp
    completed_at: Optional[str]  # ISO timestamp


def create_initial_state(
    review_id: str,
    pr_url: str,
    jira_url: Optional[str] = None,
    doc_url: Optional[str] = None,
) -> ReviewState:
    """
    Creates the initial empty ReviewState when a review starts.

    IMPORTANT: Every list field must be initialized to [] (not None).
    Because we use the `add` reducer, the reducer expects lists.
    Appending to None would crash.
    """
    return ReviewState(
        # Input
        review_id=review_id,
        pr_url=pr_url,
        jira_url=jira_url,
        doc_url=doc_url,
        # Context — empty until collected
        pr_metadata=None,
        jira_ticket=None,
        doc_content=None,
        raw_context=None,
        # Repository analysis
        changed_files_analysis=None,
        impact_graph=None,
        detected_framework=None,
        # Agent findings — empty lists (Annotated reducer expects lists)
        selected_agents=None,
        agent_findings=[],
        # Individual agent results
        requirements_result=None,
        code_review_result=None,
        security_result=None,
        database_result=None,
        scalability_result=None,
        standards_result=None,
        architecture_result=None,
        blast_radius_result=None,
        # Consensus
        critique_complete=False,
        consensus_result=None,
        # HITL
        hitl_required=False,
        human_decision=None,
        # Outputs
        github_comments_posted=False,
        doc_pr_url=None,
        test_pr_url=None,
        final_report=None,
        # Metadata
        error=None,
        started_at=None,
        completed_at=None,
    )
