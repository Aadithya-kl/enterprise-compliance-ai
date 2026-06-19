"""
Compliance Agent.
Responsible for structured gap analysis between policy and regulation documents.
Produces a machine-readable compliance assessment with violations and recommendations.
"""

from typing import Any

from app.agents.base import BaseAgent
from app.core.logging import get_logger
from app.services.compliance_service import generate_compliance_report

logger = get_logger(__name__)


class ComplianceAgent(BaseAgent):
    """
    Analyses policy documents against regulation documents to identify
    compliance gaps, violations, and areas of conformance.
    """

    @property
    def name(self) -> str:
        return "ComplianceAgent"

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        """
        Args:
            context: Must contain:
                - policy_chunks: list[str]
                - regulation_chunks: list[str]

        Returns:
            compliance_analysis: dict with violation, issues, recommendations,
                                  risk, compliance_score, violation_count,
                                  audit_timestamp, auditor
        """
        selected_files: list[str] | None = context.get("selected_files", None)
        logger.info(f"{self.name}: analyzing using Map-Reduce for selected files: {selected_files}")

        report = generate_compliance_report(selected_files)

        if "raw_response" in report:
            logger.error(f"{self.name}: LLM returned unparseable output")
            return {
                "error": "ComplianceAgent could not parse LLM output.",
                "raw_response": report["raw_response"],
            }

        logger.info(
            f"{self.name}: complete — "
            f"risk={report['risk']} score={report['compliance_score']} "
            f"violations={report['violation_count']}"
        )
        return {"compliance_analysis": report}
