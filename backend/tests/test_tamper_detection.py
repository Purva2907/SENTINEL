"""
Unit and Integration Tests for SENTINEL Multi-Spectral Tamper Detection & Scoring
================================================================================
Covers:
- Local Noise Variance Estimation
- Error Level Analysis (ELA)
- Synthetic Overlays / Marker Strokes
- Copy-Move / Cloning Detection
- Resampling Artifacts
- Text-Region Forensics
- Dominance Law: High Structural Consistency + Strong Tampering != Likely Authentic
- Robustness: Image quality / blur / brightness variations alone do NOT trigger fraud
"""

import pytest
import os
import sys
import cv2
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from forensic.tamper_detection import (
    estimate_local_noise_map,
    compute_localized_ela,
    detect_overlay_anomalies,
    detect_copy_move_cloning,
    detect_resampling_artifacts,
    analyze_text_region_forensics,
    analyze_tampering
)
from forensic.pipeline import (
    process_document,
    compute_fused_authenticity
)


# ------------------------------------------------------------------------------
# Helpers to generate synthetic test images
# ------------------------------------------------------------------------------

def create_base_document(width=600, height=800, add_text=True):
    """Creates a synthetic pristine identity card document canvas."""
    np.random.seed(42)
    img = np.ones((height, width, 3), dtype=np.uint8) * 245
    # Border & Header band
    cv2.rectangle(img, (20, 20), (width - 20, height - 20), (220, 220, 220), 2)
    cv2.rectangle(img, (20, 20), (width - 20, 90), (40, 110, 210), -1)
    cv2.putText(img, "IDENTITY AUTHENTICATION CARD", (40, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    
    # ID Photo placeholder with realistic facial/graphic geometry
    cv2.rectangle(img, (40, 120), (170, 280), (190, 190, 190), -1)
    cv2.rectangle(img, (70, 140), (140, 160), (30, 30, 30), -1) # Hair
    cv2.circle(img, (105, 185), 35, (120, 90, 80), -1)          # Face
    cv2.circle(img, (95, 175), 5, (255, 255, 255), -1)           # Eye L
    cv2.circle(img, (115, 175), 5, (255, 255, 255), -1)         # Eye R
    cv2.line(img, (105, 180), (105, 195), (60, 40, 40), 2)      # Nose
    cv2.line(img, (95, 205), (115, 205), (40, 40, 120), 2)      # Mouth
    cv2.ellipse(img, (105, 255), (55, 30), 0, 0, 180, (50, 80, 160), -1) # Shoulders
    
    # Text lines
    if add_text:
        lines = [
            "Name: RAJESH KUMAR VERMA",
            "DOB: 15/08/1992",
            "Gender: MALE",
            "ID Number: 9876 5432 1098",
            "Address: 42, Civil Lines, Sector 4",
            "New Delhi, 110001"
        ]
        y_pos = 140
        for l in lines:
            cv2.putText(img, l, (200, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (30, 30, 30), 2)
            y_pos += 30

    # Add realistic document scan noise
    noise = np.random.normal(0, 3.0, (height, width, 3)).astype(np.float32)
    noisy_img = np.clip(img.astype(np.float32) + noise, 0, 255).astype(np.uint8)
    return noisy_img


# ------------------------------------------------------------------------------
# Synthetic Modification Tests (Requirement 20)
# ------------------------------------------------------------------------------

def test_pristine_document_forensic_integrity(tmp_path):
    """Pristine document: high authenticity, no localized tampering anomaly."""
    doc = create_base_document()
    doc_path = str(tmp_path / "pristine.jpg")
    cv2.imwrite(doc_path, doc)
    
    res = analyze_tampering(doc_path)
    assert res["status"] == "NO_STRONG_ANOMALY"
    assert res["tampering_score"] <= 15
    assert res["tampering_integrity_score"] >= 85


def test_brightness_only_modification_not_suspicious(tmp_path):
    """Brightness-only modification: must NOT become strongly suspicious."""
    doc = create_base_document()
    # Increase brightness by 40 units
    bright = cv2.convertScaleAbs(doc, alpha=1.0, beta=40)
    p = str(tmp_path / "bright.jpg")
    cv2.imwrite(p, bright)
    
    res = analyze_tampering(p)
    assert res["status"] == "NO_STRONG_ANOMALY"
    assert res["tampering_score"] <= 20
    assert res["severity"] in ("NONE", "LOW")


def test_blur_only_modification_not_suspicious(tmp_path):
    """Blur-only modification: must NOT become strongly suspicious."""
    doc = create_base_document()
    # Apply Gaussian blur
    blurred = cv2.GaussianBlur(doc, (11, 11), 3.0)
    p = str(tmp_path / "blurred.jpg")
    cv2.imwrite(p, blurred)
    
    res = analyze_tampering(p)
    assert res["status"] == "NO_STRONG_ANOMALY"
    assert res["tampering_score"] <= 20
    assert res["severity"] in ("NONE", "LOW")


def test_recompression_only_not_suspicious(tmp_path):
    """Recompression: saving at lower JPEG quality should NOT trigger localized tampering fraud."""
    doc = create_base_document()
    p = str(tmp_path / "recompressed.jpg")
    cv2.imwrite(p, doc, [int(cv2.IMWRITE_JPEG_QUALITY), 65])
    
    res = analyze_tampering(p)
    # Uniform recompression affects entire canvas uniformly, no localized tampering
    assert res["status"] in ("NO_STRONG_ANOMALY", "POSSIBLE_TAMPERING")
    assert res["severity"] in ("NONE", "LOW", "MODERATE")
    assert res["tampering_score"] < 40


def test_privacy_redaction_not_tampering(tmp_path):
    """
    Section 11 & 27: test_privacy_redaction_not_tampering()
    Intentional green highlighter / blackout masking over sensitive ID numbers is PRIVACY_REDACTION (risk contribution = 0).
    """
    doc = create_base_document()
    # Paint green highlighter stroke over the ID Number text
    cv2.rectangle(doc, (190, 215), (520, 245), (50, 240, 50), -1)
    p = str(tmp_path / "privacy_redaction.jpg")
    cv2.imwrite(p, doc)
    
    res = analyze_tampering(p)
    assert res["tampering_score"] <= 15
    assert res["severity"] in ("NONE", "LOW")
    assert len(res["regions"]) >= 1
    assert any(r["signal"] == "PRIVACY_REDACTION" and r.get("risk_contribution", 0) == 0 for r in res["regions"])


def test_blackout_scribble_privacy_redaction(tmp_path):
    """
    Section 11: Blackout marker cover over sensitive field is PRIVACY_REDACTION (risk contribution = 0).
    """
    doc = create_base_document()
    # Paint black marker patch over sensitive field
    cv2.rectangle(doc, (40, 120), (170, 280), (10, 10, 10), -1)
    p = str(tmp_path / "blackout_redaction.jpg")
    cv2.imwrite(p, doc)
    
    res = analyze_tampering(p)
    assert res["tampering_score"] <= 15
    assert len(res["regions"]) >= 1
    assert any(r["signal"] == "PRIVACY_REDACTION" and r.get("risk_contribution", 0) == 0 for r in res["regions"])


def test_synthetic_overlay_paint_tampering(tmp_path):
    """
    Section 10 & 25: Malicious digital text replacement / foreign element splicing.
    """
    doc = create_base_document()
    # Paste an artificial spliced text patch with gradient edge discontinuity and noise mismatch
    spliced_box = np.ones((40, 280, 3), dtype=np.uint8) * 245
    cv2.putText(spliced_box, "FORGED: 9999 8888", (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 180), 2)
    doc[215:255, 190:470] = spliced_box
    p = str(tmp_path / "tampered_overlay.jpg")
    cv2.imwrite(p, doc)
    
    res = analyze_tampering(p, ocr_result={"detections": [{"box": [190, 215, 280, 40], "text": "FORGED: 9999 8888"}]})
    assert res["tampering_score"] >= 15 or len(res["regions"]) >= 1


def test_copy_move_cloning_tampering(tmp_path):
    """Copy-move cloning: duplicated texture block pasted across canvas."""
    doc = create_base_document()
    # Take high-texture photo element and duplicate it into document body
    src_block = doc[120:260, 40:170].copy()
    doc[400:540, 300:430] = src_block
    p = str(tmp_path / "copy_move.jpg")
    cv2.imwrite(p, doc)
    
    res = analyze_tampering(p)
    # Either copy-move or regional ELA/noise anomaly triggers
    assert res["tampering_score"] >= 20
    assert len(res["regions"]) >= 1


# ------------------------------------------------------------------------------
# Critical Regression Tests (Requirement 21)
# ------------------------------------------------------------------------------

def test_quality_change_without_tampering():
    """
    Requirement 21: test_quality_change_without_tampering()
    Severe blur, low illumination, and downsampling alone != fraud.
    """
    from backend.tests.test_authenticity_scoring import make_evidence_fixture
    fixtures = make_evidence_fixture(
        doc_type="Aadhaar Card",
        quality_score=25,   # severe blur / lighting degradation
        ocr_conf=0.20,      # reduced OCR readability
        qr_status="DETECTED_NOT_DECODED",  # scan unreadable due to blur
        typography_score=90,
        layout_score=90,
        ela_anomaly=False,
        structure_score=90
    )
    tampering = {
        "tampering_score": 0,
        "tampering_integrity_score": 100,
        "severity": "NONE",
        "status": "NO_STRONG_ANOMALY",
        "regions": [],
        "signals": []
    }
    auth, risk, supp, neg, signals, rb = compute_fused_authenticity(*fixtures, tampering_result=tampering)
    assert auth >= 70, f"Expected auth >= 70 for pure quality degradation, got {auth}"
    assert risk <= 30
    assert risk == 100 - auth
    assert not any("tampering" in n.lower() or "splicing" in n.lower() for n in neg)


def test_tampering_overrides_template_consistency():
    """
    Requirement 21: test_tampering_overrides_template_consistency()
    PROVE: HIGH STRUCTURAL CONSISTENCY + STRONG TAMPERING EVIDENCE != LIKELY AUTHENTIC
    """
    from backend.tests.test_authenticity_scoring import make_evidence_fixture
    fixtures = make_evidence_fixture(
        doc_type="Aadhaar Card",
        quality_score=95,
        ocr_conf=0.95,
        qr_status="DECODED_UNVERIFIED",
        cross_status="CONSISTENT",
        typography_score=100,
        layout_score=100,
        structure_score=100  # Perfect 100/100 structural template consistency!
    )
    tampering = {
        "tampering_score": 80,
        "tampering_integrity_score": 20,
        "severity": "HIGH",
        "status": "STRONG_TAMPERING_EVIDENCE",
        "regions": [
            {"id": "T-01", "signal": "OVERLAY_ANOMALY", "area_px": 8000}
        ],
        "signals": [{"name": "OVERLAY_ANOMALY", "severity": "HIGH"}]
    }
    auth, risk, supp, neg, signals, rb = compute_fused_authenticity(*fixtures, tampering_result=tampering)
    
    # Must NOT be Likely Authentic (requires >= 75)
    # The Dominance Law caps it at <= 45 (High Suspicion)
    assert auth <= 45, f"Expected authenticity <= 45 for HIGH tampering, got {auth}"
    assert risk >= 55, f"Expected risk >= 55, got {risk}"
    assert risk == 100 - auth
    
    classification = "Likely Authentic" if auth >= 75 else ("Review Required" if auth >= 50 else "High Suspicion")
    assert classification != "Likely Authentic"
    assert classification == "High Suspicion"
    assert any("tampering" in n.lower() or "splicing" in n.lower() for n in neg)
