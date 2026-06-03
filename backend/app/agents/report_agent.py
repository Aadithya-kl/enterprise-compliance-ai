"""
Report Agent.
Synthesises the compliance analysis and risk assessment into a
professional executive-grade audit report with an executive summary
and structured recommendations.
"""

import ollama
from typing import Any

from app.agents.base import BaseAgent
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class ReportAgent(BaseAgent):
    """
    Produces the final deliverable: a structured audit report
    containing an executive summary, detailed findings, and
    a prioritised recommendation list.
    """

    @property
    def name(self) -> str:
        return "ReportAgent"

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        """
        Args:
            context: Must contain:
                - compliance_analysis: dict (from ComplianceAgent)
                - risk_assessment: dict (from RiskAgent)

        Returns:
            final_report: dict with executive_summary, structured_findings,
                          recommendations, metadata
        """
        compliance_analysis: dict = context.get("compliance_analysis", {})
        risk_assessment: dict = context.get("risk_assessment", {})

        if not compliance_analysis:
            return {"error": "ReportAgent requires compliance_analysis in context."}
        if not risk_assessment:
            return {"error": "ReportAgent requires risk_assessment in context."}

        executive_summary = self._generate_executive_summary(
            compliance_analysis, risk_assessment
        )

        structured_findings = self._structure_findings(
            compliance_analysis, risk_assessment
        )

        final_report = {
            "executive_summary": executive_summary,
            "structured_findings": structured_findings,
            "risk_level": risk_assessment.get("risk_level", "Unknown"),
            "compliance_score": risk_assessment.get("overall_score", 0),
            "total_violations": compliance_analysis.get("violation_count", 0),
            "issues": compliance_analysis.get("issues", []),
            "recommendations": compliance_analysis.get("recommendations", []),
            "mitigation_roadmap": risk_assessment.get("mitigation_roadmap", ""),
            "audit_timestamp": compliance_analysis.get("audit_timestamp", ""),
            "auditor": compliance_analysis.get("auditor", "Compliance AI Platform"),
        }

        logger.info(
            f"{self.name}: final report produced — "
            f"risk={final_report['risk_level']} "
            f"score={final_report['compliance_score']}"
        )
        return {"final_report": final_report}

    def _generate_executive_summary(
        self,
        compliance_analysis: dict,
        risk_assessment: dict,
    ) -> str:
        """Generate a concise executive summary suitable for senior leadership."""
        risk_level = risk_assessment.get("risk_level", "Unknown")
        score = risk_assessment.get("overall_score", 0)
        violation_count = compliance_analysis.get("violation_count", 0)
        issues = compliance_analysis.get("issues", [])
        issues_text = "\n".join(f"- {issue}" for issue in issues[:5])

        prompt = f"""You are a Chief Compliance Officer writing an executive summary.

Findings:
- Overall Risk Level: {risk_level}
- Compliance Score: {score}/100
- Total Violations Identified: {violation_count}

Key Issues (top {min(5, len(issues))}):
{issues_text}

Write a concise, professional executive summary (3-4 paragraphs) suitable
for presentation to the Board of Directors. Use formal language. No bullet points."""

        try:
            response = ollama.chat(
                model=settings.OLLAMA_MODEL,
                messages=[{"role": "user", "content": prompt}],
            )
            return response["message"]["content"]
        except Exception as exc:
            logger.error(f"{self.name}: executive summary generation failed: {exc}")
            return (
                f"Executive summary generation failed. "
                f"Risk Level: {risk_level}. Compliance Score: {score}/100. "
                f"Violations: {violation_count}."
            )

    def _structure_findings(
        self,
        compliance_analysis: dict,
        risk_assessment: dict,
    ) -> list[dict]:
        """
        Combine per-issue severity with the issue text into a
        structured findings list for the report viewer.
        """
        per_issue = risk_assessment.get("per_issue_severity", [])
        recommendations = compliance_analysis.get("recommendations", [])

        findings = []
        for item in per_issue:
            idx = item.get("index", 0)
            findings.append(
                {
                    "finding_number": idx + 1,
                    "description": item.get("issue", ""),
                    "severity": item.get("severity", "medium"),
                    "recommendation": (
                        recommendations[idx]
                        if idx < len(recommendations)
                        else "Review and remediate."
                    ),
                }
            )
        return findings
