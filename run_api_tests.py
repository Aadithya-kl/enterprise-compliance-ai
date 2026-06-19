import requests
import json

base_url = "http://127.0.0.1:8000/api/v1"

print("--- Testing Issue 1: Compliance Report ---")
try:
    res = requests.post(f"{base_url}/compliance/report", json={"selected_files": ["Enterprise Security Policy"]})
    print(res.status_code, res.text)
except Exception as e:
    print(e)

print("\n--- Testing Issue 2: Ask Question ---")
try:
    res = requests.post(f"{base_url}/documents/query", json={"question": "What is the policy?", "selected_files": ["Enterprise Security Policy"]})
    print(res.status_code, res.text)
except Exception as e:
    print(e)

print("\n--- Testing Issue 3: Trend Intelligence ---")
try:
    res = requests.get(f"{base_url}/analytics/trends")
    print(res.status_code, res.text)
except Exception as e:
    print(e)

print("\n--- Testing Issue 4: Risk Analytics ---")
try:
    res = requests.post(f"{base_url}/compliance/risk", json={"selected_files": ["Enterprise Security Policy"]})
    print(res.status_code, res.text)
except Exception as e:
    print(e)

