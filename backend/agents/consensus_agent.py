"""backend/agents/consensus_agent.py"""

import time
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

from backend.models.findings import ConsensusReport
from backend.prompts.consensus import SYSTEM_PROMPT, build_human_message
from backend.config.settings import get_settings
import structlog

logger = structlog.get_logger()
settings = get_settings()


class ConsensusAgent:
    """
    The final agent in the review pipeline.
    It takes all findings from the 8 parallel agents and produces
    a single deduplicated ConsensusReport with a final risk score.
    """

    @property
    def agent_name(self) -> str:
        return "consensus_agent"

    async def run(self, state: dict) -> dict:
        review_id = state["review_id"]
        start_time = time.time()
        logger.info(f"{self.agent_name} starting", review_id=review_id)

        try:
            # 1. Gather inputs
            pr_metadata = state.get("pr_metadata", {})
            agent_findings = state.get("agent_findings", [])

            # 2. Build messages
            human_msg_content = build_human_message(
                raw_context=state.get("raw_context", ""),
                pr_metadata=pr_metadata,
                agent_findings=agent_findings,
            )

            messages = [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=human_msg_content),
            ]

            # 3. Call LLM with structured output (ConsensusReport)
            llm = ChatGoogleGenerativeAI(
                model=settings.gemini_model,
                google_api_key=settings.google_api_key,
                temperature=0,  # Deterministic synthesis
                max_retries=3,
            ).with_structured_output(ConsensusReport)

            import os
            if os.environ.get("MOCK_LLM") == "1":
                from backend.models.findings import CodeFinding, Severity, Recommendation
                report = ConsensusReport(
                    final_findings=[
                        CodeFinding(
                            title="Mock Consensus Finding",
                            severity=Severity.HIGH,
                            confidence=0.95,
                            description="Aggregated mock finding.",
                            evidence="Mock evidence",
                            file_path="src/main.py",
                            line_number=42,
                        )
                    ],
                    risk_score=75,
                    overall_assessment="High risk detected by mock consensus.",
                    recommendation=Recommendation.REQUEST_CHANGES,
                    confidence_in_assessment=0.95,
                )
            else:
                report: ConsensusReport = await llm.ainvoke(messages)

            elapsed = round(time.time() - start_time, 2)
            logger.info(
                f"{self.agent_name} complete",
                review_id=review_id,
                findings_count=len(report.final_findings),
                risk_score=report.risk_score,
                recommendation=report.recommendation,
                elapsed_seconds=elapsed,
            )

            # 4. Format findings for state
            final_agent_findings = [
                {
                    "agent": "consensus_agent",
                    "severity": f.severity.value,
                    "confidence": f.confidence,
                    "title": f.title,
                    "description": f.description,
                    "file_path": f.file_path,
                    "line_number": f.line_number,
                    "evidence": f.evidence,
                    "suggested_fix": f.suggested_fix,
                    "owasp_category": f.owasp_category,
                }
                for f in report.final_findings
            ]

            consensus_result = {
                "agent": self.agent_name,
                "findings": final_agent_findings,
                "overall_assessment": report.overall_assessment,
                "recommendation": report.recommendation.value,
                "risk_score": report.risk_score,
                "confidence": 1.0,
            }

            return {
                "consensus_result": consensus_result,
            }

        except Exception as e:
            logger.error(
                f"{self.agent_name} failed",
                review_id=review_id,
                error=str(e),
            )
            # Graceful degradation
            return {
                "consensus_result": {
                    "agent": self.agent_name,
                    "findings": [],
                    "overall_assessment": f"Consensus failed: {str(e)}",
                    "recommendation": "approve_with_comments",
                    "risk_score": 0,
                    "confidence": 0.0,
                }
            }


consensus_agent = ConsensusAgent()
