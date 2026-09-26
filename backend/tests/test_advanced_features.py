import pytest
from fastapi.testclient import TestClient
import os
import sys
import uuid
import json
import numpy as np
import cv2

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app
from database import repository
from forensic.fingerprint import (
    extract_document_fingerprint,
    calculate_cosine_similarity,
    find_shared_forensic_signals
)
from forensic.synthetic_lab import (
    generate_synthetic_document,
    apply_manipulations,
    SUPPORTED_MANIPULATIONS
)
from forensic.comparison import generate_visual_diff_heatmap, compare_ocr_texts, compare_two_documents

# Configure isolated environment for tests
os.environ["JWT_SECRET"] = "test_secret_advanced_features"
os.environ["MONGO_URL"] = "mongodb://invalid-host-for-tests:27017"

@pytest.fixture
def auth_client(tmp_path):
    db_path = tmp_path / "test_advanced_features.db"
    os.environ["SQLITE_DB_PATH"] = str(db_path)
    
    with TestClient(app) as client:
        # Register and login user A
        user_email = f"analyst_{uuid.uuid4().hex[:6]}@sentinel.org"
        client.post("/api/auth/register", json={
            "email": user_email,
            "password": "SecurePassword123!",
            "name": "Forensic Analyst Alpha",
            "role": "investigator"
        })
        login_res = client.post("/api/auth/login", json={
            "email": user_email,
            "password": "SecurePassword123!"
        })
        token_a = login_res.json()["access_token"]
        client.headers_a = {"Authorization": f"Bearer {token_a}"}

        # Register and login user B (for unauthorized case testing)
        user_b_email = f"analyst_b_{uuid.uuid4().hex[:6]}@sentinel.org"
        client.post("/api/auth/register", json={
            "email": user_b_email,
            "password": "SecurePassword123!",
            "name": "Forensic Analyst Beta",
            "role": "investigator"
        })
        login_res_b = client.post("/api/auth/login", json={
            "email": user_b_email,
            "password": "SecurePassword123!"
        })
        token_b = login_res_b.json()["access_token"]
        client.headers_b = {"Authorization": f"Bearer {token_b}"}

        yield client

# ==============================================================================
# FEATURE 1: EVIDENCE CHAIN OF CUSTODY TESTS
# ==============================================================================
def test_chain_of_custody_full_lifecycle(auth_client, tmp_path):
    """Test SHA-256 generation, persistence, TAMPER_FREE, INTEGRITY_BREACH, and UNAVAILABLE."""
    # 1. Ingest via synthetic generation & analyze
    analyze_res = auth_client.post("/api/synthetic/analyze", json={
        "document_type": "Synthetic ID",
        "manipulations": [],
        "severity": 50,
        "seed": 101
    }, headers=auth_client.headers_a)
    assert analyze_res.status_code == 200
    res_data = analyze_res.json()
    analysis = res_data["analysis"]

    assert "chain_of_custody" in analysis
    custody = analysis["chain_of_custody"]
    assert custody["analysis_version"] == "2.1.0"
    assert custody["sha256_hash"] is not None
    assert len(custody["sha256_hash"]) == 64
    stored_hash = custody["sha256_hash"]

    # 2. Create Case
    case_res = auth_client.post("/api/cases", json={
        "title": "Chain of Custody Dossier",
        "description": "Validation of evidence immutability",
        "analysis_data": analysis,
        "document_type": "Synthetic ID",
        "risk_score": analysis.get("risk_score", 0),
        "classification": analysis.get("classification", "Authentic")
    }, headers=auth_client.headers_a)
    assert case_res.status_code == 200
    case_obj = case_res.json()["case"]
    case_id = case_obj["case_id"]

    # 3. Verify Custody -> Should be TAMPER_FREE
    verify_res = auth_client.get(f"/api/cases/{case_id}/verify-custody", headers=auth_client.headers_a)
    assert verify_res.status_code == 200
    v_data = verify_res.json()
    assert v_data["success"] is True
    assert v_data["status"] == "TAMPER_FREE"
    assert v_data["stored_sha256"] == stored_hash
    assert v_data["current_sha256"] == stored_hash

    # 4. Tamper with the underlying stored file to test INTEGRITY_BREACH
    stored_filepath = case_obj.get("file_path")
    if not stored_filepath:
        import asyncio
        db_case = asyncio.run(repository.get_case(case_obj.get("user_id") or "user123", case_obj.get("id") or case_id))
        stored_filepath = db_case.get("file_path") if db_case else None
    assert stored_filepath and os.path.exists(stored_filepath)
    with open(stored_filepath, "ab") as f:
        f.write(b"TAMPERED_BYTE_INJECTION")

    breach_res = auth_client.get(f"/api/cases/{case_id}/verify-custody", headers=auth_client.headers_a)
    assert breach_res.status_code == 200
    b_data = breach_res.json()
    assert b_data["status"] == "INTEGRITY_BREACH"
    assert b_data["stored_sha256"] != b_data["current_sha256"]

    # 5. Delete file to test UNAVAILABLE
    os.remove(stored_filepath)
    unavail_res = auth_client.get(f"/api/cases/{case_id}/verify-custody", headers=auth_client.headers_a)
    assert unavail_res.status_code == 200
    u_data = unavail_res.json()
    assert u_data["status"] == "UNAVAILABLE"

# ==============================================================================
# FEATURE 2: CONTROLLED SYNTHETIC FORENSICS LAB TESTS
# ==============================================================================
def test_synthetic_lab_generation_and_safety():
    """Verify synthetic document safety watermark, fictional details, and deterministic seeds."""
    doc, meta = generate_synthetic_document(doc_type="Synthetic ID", seed="safe_seed_123")
    assert meta["synthetic"] is True
    assert meta["watermark"] == "SYNTHETIC DEMO — NOT A REAL GOVERNMENT DOCUMENT"
    assert meta["identity"]["name"] == "Aarav Demo"
    assert meta["identity"]["doc_id"] == "SYN-DEMO-001"
    assert meta["identity"]["qr_payload"] == "SENTINEL-DEMO-001"
    assert isinstance(doc, np.ndarray)
    assert doc.shape[0] > 100 and doc.shape[1] > 100

def test_synthetic_lab_all_manipulations():
    """Verify all 8 deterministic manipulation modules execute cleanly."""
    base_doc, _ = generate_synthetic_document(doc_type="Synthetic ID", seed="manip_seed")
    
    assert len(SUPPORTED_MANIPULATIONS) == 8
    for m in SUPPORTED_MANIPULATIONS:
        manip_doc, details = apply_manipulations(base_doc, [m], severity=60, seed="test_seed")
        assert manip_doc is not None
        assert manip_doc.shape == base_doc.shape
        assert len(details) == 1
        assert details[0]["manipulation"] == m
        assert details[0]["severity"] == 60

def test_synthetic_lab_one_click_analysis(auth_client):
    """Test /api/synthetic/analyze runs generated image through existing pipeline."""
    analyze_res = auth_client.post("/api/synthetic/analyze", json={
        "document_type": "Synthetic PAN-like",
        "manipulations": ["jpeg_compression", "blur"],
        "severity": 75,
        "seed": 202
    }, headers=auth_client.headers_a)
    assert analyze_res.status_code == 200
    res_data = analyze_res.json()
    assert res_data["success"] is True
    data = res_data["analysis"]
    
    # Canonical contract fields
    for field in ["risk_score", "classification", "evidence", "confidence", "heatmap", "quality", "ocr", "qr"]:
        assert field in data
    assert isinstance(data["risk_score"], (int, float))

# ==============================================================================
# FEATURE 3: FORENSIC EXPLAINABILITY PANEL TESTS
# ==============================================================================
def test_explainability_panel_metrics(auth_client):
    """Ensure evidence cards expose category, risk contribution, confidence, observed metrics, assessment."""
    analyze_res = auth_client.post("/api/synthetic/analyze", json={
        "document_type": "Synthetic ID",
        "manipulations": ["typography_alteration", "layout_shift"],
        "severity": 80,
        "seed": 303
    }, headers=auth_client.headers_a)
    assert analyze_res.status_code == 200
    evidence_list = analyze_res.json()["analysis"].get("evidence", [])
    assert len(evidence_list) > 0

    for ev in evidence_list:
        assert "category" in ev
        assert "risk_contribution" in ev
        assert isinstance(ev["risk_contribution"], (int, float))
        assert "confidence" in ev
        if ev["confidence"] is not None:
            assert isinstance(ev["confidence"], (int, float))
            assert 0 <= ev["confidence"] <= 100
        assert "observed_metrics" in ev
        assert isinstance(ev["observed_metrics"], list)
        assert len(ev["observed_metrics"]) > 0
        assert "assessment" in ev
        assert isinstance(ev["assessment"], str)

# ==============================================================================
# FEATURE 4: FORENSIC DOCUMENT FINGERPRINT TESTS
# ==============================================================================
def test_fingerprint_deterministic_and_excludes_risk():
    """Verify same characteristics yield identical hash/vector and risk_score is excluded."""
    mock_analysis_1 = {
        "dimensions": [800, 600],
        "aspect_ratio": 1.333,
        "ocr": {"words": ["SAMPLE", "IDENTITY", "DOC"], "confidence": 0.88},
        "typography": {"variance": 2.5},
        "layout": {"variance": 1.2},
        "qr": {"detected": True},
        "image_forensics": {"laplacian_variance": 120.0, "mean_luminance": 180.0, "ela_anomaly_score": 15.0},
        "risk_score": 10  # Risk score 10
    }
    
    mock_analysis_2 = {
        "dimensions": [800, 600],
        "aspect_ratio": 1.333,
        "ocr": {"words": ["SAMPLE", "IDENTITY", "DOC"], "confidence": 0.88},
        "typography": {"variance": 2.5},
        "layout": {"variance": 1.2},
        "qr": {"detected": True},
        "image_forensics": {"laplacian_variance": 120.0, "mean_luminance": 180.0, "ela_anomaly_score": 15.0},
        "risk_score": 95  # Drastically different risk score
    }

    fp1 = extract_document_fingerprint(mock_analysis_1)
    fp2 = extract_document_fingerprint(mock_analysis_2)

    # Identical vectors and hashes despite different risk scores
    assert fp1["fingerprint_hash"] == fp2["fingerprint_hash"]
    assert fp1["fingerprint_vector"] == fp2["fingerprint_vector"]

    # Cosine similarity must be 1.0 (100%)
    sim = calculate_cosine_similarity(fp1["fingerprint_vector"], fp2["fingerprint_vector"])
    assert pytest.approx(sim, 0.001) == 1.0

# ==============================================================================
# FEATURE 5: SIMILAR CASE DETECTION TESTS
# ==============================================================================
def test_similar_case_detection_and_isolation(auth_client):
    """Verify /api/cases/{case_id}/similar excludes self, isolates users, and returns deterministic ranking."""
    # Create Case 1 for User A
    c1_res = auth_client.post("/api/cases", json={
        "title": "Case 1",
        "document_type": "Synthetic ID",
        "risk_score": 25,
        "analysis_data": {
            "dimensions": [1000, 630],
            "aspect_ratio": 1.58,
            "ocr": {"words": ["AA", "BB", "CC"], "confidence": 0.90},
            "qr": {"detected": True},
            "image_forensics": {"laplacian_variance": 200.0, "mean_luminance": 200.0, "ela_anomaly_score": 5.0}
        }
    }, headers=auth_client.headers_a)
    c1_id = c1_res.json()["case"]["case_id"]

    # Create Case 2 for User A (highly similar)
    c2_res = auth_client.post("/api/cases", json={
        "title": "Case 2 (Similar)",
        "document_type": "Synthetic ID",
        "risk_score": 30,
        "analysis_data": {
            "dimensions": [1000, 630],
            "aspect_ratio": 1.58,
            "ocr": {"words": ["AA", "BB", "CC", "DD"], "confidence": 0.89},
            "qr": {"detected": True},
            "image_forensics": {"laplacian_variance": 195.0, "mean_luminance": 198.0, "ela_anomaly_score": 6.0}
        }
    }, headers=auth_client.headers_a)
    c2_id = c2_res.json()["case"]["case_id"]

    # Create Case 3 for User B (User A must NOT see this)
    c3_res = auth_client.post("/api/cases", json={
        "title": "User B Case",
        "document_type": "Synthetic ID",
        "risk_score": 28,
        "analysis_data": {
            "dimensions": [1000, 630],
            "aspect_ratio": 1.58,
            "ocr": {"words": ["AA", "BB"], "confidence": 0.90},
            "qr": {"detected": True},
            "image_forensics": {"laplacian_variance": 200.0, "mean_luminance": 200.0, "ela_anomaly_score": 5.0}
        }
    }, headers=auth_client.headers_b)
    c3_id = c3_res.json()["case"]["case_id"]

    # Query similar for Case 1 as User A
    sim_res = auth_client.get(f"/api/cases/{c1_id}/similar", headers=auth_client.headers_a)
    assert sim_res.status_code == 200
    sim_data = sim_res.json()
    assert sim_data["success"] is True
    matches = sim_data["similar_cases"]
    
    # Current case must be excluded
    matched_ids = [m["case_id"] for m in matches]
    assert c1_id not in matched_ids
    # User B's case must be excluded (authorization boundary)
    assert c3_id not in matched_ids
    # Case 2 should be returned with high similarity
    assert c2_id in matched_ids
    c2_match = next(m for m in matches if m["case_id"] == c2_id)
    assert c2_match["similarity_score"] > 0.85
    assert len(c2_match["shared_signals"]) > 0

# ==============================================================================
# FEATURE 6: INVESTIGATION TIMELINE TESTS
# ==============================================================================
def test_investigation_timeline_lifecycle(auth_client):
    """Verify timeline creation, note events, status changes, and chronological order."""
    case_res = auth_client.post("/api/cases", json={
        "title": "Timeline Test Case",
        "analysis_data": {"score": 20},
        "document_type": "Passport-like"
    }, headers=auth_client.headers_a)
    case_id = case_res.json()["case"]["case_id"]

    # Add Note -> Triggers timeline NOTE_ADDED event
    auth_client.post(f"/api/cases/{case_id}/notes", json={"text": "Initial inspection completed."}, headers=auth_client.headers_a)

    # Change status -> Triggers timeline STATUS_CHANGED event
    auth_client.patch(f"/api/cases/{case_id}/status", json={"status": "Under Review"}, headers=auth_client.headers_a)

    # Fetch Case and inspect timeline
    get_res = auth_client.get(f"/api/cases/{case_id}", headers=auth_client.headers_a)
    assert get_res.status_code == 200
    timeline = get_res.json().get("timeline", [])
    assert len(timeline) >= 4  # INGESTION, HASH, CREATION, NOTE, STATUS_CHANGE

    event_types = [e["event_type"] for e in timeline]
    assert "EVIDENCE_INGESTED" in event_types
    assert "CASE_CREATED" in event_types
    assert "NOTE_ADDED" in event_types
    assert "STATUS_CHANGED" in event_types

    # Verify timestamps are valid and chronological
    for i in range(len(timeline) - 1):
        assert timeline[i]["timestamp"] <= timeline[i+1]["timestamp"]

# ==============================================================================
# FEATURE 7: SIDE-BY-SIDE COMPARISON TESTS
# ==============================================================================
def test_document_comparison_upload(auth_client, tmp_path):
    """Test /api/compare/upload with two image specimens."""
    # Generate two images
    img1, _ = generate_synthetic_document(doc_type="Synthetic ID", seed="comp_a")
    img2, _ = apply_manipulations(img1, ["blur", "illumination_change"], severity=70, seed="comp_b")

    path1 = str(tmp_path / "specimen_a.png")
    path2 = str(tmp_path / "specimen_b.png")
    cv2.imwrite(path1, img1)
    cv2.imwrite(path2, img2)

    with open(path1, "rb") as f1, open(path2, "rb") as f2:
        res = auth_client.post("/api/compare/upload", files={
            "file_a": ("specimen_a.png", f1, "image/png"),
            "file_b": ("specimen_b.png", f2, "image/png")
        }, headers=auth_client.headers_a)

    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "difference_heatmap" in data
    assert "visual_difference_pct" in data
    assert data["visual_difference_pct"] > 0
    assert "ocr_difference" in data
    assert "dimensions_a" in data and "dimensions_b" in data

def test_document_comparison_cases(auth_client):
    """Test /api/compare/cases between two existing authorized cases."""
    c1 = auth_client.post("/api/cases", json={
        "title": "Comp Case A",
        "document_type": "Synthetic ID",
        "risk_score": 15,
        "analysis_data": {"dimensions": [800, 600]}
    }, headers=auth_client.headers_a).json()["case"]["case_id"]

    c2 = auth_client.post("/api/cases", json={
        "title": "Comp Case B",
        "document_type": "Synthetic ID",
        "risk_score": 65,
        "analysis_data": {"dimensions": [800, 600]}
    }, headers=auth_client.headers_a).json()["case"]["case_id"]

    res = auth_client.post("/api/compare/cases", json={
        "case_a": c1,
        "case_b": c2
    }, headers=auth_client.headers_a)

    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["case_a_id"] == c1
    assert data["case_b_id"] == c2
    assert data["risk_score_delta"] == 50  # |65 - 15|
