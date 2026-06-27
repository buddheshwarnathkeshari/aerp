"""backend/agents/security_agent.py"""
from backend.agents.base_agent import BaseAgent
from backend.prompts.security import SYSTEM_PROMPT


class SecurityAgent(BaseAgent):
    """Specialist agent for OWASP Top 10 and application security vulnerabilities."""

    @property
    def system_prompt(self) -> str:
        return SYSTEM_PROMPT

    @property
    def result_key(self) -> str:
        return "security_result"

    @property
    def agent_name(self) -> str:
        return "security_agent"


security_agent = SecurityAgent()
