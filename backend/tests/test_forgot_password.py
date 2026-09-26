"""
Automated Test Suite for SENTINEL Secure Forgot & Reset Password Flow
Tests:
- Anti-enumeration generic responses
- Cryptographic SHA-256 token hashing (no raw token in DB)
- 15-minute token expiration & rejection of expired tokens
- Single-use token enforcement
- Invalidation of previous tokens upon new request
- Password complexity enforcement
- Invalidation of old credentials and successful login with new password
- Safe handling of mail service failures
- Rate limiting protection (max 3 per 15 mins)
- Repository compatibility (SQLite & MongoDB)
"""

import pytest
import secrets
import hashlib
import datetime
import uuid
import os
import sys
import httpx
import asyncio
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app
from database.repository import (
    create_user, get_user_by_email, get_user_by_id,
    create_password_reset_token, get_password_reset_token,
    invalidate_user_reset_tokens, consume_password_reset_token,
    update_user_password, backend as db_backend
)
from database.sqlite import get_db as get_sqlite_conn
from auth.jwt import get_password_hash
from api.auth import clear_reset_rate_limits

client = TestClient(app)

@pytest.fixture(autouse=True)
def reset_rate_limits():
    """Ensure clean rate limiting state before every test."""
    clear_reset_rate_limits()
    yield
    clear_reset_rate_limits()

@pytest.fixture
def test_user():
    """Create a unique test user in the active database."""
    unique_suffix = uuid.uuid4().hex[:8]
    email = f"officer.{unique_suffix}@sentinel-test.org"
    raw_pass = "InitialPass2026!"
    hashed_pass = get_password_hash(raw_pass)
    # create_user is async
    import asyncio
    user = asyncio.run(create_user(
        name=f"Investigator {unique_suffix}",
        email=email,
        password_hash=hashed_pass
    ))
    return {
        "user": user,
        "email": email,
        "raw_pass": raw_pass
    }

def test_forgot_password_existing_email(test_user):
    """
    When an account exists, a one-time token is created in the DB as SHA-256 hash,
    and a generic message is returned without leaking information.
    """
    mock_post = AsyncMock()
    mock_post.return_value = httpx.Response(200, json={"success": True, "message": "Email sent"})

    with patch("httpx.AsyncClient.post", mock_post):
        res = client.post("/api/auth/forgot-password", json={"email": test_user["email"]})

    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "If an account exists" in data["message"]

    # Verify mail service was called with the reset link
    assert mock_post.called
    call_args = mock_post.call_args
    payload = call_args.kwargs.get("json") or call_args[1].get("json")
    assert payload["email"] == test_user["email"]
    assert "token=" in payload["resetUrl"]

    # Extract raw token from resetUrl
    raw_token = payload["resetUrl"].split("token=")[1]
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    # Verify DB stores the hash, NOT the raw token
    import asyncio
    db_token = asyncio.run(get_password_reset_token(token_hash))
    assert db_token is not None
    assert db_token["user_id"] == test_user["user"]["id"]
    assert db_token["used"] is False

    # Check that raw_token does not exist anywhere in SQLite
    conn = get_sqlite_conn()
    cursor = conn.execute("SELECT * FROM password_reset_tokens WHERE token_hash = ?", (raw_token,))
    assert cursor.fetchone() is None
    conn.close()

def test_forgot_password_nonexistent_email():
    """
    Nonexistent emails must receive the exact same response without triggering an email.
    Prevents account enumeration.
    """
    fake_email = f"ghost.{uuid.uuid4().hex[:8]}@nowhere.com"
    mock_post = AsyncMock()

    with patch("httpx.AsyncClient.post", mock_post):
        res = client.post("/api/auth/forgot-password", json={"email": fake_email})

    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "If an account exists" in data["message"]
    # Mail service must NOT be called for nonexistent accounts
    assert not mock_post.called

def test_generic_response_anti_enumeration(test_user):
    """
    Confirm response schemas for existing and nonexistent emails are strictly identical.
    """
    mock_post = AsyncMock(return_value=httpx.Response(200, json={"success": True}))
    with patch("httpx.AsyncClient.post", mock_post):
        res_real = client.post("/api/auth/forgot-password", json={"email": test_user["email"]})
        clear_reset_rate_limits()
        res_fake = client.post("/api/auth/forgot-password", json={"email": "nonexistent@sentinel.org"})

    assert res_real.status_code == res_fake.status_code == 200
    assert res_real.json() == res_fake.json()

def test_expired_token_rejected(test_user):
    """
    A token with an expires_at timestamp in the past must be rejected.
    """
    raw_token = secrets.token_urlsafe(48)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    past_iso = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%SZ")

    import asyncio
    asyncio.run(create_password_reset_token(test_user["user"]["id"], token_hash, past_iso))

    res = client.post("/api/auth/reset-password", json={
        "token": raw_token,
        "new_password": "NewSecurePass2026!"
    })

    assert res.status_code == 400
    assert "expired" in res.json()["detail"].lower()

def test_token_single_use_enforcement(test_user):
    """
    A token can only be consumed once. A second attempt must fail.
    """
    raw_token = secrets.token_urlsafe(48)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    future_iso = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=15)).strftime("%Y-%m-%dT%H:%M:%SZ")

    import asyncio
    asyncio.run(create_password_reset_token(test_user["user"]["id"], token_hash, future_iso))

    # First reset: must succeed
    res1 = client.post("/api/auth/reset-password", json={
        "token": raw_token,
        "new_password": "BrandNewPass2026!"
    })
    assert res1.status_code == 200
    assert res1.json()["success"] is True

    # Second reset with same token: must fail
    res2 = client.post("/api/auth/reset-password", json={
        "token": raw_token,
        "new_password": "AnotherNewPass2026!"
    })
    assert res2.status_code == 400
    assert "already been used" in res2.json()["detail"].lower()

def test_previous_token_invalidated_on_new_request(test_user):
    """
    When a new reset request is made, any previous unused token for that user is invalidated.
    """
    mock_post = AsyncMock(return_value=httpx.Response(200, json={"success": True}))
    tokens = []

    def capture_call(*args, **kwargs):
        payload = kwargs.get("json")
        t = payload["resetUrl"].split("token=")[1]
        tokens.append(t)
        return httpx.Response(200, json={"success": True})

    mock_post.side_effect = capture_call

    with patch("httpx.AsyncClient.post", mock_post):
        # Request 1
        res1 = client.post("/api/auth/forgot-password", json={"email": test_user["email"]})
        assert res1.status_code == 200

        # Request 2
        res2 = client.post("/api/auth/forgot-password", json={"email": test_user["email"]})
        assert res2.status_code == 200

    assert len(tokens) == 2
    old_token, new_token = tokens[0], tokens[1]

    # Attempt reset with old token -> must fail (invalidated)
    res_old = client.post("/api/auth/reset-password", json={
        "token": old_token,
        "new_password": "FreshPassword2026!"
    })
    assert res_old.status_code == 400
    assert "already been used" in res_old.json()["detail"].lower()

    # Attempt reset with new token -> must succeed
    res_new = client.post("/api/auth/reset-password", json={
        "token": new_token,
        "new_password": "FreshPassword2026!"
    })
    assert res_new.status_code == 200

def test_full_password_reset_and_login_lifecycle(test_user):
    """
    Full end-to-end verification:
    1. Confirm initial password works for login
    2. Forgot password request -> token generated
    3. Reset password with new valid password
    4. Verify old password no longer works
    5. Verify new password successfully logs in
    """
    # 1. Login with initial password
    login_old = client.post("/api/auth/login", json={
        "email": test_user["email"],
        "password": test_user["raw_pass"]
    })
    assert login_old.status_code == 200
    assert "access_token" in login_old.json()

    # 2. Forgot password
    captured_token = None
    def capture_token(*args, **kwargs):
        nonlocal captured_token
        captured_token = kwargs.get("json")["resetUrl"].split("token=")[1]
        return httpx.Response(200, json={"success": True})

    with patch("httpx.AsyncClient.post", side_effect=capture_token):
        res = client.post("/api/auth/forgot-password", json={"email": test_user["email"]})
        assert res.status_code == 200

    assert captured_token is not None

    # 3. Reset password
    new_password = "SuperSecure#Forensics2026"
    reset_res = client.post("/api/auth/reset-password", json={
        "token": captured_token,
        "new_password": new_password
    })
    assert reset_res.status_code == 200
    assert reset_res.json()["success"] is True

    # 4. Old password fails
    fail_login = client.post("/api/auth/login", json={
        "email": test_user["email"],
        "password": test_user["raw_pass"]
    })
    assert fail_login.status_code == 401

    # 5. New password succeeds
    success_login = client.post("/api/auth/login", json={
        "email": test_user["email"],
        "password": new_password
    })
    assert success_login.status_code == 200
    assert "access_token" in success_login.json()

def test_weak_password_validation(test_user):
    """
    Validate that weak passwords failing complexity requirements return 422 Unprocessable Entity.
    """
    raw_token = secrets.token_urlsafe(48)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    future_iso = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=15)).strftime("%Y-%m-%dT%H:%M:%SZ")

    import asyncio
    asyncio.run(create_password_reset_token(test_user["user"]["id"], token_hash, future_iso))

    weak_passwords = [
        "short1!",              # Under 8 chars
        "nouppercase123!",       # Missing uppercase
        "NOLOWERCASE123!",       # Missing lowercase
        "NoNumberSpecial!",      # Missing number
        "NoSpecialChar12345"     # Missing special character
    ]

    for weak_pwd in weak_passwords:
        res = client.post("/api/auth/reset-password", json={
            "token": raw_token,
            "new_password": weak_pwd
        })
        assert res.status_code == 422, f"Expected 422 for weak password '{weak_pwd}', got {res.status_code}"

def test_invalid_token_rejected():
    """
    Completely bogus token returns 400.
    """
    res = client.post("/api/auth/reset-password", json={
        "token": "bogus-nonexistent-token-1234567890",
        "new_password": "ValidPassword2026!"
    })
    assert res.status_code == 400
    assert "Invalid or expired" in res.json()["detail"]

def test_mail_service_unavailable_handled(test_user):
    """
    If the Nodemailer microservice is offline or errors, return 503 rather than claiming success.
    """
    with patch("httpx.AsyncClient.post", side_effect=httpx.ConnectError("Connection refused")):
        res = client.post("/api/auth/forgot-password", json={"email": test_user["email"]})
        assert res.status_code == 503
        assert "currently offline" in res.json()["detail"]

def test_rate_limiting_forgot_password(test_user):
    """
    Submitting more than 3 reset requests within the window triggers HTTP 429.
    """
    mock_post = AsyncMock(return_value=httpx.Response(200, json={"success": True}))
    with patch("httpx.AsyncClient.post", mock_post):
        # 1st request -> ok
        assert client.post("/api/auth/forgot-password", json={"email": test_user["email"]}).status_code == 200
        # 2nd request -> ok
        assert client.post("/api/auth/forgot-password", json={"email": test_user["email"]}).status_code == 200
        # 3rd request -> ok
        assert client.post("/api/auth/forgot-password", json={"email": test_user["email"]}).status_code == 200
        # 4th request -> 429 Too Many Requests
        res4 = client.post("/api/auth/forgot-password", json={"email": test_user["email"]})
        assert res4.status_code == 429
        assert "Rate limit exceeded" in res4.json()["detail"]

def test_repository_mongodb_branch_logic():
    """
    Test MongoDB repository branch code using an AsyncMock database object to verify
    full MongoDB compatibility.
    """
    async def _run():
        import database.repository as repo
        original_backend = repo.backend
        mock_mongo = AsyncMock()

        # Setup simulated collection
        mock_coll = AsyncMock()
        mock_mongo.password_reset_tokens = mock_coll
        fake_doc = {
            "_id": "507f1f77bcf86cd799439011",
            "id": "mock-token-uuid",
            "user_id": "mock-user-123",
            "token_hash": "mock-hash-abc",
            "expires_at": "2026-09-26T15:00:00Z",
            "used": False,
            "created_at": "2026-09-26T14:45:00Z"
        }
        mock_coll.find_one.return_value = fake_doc

        try:
            repo.backend = 'mongodb'
            with patch("database.repository.get_mongo_db", return_value=mock_mongo):
                # 1. create_password_reset_token
                created = await repo.create_password_reset_token(
                    user_id="user-999",
                    token_hash="hash-999",
                    expires_at="2026-09-26T16:00:00Z"
                )
                assert created["user_id"] == "user-999"
                assert mock_coll.insert_one.called

                # 2. get_password_reset_token
                retrieved = await repo.get_password_reset_token("mock-hash-abc")
                assert retrieved is not None
                assert retrieved["id"] == "mock-token-uuid"
                assert retrieved["used"] is False

                # 3. invalidate_user_reset_tokens
                await repo.invalidate_user_reset_tokens("user-999")
                assert mock_coll.update_many.called

                # 4. consume_password_reset_token
                await repo.consume_password_reset_token("mock-hash-abc")
                assert mock_coll.update_one.called

        finally:
            repo.backend = original_backend

    asyncio.run(_run())

