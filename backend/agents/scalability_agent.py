"""backend/agents/scalability_agent.py"""
from backend.agents.base_agent import BaseAgent
from backend.prompts.scalability import SYSTEM_PROMPT


class ScalabilityAgent(BaseAgent):
    """Specialist agent for performance, caching, and scalability under load."""

    @property
    def system_prompt(self) -> str:
        return SYSTEM_PROMPT

    @property
    def result_key(self) -> str:
        return "scalability_result"

    @property
    def agent_name(self) -> str:
        return "scalability_agent"


scalability_agent = ScalabilityAgent()
