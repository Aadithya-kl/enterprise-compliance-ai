import ollama
import json
import re
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def _strip_markdown_fences(text: str) -> str:
    """
    Strip markdown code fences from LLM output so json.loads() succeeds.
    Handles ```json ... ``` and plain ``` ... ``` wrappers.
    """
    # Remove ```json ... ``` or ``` ... ``` wrappers
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _extract_json_from_text(text: str) -> str:
    """
    Best-effort extraction of the first JSON object from an LLM response
    that may include surrounding explanation text.
    """
    # Try to find the first {...} block
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return match.group(0)
    return text


def analyze_compliance(policy_documents, regulation_documents):
    """
    Generate a free-text compliance analysis narrative using Llama3 via Ollama.
    """
    policy_text = "\n\n".join(policy_documents)
    regulation_text = "\n\n".join(regulation_documents)

    prompt = f"""
You are an Enterprise Compliance Auditor.

Compare the company policy against the regulation.

Find:
1. Compliance violations
2. Missing requirements
3. Policy weaknesses

Return your findings in a professional format.

Regulation:
{regulation_text}

Company Policy:
{policy_text}
"""

    try:
        response = ollama.chat(
            model="llama3",
            messages=[{"role": "user", "content": prompt}]
        )
        content = response["message"]["content"]
        logger.info("Compliance analysis completed successfully")
        return content
    except Exception as e:
        logger.error(f"Ollama analyze_compliance error: {e}")
        raise RuntimeError(f"LLM call failed: {e}") from e


def assess_risk(issues: list) -> str:
    """
    Determine risk level based on number of compliance issues.
    High: 5+, Medium: 2-4, Low: 0-1
    """
    total = len(issues)
    if total >= 5:
        return "High"
    elif total >= 2:
        return "Medium"
    return "Low"


def calculate_compliance_score(issues: list) -> int:
    """
    Calculate a compliance score (0–100) based on issue count.
    Each issue deducts 10 points; minimum is 0.
    """
    score = 100 - (len(issues) * 10)
    return max(score, 0)


def generate_compliance_report(
    policy_documents: list,
    regulation_documents: list
) -> dict:
    """
    Generate a structured compliance report as a dict.
    Instructs Llama3 to return JSON only, then parses and enriches the result.
    Returns {"raw_response": <text>} if JSON parsing fails entirely.
    """
    policy_text = "\n\n".join(policy_documents)
    regulation_text = "\n\n".join(regulation_documents)

    prompt = f"""
You are an Enterprise Compliance Auditor.

IMPORTANT:
Return ONLY valid JSON. No explanations. No markdown. No text before or after.

Required Format:

{{
    "violation": true,
    "issues": [
        "Issue 1",
        "Issue 2"
    ],
    "recommendations": [
        "Recommendation 1",
        "Recommendation 2"
    ]
}}

Regulation:
{regulation_text}

Policy:
{policy_text}
"""

    try:
        response = ollama.chat(
            model="llama3",
            messages=[{"role": "user", "content": prompt}]
        )
        content = response["message"]["content"]
    except Exception as e:
        logger.error(f"Ollama generate_compliance_report error: {e}")
        raise RuntimeError(f"LLM call failed: {e}") from e

    logger.debug(f"Raw Ollama response:\n{content}")

    # --- Robust JSON parsing with fallback strategies ---
    parsed = None

    # Strategy 1: Direct parse
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        pass

    # Strategy 2: Strip markdown fences then parse
    if parsed is None:
        try:
            parsed = json.loads(_strip_markdown_fences(content))
        except json.JSONDecodeError:
            pass

    # Strategy 3: Extract first JSON object from text then parse
    if parsed is None:
        try:
            parsed = json.loads(_extract_json_from_text(content))
        except json.JSONDecodeError:
            pass

    # All strategies failed — return raw response flag
    if parsed is None:
        logger.error(
            f"Failed to parse LLM JSON response. Raw content: {content[:500]}"
        )
        return {"raw_response": content}

    # Validate expected keys exist
    if "issues" not in parsed:
        parsed["issues"] = []
    if "recommendations" not in parsed:
        parsed["recommendations"] = []
    if "violation" not in parsed:
        parsed["violation"] = len(parsed["issues"]) > 0

    # Enrich with computed fields
    parsed["risk"] = assess_risk(parsed["issues"])
    parsed["compliance_score"] = calculate_compliance_score(parsed["issues"])
    parsed["violation_count"] = len(parsed["issues"])
    parsed["audit_timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    parsed["auditor"] = "Compliance AI Auditor"

    logger.info(
        f"Compliance report generated: risk={parsed['risk']}, "
        f"score={parsed['compliance_score']}, "
        f"violations={parsed['violation_count']}"
    )
    return parsed