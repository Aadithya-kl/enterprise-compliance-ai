"""
Trend Agents.
Implements the specific LangGraph nodes for the 5-year trend analysis.
"""

from typing import Any
import json

from app.agents.base import BaseAgent
from app.core.logging import get_logger
from app.services.compliance_service import _call_ollama, _parse_llm_json

logger = get_logger(__name__)

class TrendAnalysisAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "TrendAnalysisAgent"

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        docs = context.get("documents", [])
        if not docs:
            return {"error": "No documents provided to TrendAnalysisAgent."}
        
        docs_text = ""
        for d in docs:
            docs_text += f"--- Year: {d['year']} ---\n{d['content'][:6000]}\n\n"

        prompt = f"""You are an Expert Compliance Analyst. Analyze the compliance trends across the years.
        
CRITICAL INSTRUCTION:
Return ONLY valid JSON. No markdown. No explanations. No text before or after.

Required JSON format:
{{
    "quarterly_analysis": "Summary of quarterly trends within the years...",
    "annual_analysis": "Summary of year-over-year changes...",
    "five_year_analysis": "Summary of multi-year compliance evolution..."
}}

Documents:
{docs_text}
"""
        content = _call_ollama(prompt)
        parsed = _parse_llm_json(content)
        if not parsed:
            parsed = {
                "quarterly_analysis": "Failed to parse LLM response.",
                "annual_analysis": "Failed to parse LLM response.",
                "five_year_analysis": "Failed to parse LLM response."
            }
        return {"trend_analysis": parsed}

class RiskTrendAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "RiskTrendAgent"

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        docs = context.get("documents", [])
        if not docs:
            return {"error": "No documents provided to RiskTrendAgent."}
        
        docs_text = ""
        for d in docs:
            docs_text += f"--- Year: {d['year']} ---\n{d['content'][:6000]}\n\n"

        prompt = f"""You are an Expert Risk Assessor. Analyze how risks have evolved across the years.
        
CRITICAL INSTRUCTION:
Return ONLY valid JSON. No markdown. No explanations. No text before or after.

Required JSON format:
{{
    "risk_evolution_summary": "Detailed summary of how risks and vulnerabilities have evolved over the years..."
}}

Documents:
{docs_text}
"""
        content = _call_ollama(prompt)
        parsed = _parse_llm_json(content)
        if not parsed:
            parsed = {"risk_evolution_summary": "Failed to parse LLM response."}
        return {"risk_trend": parsed}

class ExecutiveSummaryAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "ExecutiveSummaryAgent"

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        docs = context.get("documents", [])
        if not docs:
            return {"error": "No documents provided to ExecutiveSummaryAgent."}
        
        docs_text = ""
        for d in docs:
            docs_text += f"--- Year: {d['year']} ---\n{d['content'][:6000]}\n\n"

        prompt = f"""You are a Chief Compliance Officer. Summarize the overall compliance maturity progression.
        
CRITICAL INSTRUCTION:
Return ONLY valid JSON. No markdown. No explanations. No text before or after.

Required JSON format:
{{
    "executive_summary": "Executive summary of the multi-year compliance audit...",
    "compliance_maturity_progression": "How the organization's compliance posture has matured..."
}}

Documents:
{docs_text}
"""
        content = _call_ollama(prompt)
        parsed = _parse_llm_json(content)
        if not parsed:
            parsed = {
                "executive_summary": "Failed to parse LLM response.",
                "compliance_maturity_progression": "Failed to parse LLM response."
            }
        return {"executive_summary": parsed}
