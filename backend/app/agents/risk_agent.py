"""
Risk Agent.
Ingests the compliance analysis output and produces a detailed risk assessment
with per-issue severity classification and prioritised mitigation recommendations.
"""

import ollama
from typing import Any

from app.agents.base import BaseAgent
from app.core.config import settings
from app.core.logging import get_logger
from app.services.compliance_service import assess_risk, calculate_compliance_score

logger = get_logger(__name__)

# Severity mapping based on keyword heuristics
_SEVERITY_KEYWORDS = {
    "critical": ["breach", "violation", "illegal", "prohibited", "criminal"],
    "high": ["non-compliant", "failure", "missing", "absent", "lack"],
    "medium": ["inadequate", "insufficient", "weak", "unclear", "ambiguous"],
    "low": ["minor", "could be improved", "recommendation", "suggest"],
}


def _classify_severity(issue_text: str) -> str:
    """
    Heuristically classify an issue's severity based on keyword matching.
    Returns: 'critical' | 'high' | 'medium' | 'low'
    """
    lower = issue_text.lower()
    for severity, keywords in _SEVERITY_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            return severity
    return "medium"  # Default


class RiskAgent(BaseAgent):
    """
    Evaluates each compliance issue for severity and generates
    a prioritised mitigation roadmap.
    """

    @property
    def name(self) -> str:
        return "RiskAgent"

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        """
        Args:
            context: Must contain:
                - compliance_analysis: dict (output from ComplianceAgent)

        Returns:
            risk_assessment: dict with risk_level, overall_score,
                             per_issue_severity, mitigation_roadmap
        """
        compliance_analysis: dict = context.get("compliance_analysis", {})

        if not compliance_analysis:
            logger.error(f"{self.name}: compliance_analysis missing from context")
            return {"error": "RiskAgent requires compliance_analysis in context."}

        issues: list[str] = compliance_analysis.get("issues", [])
        risk_level = assess_risk(issues)
        overall_score = calculate_compliance_score(issues)

        # Per-issue severity classification
        classified_issues = [
            {
                "issue": issue,
                "severity": _classify_severity(issue),
                "index": idx,
            }
            for idx, issue in enumerate(issues)
        ]

        # Sort by severity for prioritised display
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        classified_issues.sort(key=lambda x: severity_order.get(x["severity"], 4))

        # Generate LLM-powered mitigation roadmap
        mitigation_roadmap = self._generate_mitigation_roadmap(issues, risk_level)

        risk_assessment = {
            "risk_level": risk_level,
            "overall_score": overall_score,
            "issue_count": len(issues),
            "per_issue_severity": classified_issues,
            "mitigation_roadmap": mitigation_roadmap,
        }

        logger.info(
            f"{self.name}: complete — "
            f"risk={risk_level} score={overall_score} issues={len(issues)}"
        )
        return {"risk_assessment": risk_assessment}

    def _generate_mitigation_roadmap(
        self,
        issues: list[str],
        risk_level: str,
    ) -> str:
        """
        Use the LLM to generate a prioritised remediation roadmap
        given the identified compliance issues.
        """
        if not issues:
            return "No compliance issues identified. No remediation required."

        issues_text = "\n".join(f"- {issue}" for issue in issues)

        prompt = f"""You are a Senior Enterprise Risk Manager.

Overall Risk Level: {risk_level}

Identified compliance issues:
{issues_text}

Generate a prioritised remediation roadmap with:
1. Immediate actions (within 30 days)
2. Short-term improvements (30-90 days)
3. Long-term strategic changes (90+ days)

Be specific, actionable, and professional. No bullet points — use numbered lists."""

        try:
            response = ollama.chat(
                model=settings.OLLAMA_MODEL,
                messages=[{"role": "user", "content": prompt}],
            )
            return response["message"]["content"]
        except Exception as exc:
            logger.error(
                f"{self.name}: mitigation roadmap generation failed: {exc}"
            )
            return f"Mitigation roadmap generation failed: {exc}"
