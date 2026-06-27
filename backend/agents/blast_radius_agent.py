"""backend/agents/blast_radius_agent.py"""
from backend.agents.base_agent import BaseAgent
from backend.prompts.blast_radius import SYSTEM_PROMPT


class BlastRadiusAgent(BaseAgent):
    """Specialist agent for downstream failure impact and deployment risk analysis."""

    @property
    def system_prompt(self) -> str:
        return SYSTEM_PROMPT

    @property
    def result_key(self) -> str:
        return "blast_radius_result"

    @property
    def agent_name(self) -> str:
        return "blast_radius_agent"


blast_radius_agent = BlastRadiusAgent()
