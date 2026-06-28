"""backend/agents/security_agent.py"""
from backend.agents.base_agent import BaseAgent
from backend.prompts.security import SYSTEM_PROMPT


class SecurityAgent(BaseAgent):
    """Specialist agent for OWASP Top 10 and application security vulnerabilities."""

    SYSTEM_PROMPT = SYSTEM_PROMPT

    AGENT_NAME = "security_agent"


security_agent = SecurityAgent()
