import ollama
import json


def analyze_compliance(
    policy_documents,
    regulation_documents
):

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

    response = ollama.chat(
        model="llama3",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return response["message"]["content"]


def assess_risk(issues):

    total = len(issues)

    if total >= 5:
        return "High"

    elif total >= 2:
        return "Medium"

    return "Low"


def generate_compliance_report(
    policy_documents,
    regulation_documents
):

    policy_text = "\n\n".join(policy_documents)

    regulation_text = "\n\n".join(regulation_documents)

    prompt = f"""
You are an Enterprise Compliance Auditor.

IMPORTANT:
Return ONLY valid JSON.
Do not include explanations.
Do not include markdown.
Do not include text before or after the JSON.

Required Format:

{{
    "violation": true,
    "risk": "High",
    "issues": [
        "Issue 1"
    ],
    "recommendations": [
        "Recommendation 1"
    ]
}}

Regulation:
{regulation_text}

Policy:
{policy_text}
"""

    response = ollama.chat(
        model="llama3",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    content = response["message"]["content"]

    try:

        report = json.loads(content)

        report["risk"] = assess_risk(
            report["issues"]
        )

        return report

    except Exception:

        return {
            "raw_response": content
        }