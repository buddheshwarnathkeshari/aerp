"""
backend/agents/base_agent.py

Abstract base class that ALL specialist agents inherit from.

WHY AN ABSTRACT BASE CLASS?
  All agents (Code Review, Security, Requirements, etc.) share the same
  "lifecycle":
    1. Build the LLM with structured output
    2. Build the RAG search tool bound to this review
    3. Create a ReAct agent (Reason + Act: think → search → think → answer)
    4. Run the agent with the PR context
    5. Return a structured AgentReport

  Without a base class, we'd duplicate this ~50 lines of code in every agent.
  With a base class, each agent only needs to define:
    - Its system prompt  (WHAT to look for)
    - Its result_key    (WHERE in ReviewState to store results)

DESIGN PATTERNS USED HERE:
  1. Template Method Pattern:
     The base class defines the algorithm (run()).
     Subclasses override specific steps (system_prompt, result_key).

  2. Strategy Pattern (via LangChain):
     The LLM is swappable — you could swap Gemini for Claude/GPT-4
     without changing any agent code.

INTERVIEW: "What design patterns do you use in production?"
  "I use the Template Method pattern for our AI agent base class.
  All 8 specialist agents share the same execution lifecycle (fetch context,
  invoke LLM, parse structured output, store result). The base class
  implements this once. Each agent only overrides the prompt and result key.
  This reduced agent code by ~80% and makes adding a new agent a 20-line task."

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
from abc import ABC, abstractmethod
from typing import Any


from langchain_core.messages import SystemMessage, HumanMessage
from langchain.agents import AgentExecutor, create_react_agent
from langchain import hub

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
      2. Override system_prompt property
      3. Override result_key property
      4. That's it.

    The run() method handles everything else automatically.
    """

    # ── Abstract properties — subclasses MUST implement ───────────────────────

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """
        The system prompt that defines what this agent looks for.
        Each agent has a different domain: code quality, security, requirements, etc.
        """
        ...

    @property
    @abstractmethod
    def result_key(self) -> str:
        """
        The ReviewState key where this agent stores its result.
        Example: "code_review_result", "security_result"
        """
        ...

    @property
    @abstractmethod
    def agent_name(self) -> str:
        """Human-readable name. Used in logs and finding attribution."""
        ...

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

        WHY build tools per-review?
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
            f"{self.agent_name} starting",
            review_id=review_id,
        )

        try:
            llm = self._build_llm()
            tools = self._build_tools(review_id)

            # Build the message list for the LLM
            messages = [
                SystemMessage(content=self.system_prompt),
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
            
            await publish_agent_status(review_id, self.agent_name, "running", "Reasoning and determining needed context...")
            
            tool_results = []
            tool_response = await llm_with_tools.ainvoke(messages)

            # Execute any tool calls the LLM requested
            if hasattr(tool_response, 'tool_calls') and tool_response.tool_calls:
                for tool_call in tool_response.tool_calls[:5]:  # max 5 tool calls
                    tool_name = tool_call.get("name", "")
                    tool_args = tool_call.get("args", {})
                    logger.info(
                        f"{self.agent_name} calling tool",
                        tool=tool_name,
                        args=tool_args,
                    )
                    query_str = tool_args.get("query", "")
                    if query_str:
                        await publish_agent_status(review_id, self.agent_name, "running", f"Searching codebase for '{query_str}'...")
                    else:
                        await publish_agent_status(review_id, self.agent_name, "running", f"Running tool {tool_name}...")
                        
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
                enriched_human += "\n\n## Additional Context from Search\n" + "\n\n".join(tool_results)

            import os
            if os.environ.get("MOCK_LLM") == "1":
                from backend.schemas.findings import CodeFinding, Severity, Recommendation
                report = AgentReport(
                    findings=[
                        CodeFinding(
                            title=f"Mock finding from {self.agent_name}",
                            severity=Severity.HIGH,
                            confidence=0.9,
                            description="This is a mock finding generated because MOCK_LLM=1.",
                            evidence="Mock evidence",
                            file_path="src/main.py",
                            line_number=42,
                        )
                    ],
                    overall_assessment=f"Mock assessment from {self.agent_name}",
                    recommendation=Recommendation.REQUEST_CHANGES,
                    confidence=0.9,
                )
            else:
                from backend.schemas.findings import Recommendation
                # Final call: get structured AgentReport
                
                await publish_agent_status(review_id, self.agent_name, "running", "Compiling final findings and recommendations...")
                
                report = None
                current_messages = [
                    SystemMessage(content=self.system_prompt),
                    HumanMessage(content=enriched_human),
                ]
                
                for attempt in range(3):
                    try:
                        report = await llm.ainvoke(current_messages)
                        if report is not None:
                            break
                        # If None, the parser failed silently
                        current_messages.append(
                            HumanMessage(content="You failed to output valid JSON matching the schema. Please output strictly valid JSON matching the exact schema with NO preamble text.")
                        )
                    except Exception as parse_error:
                        current_messages.append(
                            HumanMessage(content=f"Your JSON output had a validation error: {str(parse_error)}. Please fix the syntax and output strictly valid JSON.")
                        )
                
                if report is None:
                    # Fallback if all 3 attempts fail
                    report = AgentReport(
                        findings=[],
                        overall_assessment=f"JSON Parsing Failed after 3 attempts with {self.agent_name}. The LLM output could not be parsed.",
                        recommendation=Recommendation.APPROVE_WITH_COMMENTS,
                        confidence=0.0
                    )

            elapsed = round(time.time() - start_time, 2)
            logger.info(
                f"{self.agent_name} complete",
                review_id=review_id,
                findings_count=len(report.findings),
                recommendation=report.recommendation,
                elapsed_seconds=elapsed,
            )

            # Convert Pydantic findings → AgentFinding TypedDicts for state
            agent_findings = [
                {
                    "agent": self.agent_name,
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
                "agent": self.agent_name,
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
                f"{self.agent_name} failed",
                review_id=review_id,
                error=str(e),
            )
            # Non-fatal: return empty result so other agents can continue
            return {
                self.result_key: {
                    "agent": self.agent_name,
                    "findings": [],
                    "overall_assessment": f"Agent failed: {str(e)}",
                    "recommendation": "approve_with_comments",
                    "confidence": 0.0,
                    "tokens_used": None,
                },
                "agent_findings": [],
            }
