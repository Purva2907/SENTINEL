import pytest
import os
import sys
import uuid
import math
import numpy as np
import cv2
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Configure test environment isolation
os.environ["JWT_SECRET"] = "test_secret_do_not_use_in_prod"
os.environ["MONGO_URL"] = "mongodb://invalid-host-for-tests:27017"
os.environ["SQLITE_DB_PATH"] = "test_pipeline_sentinel.db"

from app import app
from forensic.pipeline import process_document
from forensic.ocr import analyze_ocr
from forensic.qr import analyze_qr
from forensic.image_quality import analyze_quality
from forensic.heatmap import analyze_image_forensics, generate_heatmap, encode_image_to_base64

SAMPLE_IMG = "data/sentinel_dataset/documents/SYN-TEST-0001.jpg"
BLUR_IMG = "data/sentinel_dataset/documents/SYN-TEST-0006.jpg"

@pytest.fixture
def client(tmp_path):
    db_path = tmp_path / "test_pipeline_sentinel.db"
    os.environ["SQLITE_DB_PATH"] = str(db_path)
    with TestClient(app) as test_client:
        yield test_client

def get_auth_headers(client):
    test_email = f"tester_{uuid.uuid4().hex[:8]}@example.com"
    client.post("/api/auth/register", json={
        "email": test_email, 
        "password": "pass", 
        "name": "Pipeline Tester", 
        "role": "investigator"
    })
    resp = client.post("/api/auth/login", json={"email": test_email, "password": "pass"})
    token = resp.json().get("access_token")
    return {"Authorization": f"Bearer {token}"}

def test_pipeline_canonical_contract():
    """Verify canonical fields: risk_score, risk_contribution, document_type, classification, original_image, heatmap."""
    res = process_document(SAMPLE_IMG)
    
    # Canonical risk_score: finite, int, 0-100
    assert "risk_score" in res
    assert isinstance(res["risk_score"], int)
    assert 0 <= res["risk_score"] <= 100
    assert not math.isnan(res["risk_score"])
    assert not math.isinf(res["risk_score"])
    
    # Classification & Document Type
    assert "classification" in res
    assert res["classification"] in ("Likely Authentic", "Review Required", "High Suspicion")
    assert "document_type" in res
    assert isinstance(res["document_type"], str) and len(res["document_type"]) > 0
    
    # Evidence contract: every evidence item must have risk_contribution
    assert "evidence" in res
    assert len(res["evidence"]) > 0
    for ev in res["evidence"]:
        assert "risk_contribution" in ev
        assert isinstance(ev["risk_contribution"], int)
        assert ev["risk_contribution"] >= 0
        assert "category" in ev
        assert "severity" in ev
        assert "finding" in ev
        
    # Explainable risk_breakdown
    assert "risk_breakdown" in res
    rb = res["risk_breakdown"]
    for k in ("quality", "ocr", "qr", "typography", "layout", "image_forensics"):
        assert k in rb
        assert isinstance(rb[k], int)
        assert rb[k] >= 0

def test_original_image_vs_heatmap_separation():
    """Ensure original_image and heatmap are distinct and valid data URIs."""
    res = process_document(SAMPLE_IMG)
    assert "original_image" in res
    assert "heatmap" in res
    assert res["original_image"].startswith("data:image/")
    assert res["heatmap"].startswith("data:image/")
    
    # The source image must NOT equal the heatmap
    assert res["original_image"] != res["heatmap"]

def test_ocr_empty_state_and_finite_confidence(tmp_path):
    """Verify OCR handles blank image gracefully without NaN, returning NO_TEXT_RECOVERED."""
    blank_img_path = str(tmp_path / "blank.png")
    blank = np.ones((300, 500, 3), dtype=np.uint8) * 255
    cv2.imwrite(blank_img_path, blank)
    
    ocr_res = analyze_ocr(blank_img_path)
    assert ocr_res["status"] == "NO_TEXT_RECOVERED"
    assert ocr_res["confidence"] == 0.0
    assert ocr_res["average_confidence"] == 0.0
    assert not math.isnan(ocr_res["average_confidence"])
    assert ocr_res["extracted_text"] == ""
    assert ocr_res["detections"] == []

def test_qr_detection_and_decoding_states(tmp_path):
    """Verify distinct QR states: DETECTED vs DECODED vs NOT_DETECTED."""
    # 1. Clean QR on sample 1
    qr_clean = analyze_qr(SAMPLE_IMG)
    assert qr_clean["detected"] is True
    assert qr_clean["decoded"] is True
    assert qr_clean["status"] == "DECODED"
    assert "SENTINEL" in qr_clean["payload"]
    
    # 2. Blank image without QR
    blank_img_path = str(tmp_path / "no_qr.png")
    blank = np.ones((300, 500, 3), dtype=np.uint8) * 255
    cv2.imwrite(blank_img_path, blank)
    qr_none = analyze_qr(blank_img_path)
    assert qr_none["detected"] is False
    assert qr_none["decoded"] is False
    assert qr_none["status"] == "NOT_DETECTED"

def test_case_score_and_type_preservation(client):
    """Verify FastAPI endpoint + repository stores and retrieves risk_score, classification, and document_type identically."""
    headers = get_auth_headers(client)
    analysis_payload = process_document(SAMPLE_IMG)
    
    case_data = {
        "title": "Investigation Case 01",
        "description": "Preservation verification case",
        "document_type": "Identity Card",
        "status": "Active",
        "risk_score": 27,
        "classification": "Review Required",
        "analysis_data": analysis_payload
    }
    
    resp = client.post("/api/cases", json=case_data, headers=headers)
    assert resp.status_code == 200
    created = resp.json().get("case", {})
    assert created["risk_score"] == 27
    assert created["classification"] == "Review Required"
    assert created["document_type"] == "Identity Card"
    
    # Retrieve via API and check preservation
    case_id = created["id"]
    retrieved_resp = client.get(f"/api/cases/{case_id}", headers=headers)
    assert retrieved_resp.status_code == 200
    retrieved = retrieved_resp.json()
    assert retrieved["risk_score"] == 27
    assert retrieved["classification"] == "Review Required"
    assert retrieved["document_type"] == "Identity Card"
    assert "original_image" in retrieved["analysis"]
    assert "heatmap" in retrieved["analysis"]
    assert retrieved["analysis"]["original_image"] == analysis_payload["original_image"]
    assert retrieved["analysis"]["heatmap"] == analysis_payload["heatmap"]

def test_zero_data_and_analytics_robustness(client):
    """Verify endpoint handles 0 cases gracefully without crashing dashboard or returning NaN."""
    headers = get_auth_headers(client)
    resp = client.get("/api/analytics", headers=headers)
    assert resp.status_code == 200
    analytics = resp.json()
    assert analytics["total_investigations"] == 0
    assert analytics["average_risk"] == 0.0
    assert analytics["classification"] == {
        "likely_authentic": 0,
        "review_required": 0,
        "high_suspicion": 0
    }

def test_heatmap_is_valid_image_bytes():
    """Validate that heatmap base64 decodes to a valid image with non-zero dimensions."""
    import base64
    import io
    from PIL import Image

    res = process_document(SAMPLE_IMG)
    heatmap_data = res.get("heatmap", "")
    assert heatmap_data.startswith("data:image/")
    
    # Strip prefix and decode
    header, b64_str = heatmap_data.split(",", 1)
    raw_bytes = base64.b64decode(b64_str)
    assert len(raw_bytes) > 0

    img = Image.open(io.BytesIO(raw_bytes))
    assert img.format in ("JPEG", "PNG")
    assert img.width > 0
    assert img.height > 0

def test_case_detail_retrieval_by_case_id_and_missing_heatmap_graceful(client):
    """Verify case detail API returns heatmap by both UUID and human-readable case_id, and handles missing heatmap gracefully."""
    headers = get_auth_headers(client)
    
    # Case with valid heatmap
    analysis_payload = process_document(SAMPLE_IMG)
    case_data = {
        "title": "Case Detail Heatmap Test",
        "description": "Verify heatmap retrieval",
        "document_type": "Identity Card",
        "status": "Active",
        "risk_score": 15,
        "classification": "Likely Authentic",
        "analysis_data": analysis_payload
    }
    resp = client.post("/api/cases", json=case_data, headers=headers)
    assert resp.status_code == 200
    created = resp.json().get("case", {})
    uuid_id = created["id"]
    human_case_id = created["case_id"]

    # Retrieve by UUID id
    res_uuid = client.get(f"/api/cases/{uuid_id}", headers=headers)
    assert res_uuid.status_code == 200
    assert res_uuid.json()["analysis"]["heatmap"] == analysis_payload["heatmap"]

    # Retrieve by human-readable case_id
    res_human = client.get(f"/api/cases/{human_case_id}", headers=headers)
    assert res_human.status_code == 200
    assert res_human.json()["analysis"]["heatmap"] == analysis_payload["heatmap"]

    # Case with missing heatmap handled gracefully
    case_no_heatmap = {
        "title": "Case Missing Heatmap Test",
        "description": "Verify missing heatmap handling",
        "document_type": "Payslip",
        "status": "Active",
        "risk_score": 50,
        "classification": "Review Required",
        "analysis_data": {"risk_score": 50, "classification": "Review Required"}
    }
    resp2 = client.post("/api/cases", json=case_no_heatmap, headers=headers)
    assert resp2.status_code == 200
    id2 = resp2.json().get("case", {})["id"]

    res_no_heatmap = client.get(f"/api/cases/{id2}", headers=headers)
    assert res_no_heatmap.status_code == 200
    ret_data = res_no_heatmap.json()
    assert ret_data["id"] == id2
    # Heatmap missing or None is handled gracefully without breaking response
    assert ret_data.get("analysis", {}).get("heatmap") is None

