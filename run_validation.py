import sys
import os
import traceback
from dotenv import load_dotenv
from fastapi.testclient import TestClient

backend_dir = os.path.join(os.getcwd(), 'backend')
load_dotenv(os.path.join(backend_dir, '.env'))
sys.path.append(backend_dir)

from app.main import app
from app.core.dependencies import get_current_user

# Mock user for auth
class MockUser:
    id = "admin_user_id"
    is_admin = True
    role = "admin"

def override_get_current_user():
    return MockUser()

app.dependency_overrides[get_current_user] = override_get_current_user

client = TestClient(app)

print("=== TEST 1: ASK QUESTION ===")
res1 = client.post("/api/v1/documents/ask", json={
    "question": "What do these reports say?",
    "selected_files": []
})
print("Status:", res1.status_code)
if res1.status_code == 200:
    print("Success! Answer:", res1.json().get("answer")[:200] + "...")
else:
    print("Failed:", res1.text)

print("\n=== TEST 2: COMPLIANCE REPORT ===")
res2 = client.post("/api/v1/compliance/report", json={
    "selected_files": ["Enterprise Security Policy", "Annual Report 2023"]
})
print("Status:", res2.status_code)
if res2.status_code == 200:
    data = res2.json()
    print("Success! Risk:", data.get("risk"), "Score:", data.get("compliance_score"))
else:
    print("Failed:", res2.text)

print("\n=== TEST 3: RISK ANALYTICS ===")
res3 = client.post("/api/v1/compliance/risk", json={
    "selected_files": ["Enterprise Security Policy"]
})
print("Status:", res3.status_code)
if res3.status_code == 200:
    data = res3.json()
    print("Success! Risk:", data.get("risk"), "Score:", data.get("compliance_score"))
else:
    print("Failed:", res3.text)

print("\n=== TEST 4: TREND INTELLIGENCE ===")
res4 = client.get("/api/v1/analytics/trends")
print("Status:", res4.status_code)
if res4.status_code == 200:
    print("Success! AI Summary:", res4.json().get("ai_trend_summary"))
else:
    print("Failed:", res4.text)

