import pytest
import re
from playwright.sync_api import Page, expect

# Assuming Vite runs on port 5174
BASE_URL = "http://localhost:5174"

def mock_auth(page: Page):
    """Intercept auth requests and mock a logged-in session."""
    page.on("console", lambda msg: print(f"Browser console: {msg.text}"))
    page.on("requestfailed", lambda req: print(f"Request failed: {req.url} - {req.failure}"))
    
    # Catch-all to prevent un-mocked endpoints from returning 401 and redirecting to login
    page.route(re.compile(r".*/api/v1/.*"), lambda route: route.fulfill(status=200, json={"items": [], "data": [], "results": []}))
    
    # Dashboard specific endpoints to prevent React crashes
    page.route(re.compile(r".*/api/v1/dashboard/risk-distribution"), lambda route: route.fulfill(status=200, json=[]))
    page.route(re.compile(r".*/api/v1/dashboard/stats"), lambda route: route.fulfill(status=200, json={}))
    page.route(re.compile(r".*/api/v1/compliance/history.*"), lambda route: route.fulfill(status=200, json=[]))
    page.route(re.compile(r".*/api/v1/mcp/stats"), lambda route: route.fulfill(status=200, json={"status": "inactive"}))
    
    page.route(re.compile(r".*/api/v1/auth/me"), lambda route: route.fulfill(
        status=200,
        json={"id": 1, "email": "admin@example.com", "full_name": "Admin User", "role": "admin", "is_active": True}
    ))
    page.route(re.compile(r".*/api/v1/health"), lambda route: route.fulfill(
        status=200,
        json={"backend": "healthy", "database": "healthy", "qdrant": "healthy", "llm": "healthy", "supabase": "healthy"}
    ))

def test_login_to_dashboard(page: Page):
    """Scenario 1: Login -> Dashboard loads"""
    mock_auth(page)
    
    # Go to login page
    page.goto(f"{BASE_URL}/login")
    
    # Fill login form
    page.fill('input[type="email"]', "admin@example.com")
    page.fill('input[type="password"]', "password123")
    
    # Mock login endpoint
    page.route(re.compile(r".*/api/v1/auth/login"), lambda route: route.fulfill(
        status=200,
        json={"access_token": "mocked-token", "token_type": "bearer"}
    ))
    
    # Click login button
    page.click('button[type="submit"]')
    
    # Assert navigation to dashboard
    expect(page).to_have_url(BASE_URL + "/")
    expect(page.locator("text=System Health")).to_be_visible()

def test_upload_policy(page: Page):
    """Scenario 2: Upload Policy -> Ingestion success"""
    mock_auth(page)
    page.goto(f"{BASE_URL}/upload")
    
    # Mock upload endpoint
    page.route(re.compile(r".*/api/v1/documents/upload.*"), lambda route: route.fulfill(
        status=201,
        json={
            "filename": "test-policy.pdf",
            "document_type": "policy",
            "drive_file_id": "mock-drive",
            "drive_upload_status": "uploaded",
            "drive_web_view_link": "https://mock.link",
            "extracted_chars": 1000,
            "qdrant_chunks": 5
        }
    ))
    
    # Interact with UI (Assuming dropzone and type selector exist)
    # We can use fileChooser to mock file upload
    with page.expect_file_chooser() as fc_info:
        page.locator('input[type="file"]').click()
    file_chooser = fc_info.value
    # Create a dummy file in memory for Playwright to upload
    file_chooser.set_files(
        files=[{"name": "test-policy.pdf", "mimeType": "application/pdf", "buffer": b"dummy content"}]
    )
    
    page.select_option('select', 'policy')
    page.click('button:has-text("Upload")')
    
    # Verify success toast or UI update
    expect(page.locator("text=Upload Successful")).to_be_visible()

def test_ask_question(page: Page):
    """Scenario 3: Ask Question -> Answer displayed"""
    mock_auth(page)
    
    # Mock indexed files
    page.route(re.compile(r".*/api/v1/documents/indexed-files"), lambda route: route.fulfill(
        status=200,
        json={"files": [{"filename": "test-policy.pdf", "document_type": "policy"}]}
    ))
    
    page.goto(f"{BASE_URL}/qa")
    
    # Mock question submission
    page.route(re.compile(r".*/api/v1/documents/ask"), lambda route: route.fulfill(
        status=200,
        json={
            "question": "What is the policy?",
            "answer": "This is a mocked answer from the UI test.",
            "sources": [{"filename": "test-policy.pdf", "confidence": 99.5, "chunks_used": 1, "sections": ["Overview"]}],
            "diagnostics": {"retrieval_mode": "full_knowledge_base"}
        }
    ))
    
    # Fill question and submit
    page.fill('textarea', "What is the policy?")
    page.click('button:has-text("Ask Agent")')
    
    # Verify answer rendered
    expect(page.locator("text=This is a mocked answer from the UI test.")).to_be_visible()

def test_generate_compliance_report(page: Page):
    """Scenario 4: Generate Compliance Report -> Report generated"""
    mock_auth(page)
    
    page.route("**/api/v1/documents/indexed-files", lambda route: route.fulfill(
        status=200,
        json={"files": [{"filename": "test-policy.pdf", "document_type": "policy"}, {"filename": "reg.pdf", "document_type": "regulation"}]}
    ))
    
    page.goto(f"{BASE_URL}/compliance")
    
    page.route(re.compile(r".*/api/v1/documents/analyze"), lambda route: route.fulfill(
        status=200,
        json={
            "report_id": 99,
            "policy_type": "policy",
            "regulation_type": "regulation",
            "compliance_score": 85,
            "overall_status": "Compliant",
            "executive_summary": "Mocked report summary."
        }
    ))
    
    page.click('button:has-text("Generate Report")')
    expect(page.locator("text=Mocked report summary.")).to_be_visible()

def test_run_full_workflow(page: Page):
    """Scenario 5: Run Full Workflow -> Workflow completes"""
    mock_auth(page)
    
    page.route("**/api/v1/documents/indexed-files", lambda route: route.fulfill(
        status=200,
        json={"files": []}
    ))
    
    page.goto(f"{BASE_URL}/compliance")
    
    page.route(re.compile(r".*/api/v1/workflow/run"), lambda route: route.fulfill(
        status=200,
        json={
            "success": True,
            "message": "Complete",
            "audit_report_id": 1,
            "executive_summary": "Mocked full workflow",
            "risk_level": "LOW",
            "risk_score": 10,
            "total_violations": 0,
            "retrieved_documents": []
        }
    ))
    
    page.click('button:has-text("Run Full Workflow")')
    expect(page.locator("text=Mocked full workflow")).to_be_visible()

def test_trend_intelligence(page: Page):
    """Scenario 6: Trend Intelligence Query -> Analytics rendered"""
    mock_auth(page)
    page.goto(f"{BASE_URL}/analytics")
    
    page.route(re.compile(r".*/api/v1/analytics/trends"), lambda route: route.fulfill(
        status=200,
        json={"compliance_score_trend": [], "top_violations": [], "risk_score_trend": []}
    ))
    
    page.route(re.compile(r".*/api/v1/analytics/query"), lambda route: route.fulfill(
        status=200,
        json={
            "success": True,
            "route": "trend_analysis",
            "content": "Mocked trend analysis response"
        }
    ))
    
    page.fill('input[placeholder*="Ask anything"]', "Trend over time")
    page.click('button:has-text("Analyze")')
    
    expect(page.locator("text=Mocked trend analysis response")).to_be_visible()
