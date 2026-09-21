import pytest
from fastapi.testclient import TestClient
import os
import sys
import uuid

# Add backend to path so we can import app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app
from database import repository

# Configure isolated environment for tests
os.environ["JWT_SECRET"] = "test_secret_do_not_use_in_prod"
os.environ["MONGO_URL"] = "mongodb://invalid-host-for-tests:27017"  # Force SQLite fallback for test isolation
os.environ["SQLITE_DB_PATH"] = "test_sentinel.db"

@pytest.fixture
def client(tmp_path):
    # Setup isolated test DB in a temporary directory
    db_path = tmp_path / "test_sentinel.db"
    os.environ["SQLITE_DB_PATH"] = str(db_path)
    
    with TestClient(app) as client:
        yield client

def test_health_api(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "database" in data

def test_auth_flow(client):
    test_email = f"test_{uuid.uuid4()}@example.com"
    # 1. Register
    register_data = {
        "email": test_email,
        "password": "testpassword123",
        "name": "Test User",
        "role": "investigator"
    }
    response = client.post("/api/auth/register", json=register_data)
    assert response.status_code in [200, 201]
    
    # 2. Login
    login_data = {
        "email": test_email,
        "password": "testpassword123"
    }
    response = client.post("/api/auth/login", json=login_data)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    token = data["access_token"]
    
    # 3. Get /me
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/auth/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] is not None

def test_invalid_upload(client):
    # Test upload with invalid file type (txt)
    files = {'file': ('test.txt', b'this is a text file', 'text/plain')}
    response = client.post("/api/analyze", files=files, headers={"Authorization": "Bearer fake_token"})
    assert response.status_code in [400, 401] # 401 if token invalid, 400 if bad file

def test_analyze_demo_document(client):
    test_email = f"analyze_{uuid.uuid4()}@example.com"
    register_data = {"email": test_email, "password": "pass", "name": "Test", "role": "investigator"}
    client.post("/api/auth/register", json=register_data)
    login_data = {"email": test_email, "password": "pass"}
    token = client.post("/api/auth/login", json=login_data).json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    
    sample_path = os.path.join(os.path.dirname(__file__), "..", "demo", "samples", "demo_document_1.jpg")
    if os.path.exists(sample_path):
        with open(sample_path, "rb") as f:
            files = {'file': ('demo_document_1.jpg', f, 'image/jpeg')}
            response = client.post("/api/analyze", files=files, headers=headers)
            assert response.status_code == 200
            data = response.json()
            assert "data" in data
            assert "risk_score" in data["data"]
            assert 0 <= data["data"]["risk_score"] <= 100
            assert "classification" in data["data"]
    else:
        pytest.skip("Demo document not found")

def test_cases_api(client):
    test_email = f"case_{uuid.uuid4()}@example.com"
    register_data = {"email": test_email, "password": "pass", "name": "Test", "role": "investigator"}
    client.post("/api/auth/register", json=register_data)
    login_data = {"email": test_email, "password": "pass"}
    token = client.post("/api/auth/login", json=login_data).json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. List cases (should be empty for new user)
    response = client.get("/api/cases", headers=headers)
    assert response.status_code == 200
    assert len(response.json()["cases"]) == 0

    # 2. Create case
    case_data = {
        "title": "Test Case",
        "description": "Test Desc",
        "status": "Active",
        "analysis_data": {"risk_score": 85, "classification": "High Suspicion"}
    }
    response = client.post("/api/cases", json=case_data, headers=headers)
    assert response.status_code == 200
    created_case = response.json()["case"]
    case_id = created_case["id"]
    
    # 3. List cases (should be 1)
    response = client.get("/api/cases", headers=headers)
    assert len(response.json()["cases"]) == 1
    
    # 4. Get case
    response = client.get(f"/api/cases/{case_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["title"] == "Test Case"
    
    # 5. Add Note
    note_data = {"text": "This is a test note"}
    response = client.post(f"/api/cases/{case_id}/notes", json=note_data, headers=headers)
    assert response.status_code == 200
    
    # 6. Retrieve case to verify note
    response = client.get(f"/api/cases/{case_id}", headers=headers)
    notes = response.json().get("notes", [])
    assert len(notes) == 1
    assert notes[0]["text"] == "This is a test note"

def test_analytics_api(client):
    response = client.get("/api/analytics")
    assert response.status_code in [200, 401]
