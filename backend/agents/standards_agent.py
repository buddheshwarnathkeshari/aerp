"""backend/agents/standards_agent.py"""
from backend.agents.base_agent import BaseAgent
from backend.prompts.standards import SYSTEM_PROMPT


class StandardsAgent(BaseAgent):
    """Specialist agent for engineering standards, observability, and code maintainability."""

    @property
    def system_prompt(self) -> str:
        return SYSTEM_PROMPT

    @property
    def result_key(self) -> str:
        return "standards_result"

    @property
    def agent_name(self) -> str:
        return "standards_agent"


standards_agent = StandardsAgent()
