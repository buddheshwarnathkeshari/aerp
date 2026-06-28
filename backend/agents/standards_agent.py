"""backend/agents/standards_agent.py"""
from backend.agents.base_agent import BaseAgent
from backend.prompts.standards import SYSTEM_PROMPT


class StandardsAgent(BaseAgent):
    """Specialist agent for engineering standards, observability, and code maintainability."""

    SYSTEM_PROMPT = SYSTEM_PROMPT

    AGENT_NAME = "standards_agent"


standards_agent = StandardsAgent()
