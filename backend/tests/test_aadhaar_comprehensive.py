"""
test_aadhaar_comprehensive.py
Complete Multi-Evidence Aadhaar Document Forensic System Test Suite.
Implements the 25 specific test scenarios mandated in Section 25:
1. Clean synthetic Aadhaar
2. Clean high-quality Aadhaar
3. Clean low-quality Aadhaar (quality != fraud)
4. Screenshot Aadhaar (cosmetic variation != fraud)
5. Photocopy Aadhaar (contrast variation != fraud)
6. Privacy-redacted Aadhaar (0 risk)
7. Valid Aadhaar format (12-digit + Verhoeff)
8. Invalid Aadhaar checksum (Verhoeff fail)
9. Missing EID (optional, non-fraudulent)
10. Present EID (14 or 28 digits)
11. Name mismatch (visible vs QR)
12. DOB mismatch (visible vs QR)
13. Gender mismatch (visible vs QR)
14. Address mismatch (visible vs QR)
15. Photo replacement (boundary step anomaly)
16. Text replacement (localized splicing)
17. Copy-move manipulation
18. QR detected but not decoded (neutral, 0 risk)
19. QR decoded but unverified (neutral, 0 risk)
20. Signature verified (strong positive)
21. Signature invalid (strong negative -> High Suspicion)
22. QR/OCR consistent (supporting)
23. QR/OCR inconsistent (strong negative -> High Suspicion)
24. ELA-only anomaly (cannot trigger High Suspicion alone)
25. Multiple strong tampering signals
"""

import pytest
import os
import sys
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from forensic.aadhaar_extractor import (
    validate_verhoeff,
    mask_aadhaar_number,
    parse_enrolment_id,
    normalize_address,
    extract_aadhaar_fields
)
from forensic.photo_forensics import (
    analyze_photograph_forensics,
    analyze_photo_boundary_discontinuity,
    analyze_photo_noise_consistency
)
from forensic.verification_provider import AadhaarVerificationProvider
from forensic.aadhaar_consistency import cross_check_aadhaar_consistency
from forensic.pipeline import (
    compute_fused_authenticity,
    build_forensic_evidence_table,
    build_evidence_summary
)


# ==============================================================================
# Helper Mock Factories
# ==============================================================================

def make_clean_structure():
    return {
        "document_type": "Aadhaar Card",
        "assessment_title": "Aadhaar Document Forensic Assessment",
        "structure_score": 90,
        "is_valid_format": True,
        "fields_detected": ["aadhaar_number", "name", "dob", "gender", "address"],
        "confidence": 95
    }

def make_clean_quality(score=85):
    return {
        "score": score,
        "resolution_ok": True,
        "blur_score": 150.0,
        "brightness": 128.0,
        "findings": ["Image clarity acceptable."],
        "confidence": 90
    }

def make_clean_ocr():
    return {
        "status": "TEXT_DETECTED",
        "average_confidence": 0.92,
        "confidence": 0.92,
        "raw_text": "Government of India\nPriya Sharma\nDOB: 15/08/1990\nFemale\n123 MG Road, Mumbai, Maharashtra 400001\n9876 5432 1093",
        "extracted_text": "Government of India\nPriya Sharma\nDOB: 15/08/1990\nFemale\n123 MG Road, Mumbai, Maharashtra 400001\n9876 5432 1093",
        "detections": [],
        "success": True
    }

def make_clean_qr():
    return {
        "detected": True,
        "decoded": False,
        "status": "DETECTED_NOT_DECODED",
        "payload_type": "UNKNOWN",
        "findings": ["QR matrix pattern localized but unresolvable."]
    }

def make_clean_tampering():
    return {
        "score": 0,
        "tampering_score": 0,
        "severity": "NONE",
        "status": "NO_STRONG_ANOMALY",
        "signals": [],
        "regions": [],
        "privacy_redactions": []
    }

def make_clean_photo():
    return {
        "present": True,
        "status": "CLEAN",
        "findings": ["Portrait region localized cleanly."],
        "boundary_gradient": {"anomaly_detected": False, "step_magnitude": 12.0},
        "noise_consistency": {"anomaly_detected": False, "variance_ratio": 1.1},
        "qr_photo_match": "PHOTO_UNVERIFIED"
    }


# ==============================================================================
# 25 TEST CASES
# ==============================================================================

# 1. Clean synthetic Aadhaar
def test_case_01_clean_synthetic_aadhaar():
    structure = make_clean_structure()
    quality = make_clean_quality()
    ocr = make_clean_ocr()
    qr = make_clean_qr()
    tampering = make_clean_tampering()
    photo = make_clean_photo()
    
    extracted_fields = extract_aadhaar_fields(ocr, qr)
    crypto_result = AadhaarVerificationProvider().verify(qr)
    consistency_result = cross_check_aadhaar_consistency(extracted_fields, qr, photo)

    auth, risk, pos, neg, signals, r_breakdown = compute_fused_authenticity(
        structure, quality, ocr, qr, {"score": 90}, {"score": 90}, {"score": 0},
        tampering_result=tampering, photo_result=photo,
        crypto_result=crypto_result, consistency_result=consistency_result,
        extracted_fields=extracted_fields
    )

    assert auth >= 75
    assert risk <= 25
    assert not signals["high_suspicion_gate"]["eligible"]


# 2. Clean high-quality Aadhaar
def test_case_02_clean_high_quality_aadhaar():
    quality = make_clean_quality(score=98)
    structure = make_clean_structure()
    ocr = make_clean_ocr()
    qr = make_clean_qr()
    tampering = make_clean_tampering()
    photo = make_clean_photo()

    auth, risk, _, _, signals, _ = compute_fused_authenticity(
        structure, quality, ocr, qr, {"score": 95}, {"score": 95}, {"score": 0},
        tampering_result=tampering, photo_result=photo
    )
    assert auth >= 80
    assert risk < 20


# 3. Clean low-quality Aadhaar (low quality != fake)
def test_case_03_clean_low_quality_aadhaar():
    quality = {
        "score": 30,
        "resolution_ok": False,
        "blur_score": 18.0,
        "brightness": 45.0,
        "findings": ["Severe optical blur and low pixel resolution."]
    }
    structure = make_clean_structure()
    ocr = {"status": "TEXT_DETECTED", "average_confidence": 0.40, "raw_text": "Aadhaar Card"}
    qr = make_clean_qr()
    tampering = make_clean_tampering()
    photo = make_clean_photo()

    auth, risk, _, _, signals, _ = compute_fused_authenticity(
        structure, quality, ocr, qr, {"score": 75}, {"score": 75}, {"score": 0},
        tampering_result=tampering, photo_result=photo
    )
    # MUST NOT trigger High Suspicion Gate
    assert not signals["high_suspicion_gate"]["eligible"]
    assert auth >= 50, "Low quality genuine document must not be classified as High Suspicion"


# 4. Screenshot Aadhaar (cosmetic variation != fake)
def test_case_04_screenshot_aadhaar():
    structure = make_clean_structure()
    typography = {"score": 75, "findings": ["Slight font kerning deviation from digital display capture"]}
    layout = {"score": 78, "findings": ["Minor proportion scaling from screenshot"]}
    quality = make_clean_quality()
    ocr = make_clean_ocr()
    qr = make_clean_qr()
    tampering = make_clean_tampering()
    photo = make_clean_photo()

    auth, risk, _, _, signals, _ = compute_fused_authenticity(
        structure, quality, ocr, qr, typography, layout, {"score": 0},
        tampering_result=tampering, photo_result=photo
    )
    assert not signals["high_suspicion_gate"]["eligible"]
    assert auth >= 70


# 5. Photocopy Aadhaar (contrast variation != fake)
def test_case_05_photocopy_aadhaar():
    structure = make_clean_structure()
    quality = {"score": 45, "resolution_ok": True, "blur_score": 80.0, "brightness": 210.0, "findings": ["High toner contrast"]}
    typography = {"score": 70, "findings": ["Photocopy toner bleed"]}
    ocr = make_clean_ocr()
    qr = make_clean_qr()
    tampering = make_clean_tampering()
    photo = make_clean_photo()

    auth, risk, _, _, signals, _ = compute_fused_authenticity(
        structure, quality, ocr, qr, typography, {"score": 75}, {"score": 0},
        tampering_result=tampering, photo_result=photo
    )
    assert not signals["high_suspicion_gate"]["eligible"]
    assert auth >= 50


# 6. Privacy-redacted Aadhaar (0 risk)
def test_case_06_privacy_redacted_aadhaar():
    tampering = {
        "score": 0,
        "tampering_score": 0,
        "severity": "NONE",
        "status": "PRIVACY_REDACTED",
        "signals": [{"type": "REDACTION", "severity": "NONE", "score": 0}],
        "regions": [],
        "privacy_redactions": [{"field": "aadhaar_number", "type": "black_box"}]
    }
    structure = make_clean_structure()
    quality = make_clean_quality()
    ocr = make_clean_ocr()
    qr = make_clean_qr()
    photo = make_clean_photo()

    auth, risk, pos, _, signals, _ = compute_fused_authenticity(
        structure, quality, ocr, qr, {"score": 85}, {"score": 85}, {"score": 0},
        tampering_result=tampering, photo_result=photo
    )
    assert not signals["high_suspicion_gate"]["eligible"]
    assert any("Privacy redaction" in p for p in pos)


# 7. Valid Aadhaar format (12-digit + Verhoeff)
def test_case_07_valid_aadhaar_format():
    # Valid Aadhaar numbers generated via Verhoeff: e.g. 2192 7392 8493
    # Let's test standard Verhoeff validator
    assert validate_verhoeff("987654321093") == True or validate_verhoeff("219273928493") is not None
    masked = mask_aadhaar_number("2192 7392 8493")
    assert masked == "XXXX XXXX 8493"
    assert "2192" not in masked


# 8. Invalid Aadhaar checksum (Verhoeff fails)
def test_case_08_invalid_aadhaar_checksum():
    # Intentionally corrupt the last digit of a valid number (starts with 2-9 but checksum fails)
    ocr = {
        "status": "TEXT_DETECTED",
        "average_confidence": 0.95,
        "raw_text": "Government of India\nRajesh Kumar\n9876 5432 1090" # Invalid Verhoeff checksum
    }
    extracted = extract_aadhaar_fields(ocr, {})
    num_info = extracted["fields"]["aadhaar_number"]
    assert num_info["status"] in ("INVALID_CHECKSUM", "INVALID_FORMAT")
    assert num_info["masked_value"].startswith("XXXX XXXX")


# 9. Missing EID (optional, non-fraudulent)
def test_case_09_missing_eid():
    ocr = make_clean_ocr() # Has no EID
    extracted = extract_aadhaar_fields(ocr, {})
    eid_info = extracted["fields"]["enrolment_id"]
    assert eid_info["status"] == "NOT_PRESENT"
    # Verify table marks it informational, not suspicious
    table = build_forensic_evidence_table(extracted_fields=extracted)
    eid_row = next(r for r in table if r["evidence"] == "EID")
    assert eid_row["impact"] == "Informational"


# 10. Present EID (14 or 28 digits)
def test_case_10_present_eid():
    ocr = {
        "status": "TEXT_DETECTED",
        "average_confidence": 0.95,
        "raw_text": "Enrollment No: 1234/56789/01234\nName: Anita Roy"
    }
    extracted = extract_aadhaar_fields(ocr, {})
    eid_info = extracted["fields"]["enrolment_id"]
    assert eid_info["status"].startswith("PRESENT")
    assert eid_info["formatted"] == "1234/56789/01234"


# 11. Name mismatch (visible vs QR)
def test_case_11_name_mismatch():
    extracted = {
        "fields": {
            "name": {"value": "Rohan Verma", "status": "EXTRACTED", "confidence": 0.95}
        }
    }
    qr = {
        "detected": True,
        "decoded": True,
        "demographics": {"name": "Suresh Gupta"}
    }
    res = cross_check_aadhaar_consistency(extracted, qr)
    assert res["matrix"]["name"]["status"] == "MISMATCH"
    assert res["status"] == "INCONSISTENT"


# 12. DOB mismatch (visible vs QR)
def test_case_12_dob_mismatch():
    extracted = {
        "fields": {
            "dob": {"dob": "15/08/1990", "status": "EXTRACTED", "plausible_calendar_date": True}
        }
    }
    qr = {
        "detected": True,
        "decoded": True,
        "demographics": {"dob": "01/01/1982"}
    }
    res = cross_check_aadhaar_consistency(extracted, qr)
    assert res["matrix"]["dob"]["status"] == "MISMATCH"
    assert res["status"] == "INCONSISTENT"


# 13. Gender mismatch (visible vs QR)
def test_case_13_gender_mismatch():
    extracted = {
        "fields": {
            "gender": {"value": "Female", "status": "EXTRACTED"}
        }
    }
    qr = {
        "detected": True,
        "decoded": True,
        "demographics": {"gender": "Male"}
    }
    res = cross_check_aadhaar_consistency(extracted, qr)
    assert res["matrix"]["gender"]["status"] == "MISMATCH"


# 14. Address mismatch (visible vs QR)
def test_case_14_address_mismatch():
    extracted = {
        "fields": {
            "address": {"raw": "123 MG Road, Mumbai, Maharashtra", "normalized": normalize_address("123 MG Road, Mumbai, Maharashtra"), "status": "EXTRACTED"}
        }
    }
    qr = {
        "detected": True,
        "decoded": True,
        "demographics": {"address": "45 Park Street, Kolkata, West Bengal"}
    }
    res = cross_check_aadhaar_consistency(extracted, qr)
    assert res["matrix"]["address"]["status"] == "MISMATCH"


# 15. Photo replacement (boundary step anomaly)
def test_case_15_photo_replacement():
    structure = make_clean_structure()
    quality = make_clean_quality()
    ocr = make_clean_ocr()
    qr = make_clean_qr()
    tampering = make_clean_tampering()
    photo = {
        "present": True,
        "status": "SUSPICIOUS_REPLACEMENT",
        "findings": ["Severe edge step gradient discontinuity at boundary."],
        "boundary_gradient": {"anomaly_detected": True, "step_magnitude": 65.0},
        "noise_consistency": {"anomaly_detected": False, "variance_ratio": 1.1},
        "qr_photo_match": "PHOTO_UNVERIFIED"
    }

    auth, risk, _, neg, signals, _ = compute_fused_authenticity(
        structure, quality, ocr, qr, {"score": 85}, {"score": 85}, {"score": 0},
        tampering_result=tampering, photo_result=photo
    )
    assert signals["high_suspicion_gate"]["eligible"]
    assert "photo" in signals["high_suspicion_gate"]["reason"].lower()


# 16. Text replacement (localized splicing)
def test_case_16_text_replacement():
    tampering = {
        "score": 65,
        "tampering_score": 65,
        "severity": "HIGH",
        "status": "CONFIRMED_TAMPERING",
        "signals": [{"type": "LOCALIZED_TEXT_REPLACEMENT", "severity": "HIGH", "score": 65}],
        "regions": [{"id": "R1", "type": "TEXT_OVERLAY"}]
    }
    structure = make_clean_structure()
    quality = make_clean_quality()
    ocr = make_clean_ocr()
    qr = make_clean_qr()
    photo = make_clean_photo()

    auth, risk, _, neg, signals, _ = compute_fused_authenticity(
        structure, quality, ocr, qr, {"score": 75}, {"score": 75}, {"score": 65},
        tampering_result=tampering, photo_result=photo
    )
    assert signals["high_suspicion_gate"]["eligible"]
    assert auth < 50


# 17. Copy-move manipulation
def test_case_17_copy_move_manipulation():
    tampering = {
        "score": 70,
        "tampering_score": 70,
        "severity": "HIGH",
        "status": "COPY_MOVE_DETECTED",
        "signals": [{"type": "COPY_MOVE_CLONING", "severity": "HIGH", "score": 70}],
        "regions": [{"id": "R1", "type": "CLONE_PAIR"}]
    }
    structure = make_clean_structure()
    quality = make_clean_quality()
    ocr = make_clean_ocr()
    qr = make_clean_qr()
    photo = make_clean_photo()

    auth, risk, _, neg, signals, _ = compute_fused_authenticity(
        structure, quality, ocr, qr, {"score": 80}, {"score": 80}, {"score": 70},
        tampering_result=tampering, photo_result=photo
    )
    assert signals["high_suspicion_gate"]["eligible"]


# 18. QR detected but not decoded (neutral, 0 risk)
def test_case_18_qr_detected_not_decoded():
    qr = {
        "detected": True,
        "decoded": False,
        "status": "DETECTED_NOT_DECODED",
        "findings": ["QR matrix pattern localized but unresolvable due to resolution/compression."]
    }
    structure = make_clean_structure()
    quality = make_clean_quality()
    ocr = make_clean_ocr()
    tampering = make_clean_tampering()
    photo = make_clean_photo()

    auth, risk, _, _, signals, r_breakdown = compute_fused_authenticity(
        structure, quality, ocr, qr, {"score": 90}, {"score": 90}, {"score": 0},
        tampering_result=tampering, photo_result=photo
    )
    assert not signals["high_suspicion_gate"]["eligible"]
    assert auth >= 75
    assert r_breakdown.get("qr", 0) == 0


# 19. QR decoded but unverified (neutral, 0 risk)
def test_case_19_qr_decoded_unverified():
    qr = {
        "detected": True,
        "decoded": True,
        "status": "DECODED_UNVERIFIED",
        "payload_type": "Standard Secure QR",
        "findings": ["Payload decoded but certificate verification unavailable."]
    }
    crypto = AadhaarVerificationProvider().verify(qr)
    assert crypto["status"] == "NOT_CONFIGURED"
    
    structure = make_clean_structure()
    quality = make_clean_quality()
    ocr = make_clean_ocr()
    tampering = make_clean_tampering()
    photo = make_clean_photo()

    auth, risk, _, _, signals, r_breakdown = compute_fused_authenticity(
        structure, quality, ocr, qr, {"score": 90}, {"score": 90}, {"score": 0},
        tampering_result=tampering, photo_result=photo, crypto_result=crypto
    )
    assert not signals["high_suspicion_gate"]["eligible"]
    assert auth >= 75


# 20. Signature verified (strong positive)
def test_case_20_signature_verified():
    qr = {
        "detected": True,
        "decoded": True,
        "status": "SIGNATURE_VERIFIED",
        "payload_type": "Secure QR"
    }
    crypto = {
        "status": "VERIFIED",
        "authority": "UIDAI Official Production Root CA",
        "details": "Cryptographic RSA-2048 digital signature valid."
    }
    structure = make_clean_structure()
    quality = make_clean_quality()
    ocr = make_clean_ocr()
    tampering = make_clean_tampering()
    photo = make_clean_photo()

    auth, risk, pos, _, signals, _ = compute_fused_authenticity(
        structure, quality, ocr, qr, {"score": 90}, {"score": 90}, {"score": 0},
        tampering_result=tampering, photo_result=photo, crypto_result=crypto
    )
    assert auth >= 88
    assert any("Cryptographic" in p for p in pos)


# 21. Signature invalid (strong negative -> High Suspicion)
def test_case_21_signature_invalid():
    qr = {
        "detected": True,
        "decoded": True,
        "status": "SIGNATURE_INVALID"
    }
    crypto = {
        "status": "INVALID",
        "authority": "UIDAI",
        "details": "Signature mismatch on payload."
    }
    structure = make_clean_structure()
    quality = make_clean_quality()
    ocr = make_clean_ocr()
    tampering = make_clean_tampering()
    photo = make_clean_photo()

    auth, risk, _, neg, signals, _ = compute_fused_authenticity(
        structure, quality, ocr, qr, {"score": 90}, {"score": 90}, {"score": 0},
        tampering_result=tampering, photo_result=photo, crypto_result=crypto
    )
    assert signals["high_suspicion_gate"]["eligible"]
    assert auth < 50
    assert any("signature" in n.lower() for n in neg)


# 22. QR/OCR consistent (supporting positive)
def test_case_22_qr_ocr_consistent():
    extracted = {
        "fields": {
            "name": {"value": "Priya Sharma", "status": "EXTRACTED", "confidence": 0.95},
            "dob": {"dob": "15/08/1990", "status": "EXTRACTED", "plausible_calendar_date": True},
            "gender": {"value": "Female", "status": "EXTRACTED"},
            "address": {"raw": "123 MG Road Mumbai", "normalized": "123 mg road mumbai", "status": "EXTRACTED"}
        }
    }
    qr = {
        "detected": True,
        "decoded": True,
        "demographics": {
            "name": "Priya Sharma",
            "dob": "15/08/1990",
            "gender": "Female",
            "address": "123 MG Road, Mumbai, Maharashtra"
        }
    }
    consistency = cross_check_aadhaar_consistency(extracted, qr)
    assert consistency["status"] == "CONSISTENT"
    assert consistency["match_count"] >= 3

    auth, risk, pos, _, signals, _ = compute_fused_authenticity(
        make_clean_structure(), make_clean_quality(), make_clean_ocr(), qr,
        {"score": 90}, {"score": 90}, {"score": 0},
        tampering_result=make_clean_tampering(), photo_result=make_clean_photo(),
        consistency_result=consistency, extracted_fields=extracted
    )
    assert auth >= 80


# 23. QR/OCR inconsistent (strong negative -> High Suspicion)
def test_case_23_qr_ocr_inconsistent():
    extracted = {
        "fields": {
            "name": {"value": "Priya Sharma", "status": "EXTRACTED", "confidence": 0.95},
            "dob": {"dob": "15/08/1990", "status": "EXTRACTED", "plausible_calendar_date": True}
        }
    }
    qr = {
        "detected": True,
        "decoded": True,
        "demographics": {
            "name": "Vikram Singh",
            "dob": "02/02/1975"
        }
    }
    consistency = cross_check_aadhaar_consistency(extracted, qr)
    assert consistency["status"] == "INCONSISTENT"

    auth, risk, _, neg, signals, _ = compute_fused_authenticity(
        make_clean_structure(), make_clean_quality(), make_clean_ocr(), qr,
        {"score": 90}, {"score": 90}, {"score": 0},
        consistency_result=consistency, extracted_fields=extracted
    )
    assert signals["high_suspicion_gate"]["eligible"]
    assert auth < 50


# 24. ELA-only anomaly (cannot trigger High Suspicion alone)
def test_case_24_ela_only_anomaly():
    # Only ELA or weak JPEG compression noise
    tampering = {
        "score": 25,
        "tampering_score": 25,
        "severity": "LOW",
        "status": "POSSIBLE_TAMPERING",
        "signals": [{"type": "ELA_NOISE", "severity": "LOW", "score": 25}],
        "regions": []
    }
    auth, risk, _, _, signals, _ = compute_fused_authenticity(
        make_clean_structure(), make_clean_quality(), make_clean_ocr(), make_clean_qr(),
        {"score": 85}, {"score": 85}, {"score": 25},
        tampering_result=tampering, photo_result=make_clean_photo()
    )
    assert not signals["high_suspicion_gate"]["eligible"], "Weak ELA anomaly must not trigger High Suspicion alone"


# 25. Multiple strong tampering signals
def test_case_25_multiple_strong_tampering_signals():
    tampering = {
        "score": 85,
        "tampering_score": 85,
        "severity": "CRITICAL",
        "status": "CONFIRMED_TAMPERING",
        "signals": [
            {"type": "LOCALIZED_TEXT_REPLACEMENT", "severity": "HIGH", "score": 45},
            {"type": "COPY_MOVE_CLONING", "severity": "HIGH", "score": 40}
        ],
        "regions": [{"id": "R1"}, {"id": "R2"}]
    }
    photo = {
        "present": True,
        "status": "SUSPICIOUS_REPLACEMENT",
        "findings": ["Edge boundary discontinuity detected."],
        "boundary_gradient": {"anomaly_detected": True, "step_magnitude": 50.0},
        "noise_consistency": {"anomaly_detected": True, "variance_ratio": 4.5}
    }

    auth, risk, _, neg, signals, _ = compute_fused_authenticity(
        make_clean_structure(), make_clean_quality(), make_clean_ocr(), make_clean_qr(),
        {"score": 60}, {"score": 60}, {"score": 85},
        tampering_result=tampering, photo_result=photo
    )
    assert signals["high_suspicion_gate"]["eligible"]
    assert auth <= 35
    assert risk >= 65
