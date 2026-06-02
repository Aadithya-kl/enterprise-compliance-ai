import ollama
import json
from datetime import datetime

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


def calculate_compliance_score(issues):

    total_issues = len(issues)

    score = 100 - (total_issues * 10)

    if score < 0:
        score = 0

    return score


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
    print("\n\n===== OLLAMA RESPONSE =====")
    print(content)
    print("===========================\n\n")

    try:

        report = json.loads(content)
        

        report["risk"] = assess_risk(
            report["issues"]
        )

        report["compliance_score"] = (
            calculate_compliance_score(
                report["issues"]
            )
        )

        report["violation_count"] = len(
            report["issues"]
        )

        report["audit_timestamp"] = (
            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        )

        report["auditor"] = ("Compliance AI Auditor")

        return report

    except Exception:

        return {
            "raw_response": content
        }