import os
import shutil
import tempfile
import numpy as np
import cv2
import pytest
from backend.forensic.demo_reference import (
    check_demo_reference,
    ORIGINAL_SHA256,
    TAMPERED_SHA256,
    ORIGINAL_DIMENSIONS,
    TAMPERED_DIMENSIONS
)
from backend.forensic.pipeline import process_document

ORIG_PATH = os.path.abspath("frontend/assets/demo/reference/original.png")
TAMP_PATH = os.path.abspath("frontend/assets/demo/reference/tampered.png")


def test_demo_original_reference():
    """
    Test 1: Uploading the authorized original baseline reference image
    must produce LIKELY AUTHENTIC (90/100), risk 10/100, and BASELINE_MATCH.
    """
    assert os.path.exists(ORIG_PATH), f"Original reference image not found at {ORIG_PATH}"
    
    result = process_document(ORIG_PATH)
    
    assert result["authenticity_score"] == 90
    assert result["risk_score"] == 10
    assert result["classification"] == "Likely Authentic"
    assert "AUTHORIZED DEMO BASELINE" in result["classification_display"]
    
    demo_ref = result.get("demo_reference_analysis")
    assert demo_ref is not None
    assert demo_ref["enabled"] is True
    assert demo_ref["matched"] is True
    assert demo_ref["reference_type"] == "ORIGINAL"
    assert demo_ref["comparison"] == "BASELINE_MATCH"
    assert demo_ref["differences_detected"] is False
    assert len(demo_ref["evidence"]) == 8
    
    # Section 15: Ensure QR status is user-facing DETECTED and not raw unconfigured
    assert result["qr_status"] == "DETECTED"
    assert "DETECTED_NOT_DECODED" not in str(result["qr_status"])
    assert "NOT_CONFIGURED" not in str(result["qr_status"])


def test_demo_tampered_reference():
    """
    Test 2: Uploading the modified demo fixture must produce HIGH SUSPICION (15/100),
    risk 85/100, DIFFERENCES_DETECTED, and all 5 strong forensic differences.
    """
    assert os.path.exists(TAMP_PATH), f"Tampered reference image not found at {TAMP_PATH}"
    
    result = process_document(TAMP_PATH)
    
    assert result["authenticity_score"] == 15
    assert result["risk_score"] == 85
    assert result["classification"] == "High Suspicion"
    assert "DIFFERENCES DETECTED" in result["classification_display"]
    
    demo_ref = result.get("demo_reference_analysis")
    assert demo_ref is not None
    assert demo_ref["enabled"] is True
    assert demo_ref["matched"] is True
    assert demo_ref["reference_type"] == "TAMPERED"
    assert demo_ref["comparison"] == "DIFFERENCES_DETECTED"
    assert demo_ref["differences_detected"] is True
    assert len(demo_ref["differences"]) == 5
    
    # Section 7: Verify EV-D01 through EV-D06 evidence IDs
    ev_ids = [e["id"] for e in result["evidence_table"] if "id" in e]
    for required_id in ["EV-D01", "EV-D02", "EV-D03", "EV-D04", "EV-D05", "EV-D06"]:
        assert required_id in ev_ids, f"Required evidence ID {required_id} missing from evidence_table"
    
    # Verify QR presentation
    assert result["qr_status"] == "DETECTED"
    assert "DETECTED_NOT_DECODED" not in str(result["qr_status"])


def test_unknown_image_uses_normal_pipeline():
    """
    Test 3: An unrelated, unknown document must NOT trigger demo mode.
    demo_reference_analysis.matched must be False.
    """
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
        temp_img_path = tf.name
    try:
        # Create an unrelated blank document canvas
        blank = np.full((400, 600, 3), 240, dtype=np.uint8)
        cv2.putText(blank, "INVOICE #98234", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
        cv2.imwrite(temp_img_path, blank)
        
        result = process_document(temp_img_path)
        
        assert "demo_reference_analysis" in result
        assert result["demo_reference_analysis"]["enabled"] is True
        assert result["demo_reference_analysis"]["matched"] is False
    finally:
        if os.path.exists(temp_img_path):
            os.remove(temp_img_path)


def test_demo_does_not_affect_other_documents():
    """
    Test 4: Normal pipeline operations (quality, OCR, structure, fingerprinting)
    must remain intact for non-demo uploads and produce standard forensic outputs.
    """
    test_asset = os.path.abspath("frontend/assets/sentinel-mark.png")
    if os.path.exists(test_asset):
        result = process_document(test_asset)
        assert result["demo_reference_analysis"]["matched"] is False
        assert result["authenticity_score"] != 15 or result["risk_score"] != 85  # Not pinned to tampered demo
        assert "image_quality_score" in result
        assert "fingerprint" in result


def test_filename_does_not_trigger_demo():
    """
    Test 5: Renaming an unrelated image to 'original.png' or 'tampered.png'
    must NOT activate demo mode. Only cryptographic/perceptual fingerprints match.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        fake_original = os.path.join(tmpdir, "original.png")
        fake_tampered = os.path.join(tmpdir, "tampered.png")
        
        # Write random pixel data
        rnd = np.random.randint(0, 255, (300, 300, 3), dtype=np.uint8)
        cv2.imwrite(fake_original, rnd)
        cv2.imwrite(fake_tampered, rnd)
        
        matched_orig, _ = check_demo_reference(fake_original)
        matched_tamp, _ = check_demo_reference(fake_tampered)
        
        assert matched_orig is False, "Filename 'original.png' triggered demo mode without matching hash!"
        assert matched_tamp is False, "Filename 'tampered.png' triggered demo mode without matching hash!"
