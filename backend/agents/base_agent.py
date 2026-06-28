"""
backend/agents/base_agent.py

Abstract base class that ALL specialist agents inherit from.
Each agent only needs to define:
    - Its AGENT_NAME     (e.g. "security_agent")
    - Its SYSTEM_PROMPT  (WHAT to look for)

Design Note: An ABSTRACT BASE CLASS?
  All agents (Code Review, Security, Requirements, etc.) share the same
  "lifecycle":
    1. Build the LLM with structured output
    2. Build the RAG search tool bound to this review
    3. Create a ReAct agent (Reason + Act: think → search → think → answer)
    4. Run the agent with the PR context
    5. Return a structured AgentReport


DESIGN PATTERNS USED HERE:
  1. Template Method Pattern:
     The base class defines the algorithm (run()).
     Subclasses override specific steps (AGENT_NAME, SYSTEM_PROMPT).

  2. Strategy Pattern (via LangChain):
     The LLM is swappable — you could swap Gemini for Claude/GPT-4
     without changing any agent code.



HOW ReAct AGENTS WORK:
  ReAct = Reasoning + Acting (from the 2022 paper by Yao et al.)

  The agent loop:
    1. THINK: "I need to check if this user query is parameterized"
    2. ACT:   Call search_context("SQL query parameterization")
    3. OBSERVE: Read the search results
    4. THINK: "The code uses string concatenation — this is an injection risk"
    5. ANSWER: Return CodeFinding(severity=CRITICAL, ...)

  In LangChain, this is `create_react_agent()`.
  The LLM decides when to stop calling tools and return the final answer.
"""

import time
from abc import ABC

from langchain_core.messages import SystemMessage, HumanMessage

from backend.schemas.findings import AgentReport
from backend.rag.retriever import build_rag_tool
from backend.config.settings import get_settings
import structlog

logger = structlog.get_logger()
settings = get_settings()


class BaseAgent(ABC):
    """
    Abstract base class for all AERP specialist agents.

    To create a new agent:
      1. Subclass BaseAgent
      2. Set AGENT_NAME = "my_agent"  (e.g. "security_agent")
      3. Set SYSTEM_PROMPT = SYSTEM_PROMPT  (import from prompts/)

    That's it. result_key is derived automatically as AGENT_NAME with
    '_agent' replaced by '_result' (e.g. "security_agent" → "security_result").
    """

    # ── Class-level variables — the ONLY things a subclass needs to define ────
    AGENT_NAME: str = ""
    SYSTEM_PROMPT: str = ""  # subclasses assign their imported SYSTEM_PROMPT

    # ── Derived automatically — no subclass boilerplate needed ────────────────
    @property
    def result_key(self) -> str:
        """
        Derived from AGENT_NAME: "security_agent" → "security_result".
        Convention: all specialist agents follow the *_agent → *_result pattern.
        """
        return self.AGENT_NAME.replace("_agent", "_result")

    # ── Shared implementation — same for all agents ───────────────────────────

    def _build_llm(self):
        """
        Creates the LLM configured for structured output via llm_factory.
        """
        from backend.utils.llm_factory import get_llm

        llm = get_llm(temperature=0.0)
        if not llm:
            raise ValueError("Failed to initialize LLM. Check API keys.")
        # Bind the Pydantic model as the required output schema
        return llm.with_structured_output(AgentReport)

    def _build_tools(self, review_id: str) -> list:
        """
        Creates the tools available to this agent.

        Currently: just the RAG search tool (search_context).
        Future: could add static analysis tools, AST parsers, etc.

        Design Note: build tools per-review
          The search_context tool must be scoped to the CURRENT review's
          embeddings in pgvector. We "close over" the review_id
          when creating the tool — this is a Python closure.
        """
        rag_tool = build_rag_tool(review_id)
        return [rag_tool]

    async def run(
        self,
        state: dict,
        human_message: str,
    ) -> dict:
        """
        Executes the agent for one review.

        Args:
            state: The current ReviewState dict
            human_message: The formatted prompt with PR content

        Returns:
            Partial state update dict to be merged by LangGraph

        EXECUTION FLOW:
          1. Build LLM with structured output
          2. Build RAG search tool for this review
          3. Invoke LLM with system + human messages
          4. Parse response into AgentReport
          5. Convert AgentReport findings into AgentFinding dicts (for state)
          6. Return partial state update
        """
        review_id = state["review_id"]
        start_time = time.time()

        logger.info(
            f"{self.AGENT_NAME} starting",
            review_id=review_id,
        )

        try:
            llm = self._build_llm()
            tools = self._build_tools(review_id)

            # Build the message list for the LLM
            messages = [
                SystemMessage(content=self.SYSTEM_PROMPT),
                HumanMessage(content=human_message),
            ]

            # For agents with tools: use bind_tools to enable tool calling
            # The LLM will autonomously decide when to call search_context
            from backend.utils.llm_factory import get_llm

            base_llm = get_llm(temperature=0.0)
            llm_with_tools = base_llm.bind_tools(tools)

            # Run the ReAct loop: think → (optionally) use tools → final answer
            # We implement a simple loop: first get tool calls, execute, then
            # call the structured output LLM with the enriched context.
            from backend.utils.pubsub import publish_agent_status

            await publish_agent_status(
                review_id,
                self.AGENT_NAME.replace("_", " ").title(),
                "running",
                "Reasoning and determining needed context...",
            )

            tool_results = []
            tool_response = await llm_with_tools.ainvoke(messages)

            # Execute any tool calls the LLM requested
            if hasattr(tool_response, "tool_calls") and tool_response.tool_calls:
                for tool_call in tool_response.tool_calls[:5]:  # max 5 tool calls
                    tool_name = tool_call.get("name", "")
                    tool_args = tool_call.get("args", {})
                    logger.info(
                        f"{self.AGENT_NAME} calling tool",
                        tool=tool_name,
                        args=tool_args,
                    )
                    query_str = tool_args.get("query", "")
                    if query_str:
                        await publish_agent_status(
                            review_id,
                            self.AGENT_NAME.replace("_", " ").title(),
                            "running",
                            f"Searching codebase for '{query_str}'...",
                        )
                    else:
                        await publish_agent_status(
                            review_id,
                            self.AGENT_NAME.replace("_", " ").title(),
                            "running",
                            f"Running tool {tool_name}...",
                        )

                    # Find and call the matching tool
                    for t in tools:
                        if t.name == tool_name:
                            result = await t.ainvoke(tool_args)
                            tool_results.append(
                                f"[Tool: {tool_name}]\nQuery: {tool_args}\nResult:\n{result}"
                            )

            # Build enriched message with tool results, then get structured output
            enriched_human = human_message
            if tool_results:
                enriched_human += (
                    "\n\n## Additional Context from Search\n"
                    + "\n\n".join(tool_results)
                )

            from backend.schemas.findings import Recommendation
            # Final call: get structured AgentReport

            await publish_agent_status(
                review_id,
                self.AGENT_NAME.replace("_", " ").title(),
                "running",
                "Compiling final findings and recommendations...",
            )

            report = None
            current_messages = [
                SystemMessage(content=self.SYSTEM_PROMPT),
                HumanMessage(content=enriched_human),
            ]

            for attempt in range(3):
                try:
                    report = await llm.ainvoke(current_messages)
                    if report is not None:
                        break
                    # If None, the parser failed silently
                    current_messages.append(
                        HumanMessage(
                            content="You failed to output valid JSON matching the schema. Please output strictly valid JSON matching the exact schema with NO preamble text."
                        )
                    )
                except Exception as parse_error:
                    current_messages.append(
                        HumanMessage(
                            content=f"Your JSON output had a validation error: {str(parse_error)}. Please fix the syntax and output strictly valid JSON."
                        )
                    )

            if report is None:
                # Fallback if all 3 attempts fail
                report = AgentReport(
                    findings=[],
                    overall_assessment=f"JSON Parsing Failed after 3 attempts with {self.AGENT_NAME}. The LLM output could not be parsed.",
                    recommendation=Recommendation.APPROVE_WITH_COMMENTS,
                    confidence=0.0,
                )

            elapsed = round(time.time() - start_time, 2)
            logger.info(
                f"{self.AGENT_NAME} complete",
                review_id=review_id,
                findings_count=len(report.findings),
                recommendation=report.recommendation,
                elapsed_seconds=elapsed,
            )

            # Convert Pydantic findings → AgentFinding TypedDicts for state
            agent_findings = [
                {
                    "agent": self.AGENT_NAME,
                    "severity": f.severity.value,
                    "confidence": f.confidence,
                    "title": f.title,
                    "description": f.description,
                    "file_path": f.file_path,
                    "line_number": f.line_number,
                    "evidence": f.evidence,
                    "suggested_fix": f.suggested_fix,
                    "owasp_category": f.owasp_category,
                }
                for f in report.findings
            ]

            # Build AgentResult for storage in state
            agent_result = {
                "agent": self.AGENT_NAME,
                "findings": agent_findings,
                "overall_assessment": report.overall_assessment,
                "recommendation": report.recommendation.value,
                "confidence": report.confidence,
                "tokens_used": None,  # LangChain doesn't expose this easily for Gemini
            }

            return {
                self.result_key: agent_result,
                "agent_findings": agent_findings,  # Appended via reducer
            }

        except Exception as e:
            logger.error(
                f"{self.AGENT_NAME} failed",
                review_id=review_id,
                error=str(e),
            )
            # Non-fatal: return empty result so other agents can continue
            return {
                self.result_key: {
                    "agent": self.AGENT_NAME,
                    "findings": [],
                    "overall_assessment": f"Agent failed: {str(e)}",
                    "recommendation": "approve_with_comments",
                    "confidence": 0.0,
                    "tokens_used": None,
                },
                "agent_findings": [],
            }
