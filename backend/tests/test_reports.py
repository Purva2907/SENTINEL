import pytest
from fastapi.testclient import TestClient
import os
import sys
import uuid

# Add backend to path so we can import app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app

# Configure isolated environment for tests
os.environ["JWT_SECRET"] = "test_secret_do_not_use_in_prod"
os.environ["MONGO_URL"] = "mongodb://invalid-host-for-tests:27017"
os.environ["SQLITE_DB_PATH"] = "test_sentinel_reports.db"

@pytest.fixture
def client(tmp_path):
    db_path = tmp_path / "test_sentinel_reports.db"
    os.environ["SQLITE_DB_PATH"] = str(db_path)
    
    with TestClient(app) as client:
        yield client

def test_report_upload_flow(client):
    # 1. Register & login user
    test_email = f"rep_{uuid.uuid4()}@example.com"
    client.post("/api/auth/register", json={
        "email": test_email,
        "password": "securepassword",
        "name": "Forensic Inspector",
        "role": "investigator"
    })
    token = client.post("/api/auth/login", json={
        "email": test_email,
        "password": "securepassword"
    }).json().get("access_token")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Test rejection of non-image file
    invalid_file = {'file': ('notes.txt', b'some text content', 'text/plain')}
    res_inv = client.post("/api/reports/upload", files=invalid_file, headers=headers)
    assert res_inv.status_code == 400
    
    # 3. Upload valid sample image
    sample_path = os.path.join(os.path.dirname(__file__), "..", "demo", "samples", "demo_document_1.jpg")
    if not os.path.exists(sample_path):
        pytest.skip("Sample demo document not found")
        
    with open(sample_path, "rb") as f:
        files = {'file': ('demo_document_1.jpg', f, 'image/jpeg')}
        data = {
            'title': 'Intake Test Passport',
            'description': 'Automated test of direct report intake'
        }
        res_upload = client.post("/api/reports/upload", files=files, data=data, headers=headers)
        
    assert res_upload.status_code == 200
    upload_data = res_upload.json()
    assert upload_data["status"] == "success"
    assert "report" in upload_data
    assert "case" in upload_data
    report = upload_data["report"]
    report_id = report["id"]
    readable_report_id = report["report_id"]
    assert readable_report_id.startswith("RPT-")
    
    # 4. List reports and verify enriched metadata
    res_list = client.get("/api/reports", headers=headers)
    assert res_list.status_code == 200
    reports = res_list.json().get("reports", [])
    assert len(reports) >= 1
    found = next((r for r in reports if r["id"] == report_id), None)
    assert found is not None
    assert found["case_title"] == "Intake Test Passport"
    assert "risk_score" in found
    assert "classification" in found
    
    # 5. Download the generated PDF
    res_download = client.get(f"/api/reports/{report_id}/download", headers=headers)
    assert res_download.status_code == 200
    assert res_download.headers["content-type"] == "application/pdf"
    assert len(res_download.content) > 0
    assert res_download.content[:4] == b"%PDF"
