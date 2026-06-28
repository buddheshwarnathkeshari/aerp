from backend.agents.base_agent import BaseAgent
from backend.prompts.scalability import SYSTEM_PROMPT


class ScalabilityAgent(BaseAgent):
    """Specialist agent for performance, caching, and scalability under load."""

    SYSTEM_PROMPT = SYSTEM_PROMPT

    AGENT_NAME = "scalability_agent"


scalability_agent = ScalabilityAgent()
