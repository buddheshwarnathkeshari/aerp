"""
backend/agents/code_review_agent.py

The Code Review Agent — the first complete agent in AERP.

This is the simplest possible concrete agent:
  - Inherits ALL execution logic from BaseAgent (run, tools, LLM setup)
  - Only defines:
      1. What it looks for (system_prompt from prompts/code_review.py)
      2. Where it stores its result (result_key = "code_review_result")
      3. Its name for logging

INTERVIEW: "How did you structure your multi-agent system?"
  "We used the Template Method pattern. The BaseAgent class implements
  the full agent lifecycle: build LLM, bind RAG tools, run ReAct loop,
  parse structured output. Each of our 8 specialist agents simply inherits
  BaseAgent and provides a domain-specific prompt. Adding a new agent
  takes less than 20 lines of code."
"""

from backend.agents.base_agent import BaseAgent
from backend.prompts.code_review import SYSTEM_PROMPT


class CodeReviewAgent(BaseAgent):
    """
    Specialist agent for code quality review.

    Looks for:
    - Runtime errors and crashes
    - Missing error handling
    - Resource leaks
    - N+1 queries
    - Incorrect business logic
    - Missing edge case handling
    - Concurrency issues

    Does NOT look for (handled by other agents):
    - Security vulnerabilities (SecurityAgent)
    - Requirements compliance (RequirementsAgent)
    - Database schema issues (DatabaseAgent)
    """

    SYSTEM_PROMPT = SYSTEM_PROMPT
    AGENT_NAME = "code_review_agent"


# Module-level singleton — instantiated once, reused for every review
# WHY SINGLETON? The agent holds no per-review state. It's stateless.
# Creating it once at import time saves ~10ms per review.
code_review_agent = CodeReviewAgent()
