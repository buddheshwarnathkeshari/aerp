"""backend/agents/orchestrator_agent.py"""

import time
from typing import List
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field
import structlog

from backend.prompts.orchestrator import SYSTEM_PROMPT, build_human_message
from backend.config.settings import get_settings

logger = structlog.get_logger()

class OrchestratorDecision(BaseModel):
    selected_agents: List[str] = Field(
        description="List of agent keys to run. Must be subset of: ['code_review', 'security', 'database', 'requirements', 'scalability', 'standards', 'architecture', 'blast_radius']"
    )
    rationale: str = Field(description="Explanation of why these specific agents were chosen and others skipped.")

class OrchestratorAgent:
    @property
    def agent_name(self) -> str:
        return "orchestrator_agent"

    async def run(self, state: dict) -> dict:
        review_id = state["review_id"]
        start_time = time.time()
        logger.info(f"{self.agent_name} starting", review_id=review_id)
        
        pr_metadata = state.get("pr_metadata", {})
        
        # Build messages
        human_msg = build_human_message(pr_metadata)
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=human_msg)
        ]

        try:
            from backend.utils.llm_factory import get_llm
            base_llm = get_llm(temperature=0.0)
            if not base_llm:
                raise ValueError("Failed to initialize LLM for orchestrator.")
            
            llm = base_llm.with_structured_output(OrchestratorDecision)
            
            import os
            if os.environ.get("MOCK_LLM") == "1":
                decision = OrchestratorDecision(
                    selected_agents=["code_review", "security", "requirements"],
                    rationale="Mock orchestrator decision"
                )
            else:
                decision: OrchestratorDecision = await llm.ainvoke(messages)
            
            elapsed = round(time.time() - start_time, 2)
            logger.info(f"{self.agent_name} complete", review_id=review_id, selected=decision.selected_agents, elapsed=elapsed)
            
            # Always ensure code_review runs
            if "code_review" not in decision.selected_agents:
                decision.selected_agents.append("code_review")
                
            return {
                "selected_agents": decision.selected_agents
            }
            
        except Exception as e:
            logger.error(f"{self.agent_name} failed, falling back to all agents", review_id=review_id, error=str(e))
            # Fallback: run all agents
            return {
                "selected_agents": [
                    "code_review", "security", "database", "requirements", 
                    "scalability", "standards", "architecture", "blast_radius"
                ]
            }

orchestrator_agent = OrchestratorAgent()
