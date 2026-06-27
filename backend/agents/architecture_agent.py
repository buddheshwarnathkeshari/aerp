"""backend/agents/architecture_agent.py"""
from backend.agents.base_agent import BaseAgent
from backend.prompts.architecture import SYSTEM_PROMPT


class ArchitectureAgent(BaseAgent):
    """Specialist agent for SOLID violations, layer coupling, and design patterns."""

    @property
    def system_prompt(self) -> str:
        return SYSTEM_PROMPT

    @property
    def result_key(self) -> str:
        return "architecture_result"

    @property
    def agent_name(self) -> str:
        return "architecture_agent"


architecture_agent = ArchitectureAgent()
