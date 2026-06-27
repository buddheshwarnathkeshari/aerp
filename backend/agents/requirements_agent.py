"""backend/agents/requirements_agent.py"""
from backend.agents.base_agent import BaseAgent
from backend.prompts.requirements import SYSTEM_PROMPT


class RequirementsAgent(BaseAgent):
    """Specialist agent for checking PR implementation against Jira acceptance criteria."""

    @property
    def system_prompt(self) -> str:
        return SYSTEM_PROMPT

    @property
    def result_key(self) -> str:
        return "requirements_result"

    @property
    def agent_name(self) -> str:
        return "requirements_agent"


requirements_agent = RequirementsAgent()
