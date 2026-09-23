import pytest
from fastapi.testclient import TestClient
import os
import sys
import uuid

# Add backend to path so we can import app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app

os.environ["JWT_SECRET"] = "test_secret_do_not_use_in_prod"
os.environ["MONGO_URL"] = "mongodb://invalid-host-for-tests:27017"
os.environ["SQLITE_DB_PATH"] = "test_sentinel_profile.db"

@pytest.fixture
def client(tmp_path):
    db_path = tmp_path / "test_sentinel_profile.db"
    os.environ["SQLITE_DB_PATH"] = str(db_path)
    
    with TestClient(app) as client:
        yield client

def test_profile_and_password_flow(client):
    test_email = f"agent_{uuid.uuid4()}@sentinel.org"
    password = "InitialPassword123"
    
    # 1. Register
    reg_res = client.post("/api/auth/register", json={
        "name": "Special Agent Vance",
        "email": test_email,
        "password": password
    })
    assert reg_res.status_code == 200
    
    # 2. Login
    login_res = client.post("/api/auth/login", json={
        "email": test_email,
        "password": password
    })
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 3. Get /me and verify full hydrated profile
    me_res = client.get("/api/auth/me", headers=headers)
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["name"] == "Special Agent Vance"
    assert me_data["email"] == test_email
    assert me_data["role"] == "investigator"
    assert me_data["created_at"] is not None
    assert "badge_number" in me_data
    
    # 4. Update Profile (including custom avatar icon)
    update_res = client.put("/api/auth/profile", json={
        "name": "Supervisory Agent Vance",
        "department": "Cyber Document Intelligence Unit",
        "badge_number": "CDIU-007",
        "avatar": "icon:fa-user-shield|linear-gradient(135deg, #1DCED8, #0099B8)"
    }, headers=headers)
    assert update_res.status_code == 200
    up_user = update_res.json()["user"]
    assert up_user["name"] == "Supervisory Agent Vance"
    assert up_user["department"] == "Cyber Document Intelligence Unit"
    assert up_user["badge_number"] == "CDIU-007"
    assert up_user["avatar"] == "icon:fa-user-shield|linear-gradient(135deg, #1DCED8, #0099B8)"
    
    # Verify through /me again
    me_after = client.get("/api/auth/me", headers=headers).json()
    assert me_after["name"] == "Supervisory Agent Vance"
    assert me_after["department"] == "Cyber Document Intelligence Unit"
    assert me_after["badge_number"] == "CDIU-007"
    assert me_after["avatar"] == "icon:fa-user-shield|linear-gradient(135deg, #1DCED8, #0099B8)"
    
    # 5. Change Password - Negative test (wrong current password)
    bad_pw_res = client.post("/api/auth/change-password", json={
        "current_password": "WrongPassword",
        "new_password": "NewSecurePassword456"
    }, headers=headers)
    assert bad_pw_res.status_code == 400
    assert "incorrect" in bad_pw_res.json()["detail"].lower()
    
    # 6. Change Password - Positive test
    good_pw_res = client.post("/api/auth/change-password", json={
        "current_password": password,
        "new_password": "NewSecurePassword456"
    }, headers=headers)
    assert good_pw_res.status_code == 200
    
    # 7. Verify login with new password works
    new_login_res = client.post("/api/auth/login", json={
        "email": test_email,
        "password": "NewSecurePassword456"
    })
    assert new_login_res.status_code == 200
    assert "access_token" in new_login_res.json()
    
    # 8. Verify old password no longer works
    old_login_res = client.post("/api/auth/login", json={
        "email": test_email,
        "password": password
    })
    assert old_login_res.status_code == 401
