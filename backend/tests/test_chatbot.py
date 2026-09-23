import pytest
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["JWT_SECRET"] = "test_secret_do_not_use_in_prod"
os.environ["MONGO_URL"] = "mongodb://invalid-host-for-tests:27017"
os.environ["SQLITE_DB_PATH"] = "test_chatbot_sentinel.db"

from app import app
from auth.jwt import create_access_token
from fastapi.testclient import TestClient

@pytest.fixture
def client(tmp_path):
    db_path = tmp_path / "test_chatbot_sentinel.db"
    os.environ["SQLITE_DB_PATH"] = str(db_path)
    with TestClient(app) as test_client:
        yield test_client

@pytest.fixture
def auth_token():
    return create_access_token(data={"sub": "testuser", "id": "user123"})

@pytest.fixture
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}

def test_unauthenticated_chat(client):
    response = client.post("/api/chat/", json={"message": "Hello"})
    assert response.status_code == 401

def test_empty_message(client, auth_headers):
    response = client.post("/api/chat/", json={"message": "   "}, headers=auth_headers)
    assert response.status_code == 400
    assert "Empty" in response.json()["detail"]

def test_fallback_no_context(client, auth_headers):

    # Without context, it should fallback properly
    response = client.post("/api/chat/", json={"message": "Why was this flagged?"}, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    assert data["source"] in ["llm", "fallback"]
    assert isinstance(data["response"], str)
    assert "upload" in data["response"].lower() or "active" in data["response"].lower()

def test_fallback_with_context(client, auth_headers):
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

def test_structured_response(client, auth_headers):
    response = client.post("/api/chat", json={"message": "Hi", "context": {}}, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "success" in data
    assert "response" in data
    assert isinstance(data["response"], str)
    assert len(data["response"]) > 0
    assert "source" in data

def test_chat_invalid_schema_returns_422(client, auth_headers):
    # Missing required message field
    response = client.post("/api/chat", json={"invalid_field": 123}, headers=auth_headers)
    assert response.status_code == 422

def test_direct_local_fallback_no_openai():
    """Verify local fallback function generates helpful SENTINEL forensic answers directly."""
    from chatbot.fallback import generate_fallback_response
    res = generate_fallback_response("What does this risk score mean?", {"risk_score": 75, "classification": "High Suspicion"})
    assert isinstance(res, str)
    assert len(res.strip()) > 0
    assert "75" in res or "risk" in res.lower()

    # Empty context fallback
    res_empty = generate_fallback_response("What does this risk score mean?", {})
    assert isinstance(res_empty, str)
    assert len(res_empty.strip()) > 0
    assert "active" in res_empty.lower() or "context" in res_empty.lower() or "document" in res_empty.lower()

def test_chat_case_aware_with_valid_case_id(client):
    """Verify chatbot endpoint loads case data when case_id is passed and handles invalid case_id."""
    import uuid
    # Register unique user
    email = f"chat_tester_{uuid.uuid4().hex[:8]}@example.com"
    client.post("/api/auth/register", json={
        "email": email, "password": "pass", "name": "Chat Tester", "role": "investigator"
    })
    login_resp = client.post("/api/auth/login", json={"email": email, "password": "pass"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create a case with unique evidence
    case_payload = {
        "title": "Suspect Passport Case",
        "description": "Passport with altered MRZ",
        "document_type": "Passport",
        "status": "Active",
        "risk_score": 88,
        "classification": "High Suspicion",
        "analysis_data": {
            "risk_score": 88,
            "classification": "High Suspicion",
            "document_type": "Passport",
            "evidence": [
                {"title": "MRZ Checksum Failure", "finding": "Secondary check digit invalid", "risk_contribution": 50}
            ]
        }
    }
    create_resp = client.post("/api/cases", json=case_payload, headers=headers)
    assert create_resp.status_code == 200
    created = create_resp.json()["case"]
    uuid_id = created["id"]
    human_case_id = created["case_id"]

    # 1. Chat with UUID case_id
    resp_uuid = client.post("/api/chat", json={
        "message": "Explain the risk assessment for this case.",
        "case_id": uuid_id
    }, headers=headers)
    assert resp_uuid.status_code == 200
    uuid_data = resp_uuid.json()
    assert uuid_data["success"] is True
    assert "88" in uuid_data["response"] or "suspicion" in uuid_data["response"].lower()

    # 2. Chat with human-readable case_id (e.g. SC-2026-XXXX)
    resp_human = client.post("/api/chat", json={
        "message": "What evidence contributed most to the score?",
        "case_id": human_case_id
    }, headers=headers)
    assert resp_human.status_code == 200
    human_data = resp_human.json()
    assert human_data["success"] is True
    assert "mrz" in human_data["response"].lower() or "checksum" in human_data["response"].lower() or "evidence" in human_data["response"].lower()

    # 3. Invalid case_id returns 404
    resp_missing = client.post("/api/chat", json={
        "message": "Explain this case",
        "case_id": "non-existent-case-id"
    }, headers=headers)
    assert resp_missing.status_code == 404
    assert "not found" in resp_missing.json()["detail"].lower()

def test_thank_you_polite_response(client, auth_headers):
    """Verify chatbot responds warmly and helpfully to thank you pleasantries."""
    for thanks_phrase in ["Thank you so much!", "thanks", "appreciate it", "great work"]:
        resp = client.post("/api/chat", json={"message": thanks_phrase}, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert any(w in data["response"].lower() for w in ["welcome", "pleasure", "assist", "forensic", "standby"])

def test_cross_case_inquiry_and_comparison(client):
    """Verify chatbot recognizes another case when mentioned by name or ID, and can compare cases."""
    import uuid
    email = f"multi_case_{uuid.uuid4().hex[:8]}@example.com"
    client.post("/api/auth/register", json={
        "email": email, "password": "pass", "name": "Cross Case Investigator", "role": "investigator"
    })
    login_resp = client.post("/api/auth/login", json={"email": email, "password": "pass"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Case 1: Aadhaar
    c1 = client.post("/api/cases", json={
        "title": "Aadhaar Card Verification",
        "document_type": "Aadhaar Card",
        "risk_score": 52,
        "classification": "Review Required",
        "analysis_data": {"risk_score": 52, "classification": "Review Required", "document_type": "Aadhaar Card"}
    }, headers=headers).json()["case"]

    # Case 2: Passport
    c2 = client.post("/api/cases", json={
        "title": "Suspect Interpol Passport",
        "document_type": "Passport",
        "risk_score": 88,
        "classification": "High Suspicion",
        "analysis_data": {
            "risk_score": 88, 
            "classification": "High Suspicion", 
            "document_type": "Passport",
            "evidence": [{"title": "MRZ Mismatch", "finding": "Checksum altered", "risk_contribution": 45}]
        }
    }, headers=headers).json()["case"]

    # 1. Ask about the other case by name while on Case 1
    resp_other = client.post("/api/chat", json={
        "message": "What about the Passport case?",
        "case_id": c1["id"]
    }, headers=headers)
    assert resp_other.status_code == 200
    res_text = resp_other.json()["response"].lower()
    assert "passport" in res_text or "88" in res_text

    # 2. Ask to compare Case 1 and Case 2
    resp_compare = client.post("/api/chat", json={
        "message": f"Compare this case with {c2['case_id']}",
        "case_id": c1["id"]
    }, headers=headers)
    assert resp_compare.status_code == 200
    comp_text = resp_compare.json()["response"]
    assert "Comparison" in comp_text or "comparison" in comp_text.lower()
    assert "88" in comp_text or "52" in comp_text

    # 3. Ask to list all cases
    resp_list = client.post("/api/chat", json={
        "message": "List my cases please"
    }, headers=headers)
    assert resp_list.status_code == 200
    list_text = resp_list.json()["response"]
    assert "Aadhaar" in list_text or "Passport" in list_text

def test_summary_on_tokens_or_request(client, auth_headers):
    """Verify chatbot provides a comprehensive dossier summary when requested."""
    resp = client.post("/api/chat", json={
        "message": "give me summary of this case",
        "context": {
            "risk_score": 65,
            "classification": "Review Required",
            "document_type": "PAN Card",
            "evidence": [{"title": "Font Mismatch", "finding": "Disparate kerning", "risk_contribution": 25}]
        }
    }, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "summary" in data["response"].lower() or "dossier" in data["response"].lower() or "verdict" in data["response"].lower()


