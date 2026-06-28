from backend.agents.base_agent import BaseAgent
from backend.prompts.requirements import SYSTEM_PROMPT


class RequirementsAgent(BaseAgent):
    """Specialist agent for checking PR implementation against Jira acceptance criteria."""

    SYSTEM_PROMPT = SYSTEM_PROMPT

    AGENT_NAME = "requirements_agent"


requirements_agent = RequirementsAgent()
