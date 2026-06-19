import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from fastapi.testclient import TestClient
from app.main import app
from app.core.dependencies import get_current_user

# Mock the current user to bypass JWT validation during tests
from datetime import datetime, timezone

class MockUser:
    id = 1
    email = "admin@example.com"
    full_name = "Admin User"
    role = "admin"
    is_active = True
    created_at = datetime.now(timezone.utc)

    role = "admin"

def mock_get_current_user():
    return MockUser()

app.dependency_overrides[get_current_user] = mock_get_current_user

client = TestClient(app)

def test_health():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert "database" in data
    assert "llm" in data
    assert "qdrant" in data

def test_auth_me():
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "admin@example.com"

@pytest.fixture(autouse=True)
def mock_gemini(monkeypatch):
    import app.core.llm
    mock_resp = MagicMock()
    mock_resp.text = '{"executive_summary": "Mocked", "risk_level": "LOW", "risk_score": 10, "findings": [], "total_violations": 0}'
    if hasattr(app.core.llm, "client") and app.core.llm.client:
        monkeypatch.setattr(app.core.llm.client.models, "generate_content", lambda *a, **kw: mock_resp)

def test_ask_question():
    payload = {
        "question": "What does the policy say?",
        "selected_files": ["Data Privacy and Information Protection Regulation.pdf"]
    }
    response = client.post("/api/v1/documents/ask", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "diagnostics" in data

@patch("app.api.v1.workflow.run_compliance_workflow")
def test_workflow_run(mock_workflow):
    mock_workflow.return_value = {
        "success": True,
        "executive_summary": "Mocked E2E Workflow",
        "risk_level": "LOW",
        "risk_score": 10,
        "findings": [],
        "total_violations": 0,
        "retrieved_documents": []
    }
    payload = {
        "policy_type": "policy",
        "regulation_type": "regulation",
        "selected_files": ["Data Privacy and Information Protection Regulation.pdf", "Global GDPR and Privacy Accountability Regulation Standard"]
    }
    response = client.post("/api/v1/workflow/run", json=payload)
    if response.status_code == 422:
        print("Workflow validation failed:", response.json())
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "executive_summary" in data
    assert "risk_level" in data

def test_analytics_trends():
    response = client.get("/api/v1/analytics/trends")
    assert response.status_code == 200
    data = response.json()
    assert "trends" in data or "compliance_score_trend" in data

@patch("app.api.v1.analytics.run_query_router")
def test_analytics_query(mock_router):
    mock_router.return_value = {
        "route": "rag_question",
        "content": "Mocked response",
        "saved_report_id": None
    }
    payload = {"query": "Summarize risk trends"}
    response = client.post("/api/v1/analytics/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
