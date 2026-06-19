"""
Compliance analysis service.
Handles LLM-based compliance analysis and structured report generation.
Includes robust JSON parsing to handle LLM output variability.
"""

import json
import re
from datetime import datetime

from app.core.config import settings
from app.core.logging import get_logger
from app.core.llm import generate_response
from app.services.retrieval import (
    get_sampled_regulation_chunks,
    retrieve_top_k_for_text,
)

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Internal parsing helpers
# ---------------------------------------------------------------------------

def _clean_json_string(text: str) -> str:
    """Perform common cleanups on JSON strings from LLMs."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    text = text.strip()
    text = re.sub(r'(?<!:)\/\/.*$', '', text, flags=re.MULTILINE)
    text = re.sub(r',\s*\}', '}', text)
    text = re.sub(r',\s*\]', ']', text)
    return text


def _extract_first_json_object(text: str) -> str:
    """Extract the first {...} block from a text that may contain prose."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    return match.group(0) if match else text


def _parse_llm_json(content: str) -> dict | None:
    """
    Attempt to parse JSON from an LLM response using direct cleaned parse
    or regex object extraction.
    """
    cleaned = _clean_json_string(content)
    try:
        return json.loads(cleaned)
    except (json.JSONDecodeError, TypeError):
        pass

    try:
        first_obj = _extract_first_json_object(content)
        cleaned_obj = _clean_json_string(first_obj)
        return json.loads(cleaned_obj)
    except (json.JSONDecodeError, TypeError):
        pass

    return None


def _heuristic_parse(text: str) -> dict | None:
    """Heuristically extract issues and recommendations if JSON parsing fails."""
    issues = []
    recommendations = []
    is_issues = True
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        lower_line = line.lower()
        if "recommendation" in lower_line:
            is_issues = False
            continue
        if "issue" in lower_line or "violation" in lower_line:
            is_issues = True
            continue
        match = re.match(r'^(?:[-*+•]|\d+\.|\"|\')\s*(.*)$', line)
        if match:
            item = match.group(1).strip().rstrip('",. ')
            if item:
                if is_issues:
                    issues.append(item)
                else:
                    recommendations.append(item)
    if issues or recommendations:
        return {
            "violation": len(issues) > 0,
            "issues": issues,
            "recommendations": recommendations if recommendations else ["Remediate compliance issues."]
        }
    return None


# ---------------------------------------------------------------------------
# Scoring utilities
# ---------------------------------------------------------------------------

def assess_risk(issues: list) -> str:
    """
    Classify risk level based on issue count.
    High: >= 5 issues
    Medium: 2–4 issues
    Low: 0–1 issues
    """
    count = len(issues)
    if count >= 5:
        return "High"
    if count >= 2:
        return "Medium"
    return "Low"


def calculate_compliance_score(issues: list) -> int:
    """
    Calculate a compliance score (0–100).
    Deducts 10 points per issue; floor is 0.
    """
    return max(100 - len(issues) * 10, 0)


# ---------------------------------------------------------------------------
# LLM calls
# ---------------------------------------------------------------------------

def _call_llm(prompt: str) -> str:
    """Execute an LLM chat completion and return the response content."""
    return generate_response(prompt=prompt)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def analyze_compliance(
    policy_chunks: list[str],
    regulation_chunks: list[str],
) -> str:
    """
    Generate a narrative compliance analysis comparing policy to regulation.
    Returns free-text suitable for the analysis endpoint.
    """
    policy_text = "\n\n".join(policy_chunks)
    regulation_text = "\n\n".join(regulation_chunks)

    prompt = f"""You are a Senior Enterprise Compliance Auditor.

Analyze the company policy against the applicable regulation.

Identify:
1. Specific compliance violations
2. Missing regulatory requirements
3. Policy gaps or ambiguities
4. Areas of full compliance

Structure your response with clear section headings.
Be specific, citing relevant sections where possible.

Regulation:
{regulation_text}

Company Policy:
{policy_text}"""

    content = _call_llm(prompt)
    logger.info("Narrative compliance analysis generated.")
    return content


def generate_compliance_report(selected_files: list[str] | None = None) -> dict:
    """
    Generate a structured compliance report dict via LLM using a Batched Map-Reduce approach.
    """
    regulation_chunks = get_sampled_regulation_chunks(settings.MAX_REGULATION_CHUNKS, selected_files)

    if not regulation_chunks:
        return {
            "violation": False,
            "issues": ["No regulation chunks found to analyze."],
            "recommendations": ["Upload a regulation document first."],
            "structured_violations": []
        }

    batch_size = settings.REGULATION_BATCH_SIZE
    all_issues = []
    all_recommendations = []

    map_calls_count = 0
    retrieved_chunks_count = len(regulation_chunks)
    estimated_prompt_tokens = 0
    estimated_completion_tokens = 0

    # Map Phase
    for i in range(0, len(regulation_chunks), batch_size):
        batch = regulation_chunks[i:i + batch_size]
        map_calls_count += 1
        
        batch_prompt_parts = []
        for reg_chunk in batch:
            policy_chunks = retrieve_top_k_for_text(reg_chunk, "policy", settings.TOP_K_POLICY_CHUNKS, selected_files)
            retrieved_chunks_count += len(policy_chunks)
            policy_text = "\n---\n".join(policy_chunks)
            batch_prompt_parts.append(f"Regulation:\n{reg_chunk}\n\nRelevant Policy:\n{policy_text}")
            
        combined_context = "\n\n=== NEXT REQUIREMENT ===\n\n".join(batch_prompt_parts)
        
        prompt = f"""You are a Compliance Auditor. Analyze the following regulatory requirements against the retrieved policy sections.
Identify any compliance violations or missing requirements.

CRITICAL INSTRUCTION: Return ONLY valid JSON matching this schema:
{{
    "issues": ["Specific violation description 1"],
    "recommendations": ["Actionable recommendation 1"]
}}

{combined_context}"""
        
        estimated_prompt_tokens += len(prompt) // 4
        content = _call_llm(prompt)
        estimated_completion_tokens += len(content) // 4
        
        parsed = _parse_llm_json(content)
        if parsed:
            all_issues.extend(parsed.get("issues", []))
            all_recommendations.extend(parsed.get("recommendations", []))

    # Reduce Phase
    reduce_prompt = f"""You are a Senior Compliance Auditor.
Merge and deduplicate the following compliance findings into a final, cohesive structured report.

CRITICAL INSTRUCTION: Return ONLY valid JSON. No markdown.
Required JSON format:
{{
    "violation": true,
    "issues": ["Specific issue description 1"],
    "recommendations": ["Actionable recommendation 1"],
    "structured_violations": [
        {{
            "violation_type": "Access Control",
            "severity": "Critical",
            "department": "IT",
            "regulation_category": "Access Security",
            "description": "Specific issue description 1"
        }}
    ]
}}

Raw Issues: {json.dumps(all_issues)}
Raw Recommendations: {json.dumps(all_recommendations)}"""

    estimated_prompt_tokens += len(reduce_prompt) // 4
    final_content = _call_llm(reduce_prompt)
    estimated_completion_tokens += len(final_content) // 4
    reduce_calls_count = 1

    parsed = _parse_llm_json(final_content)
    if parsed is None:
        logger.warning("JSON parsing failed. Attempting heuristic list parsing...")
        parsed = _heuristic_parse(final_content)

    if parsed is None:
        logger.error("All JSON parse strategies failed.")
        parsed = {
            "violation": True,
            "issues": ["AI model returned unparseable or malformed compliance report structure."],
            "recommendations": ["Re-run the audit/analysis or verify the model configuration."]
        }

    # Normalise structure
    parsed.setdefault("issues", [])
    parsed.setdefault("recommendations", [])
    parsed.setdefault("violation", len(parsed["issues"]) > 0)
    parsed.setdefault("structured_violations", [])

    # Heuristic fallback if structured_violations is missing
    if not parsed.get("structured_violations") and parsed.get("issues"):
        for issue in parsed["issues"]:
            issue_lower = issue.lower()
            
            # Severity detection
            severity = "Medium"
            if any(kw in issue_lower for kw in ["critical", "mfa", "encryption", "credentials"]):
                severity = "Critical"
            elif any(kw in issue_lower for kw in ["high", "password", "access", "unauthorized"]):
                severity = "High"
            elif any(kw in issue_lower for kw in ["low", "minor", "version", "formatting"]):
                severity = "Low"
                
            # Type detection
            v_type = "Other"
            if any(kw in issue_lower for kw in ["mfa", "auth", "login", "password", "privilege"]):
                v_type = "Access Control"
            elif any(kw in issue_lower for kw in ["encrypt", "aes", "ssl", "tls", "rest", "transit"]):
                v_type = "Data Encryption"
            elif any(kw in issue_lower for kw in ["audit", "log", "history", "record"]):
                v_type = "Audit Logging"
            elif any(kw in issue_lower for kw in ["privacy", "gdpr", "personal", "pii"]):
                v_type = "Data Privacy"
                
            # Department detection
            dept = "General"
            if any(kw in issue_lower for kw in ["it", "system", "administrator", "network"]):
                dept = "IT"
            elif any(kw in issue_lower for kw in ["finance", "billing", "payment"]):
                dept = "Finance"
            elif any(kw in issue_lower for kw in ["hr", "employee", "staff"]):
                dept = "HR"

            parsed["structured_violations"].append({
                "violation_type": v_type,
                "severity": severity,
                "department": dept,
                "regulation_category": "Compliance Standards",
                "description": issue
            })

    # Enrich with computed fields
    parsed["risk"] = assess_risk(parsed["issues"])
    parsed["compliance_score"] = calculate_compliance_score(parsed["issues"])
    parsed["violation_count"] = len(parsed["issues"])
    parsed["audit_timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    parsed["auditor"] = "Compliance AI Auditor"
    
    # Append metrics
    parsed["metrics"] = {
        "map_calls_count": map_calls_count,
        "reduce_calls_count": reduce_calls_count,
        "retrieved_chunks_count": retrieved_chunks_count,
        "estimated_prompt_tokens": estimated_prompt_tokens,
        "estimated_completion_tokens": estimated_completion_tokens
    }

    logger.info(
        f"Report generated: risk={parsed['risk']} "
        f"score={parsed['compliance_score']} "
        f"violations={parsed['violation_count']} "
        f"map_calls={map_calls_count} reduce_calls={reduce_calls_count}"
    )
    return parsed
