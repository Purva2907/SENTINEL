import os
import sys
import io
import uuid
import shutil
import pytest
import pymupdf
from fastapi import HTTPException
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app
from forensic.evidence import validate_and_decode_image, ingest_evidence, sanitize_custody_for_client


def create_in_memory_pdf(text_lines=None, pages=1) -> bytes:
    doc = pymupdf.open()
    for page_idx in range(pages):
        page = doc.new_page(width=595, height=842)
        lines = text_lines or [
            "GOVERNMENT OF INDIA / UIDAI / AADHAAR",
            "Name: Citizen Test",
            "DOB: 15/08/1992",
            "Gender: MALE",
            "1234 5678 9012"
        ]
        y = 72
        for line in lines:
            page.insert_text((50, y), line, fontsize=14)
            y += 35
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def test_validate_and_decode_valid_pdf():
    pdf_bytes = create_in_memory_pdf()
    cv_img, ext, mime = validate_and_decode_image(pdf_bytes)

    assert cv_img is not None
    assert cv_img.size > 0
    assert len(cv_img.shape) == 3
    assert ext == ".png"
    assert mime == "application/pdf"


def test_validate_and_decode_corrupted_pdf():
    corrupted_bytes = b"%PDF-1.4\n%corrupt stream\n" + b"\x00\xff" * 50
    with pytest.raises(HTTPException) as exc:
        validate_and_decode_image(corrupted_bytes)
    assert exc.value.status_code == 400


def test_validate_and_decode_oversized_file():
    huge_bytes = b"%PDF-" + b"0" * (26 * 1024 * 1024)
    with pytest.raises(HTTPException) as exc:
        validate_and_decode_image(huge_bytes)
    assert exc.value.status_code == 400
    assert "exceeds maximum allowed size" in exc.value.detail


def test_ingest_evidence_pdf(tmp_path):
    pdf_bytes = create_in_memory_pdf(pages=2)
    upload_dir = str(tmp_path / "uploads")

    file_path, custody = ingest_evidence(
        file_bytes=pdf_bytes,
        original_filename="aadhaar_card_v2.pdf",
        investigator={"id": "INV-TEST", "name": "Forensic Officer"},
        upload_dir=upload_dir
    )

    assert os.path.exists(file_path)
    assert file_path.endswith(".png")
    assert "pdf_path" in custody
    assert os.path.exists(custody["pdf_path"])
    assert custody["format"] == "PDF"
    assert custody["page_count"] == 2
    assert custody["mime_type"] == "application/pdf"
    assert custody["original_filename"] == "aadhaar_card_v2.pdf"

    # Verify custody sanitation
    client_custody = sanitize_custody_for_client(custody)
    assert "file_path" not in client_custody
    assert "pdf_path" not in client_custody
    assert client_custody["format"] == "PDF"


def test_api_analyze_pdf_upload():
    client = TestClient(app)
    test_email = f"pdf_tester_{uuid.uuid4()}@example.com"
    client.post("/api/auth/register", json={
        "email": test_email,
        "password": "securepassword",
        "name": "PDF Investigator",
        "role": "investigator"
    })
    login_res = client.post("/api/auth/login", json={
        "email": test_email,
        "password": "securepassword"
    })
    assert login_res.status_code == 200
    token = login_res.json().get("access_token")

    pdf_bytes = create_in_memory_pdf()
    response = client.post(
        "/api/analyze",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("specimen_intake.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "data" in data
    assert data["data"]["chain_of_custody"]["format"] == "PDF"
    assert "risk_score" in data["data"]
    assert "authenticity_score" in data["data"]


def test_api_compare_pdf_upload():
    client = TestClient(app)
    test_email = f"compare_pdf_{uuid.uuid4()}@example.com"
    client.post("/api/auth/register", json={
        "email": test_email,
        "password": "securepassword",
        "name": "Compare Investigator",
        "role": "investigator"
    })
    login_res = client.post("/api/auth/login", json={
        "email": test_email,
        "password": "securepassword"
    })
    assert login_res.status_code == 200
    token = login_res.json().get("access_token")

    pdf_a = create_in_memory_pdf(["SPECIMEN A BASELINE DOCUMENT", "Serial: AA-100234"])
    pdf_b = create_in_memory_pdf(["SPECIMEN B TARGET DOCUMENT", "Serial: BB-990811"])

    response = client.post(
        "/api/compare/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={
            "file_a": ("specimen_a.pdf", io.BytesIO(pdf_a), "application/pdf"),
            "file_b": ("specimen_b.pdf", io.BytesIO(pdf_b), "application/pdf")
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "visual_difference_pct" in data
