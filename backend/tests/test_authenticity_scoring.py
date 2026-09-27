import pytest
import os
import sys
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from forensic.pipeline import (
    process_document,
    detect_document_structure,
    compute_fused_authenticity
)

# ---------------------------------------------------------------------------
# Test Helpers for Synthetic Evidence Scenarios
# ---------------------------------------------------------------------------

def make_evidence_fixture(
    doc_type="Aadhaar Card",
    quality_score=95,
    ocr_conf=0.90,
    qr_status="DECODED_UNVERIFIED",
    qr_payload_type="AADHAAR_SECURE_QR",
    cross_status="CONSISTENT",
    typography_score=95,
    layout_score=95,
    ela_anomaly=False,
    forensic_score=100,
    structure_score=95
):
    structure_info = {
        "document_type": doc_type,
        "assessment_title": f"{doc_type.upper()} ASSESSMENT",
        "structure_score": structure_score,
        "fields_detected": {"id_number": "XXXX XXXX 1234"},
        "findings": ["Standard structure confirmed."],
        "is_valid_format": True
    }
    quality_res = {
        "score": quality_score,
        "risk_contribution": 0 if quality_score >= 50 else 2,
        "interpretation": "Substrate clarity optimal." if quality_score >= 80 else "Image quality is reduced.",
        "findings": ["Quality evaluated."],
        "blur_score": 150.0,
        "brightness": 128.0,
        "resolution_ok": True,
        "dimensions": [800, 1000]
    }
    ocr_res = {
        "extracted_text": "Sample text",
        "raw_text": "GOVERNMENT OF INDIA\nAADHAAR\n1234 5678 9012\nDOB: 01/01/1990\nMALE",
        "confidence": ocr_conf,
        "average_confidence": ocr_conf,
        "evidence_strength": "STRONG" if ocr_conf > 0.7 else ("MODERATE" if ocr_conf > 0.45 else "LIMITED"),
        "status": "TEXT_DETECTED",
        "risk_contribution": 0,
        "findings": [f"OCR confidence {ocr_conf * 100:.1f}%"]
    }
    qr_res = {
        "detected": qr_status != "NOT_DETECTED",
        "decoded": qr_status in ("DECODED_UNVERIFIED", "SIGNATURE_VERIFIED", "SIGNATURE_INVALID", "DECODED_URL"),
        "status": qr_status,
        "payload_type": qr_payload_type,
        "payload": "SAMPLE_PAYLOAD",
        "verification": {"status": "VERIFIED" if qr_status == "SIGNATURE_VERIFIED" else ("INVALID" if qr_status == "SIGNATURE_INVALID" else "NOT_PERFORMED")},
        "ocr_cross_check": {"status": cross_status},
        "findings": [f"QR evaluated with status {qr_status}"]
    }
    typo_res = {
        "score": typography_score,
        "risk_contribution": 0 if typography_score >= 70 else 15,
        "findings": ["Typography evaluated."]
    }
    layout_res = {
        "score": layout_score,
        "risk_contribution": 0 if layout_score >= 70 else 15,
        "findings": ["Layout evaluated."]
    }
    forensics_res = {
        "score": forensic_score,
        "anomaly_detected": ela_anomaly,
        "risk_contribution": 25 if ela_anomaly else 0,
        "findings": ["Forensics evaluated."]
    }
    return (structure_info, quality_res, ocr_res, qr_res, typo_res, layout_res, forensics_res)


# ===========================================================================
# 15 REGRESSION TEST CASES (Requirement 23)
# ===========================================================================

def test_case_01_genuine_high_quality_aadhaar():
    """1. Genuine high-quality Aadhaar: must score in high authenticity (>= 85)."""
    fixtures = make_evidence_fixture(
        doc_type="Aadhaar Card",
        quality_score=95,
        ocr_conf=0.92,
        qr_status="DECODED_UNVERIFIED",
        cross_status="CONSISTENT"
    )
    auth, risk, supp, neg, signals, rb = compute_fused_authenticity(*fixtures)
    assert auth >= 85
    assert risk == 100 - auth
    assert risk <= 15
    assert len(neg) == 0
    assert len(supp) > 0


def test_case_02_genuine_low_quality_aadhaar():
    """2. Genuine low-quality Aadhaar: blur/exposure must NOT cause high fraud risk."""
    fixtures = make_evidence_fixture(
        doc_type="Aadhaar Card",
        quality_score=45,  # heavily reduced image quality
        ocr_conf=0.38,     # low OCR confidence
        qr_status="DETECTED_NOT_DECODED",  # undecodable due to blur
        cross_status="NOT_AVAILABLE"
    )
    auth, risk, supp, neg, signals, rb = compute_fused_authenticity(*fixtures)
    # Low quality alone must NOT result in High Suspicion fraud
    assert auth >= 70, f"Expected auth >= 70, got {auth}"
    assert risk <= 30
    assert risk == 100 - auth
    assert len(neg) == 0


def test_case_03_genuine_aadhaar_with_readable_qr():
    """3. Genuine Aadhaar with readable QR: strong positive authenticity."""
    fixtures = make_evidence_fixture(
        doc_type="Aadhaar Card",
        quality_score=85,
        ocr_conf=0.85,
        qr_status="DECODED_UNVERIFIED",
        qr_payload_type="AADHAAR_SECURE_QR",
        cross_status="CONSISTENT"
    )
    auth, risk, supp, neg, signals, rb = compute_fused_authenticity(*fixtures)
    assert auth >= 90
    assert risk == 100 - auth
    assert risk <= 10


def test_case_04_genuine_aadhaar_with_decoded_unverified_qr():
    """4. Genuine Aadhaar with decoded-but-unverified QR: stays honest without UIDAI cert."""
    fixtures = make_evidence_fixture(
        doc_type="Aadhaar Card",
        quality_score=80,
        ocr_conf=0.75,
        qr_status="DECODED_UNVERIFIED",
        cross_status="CONSISTENT"
    )
    auth, risk, supp, neg, signals, rb = compute_fused_authenticity(*fixtures)
    assert auth >= 85
    assert risk == 100 - auth
    assert signals["qr"]["status"] == "DECODED_UNVERIFIED"


def test_case_05_aadhaar_qr_ocr_consistent():
    """5. Aadhaar QR/OCR consistent: verifies data consistency."""
    fixtures = make_evidence_fixture(
        doc_type="Aadhaar Card",
        qr_status="DECODED_UNVERIFIED",
        cross_status="CONSISTENT"
    )
    auth, risk, supp, neg, signals, rb = compute_fused_authenticity(*fixtures)
    assert any("consistent" in s.lower() for s in supp)
    assert auth >= 85


def test_case_06_aadhaar_qr_ocr_inconsistent():
    """6. Aadhaar QR/OCR inconsistent: must trigger strong negative authenticity impact."""
    fixtures = make_evidence_fixture(
        doc_type="Aadhaar Card",
        qr_status="DECODED_UNVERIFIED",
        cross_status="INCONSISTENT"  # Tampered: QR says Alice, OCR text says Bob
    )
    auth, risk, supp, neg, signals, rb = compute_fused_authenticity(*fixtures)
    # Critical assertion: QR/OCR inconsistency must have strong negative authenticity impact
    assert auth <= 40, f"Expected auth <= 40, got {auth}"
    assert risk >= 60
    assert risk == 100 - auth
    assert any("contradiction" in n.lower() or "inconsistent" in n.lower() for n in neg)


def test_case_07_tampered_aadhaar_splicing():
    """7. Tampered Aadhaar: localized ELA compression anomaly drops authenticity."""
    fixtures = make_evidence_fixture(
        doc_type="Aadhaar Card",
        ela_anomaly=True,
        forensic_score=40
    )
    auth, risk, supp, neg, signals, rb = compute_fused_authenticity(*fixtures)
    assert auth <= 50
    assert risk >= 50
    assert risk == 100 - auth
    assert any("splicing" in n.lower() or "compression" in n.lower() for n in neg)


def test_case_08_severe_tampered_aadhaar():
    """8. Severe tampered Aadhaar: invalid signature + splicing + mismatch."""
    fixtures = make_evidence_fixture(
        doc_type="Aadhaar Card",
        qr_status="SIGNATURE_INVALID",
        cross_status="INCONSISTENT",
        ela_anomaly=True,
        forensic_score=30,
        structure_score=40
    )
    auth, risk, supp, neg, signals, rb = compute_fused_authenticity(*fixtures)
    assert auth <= 20
    assert risk >= 80
    assert risk == 100 - auth
    assert len(neg) >= 2


def test_case_09_genuine_pan():
    """9. Genuine PAN: 10-char PAN format, no QR mandate penalty, high authenticity."""
    fixtures = make_evidence_fixture(
        doc_type="PAN Card",
        quality_score=90,
        ocr_conf=0.88,
        qr_status="NOT_APPLICABLE",
        structure_score=100
    )
    auth, risk, supp, neg, signals, rb = compute_fused_authenticity(*fixtures)
    assert auth >= 85
    assert risk == 100 - auth
    assert risk <= 15
    assert len(neg) == 0


def test_case_10_tampered_pan():
    """10. Tampered PAN: invalid syntax or localized digital splicing."""
    fixtures = make_evidence_fixture(
        doc_type="PAN Card",
        structure_score=40,  # Invalid PAN syntax
        ela_anomaly=True,
        forensic_score=40
    )
    auth, risk, supp, neg, signals, rb = compute_fused_authenticity(*fixtures)
    assert auth <= 45
    assert risk >= 55
    assert risk == 100 - auth


def test_case_11_low_quality_genuine_pan():
    """11. Low-quality genuine PAN: phone scan must NOT produce fraud verdict."""
    fixtures = make_evidence_fixture(
        doc_type="PAN Card",
        quality_score=50,
        ocr_conf=0.40,
        qr_status="NOT_APPLICABLE",
        structure_score=95
    )
    auth, risk, supp, neg, signals, rb = compute_fused_authenticity(*fixtures)
    assert auth >= 75
    assert risk <= 25
    assert risk == 100 - auth


def test_case_12_qr_unavailable_pan():
    """12. QR unavailable PAN: older physical PAN cards without QR must not be penalized."""
    fixtures = make_evidence_fixture(
        doc_type="PAN Card",
        qr_status="NOT_DETECTED",
        structure_score=95
    )
    auth, risk, supp, neg, signals, rb = compute_fused_authenticity(*fixtures)
    assert auth >= 85
    assert risk <= 15
    assert len(neg) == 0


def test_case_13_invalid_qr_signature():
    """13. Invalid QR signature: cryptographic forgery must have strong negative authenticity impact."""
    fixtures = make_evidence_fixture(
        doc_type="Aadhaar Card",
        qr_status="SIGNATURE_INVALID"
    )
    auth, risk, supp, neg, signals, rb = compute_fused_authenticity(*fixtures)
    # Critical assertion: SIGNATURE_INVALID must cap authenticity to <= 25
    assert auth <= 25, f"Expected auth <= 25, got {auth}"
    assert risk >= 75
    assert risk == 100 - auth
    assert any("signature" in n.lower() for n in neg)


def test_case_14_valid_qr_signature():
    """14. Valid QR signature: cryptographic pass dominates authenticity assessment."""
    fixtures = make_evidence_fixture(
        doc_type="Aadhaar Card",
        qr_status="SIGNATURE_VERIFIED",
        cross_status="CONSISTENT"
    )
    auth, risk, supp, neg, signals, rb = compute_fused_authenticity(*fixtures)
    assert auth >= 95
    assert risk <= 5
    assert risk == 100 - auth
    assert any("signature" in s.lower() for s in supp)


def test_case_15_quality_degradation_without_tampering():
    """15. Quality degradation without tampering: blur, resolution, and overexposure alone != fraud."""
    fixtures = make_evidence_fixture(
        doc_type="Aadhaar Card",
        quality_score=35,   # severe blur / overexposure
        ocr_conf=0.30,      # reduced OCR readability
        qr_status="DETECTED_NOT_DECODED",
        typography_score=90,
        layout_score=90,
        ela_anomaly=False
    )
    auth, risk, supp, neg, signals, rb = compute_fused_authenticity(*fixtures)
    # CRITICAL ASSERTION: Low image quality alone must NOT cause high fraud risk
    assert risk <= 35, f"Expected risk <= 35 for degraded quality alone, got {risk}"
    assert auth >= 65
    assert risk == 100 - auth
    assert len(neg) == 0


# ===========================================================================
# Canonical Mathematical Invariants
# ===========================================================================

def test_canonical_score_mathematical_coupling():
    """Verify authenticity_score and risk_score are strictly coupled: risk_score = 100 - authenticity_score."""
    for q in [20, 50, 80, 100]:
        for qr in ["DECODED_UNVERIFIED", "SIGNATURE_INVALID", "NOT_DETECTED"]:
            fixtures = make_evidence_fixture(quality_score=q, qr_status=qr)
            auth, risk, _, _, _, _ = compute_fused_authenticity(*fixtures)
            assert risk == 100 - auth
            assert 0 <= auth <= 100
            assert 0 <= risk <= 100


def test_clean_authorized_aadhaar_high_authenticity():
    """Genuinely clean authorized Aadhaar: high structural consistency + no tampering -> high authenticity."""
    sample_path = "data/uploads/test_pristine.jpg"
    if os.path.exists(sample_path):
        res = process_document(sample_path)
        assert res["authenticity_score"] >= 75, f"Expected >= 75, got {res['authenticity_score']}"
        assert res["risk_score"] == 100 - res["authenticity_score"]
        assert res["classification"] == "Likely Authentic"
        assert res["tampering"]["status"] == "NO_STRONG_ANOMALY"
        assert "supporting_evidence" in res
        assert len(res["supporting_evidence"]) > 0


def test_quality_change_without_tampering():
    """Prove that severe blur or low image quality alone does NOT trigger fraud when no tampering exists."""
    fixtures = make_evidence_fixture(
        doc_type="Aadhaar Card",
        quality_score=30,  # severe blur / degradation
        ocr_conf=0.25,     # degraded OCR
        qr_status="DETECTED_NOT_DECODED",  # scan unreadable, not invalid
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
    """Prove: HIGH STRUCTURAL CONSISTENCY + STRONG TAMPERING EVIDENCE != LIKELY AUTHENTIC."""
    fixtures = make_evidence_fixture(
        doc_type="Aadhaar Card",
        quality_score=95,
        ocr_conf=0.95,
        qr_status="DECODED_UNVERIFIED",
        cross_status="CONSISTENT",
        typography_score=98,
        layout_score=98,
        structure_score=100  # Perfect structural template consistency!
    )
    tampering = {
        "tampering_score": 75,
        "tampering_integrity_score": 25,
        "severity": "HIGH",
        "status": "STRONG_TAMPERING_EVIDENCE",
        "regions": [
            {"id": "T-01", "signal": "OVERLAY_ANOMALY", "area_px": 5000}
        ],
        "signals": [{"name": "OVERLAY_ANOMALY", "severity": "HIGH"}]
    }
    auth, risk, supp, neg, signals, rb = compute_fused_authenticity(*fixtures, tampering_result=tampering)
    
    # Must NOT be Likely Authentic (requires >= 75)
    assert auth < 50, f"Expected authenticity < 50 for HIGH tampering, got {auth}"
    assert risk > 50, f"Expected risk > 50, got {risk}"
    assert risk == 100 - auth
    classification = "Likely Authentic" if auth >= 75 else ("Review Required" if auth >= 50 else "High Suspicion")
    assert classification != "Likely Authentic"
    assert classification == "High Suspicion"
    assert any("tampering" in n.lower() for n in neg)


# ===========================================================================
# Section 27: 10 Explicit Regression Tests
# ===========================================================================

def test_clean_aadhaar_not_high_risk():
    """1. REAL / CLEAN AADHAAR: High authenticity (>= 75), risk <= 25, classification != High Suspicion."""
    fixtures = make_evidence_fixture(
        doc_type="Aadhaar Card",
        quality_score=85,
        ocr_conf=0.90,
        qr_status="DETECTED_NOT_DECODED",
        cross_status="NOT_AVAILABLE",
        typography_score=90,
        layout_score=90,
        structure_score=95
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
    assert auth >= 75, f"Expected clean Aadhaar auth >= 75, got {auth}"
    assert risk <= 25
    assert risk == 100 - auth
    assert not signals["high_suspicion_gate"]["eligible"]


def test_quality_artifact_not_tampering():
    """2. Quality artifacts (blur, scanner noise, JPEG recompression) do not become tampering evidence."""
    fixtures = make_evidence_fixture(
        doc_type="Aadhaar Card",
        quality_score=38,  # Degraded scan
        ocr_conf=0.35,     # Moderate OCR confidence
        qr_status="DETECTED_NOT_DECODED",
        typography_score=80,
        layout_score=82,
        structure_score=85
    )
    tampering = {
        "tampering_score": 5,
        "tampering_integrity_score": 95,
        "severity": "LOW",
        "status": "NO_STRONG_ANOMALY",
        "regions": [],
        "signals": [{"name": "UNIFORM_PROFILE", "severity": "LOW"}]
    }
    auth, risk, supp, neg, signals, rb = compute_fused_authenticity(*fixtures, tampering_result=tampering)
    assert not signals["high_suspicion_gate"]["eligible"]
    assert auth >= 50, f"Expected auth >= 50 for pure quality degradation, got {auth}"
    assert risk <= 50
    assert risk == 100 - auth


def test_ela_alone_not_high_risk():
    """3. ELA anomaly alone without independent corroboration cannot create HIGH SUSPICION."""
    fixtures = make_evidence_fixture(
        doc_type="Aadhaar Card",
        quality_score=80,
        ocr_conf=0.88,
        qr_status="DETECTED_NOT_DECODED",
        ela_anomaly=True,
        structure_score=90
    )
    tampering = {
        "tampering_score": 25,  # Weak ELA alone
        "tampering_integrity_score": 75,
        "severity": "LOW",
        "status": "POSSIBLE_TAMPERING",
        "regions": [{"id": "T-01", "signal": "ELA_ANOMALY", "type": "TAMPERING", "area_px": 800}],
        "signals": [{"name": "ELA_ANOMALY", "severity": "LOW"}]
    }
    auth, risk, supp, neg, signals, rb = compute_fused_authenticity(*fixtures, tampering_result=tampering)
    assert not signals["high_suspicion_gate"]["eligible"]
    assert auth >= 50, f"Expected auth >= 50 for ELA alone, got {auth}"
    assert risk <= 50
    assert risk == 100 - auth


def test_qr_not_decoded_is_neutral():
    """4. DETECTED_NOT_DECODED is neutral: 0 penalty, zero fraud contribution."""
    fixtures = make_evidence_fixture(
        doc_type="Aadhaar Card",
        qr_status="DETECTED_NOT_DECODED",
        cross_status="NOT_AVAILABLE"
    )
    auth, risk, supp, neg, signals, rb = compute_fused_authenticity(*fixtures)
    assert rb["qr"] == 0, f"Expected QR risk contribution == 0, got {rb['qr']}"
    assert not any("contradiction" in n.lower() or "compromised" in n.lower() for n in neg)


def test_signature_invalid_is_high_risk():
    """5. Cryptographic signature invalidation is strong negative evidence -> HIGH SUSPICION."""
    fixtures = make_evidence_fixture(
        doc_type="Aadhaar Card",
        qr_status="SIGNATURE_INVALID",
        cross_status="NOT_AVAILABLE"
    )
    auth, risk, supp, neg, signals, rb = compute_fused_authenticity(*fixtures)
    assert signals["high_suspicion_gate"]["eligible"]
    assert auth <= 25, f"Expected auth <= 25 for invalid signature, got {auth}"
    assert risk >= 75
    assert risk == 100 - auth
    assert any("signature" in n.lower() for n in neg)


def test_qr_ocr_mismatch_is_high_risk():
    """6. QR/OCR identity contradiction is strong negative evidence -> HIGH SUSPICION."""
    fixtures = make_evidence_fixture(
        doc_type="Aadhaar Card",
        qr_status="DECODED_UNVERIFIED",
        cross_status="INCONSISTENT"
    )
    auth, risk, supp, neg, signals, rb = compute_fused_authenticity(*fixtures)
    assert signals["high_suspicion_gate"]["eligible"]
    assert auth <= 35, f"Expected auth <= 35 for identity contradiction, got {auth}"
    assert risk >= 65
    assert risk == 100 - auth
    assert any("contradiction" in n.lower() for n in neg)


def test_privacy_redaction_not_tampering():
    """7. Digital highlighter or marker redactions (green/blackout) over PII do not cause fraud penalty."""
    fixtures = make_evidence_fixture(
        doc_type="Aadhaar Card",
        quality_score=85,
        ocr_conf=0.75,
        qr_status="DETECTED_NOT_DECODED"
    )
    tampering = {
        "tampering_score": 0,
        "tampering_integrity_score": 100,
        "severity": "NONE",
        "status": "NO_STRONG_ANOMALY",
        "regions": [
            {
                "id": "PR-01",
                "type": "USER_PRIVACY_MASK",
                "signal": "PRIVACY_REDACTION",
                "risk_contribution": 0,
                "finding": "Privacy redaction observed"
            }
        ],
        "privacy_redactions": [
            {"id": "PR-01", "type": "USER_PRIVACY_MASK", "risk_contribution": 0}
        ],
        "signals": []
    }
    auth, risk, supp, neg, signals, rb = compute_fused_authenticity(*fixtures, tampering_result=tampering)
    assert not signals["high_suspicion_gate"]["eligible"]
    assert auth >= 75, f"Expected auth >= 75 with privacy redactions, got {auth}"
    assert risk <= 25
    assert risk == 100 - auth
    assert any("privacy redaction" in s.lower() for s in supp)


def test_correlated_signals_not_double_counted():
    """8. Correlated compression signals (ELA, resampling, noise) are grouped and capped at <= 10."""
    fixtures = make_evidence_fixture(
        doc_type="Aadhaar Card",
        quality_score=80,
        ocr_conf=0.85,
        qr_status="DETECTED_NOT_DECODED",
        ela_anomaly=True,
        typography_score=90,
        layout_score=90
    )
    tampering = {
        "tampering_score": 18,  # Correlated weak signals
        "tampering_integrity_score": 82,
        "severity": "LOW",
        "status": "POSSIBLE_TAMPERING",
        "regions": [],
        "signals": [
            {"name": "ELA_ANOMALY", "severity": "LOW"},
            {"name": "RESAMPLING_ARTIFACT", "severity": "LOW"}
        ]
    }
    auth, risk, supp, neg, signals, rb = compute_fused_authenticity(*fixtures, tampering_result=tampering)
    assert not signals["high_suspicion_gate"]["eligible"]
    assert rb["image_forensics"] <= 10, f"Expected correlated forensics capped at <= 10, got {rb['image_forensics']}"
    assert auth >= 75


def test_strong_tampering_overrides_structure():
    """9. Confirmed localized tampering overrides perfect structural consistency -> HIGH SUSPICION."""
    fixtures = make_evidence_fixture(
        doc_type="Aadhaar Card",
        quality_score=95,
        ocr_conf=0.95,
        qr_status="DECODED_UNVERIFIED",
        cross_status="CONSISTENT",
        typography_score=98,
        layout_score=98,
        structure_score=100
    )
    tampering = {
        "tampering_score": 75,
        "tampering_integrity_score": 25,
        "severity": "HIGH",
        "status": "STRONG_TAMPERING_EVIDENCE",
        "regions": [
            {"id": "T-01", "signal": "OVERLAY_ANOMALY", "type": "TAMPERING", "area_px": 5000}
        ],
        "signals": [{"name": "OVERLAY_ANOMALY", "severity": "HIGH"}]
    }
    auth, risk, supp, neg, signals, rb = compute_fused_authenticity(*fixtures, tampering_result=tampering)
    assert signals["high_suspicion_gate"]["eligible"]
    assert auth < 50
    assert risk > 50
    assert risk == 100 - auth
    assert any("tampering" in n.lower() for n in neg)


def test_clean_vs_tampered_separation():
    """10. Clean vs tampered separation: clean >= 80, tampered <= 40, separation gap >= 40."""
    clean_fixtures = make_evidence_fixture(
        doc_type="Aadhaar Card",
        quality_score=90,
        ocr_conf=0.90,
        qr_status="DECODED_UNVERIFIED",
        cross_status="CONSISTENT",
        structure_score=95
    )
    clean_tampering = {
        "tampering_score": 0,
        "tampering_integrity_score": 100,
        "severity": "NONE",
        "status": "NO_STRONG_ANOMALY",
        "regions": [],
        "signals": []
    }
    clean_auth, clean_risk, _, _, _, _ = compute_fused_authenticity(*clean_fixtures, tampering_result=clean_tampering)

    tampered_fixtures = make_evidence_fixture(
        doc_type="Aadhaar Card",
        quality_score=90,
        ocr_conf=0.90,
        qr_status="DECODED_UNVERIFIED",
        cross_status="CONSISTENT",
        structure_score=95
    )
    tampered_evidence = {
        "tampering_score": 80,
        "tampering_integrity_score": 20,
        "severity": "CRITICAL",
        "status": "STRONG_TAMPERING_EVIDENCE",
        "regions": [
            {"id": "T-01", "signal": "OVERLAY_ANOMALY", "type": "TAMPERING", "area_px": 6000}
        ],
        "signals": [{"name": "OVERLAY_ANOMALY", "severity": "CRITICAL"}]
    }
    tampered_auth, tampered_risk, _, _, _, _ = compute_fused_authenticity(*tampered_fixtures, tampering_result=tampered_evidence)

    assert clean_auth >= 80, f"Expected clean auth >= 80, got {clean_auth}"
    assert tampered_auth <= 40, f"Expected tampered auth <= 40, got {tampered_auth}"
    separation = clean_auth - tampered_auth
    assert separation >= 40, f"Expected separation >= 40 points, got {separation}"

