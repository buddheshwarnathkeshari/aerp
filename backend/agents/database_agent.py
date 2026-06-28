from backend.agents.base_agent import BaseAgent
from backend.prompts.database import SYSTEM_PROMPT


class DatabaseAgent(BaseAgent):
    """Specialist agent for N+1 queries, unsafe migrations, and DB correctness."""

    SYSTEM_PROMPT = SYSTEM_PROMPT

    AGENT_NAME = "database_agent"


database_agent = DatabaseAgent()
