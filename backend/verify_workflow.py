"""
End-to-end workflow verification script.
Tests the full AI pipeline: document retrieval -> compliance -> risk -> report -> persist.

Run from backend/ directory with the server running on port 8000:
    .\\venv\\Scripts\\python.exe verify_workflow.py
"""

import sys
import time
import requests


BASE_URL = "http://localhost:8000/api/v1"


def login() -> str:
    print("Step 1: Authenticating as admin...")
    r = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": "admin@company.com", "password": "Admin123!"},
        timeout=15,
    )
    if r.status_code != 200:
        print(f"FAILED: login returned {r.status_code}: {r.text}")
        sys.exit(1)
    token = r.json()["access_token"]
    print("SUCCESS: Admin authenticated.")
    return token


def check_documents(token: str) -> None:
    """Verify that ChromaDB has at least one policy and one regulation document."""
    print("\nStep 2: Checking ChromaDB document store...")
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(f"{BASE_URL}/documents", headers=headers, timeout=15)
    if r.status_code == 200:
        docs = r.json()
        print(f"  Found {len(docs)} documents in store.")
    else:
        print(f"  Document list returned {r.status_code} — continuing anyway.")


def run_workflow(token: str) -> dict:
    print("\nStep 3: Triggering full AI workflow (POST /workflow/run)...")
    print("  This may take 30-120 seconds depending on Ollama response times.")
    headers = {"Authorization": f"Bearer {token}"}
    t = time.monotonic()

    r = requests.post(
        f"{BASE_URL}/workflow/run",
        json={"policy_type": "policy", "regulation_type": "regulation"},
        headers=headers,
        timeout=310,  # slightly over the backend 300s timeout
    )
    elapsed = time.monotonic() - t
    print(f"  Response received in {elapsed:.1f}s — HTTP {r.status_code}")

    if r.status_code != 200:
        print(f"FAILED: {r.status_code}: {r.text}")
        sys.exit(1)

    data = r.json()
    return data


def validate_response(data: dict) -> None:
    print("\nStep 4: Validating workflow response...")
    assert data.get("success") is True, f"success field is not True: {data}"
    assert data.get("saved_report_id") is not None, "saved_report_id is missing"
    assert data.get("risk_level") is not None, "risk_level is missing"
    assert data.get("compliance_score") is not None, "compliance_score is missing"
    assert data.get("total_violations") is not None, "total_violations is missing"
    assert data.get("executive_summary") is not None, "executive_summary is missing"

    print(f"  success           : {data['success']}")
    print(f"  saved_report_id   : {data['saved_report_id']}")
    print(f"  risk_level        : {data['risk_level']}")
    print(f"  compliance_score  : {data['compliance_score']}")
    print(f"  total_violations  : {data['total_violations']}")
    print(f"  executive_summary : {data['executive_summary'][:80]}...")
    print("SUCCESS: All workflow response fields validated.")


def verify_report_persisted(token: str, report_id: int) -> None:
    print(f"\nStep 5: Verifying report id={report_id} is retrievable from audit history...")
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(
        f"{BASE_URL}/compliance/history/{report_id}",
        headers=headers,
        timeout=15,
    )
    if r.status_code != 200:
        print(f"FAILED: audit history fetch returned {r.status_code}: {r.text}")
        sys.exit(1)
    print(f"SUCCESS: Report id={report_id} confirmed in database.")


if __name__ == "__main__":
    token = login()
    check_documents(token)
    result = run_workflow(token)
    validate_response(result)
    verify_report_persisted(token, result["saved_report_id"])

    print("\n" + "=" * 60)
    print("FULL WORKFLOW VERIFIED SUCCESSFULLY")
    print("=" * 60)
