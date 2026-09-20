import pytest
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fastapi.testclient import TestClient
from app import app
from auth.jwt import create_access_token

client = TestClient(app)

@pytest.fixture
def auth_token():
    return create_access_token(data={"sub": "testuser", "id": "user123"})

@pytest.fixture
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}

def test_unauthenticated_chat():
    response = client.post("/api/chat/", json={"message": "Hello"})
    assert response.status_code == 401

def test_empty_message(auth_headers):
    response = client.post("/api/chat/", json={"message": "   "}, headers=auth_headers)
    assert response.status_code == 400
    assert "Empty" in response.json()["detail"]

def test_fallback_no_context(auth_headers):
    # Without context, it should fallback properly
    response = client.post("/api/chat/", json={"message": "Why was this flagged?"}, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    assert data["source"] in ["llm", "fallback"]
    assert isinstance(data["response"], str)
    assert "upload" in data["response"].lower() or "active" in data["response"].lower()

def test_fallback_with_context(auth_headers):
    # Using fallback explicitly for a specific question with context
    context = {
        "risk_score": 85,
        "classification": "High Suspicion",
        "evidence": [
            {"title": "Typography Mismatch", "finding": "Inconsistent fonts.", "risk_contribution": 40}
        ]
    }
    response = client.post("/api/chat/", json={"message": "What is the strongest evidence?", "context": context}, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    # It might use LLM or fallback, but the response must refer to typography
    assert "typography" in data["response"].lower() or "fonts" in data["response"].lower()

def test_structured_response(auth_headers):
    response = client.post("/api/chat/", json={"message": "Hi", "context": {}}, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "success" in data
    assert "response" in data
    assert "source" in data
