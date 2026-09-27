import re
from typing import Dict, Any, Optional, List, Tuple
from .aadhaar_extractor import normalize_address

# ==============================================================================
# AADHAAR MULTI-FIELD EVIDENCE CONSISTENCY CROSS-CHECK MATRIX
# ==============================================================================

def cross_check_aadhaar_evidence(
    extracted_fields: Dict[str, Any],
    qr_result: Dict[str, Any],
    photo_result: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Evaluates cross-corroboration between visible extracted fields and
    machine-readable Secure QR payload data.
    
    Generates Evidence Matrix:
                        MATCH       MISMATCH      UNKNOWN
      Name                ✓             !            -
      DOB                 ✓             !            -
      Gender              ✓             !            -
      Address             ✓             !            -
      Photo               ✓             !            -
      Aadhaar Reference   ✓             !            -
      
    Crucial Rule:
    Only confident extractions on both sides can produce a MISMATCH.
    OCR character uncertainty or missing fields MUST produce UNKNOWN, NOT a fraud mismatch.
    """
    matrix = {
        "name": {"status": "UNKNOWN", "visible": None, "qr": None, "confidence": 0.0, "details": "Field not available for comparison."},
        "dob": {"status": "UNKNOWN", "visible": None, "qr": None, "confidence": 0.0, "details": "Field not available for comparison."},
        "gender": {"status": "UNKNOWN", "visible": None, "qr": None, "confidence": 0.0, "details": "Field not available for comparison."},
        "address": {"status": "UNKNOWN", "visible": None, "qr": None, "confidence": 0.0, "details": "Field not available for comparison."},
        "photo": {"status": "UNKNOWN", "visible": None, "qr": None, "confidence": 0.0, "details": "Field not available for comparison."},
        "aadhaar_reference": {"status": "UNKNOWN", "visible": None, "qr": None, "confidence": 0.0, "details": "Field not available for comparison."}
    }

    qr_decoded = qr_result.get("decoded", False) if qr_result else False
    demographics = (qr_result.get("demographics") or {}) if qr_decoded else {}
    fields = (extracted_fields.get("fields") or {}) if extracted_fields else {}

    # 1. Name Cross-Check
    vis_name_data = fields.get("name", {})
    vis_name = vis_name_data.get("value")
    vis_name_conf = vis_name_data.get("confidence", 0.0)
    conf_norm = vis_name_conf * 100.0 if (0.0 < vis_name_conf <= 1.0) else vis_name_conf
    if vis_name_conf == 0.0 and vis_name_data.get("status") == "EXTRACTED":
        conf_norm = 90.0
    qr_name = demographics.get("name", "").strip()

    if qr_decoded and qr_name and vis_name and conf_norm >= 50.0:
        qr_tokens = set(re.sub(r'[^a-zA-Z\s]', '', qr_name.lower()).split())
        vis_tokens = set(re.sub(r'[^a-zA-Z\s]', '', vis_name.lower()).split())
        overlap = len(qr_tokens.intersection(vis_tokens))
        
        if overlap == len(qr_tokens) or overlap == len(vis_tokens) or overlap >= 2:
            matrix["name"] = {
                "status": "MATCH",
                "visible": vis_name,
                "qr": qr_name,
                "confidence": 95.0,
                "details": f"Visible name '{vis_name}' strictly matches QR name '{qr_name}'."
            }
        elif overlap == 1 and max(len(qr_tokens), len(vis_tokens)) <= 3:
            matrix["name"] = {
                "status": "MATCH",
                "visible": vis_name,
                "qr": qr_name,
                "confidence": 80.0,
                "details": f"Visible name '{vis_name}' partially matches QR name '{qr_name}'."
            }
        else:
            matrix["name"] = {
                "status": "MISMATCH",
                "visible": vis_name,
                "qr": qr_name,
                "confidence": 90.0,
                "details": f"DISCREPANCY: Visible name '{vis_name}' contradicts QR name '{qr_name}'."
            }
    elif qr_decoded and qr_name:
        matrix["name"] = {
            "status": "UNKNOWN",
            "visible": vis_name,
            "qr": qr_name,
            "confidence": 40.0,
            "details": "QR name present; visible name had insufficient OCR recognition confidence."
        }
    elif vis_name:
        matrix["name"] = {
            "status": "UNKNOWN",
            "visible": vis_name,
            "qr": None,
            "confidence": vis_name_conf,
            "details": "Visible name isolated; QR payload unavailable."
        }

    # 2. DOB Cross-Check
    vis_dob_data = fields.get("dob", {})
    vis_dob = vis_dob_data.get("dob")
    qr_dob = demographics.get("dob", "").strip()

    if qr_decoded and qr_dob and vis_dob:
        qr_digits = re.sub(r'\D', '', qr_dob)
        vis_digits = re.sub(r'\D', '', vis_dob)
        # Check either exact match or matching year (last 4 digits)
        if qr_digits == vis_digits:
            matrix["dob"] = {
                "status": "MATCH",
                "visible": vis_dob,
                "qr": qr_dob,
                "confidence": 98.0,
                "details": f"Visible DOB '{vis_dob}' matches QR DOB '{qr_dob}'."
            }
        elif len(qr_digits) >= 4 and len(vis_digits) >= 4 and qr_digits[-4:] == vis_digits[-4:]:
            matrix["dob"] = {
                "status": "MATCH",
                "visible": vis_dob,
                "qr": qr_dob,
                "confidence": 85.0,
                "details": f"Birth year {qr_digits[-4:]} matches between visible and QR records."
            }
        else:
            # Only mismatch if both dates are well-formed (at least 6 digits)
            if len(qr_digits) >= 6 and len(vis_digits) >= 6:
                matrix["dob"] = {
                    "status": "MISMATCH",
                    "visible": vis_dob,
                    "qr": qr_dob,
                    "confidence": 92.0,
                    "details": f"DISCREPANCY: Visible DOB '{vis_dob}' contradicts QR DOB '{qr_dob}'."
                }
            else:
                matrix["dob"] = {
                    "status": "UNKNOWN",
                    "visible": vis_dob,
                    "qr": qr_dob,
                    "confidence": 50.0,
                    "details": "Date strings partially incomplete; insufficient confidence for mismatch."
                }
    elif qr_decoded and qr_dob:
        matrix["dob"] = {"status": "UNKNOWN", "visible": vis_dob, "qr": qr_dob, "confidence": 40.0, "details": "QR DOB present; visible DOB unread."}
    elif vis_dob:
        matrix["dob"] = {"status": "UNKNOWN", "visible": vis_dob, "qr": None, "confidence": 50.0, "details": "Visible DOB present; QR payload unread."}

    # 3. Gender Cross-Check
    vis_gender_data = fields.get("gender", {})
    vis_gender = vis_gender_data.get("value")
    qr_gender = demographics.get("gender", "").strip().upper()

    if qr_decoded and qr_gender and vis_gender:
        qr_g_norm = "MALE" if qr_gender.startswith("M") else ("FEMALE" if qr_gender.startswith("F") else "TRANSGENDER")
        vis_g_norm = vis_gender.upper()
        if qr_g_norm == vis_g_norm:
            matrix["gender"] = {
                "status": "MATCH",
                "visible": vis_gender,
                "qr": qr_gender,
                "confidence": 98.0,
                "details": f"Demographic gender '{vis_gender}' matches QR record."
            }
        else:
            matrix["gender"] = {
                "status": "MISMATCH",
                "visible": vis_gender,
                "qr": qr_gender,
                "confidence": 95.0,
                "details": f"DISCREPANCY: Visible gender '{vis_gender}' contradicts QR gender '{qr_gender}'."
            }
    elif qr_decoded and qr_gender:
        matrix["gender"] = {"status": "UNKNOWN", "visible": vis_gender, "qr": qr_gender, "confidence": 40.0, "details": "QR gender present; visible unread."}
    elif vis_gender:
        matrix["gender"] = {"status": "UNKNOWN", "visible": vis_gender, "qr": None, "confidence": 50.0, "details": "Visible gender present; QR unread."}

    # 4. Address Cross-Check
    vis_addr_data = fields.get("address", {})
    vis_addr_raw = vis_addr_data.get("raw_address") or vis_addr_data.get("raw") or ""
    vis_addr_norm = vis_addr_data.get("normalized_address") or vis_addr_data.get("normalized") or normalize_address(vis_addr_raw or "")
    qr_addr_raw = demographics.get("address", "").strip()
    qr_addr_norm = normalize_address(qr_addr_raw)

    if qr_decoded and qr_addr_norm and vis_addr_norm:
        qr_tokens = set(qr_addr_norm.split())
        vis_tokens = set(vis_addr_norm.split())
        if qr_tokens and vis_tokens:
            overlap = len(qr_tokens.intersection(vis_tokens))
            ratio = overlap / min(len(qr_tokens), len(vis_tokens))
            if ratio >= 0.50 or overlap >= 3:
                matrix["address"] = {
                    "status": "MATCH",
                    "visible": vis_addr_raw[:40] + "..." if len(vis_addr_raw or "") > 40 else vis_addr_raw,
                    "qr": qr_addr_raw[:40] + "..." if len(qr_addr_raw) > 40 else qr_addr_raw,
                    "confidence": 88.0,
                    "details": f"Address matches with {ratio*100:.0f}% semantic token congruence."
                }
            elif ratio < 0.20 and len(qr_tokens) >= 3 and len(vis_tokens) >= 3:
                matrix["address"] = {
                    "status": "MISMATCH",
                    "visible": vis_addr_raw[:40] + "..." if len(vis_addr_raw or "") > 40 else vis_addr_raw,
                    "qr": qr_addr_raw[:40] + "..." if len(qr_addr_raw) > 40 else qr_addr_raw,
                    "confidence": 85.0,
                    "details": "DISCREPANCY: Visible address key geographic tokens contradict QR address record."
                }
            else:
                matrix["address"] = {
                    "status": "UNKNOWN",
                    "visible": vis_addr_raw[:40] + "..." if len(vis_addr_raw or "") > 40 else vis_addr_raw,
                    "qr": qr_addr_raw[:40] + "..." if len(qr_addr_raw) > 40 else qr_addr_raw,
                    "confidence": 60.0,
                    "details": "Address tokens partially overlapping; insufficient certainty for strict mismatch."
                }
    elif qr_decoded and qr_addr_norm:
        matrix["address"] = {"status": "UNKNOWN", "visible": vis_addr_raw, "qr": qr_addr_raw, "confidence": 40.0, "details": "QR address present; visible unread."}
    elif vis_addr_norm:
        matrix["address"] = {"status": "UNKNOWN", "visible": vis_addr_raw, "qr": None, "confidence": 50.0, "details": "Visible address present; QR unread."}

    # 5. Photograph Cross-Check
    if photo_result:
        photo_match = photo_result.get("photo_match_status", "PHOTO_NOT_AVAILABLE")
        if photo_match == "PHOTO_CONSISTENT":
            matrix["photo"] = {
                "status": "MATCH",
                "visible": "Detected",
                "qr": "Decoded",
                "confidence": 90.0,
                "details": "Visible photograph correlates with QR decoded portrait."
            }
        elif photo_match == "PHOTO_INCONSISTENT":
            matrix["photo"] = {
                "status": "MISMATCH",
                "visible": "Detected",
                "qr": "Decoded",
                "confidence": 95.0,
                "details": "CRITICAL DISCREPANCY: Visible portrait contradicts QR decoded image."
            }
        else:
            matrix["photo"] = {
                "status": "UNKNOWN",
                "visible": "Detected" if photo_result.get("present") else "Not detected",
                "qr": "Not provided",
                "confidence": 50.0,
                "details": "Secure QR did not provide verifiable portrait bytes."
            }

    # 6. Aadhaar Reference / Last Digits Cross-Check
    vis_num_data = fields.get("aadhaar_number", {})
    vis_masked = vis_num_data.get("masked_value")
    vis_last4 = vis_masked[-4:] if (vis_masked and len(vis_masked) >= 4 and vis_masked[-4:].isdigit()) else None
    qr_last4 = demographics.get("aadhaar_last_4")

    if qr_last4 and vis_last4:
        if qr_last4 == vis_last4:
            matrix["aadhaar_reference"] = {
                "status": "MATCH",
                "visible": f"XXXX XXXX {vis_last4}",
                "qr": f"Reference: {qr_last4}",
                "confidence": 98.0,
                "details": f"Aadhaar last 4 digits ({vis_last4}) match QR reference."
            }
        else:
            matrix["aadhaar_reference"] = {
                "status": "MISMATCH",
                "visible": f"XXXX XXXX {vis_last4}",
                "qr": f"Reference: {qr_last4}",
                "confidence": 96.0,
                "details": f"DISCREPANCY: Visible Aadhaar last 4 digits ({vis_last4}) contradict QR reference ({qr_last4})."
            }
    elif qr_last4:
        matrix["aadhaar_reference"] = {"status": "UNKNOWN", "visible": None, "qr": qr_last4, "confidence": 50.0, "details": "QR reference present; visible unread."}
    elif vis_last4:
        matrix["aadhaar_reference"] = {"status": "UNKNOWN", "visible": f"XXXX XXXX {vis_last4}", "qr": None, "confidence": 50.0, "details": "Visible digits present; QR reference unread."}

    # Summarize Matrix
    matches = sum(1 for v in matrix.values() if v["status"] == "MATCH")
    mismatches = sum(1 for v in matrix.values() if v["status"] == "MISMATCH")
    unknowns = sum(1 for v in matrix.values() if v["status"] == "UNKNOWN")

    if mismatches > 0:
        overall_status = "INCONSISTENT"
    elif matches >= 2:
        overall_status = "CONSISTENT"
    elif matches == 1:
        overall_status = "PARTIALLY_CONSISTENT"
    else:
        overall_status = "NOT_AVAILABLE"

    return {
        "status": overall_status,
        "matrix": matrix,
        "match_count": matches,
        "mismatch_count": mismatches,
        "unknown_count": unknowns,
        "summary": f"{matches} matched, {mismatches} mismatched, {unknowns} unverified"
    }

# Alias for naming consistency across modules
cross_check_aadhaar_consistency = cross_check_aadhaar_evidence

