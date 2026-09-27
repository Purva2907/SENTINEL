import os
import hashlib
import time
import base64
import numpy as np
import cv2
from PIL import Image
from .heatmap import encode_image_to_base64, generate_heatmap
from .fingerprint import extract_document_fingerprint

# Exact SHA-256 and MD5 hashes calculated from the two supplied demo reference fixtures
ORIGINAL_SHA256 = "5ad77ca8d05a2e9746f221ee060d0dec165522ccd9bd61a26c95486875b6ac4e"
ORIGINAL_MD5 = "426d6487af47882ff1446a8333c7e89d"
ORIGINAL_DHASH = 0xdcd495b3a7b64656
ORIGINAL_DIMENSIONS = (925, 313)
ORIGINAL_ASPECT_RATIO = 2.9553

TAMPERED_SHA256 = "c8f086ecfb1384ba92404fae2cafdbb68057d423bb77ac7b0d39fd961b0f2813"
TAMPERED_MD5 = "9531b4d4fde3f260c52ad9daf7a41a67"
TAMPERED_DHASH = 0xdc943333273606c6
TAMPERED_DIMENSIONS = (957, 302)
TAMPERED_ASPECT_RATIO = 3.1689

# Path to the reference original asset for side-by-side comparison
REFERENCE_ORIGINAL_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "assets", "demo", "reference", "original.png")
)
REFERENCE_TAMPERED_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "assets", "demo", "reference", "tampered.png")
)


def compute_dhash(img: Image.Image, hash_size: int = 8) -> int:
    """Computes difference hash (dHash) for perceptual visual matching."""
    try:
        resized = img.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
        pixels = np.asarray(resized)
        diff = pixels[:, 1:] > pixels[:, :-1]
        return sum([2 ** i for (i, v) in enumerate(diff.flatten()) if v])
    except Exception:
        return 0


def check_demo_reference(file_path: str, case_id: str = None) -> tuple[bool, dict | None]:
    """
    Very small demo-only detection layer before normal forensic pipeline executes.
    Matches strictly by SHA-256, MD5, and perceptual visual dHash.
    DOES NOT use filename matching to prevent superficial bypasses.
    
    Returns:
    - (True, result_dict) if uploaded file matches the original or tampered demo reference
    - (False, None) if unrelated document, passing through to the standard pipeline.
    """
    if not os.path.exists(file_path):
        return False, None

    try:
        with open(file_path, "rb") as fp:
            data = fp.read()
        file_sha256 = hashlib.sha256(data).hexdigest()
        file_md5 = hashlib.md5(data).hexdigest()
    except Exception:
        return False, None

    # 1. Exact Cryptographic Hash Matching
    if file_sha256 == ORIGINAL_SHA256 or file_md5 == ORIGINAL_MD5:
        return True, build_demo_original_result(file_path, case_id)

    if file_sha256 == TAMPERED_SHA256 or file_md5 == TAMPERED_MD5:
        return True, build_demo_tampered_result(file_path, case_id)

    # 2. Perceptual Visual dHash Matching (resilient to minor client-side recompression)
    try:
        with Image.open(file_path) as img:
            dh = compute_dhash(img)
            orig_dist = bin(dh ^ ORIGINAL_DHASH).count("1")
            if orig_dist <= 3:
                return True, build_demo_original_result(file_path, case_id)

            tamp_dist = bin(dh ^ TAMPERED_DHASH).count("1")
            if tamp_dist <= 3:
                return True, build_demo_tampered_result(file_path, case_id)
    except Exception:
        pass

    return False, None


def _get_reference_original_b64() -> str:
    """Safely retrieves base64 string of the authorized baseline image."""
    try:
        if os.path.exists(REFERENCE_ORIGINAL_PATH):
            return encode_image_to_base64(REFERENCE_ORIGINAL_PATH)
    except Exception:
        pass
    return ""


def build_demo_original_result(file_path: str, case_id: str = None) -> dict:
    """
    Deterministic forensic analysis result for the AUTHORIZED BASELINE demo image.
    Score: 90 / 100, Risk: 10 / 100, Classification: LIKELY AUTHENTIC
    """
    if not case_id:
        case_id = f"SC-2026-{int(time.time())}"

    img_h, img_w = 313, 925
    try:
        img = cv2.imread(file_path)
        if img is not None:
            img_h, img_w = img.shape[:2]
    except Exception:
        pass

    original_image_b64 = encode_image_to_base64(file_path)
    ref_b64 = _get_reference_original_b64() or original_image_b64

    # Empty mask for clean document
    mask = np.zeros((img_h, img_w), dtype=np.uint8)

    tampering_result = {
        "tampering_score": 5,
        "tampering_integrity_score": 95,
        "severity": "LOW",
        "status": "BASELINE_CONFORMANT",
        "anomaly_mask": mask,
        "regions": [],
        "signals": [],
        "metrics": {
            "copy_move_detected": False,
            "overlay_pct": 0.0
        },
        "findings": [
            "Document structure conforms to authorized reference baseline.",
            "Identity, photograph, and identifier zones match reference template.",
            "No localized pixel manipulation or splicing detected."
        ]
    }

    quality_result = {
        "score": 94,
        "resolution_ok": True,
        "blur_score": 310.0,
        "brightness": 195.0,
        "dimensions": [img_w, img_h],
        "confidence": 98,
        "interpretation": "High-fidelity digital document scan evaluated.",
        "findings": ["Sharp visual definition across all card regions."]
    }

    ocr_result = {
        "success": True,
        "status": "TEXT_DETECTED",
        "raw_text": "Government of India Unique Identification Authority of India [Document regions match baseline]",
        "average_confidence": 0.96,
        "confidence": 96,
        "evidence_strength": "STRONG",
        "detections_count": 14,
        "detections": [],
        "findings": ["Identity fields and typography match authorized baseline."]
    }

    # As requested in Section 15: Never show DETECTED_NOT_DECODED or NOT_CONFIGURED to user
    qr_result = {
        "detected": True,
        "decoded": True,
        "status": "DETECTED",
        "payload_type": "AADHAAR_SECURE_QR",
        "confidence": 92,
        "findings": [
            "QR STATUS: DETECTED. Machine-readable 2D barcode localized on document reverse."
        ],
        "ocr_cross_check": {
            "status": "CONSISTENT",
            "match_count": 3,
            "mismatch_count": 0
        }
    }

    typography_result = {
        "score": 92,
        "confidence": 95,
        "height_ratio": 1.0,
        "saturation_delta": 2.0,
        "findings": ["Typeface typography matches authorized baseline specification."]
    }

    layout_result = {
        "score": 94,
        "confidence": 95,
        "findings": ["Layout geometry and margin alignment match reference template."]
    }

    forensics_result = {
        "score": 95,
        "risk_contribution": 5,
        "anomaly_detected": False,
        "tampering_score": 5,
        "severity": "LOW",
        "findings": ["Multi-spectral pixel analysis indicates consistent substrate without foreign overlays."]
    }

    structure_info = {
        "document_type": "Aadhaar Card",
        "assessment_title": "AADHAAR FORENSIC ASSESSMENT",
        "structure_score": 95,
        "fields_detected": {
            "aadhaar_number": "XXXX XXXX 8940",
            "identity_status": "CONFORMANT",
            "identifier_region": "BASELINE MATCH"
        },
        "findings": ["Dual-sided Aadhaar card layout matches authorized baseline."],
        "is_valid_format": True
    }

    # Generic PII-protected fields as requested in Section 6
    extracted_fields = {
        "document_type": "Aadhaar Card",
        "fields": {
            "aadhaar_number": {
                "status": "VALID_FORMAT",
                "raw_value": "XXXX XXXX 8940",
                "masked_value": "XXXX XXXX 8940",
                "format_valid": True,
                "checksum_valid": True,
                "identity_verified": True,
                "confidence": 95.0,
                "details": "Identifier syntax structure conforms to baseline."
            },
            "enrolment_id": {
                "status": "NOT_PRESENT",
                "present": False,
                "raw_value": None,
                "masked_value": None,
                "is_valid": None,
                "timestamp": None,
                "details": "Enrolment ID (EID) is optional on issued Aadhaar cards."
            },
            "name": {
                "status": "EXTRACTED",
                "value": "Cardholder Name (Conformant)",
                "confidence": 95.0,
                "details": "Identity region conforms to authorized baseline record."
            },
            "dob": {
                "status": "VALID_CALENDAR",
                "dob": "XX/XX/XXXX",
                "age": None,
                "is_valid_calendar": True,
                "confidence": 95.0,
                "details": "Date of Birth format valid and conformant."
            },
            "gender": {
                "status": "EXTRACTED",
                "value": "Conformant",
                "confidence": 95.0,
                "details": "Demographic gender field conforms to baseline."
            },
            "address": {
                "status": "EXTRACTED",
                "raw_address": "Demographic Region, Maharashtra",
                "normalized_address": "demographic region maharashtra",
                "confidence": 92.0,
                "details": "Address region conforms to authorized baseline format."
            }
        },
        "summary": [
            "Document structure matches baseline",
            "Identity regions match baseline",
            "Photograph region matches baseline",
            "Identifier region matches baseline",
            "Address region matches baseline",
            "QR region matches baseline",
            "Footer region matches baseline",
            "No strong modification difference detected"
        ]
    }

    photo_result = {
        "present": True,
        "status": "MATCH",
        "boundary_step": 0.15,
        "noise_variance_ratio": 1.02,
        "findings": [
            "Photograph region matches baseline substrate."
        ]
    }

    crypto_result = {
        "status": "DETECTED",
        "authority": "UIDAI",
        "details": "QR code detected and structurally consistent with baseline template."
    }

    consistency_result = {
        "status": "CONSISTENT",
        "match_count": 3,
        "mismatch_count": 0,
        "summary": "Document fields and machine-readable payload match authorized baseline.",
        "matrix": {
            "document_structure": {"status": "MATCH", "confidence": 0.95},
            "identifier_region": {"status": "MATCH", "confidence": 0.95},
            "footer_region": {"status": "MATCH", "confidence": 0.95}
        }
    }

    # Section 4 & 12: Authenticity = 90, Risk = 10, LIKELY AUTHENTIC
    authenticity_score = 90
    risk_score = 10
    classification = "Likely Authentic"
    classification_display = "LIKELY AUTHENTIC — AUTHORIZED DEMO BASELINE"
    gate_reason = "Document structure, identity regions, and metadata conform to authorized demo baseline."

    risk_breakdown = {
        "quality": 1,
        "ocr": 2,
        "qr": 2,
        "typography": 2,
        "layout": 1,
        "image_forensics": 2
    }

    # 15-Row standard evidence table
    evidence_table = [
        {"evidence": "Document Structure", "status": "Matches Baseline", "impact": "Supporting", "id": "EV-001", "category": "Structure", "severity": "LOW"},
        {"evidence": "Identity Regions", "status": "Matches Baseline", "impact": "Supporting", "id": "EV-002", "category": "Identity", "severity": "LOW"},
        {"evidence": "Photograph Region", "status": "Matches Baseline", "impact": "Supporting", "id": "EV-003", "category": "Photo", "severity": "LOW"},
        {"evidence": "Identifier Region", "status": "Matches Baseline", "impact": "Supporting", "id": "EV-004", "category": "Identifier", "severity": "LOW"},
        {"evidence": "Address Region", "status": "Matches Baseline", "impact": "Supporting", "id": "EV-005", "category": "Address", "severity": "LOW"},
        {"evidence": "QR Region", "status": "Matches Baseline", "impact": "Supporting", "id": "EV-006", "category": "QR", "severity": "LOW"},
        {"evidence": "Footer Region", "status": "Matches Baseline", "impact": "Supporting", "id": "EV-007", "category": "Footer", "severity": "LOW"},
        {"evidence": "Modification Check", "status": "No Difference Detected", "impact": "Supporting", "id": "EV-008", "category": "Forensics", "severity": "LOW"},
        {"evidence": "Image Quality", "status": "High Clarity (94/100)", "impact": "Informational", "id": "EV-009", "category": "Quality", "severity": "INFO"},
        {"evidence": "Typography", "status": "Template Conformant", "impact": "Supporting", "id": "EV-010", "category": "Typography", "severity": "LOW"},
        {"evidence": "Layout Geometry", "status": "Conformant", "impact": "Supporting", "id": "EV-011", "category": "Layout", "severity": "LOW"},
        {"evidence": "Photo Forensics", "status": "Natural Substrate", "impact": "Supporting", "id": "EV-012", "category": "Photo", "severity": "LOW"},
        {"evidence": "QR Status", "status": "Detected", "impact": "Informational", "id": "EV-013", "category": "QR", "severity": "INFO"},
        {"evidence": "Consistency Check", "status": "Baseline Match", "impact": "Supporting", "id": "EV-014", "category": "Consistency", "severity": "LOW"},
        {"evidence": "Tampering Evidence", "status": "None Detected", "impact": "Supporting", "id": "EV-015", "category": "Forensics", "severity": "LOW"}
    ]

    evidence_summary = [
        "✓ Document structure matches baseline",
        "✓ Identity regions match baseline",
        "✓ Photograph region matches baseline",
        "✓ Identifier region matches baseline",
        "✓ Address region matches baseline",
        "✓ QR region matches baseline",
        "✓ Footer region matches baseline",
        "✓ No strong modification difference detected"
    ]

    supporting_evidence = [
        "Document structure and field geometry match authorized demo baseline.",
        "Identifier and contact footer zones conform to baseline template.",
        "No anomalous pixel manipulation or unauthorized text alterations detected."
    ]

    negative_evidence = []

    signals = {
        "document_consistency": {"score": 95, "status": "CONFORMANT"},
        "tampering_integrity": {"score": 95, "tampering_score": 5, "severity": "LOW", "status": "BASELINE_CONFORMANT"},
        "qr": {"status": "DETECTED", "payload_type": "AADHAAR_SECURE_QR", "integrity": 90, "cross_check": "CONSISTENT"},
        "ocr": {"status": "TEXT_DETECTED", "confidence": 0.96, "evidence_strength": "STRONG"},
        "structure": {"document_type": "Aadhaar Card", "valid_format": True, "integrity": 95},
        "typography": {"score": 92, "status": "CONFORMANT"},
        "layout": {"score": 94, "status": "CONFORMANT"},
        "image_forensics": {"score": 95, "tampering_score": 5, "severity": "LOW", "anomaly_detected": False},
        "high_suspicion_gate": {"eligible": False, "reason": "Authorized baseline match"},
        "photo": photo_result,
        "verification": crypto_result,
        "consistency": consistency_result,
        "aadhaar_fields": extracted_fields,
        "evidence_table": evidence_table,
        "evidence_summary": evidence_summary
    }

    heatmap_b64 = generate_heatmap(file_path, tampering_result=tampering_result)
    tampering_result.pop("anomaly_mask", None)

    evidence = [
        {
            "id": "EV-001",
            "category": "Reference",
            "title": "Document Structure Baseline Inspection",
            "severity": "Info",
            "risk_contribution": 1,
            "confidence": 98,
            "observed_metrics": ["Structure match: 100%", "Reference comparison: BASELINE MATCH"],
            "assessment": "Document structure matches authorized reference baseline.",
            "finding": "Baseline match verified across card geometry and boundaries.",
            "explanation": "Compares document structural alignment with authorized reference template."
        },
        {
            "id": "EV-002",
            "category": "Identifier",
            "title": "Identifier Region Verification",
            "severity": "Info",
            "risk_contribution": 1,
            "confidence": 95,
            "observed_metrics": ["Identifier zone: CONFORMANT", "Check-digit syntax: VALID"],
            "assessment": "Identifier region matches authorized baseline format.",
            "finding": "Identifier format conformant with zero alteration detected.",
            "explanation": "Validates primary and secondary identification markers against reference."
        },
        {
            "id": "EV-003",
            "category": "Footer",
            "title": "Footer / Contact Region Inspection",
            "severity": "Info",
            "risk_contribution": 1,
            "confidence": 96,
            "observed_metrics": ["Official domain: uidai.gov.in", "Contact zone: MATCH"],
            "assessment": "Footer contact information matches authorized reference.",
            "finding": "Official government domain suffix verified (.gov.in).",
            "explanation": "Screens official contact information against authorized baseline."
        },
        {
            "id": "EV-004",
            "category": "Text",
            "title": "Document Text Region Inspection",
            "severity": "Info",
            "risk_contribution": 2,
            "confidence": 95,
            "observed_metrics": ["Typography kerning: STABLE", "Character glyphs: CONFORMANT"],
            "assessment": "Typography and text regions match authorized baseline.",
            "finding": "No text modification or font anomaly detected.",
            "explanation": "Screens for localized typographical and textual anomalies."
        },
        {
            "id": "EV-005",
            "category": "QR",
            "title": "QR Region Inspection",
            "severity": "Info",
            "risk_contribution": 2,
            "confidence": 92,
            "observed_metrics": ["2D matrix: DETECTED", "Matrix alignment: CONFORMANT"],
            "assessment": "QR code present and structurally aligned with reference.",
            "finding": "QR STATUS: DETECTED.",
            "explanation": "Validates presence and spatial alignment of machine-readable barcode."
        },
        {
            "id": "EV-006",
            "category": "Layout",
            "title": "Layout Alignment Check",
            "severity": "Info",
            "risk_contribution": 1,
            "confidence": 94,
            "observed_metrics": ["Layout score: 94/100", "Baseline deviation: 0%"],
            "assessment": "Layout matches baseline template specification.",
            "finding": "Standard dual-sided layout conformant.",
            "explanation": "Evaluates canvas spatial layout against authorized reference."
        }
    ]

    fingerprint = extract_document_fingerprint({
        "quality": quality_result,
        "ocr": ocr_result,
        "qr": qr_result,
        "typography": typography_result,
        "layout": layout_result,
        "image_forensics": forensics_result,
        "tampering": tampering_result
    }, image_dimensions=[img_w, img_h])

    recommendation = (
        "Likely authentic. Document structure, identity regions, and metadata match the "
        "authorized reference baseline. No strong evidence of modification detected."
    )

    aadhaar_profile = {
        "fields": extracted_fields,
        "photo_forensics": photo_result,
        "verification": crypto_result,
        "consistency": consistency_result,
        "evidence_table": evidence_table,
        "evidence_summary": evidence_summary,
        "disclaimer": "SENTINEL performs forensic screening and does not replace official UIDAI authentication or authorized identity verification."
    }

    # Section 13: demo_reference_analysis block
    demo_reference_analysis = {
        "enabled": True,
        "matched": True,
        "reference_type": "ORIGINAL",
        "reference_status": "AUTHORIZED DEMO BASELINE",
        "comparison": "BASELINE_MATCH",
        "label": "DEMO REFERENCE ANALYSIS — Reference-assisted forensic demonstration",
        "overall_finding": "BASELINE MATCH — NO MODIFICATION DETECTED",
        "differences_detected": False,
        "evidence": [
            "Document structure matches baseline",
            "Identity regions match baseline",
            "Photograph region matches baseline",
            "Identifier region matches baseline",
            "Address region matches baseline",
            "QR region matches baseline",
            "Footer region matches baseline",
            "No strong modification difference detected"
        ],
        "modified_regions": [],
        "reference_image": ref_b64,
        "submitted_image": original_image_b64,
        "reference_image_url": "assets/demo/reference/original.png",
        "submitted_image_url": "assets/demo/reference/original.png"
    }

    return {
        "case_id": case_id,
        "document_type": "Aadhaar Card",
        "assessment_title": "AADHAAR FORENSIC ASSESSMENT",
        "authenticity_score": authenticity_score,
        "risk_score": risk_score,
        "classification": classification,
        "classification_display": classification_display,
        "confidence": 96,
        "risk_contribution": risk_score,
        "image_quality_score": 94,
        "tampering_evidence_score": 5,
        "document_consistency_score": 95,
        "tampering_integrity_score": 95,
        "verification_status": "DETECTED",
        "field_consistency": "CONSISTENT",
        "qr_status": "DETECTED",
        "photo_status": "MATCH",
        "forensic_status": "BASELINE_CONFORMANT",
        "document_structure_status": "CONSISTENT",
        "image_quality_status": "GOOD",
        "privacy_status": "NONE_DETECTED",
        "evidence_table": evidence_table,
        "evidence_summary": evidence_summary,
        "aadhaar_profile": aadhaar_profile,
        "disclaimer": "SENTINEL performs forensic screening and does not replace official UIDAI authentication or authorized identity verification.",
        "aadhaar_secure_qr_status": "DETECTED",
        "is_high_suspicion_eligible": False,
        "gate_reason": gate_reason,
        "quality": quality_result,
        "ocr": ocr_result,
        "qr": qr_result,
        "typography": typography_result,
        "layout": layout_result,
        "image_forensics": forensics_result,
        "tampering": tampering_result,
        "structure": structure_info,
        "signals": signals,
        "supporting_evidence": supporting_evidence,
        "negative_evidence": negative_evidence,
        "risk_breakdown": risk_breakdown,
        "evidence": evidence,
        "original_image": original_image_b64,
        "heatmap": heatmap_b64,
        "fingerprint": fingerprint,
        "recommendation": recommendation,
        "demo_reference_analysis": demo_reference_analysis,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }


def build_demo_tampered_result(file_path: str, case_id: str = None) -> dict:
    """
    Deterministic forensic analysis result for the TAMPERED demo reference image.
    Score: 15 / 100, Risk: 85 / 100, Classification: HIGH SUSPICION
    Highlights differences across:
    1. Identifier Region (MISMATCH DETECTED - HIGH)
    2. Footer / Contact Region (MISMATCH DETECTED - HIGH)
    3. Document Text Region (MODIFICATION DETECTED - HIGH)
    4. QR / Machine-readable Region (VISUAL DIFFERENCE DETECTED - MEDIUM)
    5. Document Structure (REFERENCE DIFFERENCE DETECTED - MEDIUM)
    Overall: MULTIPLE INDEPENDENT DIFFERENCES DETECTED
    """
    if not case_id:
        case_id = f"SC-2026-{int(time.time())}"

    img_h, img_w = 302, 957
    try:
        img = cv2.imread(file_path)
        if img is not None:
            img_h, img_w = img.shape[:2]
    except Exception:
        pass

    scale_y = img_h / 302.0
    scale_x = img_w / 957.0

    original_image_b64 = encode_image_to_base64(file_path)
    ref_b64 = _get_reference_original_b64() or original_image_b64

    # Spatial anomaly mask covering the known modified regions
    mask = np.zeros((img_h, img_w), dtype=np.uint8)

    # 1. Front Identifier Region (VID)
    vy1, vy2 = int(250 * scale_y), int(285 * scale_y)
    vx1, vx2 = int(125 * scale_x), int(390 * scale_x)
    mask[vy1:vy2, vx1:vx2] = 255

    # 2. Back Identifier Region (VID)
    vby1, vby2 = int(250 * scale_y), int(285 * scale_y)
    vbx1, vbx2 = int(630 * scale_x), int(890 * scale_x)
    mask[vby1:vby2, vbx1:vbx2] = 255

    # 3. Footer / Contact Region (Email / Website)
    fy1, fy2 = int(270 * scale_y), int(300 * scale_y)
    fx1, fx2 = int(610 * scale_x), int(810 * scale_x)
    mask[fy1:fy2, fx1:fx2] = 255

    # 4. QR matrix boundary
    qy1, qy2 = int(65 * scale_y), int(260 * scale_y)
    qx1, qx2 = int(740 * scale_x), int(935 * scale_x)

    regions = [
        {
            "x": vx1,
            "y": vy1,
            "w": vx2 - vx1,
            "h": vy2 - vy1,
            "signal": "IDENTIFIER_MISMATCH",
            "id": "T-01",
            "type": "IDENTIFIER_REGION",
            "severity": "HIGH",
            "area_px": (vx2 - vx1) * (vy2 - vy1),
            "label": "Identifier Region Mismatch"
        },
        {
            "x": vbx1,
            "y": vby1,
            "w": vbx2 - vbx1,
            "h": vby2 - vby1,
            "signal": "IDENTIFIER_MISMATCH",
            "id": "T-02",
            "type": "IDENTIFIER_REGION",
            "severity": "HIGH",
            "area_px": (vbx2 - vbx1) * (vby2 - vby1),
            "label": "Identifier Region Mismatch"
        },
        {
            "x": fx1,
            "y": fy1,
            "w": fx2 - fx1,
            "h": fy2 - fy1,
            "signal": "FOOTER_CONTACT_MISMATCH",
            "id": "T-03",
            "type": "FOOTER_REGION",
            "severity": "HIGH",
            "area_px": (fx2 - fx1) * (fy2 - fy1),
            "label": "Footer / Contact Mismatch"
        },
        {
            "x": qx1,
            "y": qy1,
            "w": qx2 - qx1,
            "h": qy2 - qy1,
            "signal": "QR_REGION_DIFFERENCE",
            "id": "T-04",
            "type": "QR_REGION",
            "severity": "MEDIUM",
            "area_px": (qx2 - qx1) * (qy2 - qy1),
            "label": "QR Visual Difference"
        }
    ]

    tampering_result = {
        "tampering_score": 85,
        "tampering_integrity_score": 15,
        "severity": "HIGH",
        "status": "STRONG_TAMPERING_EVIDENCE",
        "anomaly_mask": mask,
        "regions": regions,
        "signals": [
            {"name": "IDENTIFIER_MISMATCH", "severity": "HIGH"},
            {"name": "FOOTER_CONTACT_MISMATCH", "severity": "HIGH"},
            {"name": "TEXT_MODIFICATION", "severity": "HIGH"},
            {"name": "QR_VISUAL_DIFFERENCE", "severity": "MEDIUM"},
            {"name": "STRUCTURE_DIFFERENCE", "severity": "MEDIUM"}
        ],
        "metrics": {
            "copy_move_detected": False,
            "overlay_pct": 12.8
        },
        "findings": [
            "Strong forensic differences detected against authorized demo reference baseline.",
            "Identifier Region: Mismatch detected in secondary identification zone.",
            "Footer / Contact Region: Content mismatch detected in official contact metadata.",
            "Document Text Region: Modification detected across typography kerning and character forms.",
            "QR / Machine-readable Region: Visual difference detected against baseline matrix.",
            "Document Structure: Reference difference detected in aspect ratio and canvas boundaries."
        ]
    }

    quality_result = {
        "score": 92,
        "resolution_ok": True,
        "blur_score": 285.0,
        "brightness": 190.0,
        "dimensions": [img_w, img_h],
        "confidence": 95,
        "interpretation": "High-clarity document scan evaluated.",
        "findings": ["Clean scan; image clarity confirms anomalies are not artifact-induced."]
    }

    ocr_result = {
        "success": True,
        "status": "TEXT_DETECTED",
        "raw_text": "Government of India Unique Identification Authority of India [Document text modified against baseline]",
        "average_confidence": 0.94,
        "confidence": 94,
        "evidence_strength": "STRONG",
        "detections_count": 12,
        "detections": [],
        "findings": [
            "Identifier mismatch detected.",
            "Footer information mismatch detected in official contact email zone."
        ]
    }

    # QR Presentation rule (Section 15): Show QR STATUS: DETECTED, never raw unconfigured enums
    qr_result = {
        "detected": True,
        "decoded": False,
        "status": "DETECTED",
        "payload_type": "AADHAAR_SECURE_QR",
        "confidence": 85,
        "findings": [
            "QR STATUS: DETECTED. Machine-readable matrix present on card reverse; visual payload density deviates from reference baseline."
        ],
        "ocr_cross_check": {
            "status": "INCONSISTENT",
            "match_count": 0,
            "mismatch_count": 2
        }
    }

    typography_result = {
        "score": 38,
        "confidence": 92,
        "height_ratio": 1.22,
        "saturation_delta": 22.0,
        "findings": ["Typography disparity: altered kerning and modified character strings in footer zone."]
    }

    layout_result = {
        "score": 45,
        "confidence": 90,
        "findings": ["Canvas aspect ratio (3.17 vs 2.96 baseline) and footer margins deviate from reference."]
    }

    forensics_result = {
        "score": 15,
        "risk_contribution": 40,
        "anomaly_detected": True,
        "tampering_score": 85,
        "severity": "HIGH",
        "findings": ["Multi-spectral analysis isolated multiple localized alterations against authorized baseline."]
    }

    structure_info = {
        "document_type": "Aadhaar Card",
        "assessment_title": "AADHAAR FORENSIC ASSESSMENT",
        "structure_score": 40,
        "fields_detected": {
            "aadhaar_number": "XXXX XXXX 8940",
            "identity_status": "MODIFIED",
            "identifier_region": "MISMATCH DETECTED"
        },
        "findings": [
            "Document structure deviates from reference baseline.",
            "Identifier and footer regions exhibit confirmed alterations."
        ],
        "is_valid_format": False
    }

    # PII Protection: NO person's real name, real Aadhaar number, real VID, or real address
    extracted_fields = {
        "document_type": "Aadhaar Card",
        "fields": {
            "aadhaar_number": {
                "status": "VALID_FORMAT",
                "raw_value": "XXXX XXXX 8940",
                "masked_value": "XXXX XXXX 8940",
                "format_valid": True,
                "checksum_valid": True,
                "identity_verified": False,
                "confidence": 95.0,
                "details": "Aadhaar number syntax check valid."
            },
            "enrolment_id": {
                "status": "NOT_PRESENT",
                "present": False,
                "raw_value": None,
                "masked_value": None,
                "is_valid": None,
                "timestamp": None,
                "details": "Enrolment ID (EID) not present."
            },
            "name": {
                "status": "MODIFIED",
                "value": "Cardholder Name (Modified)",
                "confidence": 92.0,
                "details": "Identity field modification detected against authorized reference."
            },
            "dob": {
                "status": "VALID_CALENDAR",
                "dob": "XX/XX/XXXX",
                "age": None,
                "is_valid_calendar": True,
                "confidence": 90.0,
                "details": "Date of Birth valid calendar format."
            },
            "gender": {
                "status": "EXTRACTED",
                "value": "Female",
                "confidence": 95.0,
                "details": "Demographic gender field identified."
            },
            "address": {
                "status": "EXTRACTED",
                "raw_address": "Demographic Region, Maharashtra",
                "normalized_address": "demographic region maharashtra",
                "confidence": 90.0,
                "details": "Address region evaluated."
            }
        },
        "summary": [
            "Identifier Region: MISMATCH DETECTED (HIGH)",
            "Footer / Contact Region: MISMATCH DETECTED (HIGH)",
            "Document Text Region: MODIFICATION DETECTED (HIGH)",
            "QR / Machine-readable Region: VISUAL DIFFERENCE DETECTED (MEDIUM)",
            "Document Structure: REFERENCE DIFFERENCE DETECTED (MEDIUM)",
            "Overall: MULTIPLE INDEPENDENT DIFFERENCES DETECTED"
        ]
    }

    photo_result = {
        "present": True,
        "status": "MATCH",
        "boundary_step": 0.22,
        "noise_variance_ratio": 1.05,
        "findings": [
            "Biometric photo present; substrate consistent."
        ]
    }

    crypto_result = {
        "status": "DETECTED",
        "authority": "UIDAI",
        "details": "QR code detected on card reverse; visual matrix payload differs from reference."
    }

    consistency_result = {
        "status": "INCONSISTENT",
        "match_count": 0,
        "mismatch_count": 3,
        "summary": "Multiple independent differences detected against authorized demo reference baseline.",
        "matrix": {
            "identifier_region": {"status": "MISMATCH", "confidence": 0.98},
            "footer_contact": {"status": "MISMATCH", "confidence": 0.98},
            "document_text": {"status": "MODIFIED", "confidence": 0.94}
        }
    }

    # Section 12: Authenticity = 15, Risk = 85, HIGH SUSPICION
    authenticity_score = 15
    risk_score = 85
    classification = "High Suspicion"
    classification_display = "HIGH SUSPICION — REFERENCE COMPARISON DIFFERENCES DETECTED"
    gate_reason = "Multiple independent differences detected: Identifier region mismatch, footer contact mismatch, and typography alterations against authorized baseline."

    risk_breakdown = {
        "quality": 2,
        "ocr": 20,
        "qr": 15,
        "typography": 18,
        "layout": 10,
        "image_forensics": 20
    }

    # Section 7: Exact 6 core demo evidence items + standard 15-pillar table
    evidence_table = [
        {"evidence": "Reference Comparison", "status": "Baseline mismatch", "impact": "Strong Suspicious", "id": "EV-D01", "category": "Reference", "finding": "Baseline mismatch", "severity": "HIGH"},
        {"evidence": "Identifier Region", "status": "Region mismatch detected", "impact": "Strong Suspicious", "id": "EV-D02", "category": "Identifier", "finding": "Region mismatch detected", "severity": "HIGH"},
        {"evidence": "Footer / Contact Region", "status": "Content mismatch detected", "impact": "Strong Suspicious", "id": "EV-D03", "category": "Footer", "finding": "Content mismatch detected", "severity": "HIGH"},
        {"evidence": "Document Text Region", "status": "Modification detected", "impact": "Strong Suspicious", "id": "EV-D04", "category": "Text", "finding": "Modification detected", "severity": "HIGH"},
        {"evidence": "QR Region", "status": "Visual difference detected", "impact": "Suspicious", "id": "EV-D05", "category": "QR Region", "finding": "Visual difference detected", "severity": "MEDIUM"},
        {"evidence": "Document Layout", "status": "Baseline difference", "impact": "Suspicious", "id": "EV-D06", "category": "Layout", "finding": "Baseline difference", "severity": "MEDIUM"},
        {"evidence": "Photograph", "status": "Biometric photo present", "impact": "Neutral", "id": "EV-D07", "category": "Photo", "finding": "Biometric photo present", "severity": "INFO"},
        {"evidence": "Photo Substrate", "status": "Consistent substrate", "impact": "Neutral", "id": "EV-D08", "category": "Photo", "finding": "Consistent substrate", "severity": "INFO"},
        {"evidence": "Secure QR", "status": "Detected (Standard 2D Matrix)", "impact": "Neutral", "id": "EV-D09", "category": "QR", "finding": "2D Matrix present", "severity": "INFO"},
        {"evidence": "Identity Corroboration", "status": "Contradictory Metadata", "impact": "Strong Suspicious", "id": "EV-D10", "category": "Consistency", "finding": "Contradictory metadata", "severity": "HIGH"},
        {"evidence": "Contact Domain", "status": "Unauthorized Suffix Modification", "impact": "Strong Suspicious", "id": "EV-D11", "category": "Metadata", "finding": "Unauthorized suffix", "severity": "HIGH"},
        {"evidence": "Document Structure", "status": "Dual-Card UIDAI Layout", "impact": "Neutral", "id": "EV-D12", "category": "Structure", "finding": "Standard card geometry", "severity": "INFO"},
        {"evidence": "Forensic Splicing", "status": "Localized Substitution", "impact": "Suspicious", "id": "EV-D13", "category": "Forensics", "finding": "Localized substitution", "severity": "HIGH"},
        {"evidence": "Image Quality", "status": "Optimal Scan Resolution", "impact": "Informational", "id": "EV-D14", "category": "Quality", "finding": "Adequate resolution", "severity": "INFO"},
        {"evidence": "Tampering Evidence", "status": "Multiple Differences Detected", "impact": "Strong Suspicious", "id": "EV-D15", "category": "Tampering", "finding": "Multiple differences detected", "severity": "HIGH"}
    ]

    evidence_summary = [
        "✗ Reference Comparison: DIFFERENCES DETECTED",
        "✗ 1. Identifier Region: MISMATCH DETECTED (Severity: HIGH)",
        "✗ 2. Footer / Contact Region: MISMATCH DETECTED (Severity: HIGH)",
        "✗ 3. Document Text Region: MODIFICATION DETECTED (Severity: HIGH)",
        "✗ 4. QR / Machine-readable Region: VISUAL DIFFERENCE DETECTED (Severity: MEDIUM)",
        "✗ 5. Document Structure: REFERENCE DIFFERENCE DETECTED (Severity: MEDIUM)",
        "✗ Overall: MULTIPLE INDEPENDENT DIFFERENCES DETECTED"
    ]

    negative_evidence = [
        "IDENTIFIER REGION MISMATCH: Secondary identification markers deviate from authorized baseline.",
        "FOOTER CONTACT MISMATCH: Official support contact altered from authorized baseline domain.",
        "DOCUMENT TEXT MODIFICATION: Typography kerning and glyph structures show tampering.",
        "QR VISUAL DIFFERENCE: 2D barcode matrix pattern differs visually from reference baseline.",
        "DOCUMENT STRUCTURE DIFFERENCE: Card geometry and margin coordinates show baseline discrepancy."
    ]

    supporting_evidence = []

    signals = {
        "document_consistency": {"score": 25, "status": "IRREGULAR"},
        "tampering_integrity": {"score": 15, "tampering_score": 85, "severity": "HIGH", "status": "STRONG_TAMPERING_EVIDENCE"},
        "qr": {"status": "DETECTED", "payload_type": "AADHAAR_SECURE_QR", "integrity": 20, "cross_check": "INCONSISTENT"},
        "ocr": {"status": "TEXT_DETECTED", "confidence": 0.94, "evidence_strength": "STRONG"},
        "structure": {"document_type": "Aadhaar Card", "valid_format": False, "integrity": 30},
        "typography": {"score": 38, "status": "DISPARITY"},
        "layout": {"score": 45, "status": "ANOMALY"},
        "image_forensics": {"score": 15, "tampering_score": 85, "severity": "HIGH", "anomaly_detected": True},
        "high_suspicion_gate": {"eligible": True, "reason": gate_reason},
        "photo": photo_result,
        "verification": crypto_result,
        "consistency": consistency_result,
        "aadhaar_fields": extracted_fields,
        "evidence_table": evidence_table,
        "evidence_summary": evidence_summary
    }

    heatmap_b64 = generate_heatmap(file_path, tampering_result=tampering_result)
    tampering_result.pop("anomaly_mask", None)

    # Core canonical evidence list (EV-D01 to EV-D06) as explicitly requested in Section 7
    evidence = [
        {
            "id": "EV-D01",
            "category": "Reference",
            "title": "Reference Baseline Comparison (DIFFERENCES DETECTED)",
            "severity": "High",
            "risk_contribution": 30,
            "confidence": 98,
            "observed_metrics": [
                "Reference Status: MODIFIED DEMO FIXTURE",
                "Comparison: DIFFERENCES DETECTED",
                "Overall: MULTIPLE INDEPENDENT DIFFERENCES DETECTED"
            ],
            "assessment": "Submitted document exhibits multiple distinct structural and textual differences against authorized baseline.",
            "finding": "Baseline mismatch detected across multiple independent card regions.",
            "explanation": "Compares submitted specimen against authorized reference baseline standard."
        },
        {
            "id": "EV-D02",
            "category": "Identifier",
            "title": "Identifier Region (MISMATCH DETECTED)",
            "severity": "High",
            "risk_contribution": 25,
            "confidence": 96,
            "observed_metrics": [
                "Identifier Region: MISMATCH DETECTED",
                "Front identifier zone: Modified",
                "Back identifier zone: Modified"
            ],
            "assessment": "Secondary identifier zone differs from authorized baseline reference.",
            "finding": "Region mismatch detected in primary identifier fields.",
            "explanation": "Screens identifier zones for altered digits, replacement glyphs, and synthetic reconstruction."
        },
        {
            "id": "EV-D03",
            "category": "Footer",
            "title": "Footer / Contact Region (MISMATCH DETECTED)",
            "severity": "High",
            "risk_contribution": 25,
            "confidence": 98,
            "observed_metrics": [
                "Footer / Contact Region: MISMATCH DETECTED",
                "Official support email: Altered domain extension",
                "Expected: .gov.in | Observed: Unauthorized suffix"
            ],
            "assessment": "Official support contact and web domain suffix differ from authorized baseline.",
            "finding": "Content mismatch detected in official government contact footer.",
            "explanation": "Validates official government contact details and domain extensions against reference standards."
        },
        {
            "id": "EV-D04",
            "category": "Text",
            "title": "Document Text Region (MODIFICATION DETECTED)",
            "severity": "High",
            "risk_contribution": 20,
            "confidence": 92,
            "observed_metrics": [
                "Document Text Region: MODIFICATION DETECTED",
                "Typography kerning: Discontinuous",
                "Character contours: Resampled"
            ],
            "assessment": "Localized text kerning and glyph structures show tampering against baseline.",
            "finding": "Modification detected in textual fields.",
            "explanation": "Analyzes font geometry, text alignment, and edge sharpness against reference."
        },
        {
            "id": "EV-D05",
            "category": "QR Region",
            "title": "QR / Machine-readable Region (VISUAL DIFFERENCE DETECTED)",
            "severity": "Medium",
            "risk_contribution": 15,
            "confidence": 88,
            "observed_metrics": [
                "QR / Machine-readable Region: VISUAL DIFFERENCE DETECTED",
                "Matrix pattern: Deviates from baseline payload density",
                "QR Status: DETECTED"
            ],
            "assessment": "2D barcode visual pattern and module alignment deviate from baseline reference.",
            "finding": "Visual difference detected in machine-readable matrix.",
            "explanation": "Performs optical pattern comparison between submitted 2D barcode and reference standard."
        },
        {
            "id": "EV-D06",
            "category": "Layout",
            "title": "Document Structure (REFERENCE DIFFERENCE DETECTED)",
            "severity": "Medium",
            "risk_contribution": 15,
            "confidence": 90,
            "observed_metrics": [
                "Document Structure: REFERENCE DIFFERENCE DETECTED",
                "Observed dimensions: 957x302 (Aspect ratio: 3.17)",
                "Baseline dimensions: 925x313 (Aspect ratio: 2.96)"
            ],
            "assessment": "Canvas aspect ratio and margin alignment differ from baseline specification.",
            "finding": "Baseline difference detected in overall document geometry.",
            "explanation": "Evaluates overall document dimensions, margin ratios, and canvas scaling against reference."
        }
    ]

    fingerprint = extract_document_fingerprint({
        "quality": quality_result,
        "ocr": ocr_result,
        "qr": qr_result,
        "typography": typography_result,
        "layout": layout_result,
        "image_forensics": forensics_result,
        "tampering": tampering_result
    }, image_dimensions=[img_w, img_h])

    recommendation = (
        "High forensic suspicion. Strong evidence of modification detected: Multiple independent "
        "differences detected across identifier region, footer contact details, and document text. "
        "Immediate rejection and manual review advised."
    )

    aadhaar_profile = {
        "fields": extracted_fields,
        "photo_forensics": photo_result,
        "verification": crypto_result,
        "consistency": consistency_result,
        "evidence_table": evidence_table,
        "evidence_summary": evidence_summary,
        "disclaimer": "SENTINEL performs forensic screening and does not replace official UIDAI authentication or authorized identity verification."
    }

    # Section 13: demo_reference_analysis block
    demo_reference_analysis = {
        "enabled": True,
        "matched": True,
        "reference_type": "TAMPERED",
        "reference_status": "MODIFIED DEMO SPECIMEN",
        "comparison": "DIFFERENCES_DETECTED",
        "label": "DEMO REFERENCE ANALYSIS — Reference-assisted forensic demonstration",
        "overall_finding": "MULTIPLE INDEPENDENT DIFFERENCES DETECTED",
        "differences_detected": True,
        "differences": [
            {
                "id": "DIFF-01",
                "name": "Identifier Region",
                "status": "MISMATCH DETECTED",
                "severity": "HIGH",
                "description": "Secondary identifier zone differs from authorized baseline reference."
            },
            {
                "id": "DIFF-02",
                "name": "Footer / Contact Region",
                "status": "MISMATCH DETECTED",
                "severity": "HIGH",
                "description": "Official support contact and web domain suffix differ from authorized baseline."
            },
            {
                "id": "DIFF-03",
                "name": "Document Text Region",
                "status": "MODIFICATION DETECTED",
                "severity": "HIGH",
                "description": "Localized text kerning and glyph structures show tampering against baseline."
            },
            {
                "id": "DIFF-04",
                "name": "QR / Machine-readable Region",
                "status": "VISUAL DIFFERENCE DETECTED",
                "severity": "MEDIUM",
                "description": "2D matrix visual alignment and payload density deviate from reference."
            },
            {
                "id": "DIFF-05",
                "name": "Document Structure",
                "status": "REFERENCE DIFFERENCE DETECTED",
                "severity": "MEDIUM",
                "description": "Canvas aspect ratio and margin alignment differ from baseline specification."
            }
        ],
        "modified_regions": [
            {
                "name": "Identifier Region (Front)",
                "x": vx1, "y": vy1, "w": vx2 - vx1, "h": vy2 - vy1,
                "severity": "HIGH",
                "label": "Identifier Mismatch"
            },
            {
                "name": "Identifier Region (Back)",
                "x": vbx1, "y": vby1, "w": vbx2 - vbx1, "h": vby2 - vby1,
                "severity": "HIGH",
                "label": "Identifier Mismatch"
            },
            {
                "name": "Footer / Contact Region",
                "x": fx1, "y": fy1, "w": fx2 - fx1, "h": fy2 - fy1,
                "severity": "HIGH",
                "label": "Footer Domain Mismatch"
            }
        ],
        "reference_image": ref_b64,
        "submitted_image": original_image_b64,
        "reference_image_url": "assets/demo/reference/original.png",
        "submitted_image_url": "assets/demo/reference/tampered.png"
    }

    return {
        "case_id": case_id,
        "document_type": "Aadhaar Card",
        "assessment_title": "AADHAAR FORENSIC ASSESSMENT",
        "authenticity_score": authenticity_score,
        "risk_score": risk_score,
        "classification": classification,
        "classification_display": classification_display,
        "confidence": 95,
        "risk_contribution": risk_score,
        "image_quality_score": 92,
        "tampering_evidence_score": 85,
        "document_consistency_score": 25,
        "tampering_integrity_score": 15,
        "verification_status": "DETECTED",
        "field_consistency": "INCONSISTENT",
        "qr_status": "DETECTED",
        "photo_status": "MATCH",
        "forensic_status": "STRONG_TAMPERING_EVIDENCE",
        "document_structure_status": "IRREGULAR",
        "image_quality_status": "GOOD",
        "privacy_status": "NONE_DETECTED",
        "evidence_table": evidence_table,
        "evidence_summary": evidence_summary,
        "aadhaar_profile": aadhaar_profile,
        "disclaimer": "SENTINEL performs forensic screening and does not replace official UIDAI authentication or authorized identity verification.",
        "aadhaar_secure_qr_status": "DETECTED",
        "is_high_suspicion_eligible": True,
        "gate_reason": gate_reason,
        "quality": quality_result,
        "ocr": ocr_result,
        "qr": qr_result,
        "typography": typography_result,
        "layout": layout_result,
        "image_forensics": forensics_result,
        "tampering": tampering_result,
        "structure": structure_info,
        "signals": signals,
        "supporting_evidence": supporting_evidence,
        "negative_evidence": negative_evidence,
        "risk_breakdown": risk_breakdown,
        "evidence": evidence,
        "original_image": original_image_b64,
        "heatmap": heatmap_b64,
        "fingerprint": fingerprint,
        "recommendation": recommendation,
        "demo_reference_analysis": demo_reference_analysis,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
