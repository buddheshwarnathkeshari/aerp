"""backend/agents/architecture_agent.py"""
from backend.agents.base_agent import BaseAgent
from backend.prompts.architecture import SYSTEM_PROMPT


class ArchitectureAgent(BaseAgent):
    """Specialist agent for SOLID violations, layer coupling, and design patterns."""

    SYSTEM_PROMPT = SYSTEM_PROMPT

    AGENT_NAME = "architecture_agent"


architecture_agent = ArchitectureAgent()
