"""backend/agents/database_agent.py"""
from backend.agents.base_agent import BaseAgent
from backend.prompts.database import SYSTEM_PROMPT


class DatabaseAgent(BaseAgent):
    """Specialist agent for N+1 queries, unsafe migrations, and DB correctness."""

    @property
    def system_prompt(self) -> str:
        return SYSTEM_PROMPT

    @property
    def result_key(self) -> str:
        return "database_result"

    @property
    def agent_name(self) -> str:
        return "database_agent"


database_agent = DatabaseAgent()
