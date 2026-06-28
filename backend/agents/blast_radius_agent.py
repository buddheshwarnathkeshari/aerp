"""backend/agents/blast_radius_agent.py"""
from backend.agents.base_agent import BaseAgent
from backend.prompts.blast_radius import SYSTEM_PROMPT


class BlastRadiusAgent(BaseAgent):
    """Specialist agent for downstream failure impact and deployment risk analysis."""

    SYSTEM_PROMPT = SYSTEM_PROMPT

    AGENT_NAME = "blast_radius_agent"


blast_radius_agent = BlastRadiusAgent()
