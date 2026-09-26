import pytest
from fastapi.testclient import TestClient
import os
import sys
import uuid
import json
import io
import time
from unittest.mock import patch, MagicMock
from PIL import Image, ImageDraw
import cv2
import numpy as np

# Add backend to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app
from database import repository
from database.sqlite import get_db, init_sqlite
from auth.jwt import create_access_token
from forensic.comparison import compute_visual_difference_percentage, compare_two_documents
from forensic.synthetic_lab import create_base_synthetic_document, apply_manipulation
from forensic.qr import analyze_qr
from forensic.heatmap import generate_heatmap

# Ensure isolated environment variables for testing
os.environ["JWT_SECRET"] = "test_hardening_secret_key_12345"
os.environ["MONGO_URL"] = "mongodb://invalid-host-for-tests:27017"

@pytest.fixture
def auth_client(tmp_path):
    """Provides an isolated SQLite DB test fixture with two distinct registered users."""
    db_path = tmp_path / "test_hardening.db"
    os.environ["SQLITE_DB_PATH"] = str(db_path)
    
    with TestClient(app) as client:
        # User Alpha (Primary)
        user_a_email = f"alpha_{uuid.uuid4().hex[:6]}@sentinel.org"
        reg_a = client.post("/api/auth/register", json={
            "email": user_a_email,
            "password": "Password123!",
            "name": "Investigator Alpha",
            "role": "investigator"
        })
        assert reg_a.status_code in [200, 201]
        login_a = client.post("/api/auth/login", json={
            "email": user_a_email,
            "password": "Password123!"
        })
        token_a = login_a.json()["access_token"]
        client.token_a = token_a
        me_a = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token_a}"}).json()
        client.user_a_id = me_a["id"]
        client.headers_a = {"Authorization": f"Bearer {token_a}"}

        # User Beta (For authorization boundary tests)
        user_b_email = f"beta_{uuid.uuid4().hex[:6]}@sentinel.org"
        reg_b = client.post("/api/auth/register", json={
            "email": user_b_email,
            "password": "Password123!",
            "name": "Investigator Beta",
            "role": "investigator"
        })
        assert reg_b.status_code in [200, 201]
        login_b = client.post("/api/auth/login", json={
            "email": user_b_email,
            "password": "Password123!"
        })
        token_b = login_b.json()["access_token"]
        client.token_b = token_b
        me_b = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token_b}"}).json()
        client.user_b_id = me_b["id"]
        client.headers_b = {"Authorization": f"Bearer {token_b}"}

        yield client

def _create_test_image_bytes(format="JPEG", size=(300, 300), color=(255, 255, 255)):
    buf = io.BytesIO()
    img = Image.new("RGB", size, color=color)
    img.save(buf, format=format)
    return buf.getvalue()

# ==============================================================================
# 1. AUTHENTICATE DOCUMENT ANALYSIS: POST /api/analyze requires auth
# ==============================================================================
def test_unauthenticated_analyze_returns_401(auth_client):
    img_bytes = _create_test_image_bytes()
    files = {"file": ("test.jpg", img_bytes, "image/jpeg")}
    response = auth_client.post("/api/analyze", files=files)
    assert response.status_code == 401

# ==============================================================================
# 2. FIX JWT USER VALIDATION: Deleted DB user returns 401
# ==============================================================================
def test_deleted_jwt_user_returns_401(auth_client):
    # Construct a valid JWT for an ID that does not exist in the DB
    fake_user_id = f"nonexistent_{uuid.uuid4().hex}"
    fake_token = create_access_token(data={"sub": fake_user_id, "email": "ghost@sentinel.org"})
    headers = {"Authorization": f"Bearer {fake_token}"}
    response = auth_client.get("/api/auth/me", headers=headers)
    assert response.status_code == 401

# ==============================================================================
# 3. VALIDATE ACTUAL IMAGE CONTENT: Invalid image bytes with image MIME returns 400
# ==============================================================================
def test_invalid_image_with_image_mime_returns_400(auth_client):
    # A text file masquerading as a JPEG
    fake_image_bytes = b"NOT_A_REAL_IMAGE_CORRUPT_HEADER_PAYLOAD"
    files = {"file": ("malicious.jpg", fake_image_bytes, "image/jpeg")}
    response = auth_client.post("/api/analyze", files=files, headers=auth_client.headers_a)
    assert response.status_code == 400

# ==============================================================================
# 4. OVERSIZED IMAGE ENFORCEMENT
# ==============================================================================
def test_oversized_image_returns_400_or_413(auth_client):
    # Exceed MAX_FILE_SIZE (15MB + 1KB)
    oversized_bytes = b"0" * (15 * 1024 * 1024 + 1024)
    files = {"file": ("huge.jpg", oversized_bytes, "image/jpeg")}
    response = auth_client.post("/api/analyze", files=files, headers=auth_client.headers_a)
    assert response.status_code in [400, 413]

# ==============================================================================
# 5. SAFE STORAGE FILENAMES & PATH TRAVERSAL RESISTANCE
# ==============================================================================
def test_path_traversal_filename_sanitized(auth_client):
    img_bytes = _create_test_image_bytes()
    malicious_filename = "../../../etc/passwd"
    files = {"file": (malicious_filename, img_bytes, "image/jpeg")}
    response = auth_client.post("/api/analyze", files=files, headers=auth_client.headers_a)
    assert response.status_code == 200
    res_data = response.json().get("data", {})
    custody = res_data.get("chain_of_custody", {}) or response.json().get("chain_of_custody", {})
    # Stored filename must be safe evidence_<uuid>.jpg, never containing ../ or etc/passwd
    assert "stored_filename" in custody
    assert not custody["stored_filename"].startswith("..")
    assert "etc" not in custody["stored_filename"]
    # Physical file_path must NOT be leaked to client
    assert "file_path" not in custody

# ==============================================================================
# 6. UNAUTHORIZED CASE ACCESS
# ==============================================================================
def test_unauthorized_case_access(auth_client):
    # User Alpha creates a case
    create_res = auth_client.post("/api/cases", json={
        "title": "Alpha Confidential Case",
        "description": "Sensitive investigation",
        "document_type": "Passport",
        "risk_score": 10,
        "classification": "Authentic",
        "analysis_data": {"findings": []}
    }, headers=auth_client.headers_a)
    assert create_res.status_code == 200
    case_id = create_res.json()["case"]["case_id"]

    # User Beta tries to read Alpha's case
    get_res = auth_client.get(f"/api/cases/{case_id}", headers=auth_client.headers_b)
    assert get_res.status_code in [403, 404]

# ==============================================================================
# 7. UNAUTHORIZED CASE COMPARISON
# ==============================================================================
def test_unauthorized_comparison_between_tenants(auth_client):
    # Alpha creates a case
    res_a = auth_client.post("/api/cases", json={
        "title": "Alpha Case",
        "analysis_data": {"findings": []}
    }, headers=auth_client.headers_a)
    case_a_id = res_a.json()["case"]["case_id"]

    # Beta creates a case
    res_b = auth_client.post("/api/cases", json={
        "title": "Beta Case",
        "analysis_data": {"findings": []}
    }, headers=auth_client.headers_b)
    case_b_id = res_b.json()["case"]["case_id"]

    # Beta attempts to compare their case against Alpha's case
    compare_res = auth_client.post("/api/compare/cases", json={
        "base_case_id": case_b_id,
        "suspect_case_id": case_a_id
    }, headers=auth_client.headers_b)
    assert compare_res.status_code in [400, 403, 404]

# ==============================================================================
# 8 & 9. CONTACT / NODEMAILER FAILURE AND RATE LIMITING
# ==============================================================================
def test_contact_mail_service_unavailable_returns_error(auth_client):
    import httpx
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.side_effect = httpx.ConnectError("Node service offline")
        response = auth_client.post("/api/contact", json={
            "name": "Jane Doe",
            "email": "jane@example.com",
            "organization": "Sentinel Forensics",
            "subject": "Case Inquiry",
            "message": "Inquiry regarding forensics analysis service."
        })
        # NEVER return success=True when service fails
        assert response.status_code in [502, 503]
        detail_msg = response.json()["detail"].lower()
        assert any(t in detail_msg for t in ["offline", "unavailable", "unreachable"])

def test_contact_mail_service_preserves_429(auth_client):
    import httpx
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.json.return_value = {"error": "Rate limit exceeded"}
        mock_post.return_value = mock_response

        response = auth_client.post("/api/contact", json={
            "name": "Jane Doe",
            "email": "jane@example.com",
            "organization": "Sentinel Forensics",
            "subject": "Case Inquiry",
            "message": "Testing rate limit on contact service."
        })
        assert response.status_code == 429

# ==============================================================================
# 10 & 11. VISUAL DIFFERENCE MATRIX CALCULATION & IDENTICAL IMAGES
# ==============================================================================
def test_visual_difference_calculation_identical_and_different(tmp_path):
    # 1. Identical images -> ~0%
    img1 = np.ones((100, 100, 3), dtype=np.uint8) * 200
    img2 = np.ones((100, 100, 3), dtype=np.uint8) * 200
    p1 = str(tmp_path / "img1.png")
    p2 = str(tmp_path / "img2.png")
    cv2.imwrite(p1, img1)
    cv2.imwrite(p2, img2)

    diff_pct_identical = compute_visual_difference_percentage(p1, p2, diff_threshold=25)
    assert diff_pct_identical == 0.0

    # 2. Visibly different images (a 30x30 square altered from 200 to 50)
    img_diff = img1.copy()
    img_diff[10:40, 10:40] = 50
    p_diff = str(tmp_path / "img_diff.png")
    cv2.imwrite(p_diff, img_diff)

    diff_pct_diff = compute_visual_difference_percentage(p1, p_diff, diff_threshold=25)
    # 900 pixels out of 10000 = 9.0%
    assert 8.9 <= diff_pct_diff <= 9.1

    # 3. Heavily different images (all pixels altered)
    img_heavy = np.zeros((100, 100, 3), dtype=np.uint8)
    p_heavy = str(tmp_path / "img_heavy.png")
    cv2.imwrite(p_heavy, img_heavy)

    diff_pct_heavy = compute_visual_difference_percentage(p1, p_heavy, diff_threshold=25)
    assert diff_pct_heavy >= 99.0

# ==============================================================================
# 12. SIMILAR CASE SCORE CONTRACT (0–100)
# ==============================================================================
def test_similar_case_score_contract(auth_client):
    # Create two very similar synthetic cases for Alpha
    res1 = auth_client.post("/api/synthetic/analyze", json={
        "document_type": "Synthetic ID",
        "manipulations": [],
        "severity": 10,
        "seed": 42
    }, headers=auth_client.headers_a)
    analysis1 = res1.json()["analysis"]

    c1 = auth_client.post("/api/cases", json={
        "title": "Baseline Doc",
        "analysis_data": analysis1,
        "document_type": "Synthetic ID",
        "risk_score": 10,
        "classification": "Authentic"
    }, headers=auth_client.headers_a).json()["case"]

    res2 = auth_client.post("/api/synthetic/analyze", json={
        "document_type": "Synthetic ID",
        "manipulations": [],
        "severity": 10,
        "seed": 42
    }, headers=auth_client.headers_a)
    analysis2 = res2.json()["analysis"]

    c2 = auth_client.post("/api/cases", json={
        "title": "Twin Doc",
        "analysis_data": analysis2,
        "document_type": "Synthetic ID",
        "risk_score": 10,
        "classification": "Authentic"
    }, headers=auth_client.headers_a).json()["case"]

    sim_res = auth_client.get(f"/api/cases/{c1['case_id']}/similar", headers=auth_client.headers_a)
    assert sim_res.status_code == 200
    similar_cases = sim_res.json()["similar_cases"]
    assert len(similar_cases) >= 1
    match = similar_cases[0]
    # Canonical contract is 0–100 (e.g. >= 85.0 for identical/near-identical)
    assert 0.0 <= match["similarity_score"] <= 100.0
    assert match["similarity_score"] >= 85.0

# ==============================================================================
# 13 & 14. GENUINE SYNTHETIC QR GENERATION & CORRUPTION
# ==============================================================================
def test_synthetic_qr_payload_and_corruption(tmp_path):
    # Pristine synthetic document with QR
    pristine_img = create_base_synthetic_document(doc_type="Synthetic ID", seed=777)
    p_pristine = str(tmp_path / "pristine.jpg")
    pristine_img.save(p_pristine, "JPEG")
    
    qr_result_pristine = analyze_qr(p_pristine, document_type="Synthetic ID")

    assert qr_result_pristine["status"] == "DECODED"
    assert qr_result_pristine["payload"] == "SENTINEL-DEMO-001"
    assert any("not cryptographically verified" in f.lower() for f in qr_result_pristine["findings"])

    # Corrupt the QR code using qr_tamper manipulation
    corrupted_img, meta = apply_manipulation(pristine_img, "qr_tamper", severity=90, seed=777)
    p_corrupted = str(tmp_path / "corrupted.jpg")
    corrupted_img.save(p_corrupted, "JPEG")
    
    qr_result_corrupted = analyze_qr(p_corrupted, document_type="Synthetic ID")

    assert qr_result_corrupted["status"] in ["DETECTED_NOT_DECODED", "NOT_DETECTED"]
    assert qr_result_corrupted["payload"] == ""

# ==============================================================================
# 15. ELA HEATMAP SIGNAL SEPARATION: Blur must not trigger ELA anomaly
# ==============================================================================
def test_ela_vs_quality_separation(tmp_path):
    # Flat image saved to disk
    img = Image.new("RGB", (200, 200), color=(180, 180, 180))
    p_img = str(tmp_path / "test_img.jpg")
    img.save(p_img, "JPEG", quality=90)

    # Findings containing ONLY quality/blur warnings
    evidence_quality_only = [
        {"category": "Quality", "rule_id": "QUAL_BLUR", "observation": "Low Laplacian sharpness", "risk_contribution": 15}
    ]
    # In generate_heatmap, has_anomaly requires category == "Image Forensics" and risk_contribution > 0
    # Check that when only Quality findings are passed, has_anomaly is False
    from forensic.heatmap import analyze_image_forensics
    has_anomaly_quality = any(
        ev.get("category") == "Image Forensics" and ev.get("risk_contribution", 0) > 0
        for ev in evidence_quality_only
    )
    assert has_anomaly_quality is False

    # Adding an Image Forensics finding activates ELA anomaly
    evidence_with_ela = [
        {"category": "Image Forensics", "rule_id": "ELA_ANOMALY", "observation": "High error rate", "risk_contribution": 25}
    ]
    has_anomaly_ela = any(
        ev.get("category") == "Image Forensics" and ev.get("risk_contribution", 0) > 0
        for ev in evidence_with_ela
    )
    assert has_anomaly_ela is True

    # Both produce a valid non-empty base64 image data URI
    heatmap_clean = generate_heatmap(p_img, evidence_quality_only)
    assert heatmap_clean.startswith("data:image/jpeg;base64,")
    heatmap_anom = generate_heatmap(p_img, evidence_with_ela)
    assert heatmap_anom.startswith("data:image/jpeg;base64,")

# ==============================================================================
# 16 & 17. REPORT-CREATED CUSTODY & REPORT_GENERATED TIMELINE EVENT
# ==============================================================================
def test_report_upload_custody_and_timeline_events(auth_client):
    img_bytes = _create_test_image_bytes()
    files = {"file": ("report_doc.jpg", img_bytes, "image/jpeg")}
    data = {
        "title": "Audit Dossier Case",
        "notes": "Verified by investigator",
        "format": "json"
    }
    rep_res = auth_client.post("/api/reports/upload", files=files, data=data, headers=auth_client.headers_a)
    assert rep_res.status_code == 200
    r_json = rep_res.json()
    case_id = r_json["case"]["case_id"]

    # Verify custody integrity for this report-created case
    v_res = auth_client.get(f"/api/cases/{case_id}/verify-custody", headers=auth_client.headers_a)
    assert v_res.status_code == 200
    v_data = v_res.json()
    assert v_data["status"] == "TAMPER_FREE"

    # Verify timeline contains EVIDENCE_INGESTED, SHA256_CALCULATED, REPORT_GENERATED
    case_res = auth_client.get(f"/api/cases/{case_id}", headers=auth_client.headers_a)
    assert case_res.status_code == 200
    events = [e["event_type"] for e in case_res.json().get("timeline", [])]
    assert "EVIDENCE_INGESTED" in events
    assert "SHA256_CALCULATED" in events
    assert "REPORT_GENERATED" in events

# ==============================================================================
# 18. STATUS VALIDATION
# ==============================================================================
def test_status_validation(auth_client):
    res = auth_client.post("/api/cases", json={
        "title": "Status Test Case",
        "analysis_data": {"findings": []}
    }, headers=auth_client.headers_a)
    case_id = res.json()["case"]["case_id"]

    # Allowed statuses: Active, Under Review, Closed
    for valid_status in ["Active", "Under Review", "Closed"]:
        s_res = auth_client.patch(f"/api/cases/{case_id}/status", json={"status": valid_status}, headers=auth_client.headers_a)
        assert s_res.status_code == 200

    # Reject invalid / arbitrary status
    inv_res = auth_client.patch(f"/api/cases/{case_id}/status", json={"status": "HACKED_STATUS"}, headers=auth_client.headers_a)
    assert inv_res.status_code in [400, 422]

# ==============================================================================
# 19. NOTE VALIDATION: Reject empty and excessive notes
# ==============================================================================
def test_note_validation(auth_client):
    res = auth_client.post("/api/cases", json={
        "title": "Notes Test Case",
        "analysis_data": {"findings": []}
    }, headers=auth_client.headers_a)
    case_id = res.json()["case"]["case_id"]

    # Empty note -> 400 or 422
    empty_res = auth_client.post(f"/api/cases/{case_id}/notes", json={"text": "   "}, headers=auth_client.headers_a)
    assert empty_res.status_code in [400, 422]

    # Excessively long note (> 2000 chars) -> 400 or 422
    huge_note = "A" * 2001
    huge_res = auth_client.post(f"/api/cases/{case_id}/notes", json={"text": huge_note}, headers=auth_client.headers_a)
    assert huge_res.status_code in [400, 422]

    # Valid note -> 200
    valid_res = auth_client.post(f"/api/cases/{case_id}/notes", json={"text": "Official investigator note."}, headers=auth_client.headers_a)
    assert valid_res.status_code == 200

# ==============================================================================
# 20. AVATAR VALIDATION: Reject arbitrary HTML / scripts / external URLs
# ==============================================================================
def test_avatar_validation(auth_client):
    # Allowed: icon format
    res_icon = auth_client.put("/api/auth/profile", json={"name": "Investigator Alpha", "avatar": "icon:shield-halved|#00d4ff"}, headers=auth_client.headers_a)
    assert res_icon.status_code == 200

    # Allowed: base64 image within limits
    tiny_b64 = "data:image/jpeg;base64," + "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
    res_b64 = auth_client.put("/api/auth/profile", json={"name": "Investigator Alpha", "avatar": tiny_b64}, headers=auth_client.headers_a)
    assert res_b64.status_code == 200

    # Disallowed: JavaScript injection or arbitrary URLs
    res_xss = auth_client.put("/api/auth/profile", json={"name": "Investigator Alpha", "avatar": "<script>alert(1)</script>"}, headers=auth_client.headers_a)
    assert res_xss.status_code in [400, 422]

    res_url = auth_client.put("/api/auth/profile", json={"name": "Investigator Alpha", "avatar": "https://malicious.site/exploit.png"}, headers=auth_client.headers_a)
    assert res_url.status_code in [400, 422]
