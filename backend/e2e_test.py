import sys
import json
import urllib.request
import urllib.error
import urllib.parse
from io import BytesIO

BASE_URL = "http://localhost:8000/api/v1"

def request(method, path, data=None, headers=None, files=None):
    url = BASE_URL + path
    if headers is None:
        headers = {}
        
    # We will use requests if installed, otherwise fallback to urllib
    try:
        import requests
        if files:
            resp = requests.request(method, url, data=data, headers=headers, files=files)
            return resp.status_code, resp.json() if resp.text else None
        else:
            if data and not isinstance(data, dict):
                resp = requests.request(method, url, data=data, headers=headers)
            else:
                resp = requests.request(method, url, json=data, headers=headers)
            return resp.status_code, resp.json() if resp.text else None
    except ImportError:
        print("requests module required")
        sys.exit(1)

def run_tests():
    print("--- STARTING END-TO-END VALIDATION ---")
    
    # 1. Auth Registration
    print("1. Testing Registration...")
    email = "test_user_e2e@example.com"
    pwd = "TestPassword123!"
    status, data = request("POST", "/auth/register", data={
        "email": email,
        "password": pwd,
        "full_name": "E2E Test User",
        "role": "auditor"
    })
    print(f"Register status: {status}")
    if status not in [201, 409]:
        print(f"FAILED: {data}")
    
    # 2. Auth Login
    print("2. Testing Login...")
    status, token_data = request("POST", "/auth/login", data={
        "email": email,
        "password": pwd
    })
    print(f"Login status: {status}")
    if status != 200:
        print(f"FAILED: {token_data}")
        return
        
    token = token_data["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}
    
    # 3. Test Me
    print("3. Testing /auth/me...")
    status, me_data = request("GET", "/auth/me", headers=auth_headers)
    print(f"Me status: {status}")
    if status != 200:
        print(f"FAILED: {me_data}")
        return

    # 4. Ingestion - Upload TXT
    print("4. Testing TXT Upload...")
    txt_content = b"This is a test policy document for compliance. It mandates regular audits."
    files = {'file': ('test_policy.txt', txt_content, 'text/plain')}
    status, upload_txt = request("POST", "/documents/upload?document_type=policy", headers=auth_headers, files=files)
    print(f"TXT Upload status: {status}")
    print(f"Response: {upload_txt}")
    
    # 5. Duplicate Upload
    print("5. Testing Duplicate Detection...")
    status, upload_txt_dup = request("POST", "/documents/upload?document_type=policy", headers=auth_headers, files=files)
    print(f"Duplicate Upload status: {status}")
    print(f"Response: {upload_txt_dup}")

    # 6. Ask Question (Global)
    print("6. Testing Ask Question (Global)...")
    status, ask_resp = request("POST", "/documents/ask", headers=auth_headers, data={
        "question": "What does the policy mandate?",
        "selected_files": []
    })
    print(f"Ask Global status: {status}")
    print(f"Response: {ask_resp}")
    
    # 7. Ask Question (Scoped)
    print("7. Testing Ask Question (Scoped)...")
    if upload_txt and "filename" in upload_txt:
        file_name = upload_txt["filename"]
        status, ask_scoped = request("POST", "/documents/ask", headers=auth_headers, data={
            "question": "What does the policy mandate?",
            "selected_files": [file_name]
        })
        print(f"Ask Scoped status: {status}")
        print(f"Response: {ask_scoped}")
        
    # 8. Compliance Report (Quick)
    print("8. Testing Compliance Report (Quick)...")
    status, report_quick = request("POST", "/compliance/report", headers=auth_headers, data={
        "title": "Test Report",
        "scope": "Quick assessment",
        "selected_files": []
    })
    print(f"Report status: {status}")
    print(f"Response: {report_quick}")

    print("--- TESTS COMPLETED ---")

if __name__ == "__main__":
    run_tests()
