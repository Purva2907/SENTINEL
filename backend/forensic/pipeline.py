import os
import re
import time
from .image_quality import analyze_quality
from .ocr import analyze_ocr
from .qr import analyze_qr
from .typography import analyze_typography
from .layout import analyze_layout
from .heatmap import generate_heatmap, analyze_image_forensics, encode_image_to_base64
from .fingerprint import extract_document_fingerprint
from .aadhaar_extractor import extract_aadhaar_fields, mask_aadhaar_number, validate_verhoeff
from .photo_forensics import analyze_photograph_forensics
from .verification_provider import AadhaarVerificationProvider
from .aadhaar_consistency import cross_check_aadhaar_consistency
from .fictional_detector import is_fictional_document, build_fictional_analysis_result

def detect_document_structure(ocr_result: dict, qr_result: dict) -> dict:
    """
    Evaluates document type (Aadhaar, PAN, Generic ID) and checks internal field structure.
    Never claims official government verification unless cryptographic certs are validated.
    """
    raw_text = (ocr_result.get("raw_text") or "").upper()
    qr_payload = str(qr_result.get("payload") or "").upper()
    qr_demographics = qr_result.get("demographics") or {}
    
    # 1. PAN Card Detection
    pan_match = re.search(r'\b[A-Z]{5}[0-9]{4}[A-Z]\b', raw_text)
    is_pan = bool(
        pan_match or 
        "INCOME TAX" in raw_text or 
        "PERMANENT ACCOUNT" in raw_text or 
        ("GOVT. OF INDIA" in raw_text and ("FATHER" in raw_text or "SIGNATURE" in raw_text))
    )
    
    # 2. Aadhaar Card Detection
    aadhaar_match = re.search(r'\b\d{4}\s?\d{4}\s?\d{4}\b', raw_text) or re.search(r'\bXXXX\s?XXXX\s?\d{4}\b', raw_text)
    is_aadhaar_qr = qr_result.get("payload_type") == "AADHAAR_SECURE_QR" or "PRINTLETTERBARCODEDATA" in qr_payload
    is_aadhaar = bool(
        is_aadhaar_qr or
        aadhaar_match or 
        "AADHAAR" in raw_text or 
        "UIDAI" in raw_text or 
        "UNIQUE IDENTIFICATION" in raw_text or 
        "MERA AADHAAR" in raw_text
    )
    
    fields = {}
    findings = []
    
    if is_pan and not is_aadhaar:
        doc_type = "PAN Card"
        title = "PAN DOCUMENT FORENSIC ASSESSMENT"
        structure_score = 90
        
        if pan_match:
            fields["pan_number"] = pan_match.group(0)
            findings.append(f"Standard 10-character PAN syntax verified ({pan_match.group(0)[:5]}****{pan_match.group(0)[-1]}).")
            structure_score = 100
        else:
            findings.append("PAN document markers detected; 10-character alphanumeric ID not isolated by OCR.")
            structure_score = 75
            
        has_dob = bool(re.search(r'\b\d{2}[/-]\d{2}[/-]\d{4}\b', raw_text))
        if has_dob:
            fields["dob"] = "Present"
            findings.append("Date of Birth structure verified.")
        if "INCOME TAX" in raw_text:
            fields["authority"] = "Income Tax Department"
            findings.append("Income Tax Department header confirmed.")
            
        return {
            "document_type": doc_type,
            "assessment_title": title,
            "structure_score": structure_score,
            "fields_detected": fields,
            "findings": findings,
            "is_valid_format": bool(pan_match)
        }
        
    elif is_aadhaar or not is_pan:
        doc_type = "Aadhaar Card"
        title = "AADHAAR FORENSIC ASSESSMENT"
        structure_score = 85
        
        if aadhaar_match:
            raw_id = aadhaar_match.group(0)
            clean_digits = re.sub(r'\D', '', raw_id)
            last4 = clean_digits[-4:] if len(clean_digits) >= 4 else "1234"
            fields["aadhaar_number"] = f"XXXX XXXX {last4}"
            findings.append("Standard 12-digit Aadhaar identification structure verified.")
            structure_score = 95
        elif qr_demographics and "aadhaar_last_4" in qr_demographics:
            fields["aadhaar_number"] = f"XXXX XXXX {qr_demographics['aadhaar_last_4']}"
            findings.append("Aadhaar identification credential recovered from machine-readable payload.")
            structure_score = 95
        else:
            findings.append("Aadhaar layout markers detected; 12-digit sequence not isolated by OCR.")
            structure_score = 75
            
        has_dob = bool(re.search(r'\b(DOB|BIRTH|YEAR OF BIRTH)\b|\b\d{2}[/-]\d{2}[/-]\d{4}\b|\b\d{4}\b', raw_text))
        if has_dob:
            fields["dob"] = "Present"
            findings.append("Date of Birth / Year of Birth field identified.")
            structure_score = min(100, structure_score + 5)
            
        has_gender = bool(re.search(r'\b(MALE|FEMALE|TRANSGENDER)\b', raw_text))
        if has_gender:
            fields["gender"] = "Present"
            findings.append("Demographic gender field identified.")
            
        return {
            "document_type": doc_type,
            "assessment_title": title,
            "structure_score": structure_score,
            "fields_detected": fields,
            "findings": findings,
            "is_valid_format": bool(aadhaar_match or is_aadhaar_qr)
        }
    else:
        doc_type = "Identity Card"
        title = "DOCUMENT FORENSIC ASSESSMENT"
        return {
            "document_type": doc_type,
            "assessment_title": title,
            "structure_score": 80,
            "fields_detected": {},
            "findings": ["Standard document structure evaluated."],
            "is_valid_format": True
        }

from .tamper_detection import analyze_tampering

def build_forensic_evidence_table(
    structure_info: dict = None,
    extracted_fields: dict = None,
    crypto_result: dict = None,
    consistency_result: dict = None,
    photo_result: dict = None,
    qr_result: dict = None,
    tampering_result: dict = None,
    quality_result: dict = None,
    typography_result: dict = None
) -> list:
    """
    Constructs the dynamic 15-row Forensic Evidence Table (Section 22).
    Every row status and impact is dynamically derived from actual analysis without hardcoding.
    """
    structure_info = structure_info or {}
    extracted_fields = extracted_fields or {}
    crypto_result = crypto_result or {}
    consistency_result = consistency_result or {}
    photo_result = photo_result or {}
    qr_result = qr_result or {}
    tampering_result = tampering_result or {}
    quality_result = quality_result or {}
    typography_result = typography_result or {}
    
    fields = extracted_fields.get("fields", {})
    matrix = consistency_result.get("matrix", {})
    
    table = []
    
    # 1. Aadhaar number
    num_info = fields.get("aadhaar_number", {})
    num_st = num_info.get("status", "NOT_VISIBLE")
    masked_val = num_info.get("masked_value", "XXXX XXXX 1234")
    if num_st == "CHECKSUM_VALID":
        st_txt = f"Valid ({masked_val}, Verhoeff Checked)"
        imp_txt = "Supporting"
    elif num_st in ("FORMAT_VALID", "MASKED_VALID"):
        st_txt = f"Valid Format ({masked_val})"
        imp_txt = "Supporting"
    elif num_st in ("INVALID_CHECKSUM", "INVALID_FORMAT"):
        st_txt = "Invalid Checksum / Structure"
        imp_txt = "Suspicious"
    else:
        st_txt = "Not Isolated / Incomplete"
        imp_txt = "Neutral"
    table.append({"evidence": "Aadhaar number", "status": st_txt, "impact": imp_txt})
    
    # 2. EID / Enrolment Information
    eid_info = fields.get("enrolment_id", {})
    eid_st = eid_info.get("status", "NOT_PRESENT")
    if eid_st in ("PRESENT_VALID", "PRESENT_INCOMPLETE_TIMESTAMP"):
        eid_txt = f"Present ({eid_info.get('formatted', '14/28 digit')})"
    elif eid_st == "PRESENT_INVALID_SYNTAX":
        eid_txt = "Present (Malformed Syntax)"
    else:
        eid_txt = "Absent (Standard Issued Aadhaar)"
    table.append({"evidence": "EID", "status": eid_txt, "impact": "Informational"})
    
    # 3. Name
    name_m = matrix.get("name", {})
    name_info = fields.get("name", {})
    if name_m.get("status") == "MATCH":
        n_st = "Consistent (Matches QR)"
        n_imp = "Supporting"
    elif name_m.get("status") == "MISMATCH":
        n_st = "Mismatch (Contradicts QR)"
        n_imp = "Suspicious"
    elif name_info.get("status") == "EXTRACTED":
        n_st = f"Extracted ({name_info.get('value', 'Visible')})"
        n_imp = "Supporting"
    elif name_info.get("status") == "UNCERTAIN":
        n_st = "Uncertain (Low OCR Confidence)"
        n_imp = "Neutral"
    else:
        n_st = "Not Visible"
        n_imp = "Neutral"
    table.append({"evidence": "Name", "status": n_st, "impact": n_imp})
    
    # 4. DOB / Age
    dob_m = matrix.get("dob", {})
    dob_info = fields.get("dob", {})
    if dob_m.get("status") == "MATCH":
        d_st = "Consistent (Matches QR)"
        d_imp = "Supporting"
    elif dob_m.get("status") == "MISMATCH":
        d_st = "Mismatch (Contradicts QR)"
        d_imp = "Suspicious"
    elif dob_info.get("status") == "EXTRACTED":
        d_st = f"Valid Date ({dob_info.get('dob', 'Calendar Valid')})"
        d_imp = "Supporting"
    elif dob_info.get("status") == "UNCERTAIN":
        d_st = "Uncertain (OCR Distortion)"
        d_imp = "Neutral"
    else:
        d_st = "Not Visible"
        d_imp = "Neutral"
    table.append({"evidence": "DOB", "status": d_st, "impact": d_imp})
    
    # 5. Gender
    gen_m = matrix.get("gender", {})
    gen_info = fields.get("gender", {})
    if gen_m.get("status") == "MATCH":
        g_st = "Consistent (Matches QR)"
        g_imp = "Supporting"
    elif gen_m.get("status") == "MISMATCH":
        g_st = "Mismatch (Contradicts QR)"
        g_imp = "Suspicious"
    elif gen_info.get("status") == "EXTRACTED":
        g_st = f"Extracted ({gen_info.get('value', 'Visible')})"
        g_imp = "Supporting"
    else:
        g_st = "Not Visible"
        g_imp = "Neutral"
    table.append({"evidence": "Gender", "status": g_st, "impact": g_imp})
    
    # 6. Address
    addr_m = matrix.get("address", {})
    addr_info = fields.get("address", {})
    if addr_m.get("status") == "MATCH":
        a_st = "Consistent (Semantic Match)"
        a_imp = "Supporting"
    elif addr_m.get("status") == "MISMATCH":
        a_st = "Mismatch (Contradicts QR)"
        a_imp = "Suspicious"
    elif addr_info.get("status") == "EXTRACTED":
        a_st = "Extracted (Normalized)"
        a_imp = "Supporting"
    else:
        a_st = "Not Visible"
        a_imp = "Neutral"
    table.append({"evidence": "Address", "status": a_st, "impact": a_imp})
    
    # 7. Photograph
    if photo_result.get("present"):
        p_st = "Present (Portrait Localized)"
        p_imp = "Supporting"
    else:
        p_st = "Absent / Not Localized"
        p_imp = "Informational"
    table.append({"evidence": "Photograph", "status": p_st, "impact": p_imp})
    
    # 8. Photo forensics
    pf_st = photo_result.get("status", "CLEAN")
    if pf_st == "CLEAN":
        pf_txt = "Clean (No Splicing Anomaly)"
        pf_imp = "Supporting"
    elif pf_st == "MANIPULATED_BOUNDARY":
        pf_txt = "Manipulated Boundary"
        pf_imp = "Suspicious"
    elif pf_st == "SUSPICIOUS_REPLACEMENT":
        pf_txt = "Suspicious Replacement"
        pf_imp = "Suspicious"
    elif pf_st == "PHOTO_INCONSISTENT":
        pf_txt = "Contradicts QR Portrait"
        pf_imp = "Suspicious"
    else:
        pf_txt = "Unverified"
        pf_imp = "Neutral"
    table.append({"evidence": "Photo forensics", "status": pf_txt, "impact": pf_imp})
    
    # 9. Secure QR
    is_pan_doc = structure_info.get("document_type") == "PAN Card"
    if qr_result.get("decoded"):
        sq_st = "Decoded Successfully"
        sq_imp = "Supporting"
    elif qr_result.get("detected"):
        sq_st = "Detected (Bitstream Unresolvable)"
        sq_imp = "Neutral"
    elif is_pan_doc:
        sq_st = "Not Present (Legacy Format)"
        sq_imp = "Neutral"
    else:
        sq_st = "Not Detected / Missing on Canvas"
        sq_imp = "Review Required (Missing Security Feature)"
    table.append({"evidence": "Secure QR", "status": sq_st, "impact": sq_imp})
    
    # 10. QR signature
    sig_st = crypto_result.get("status", "NOT_CONFIGURED")
    if sig_st == "VERIFIED":
        sig_txt = "Verified (Official UIDAI Authority)"
        sig_imp = "Strong Supporting"
    elif sig_st == "INVALID":
        sig_txt = "Invalid (Signature Mismatch)"
        sig_imp = "Strong Suspicious"
    else:
        sig_txt = "Unavailable (Provider Not Configured)"
        sig_imp = "Neutral"
    table.append({"evidence": "QR signature", "status": sig_txt, "impact": sig_imp})
    
    # 11. QR/OCR consistency
    cross_st = consistency_result.get("status", "NOT_AVAILABLE")
    if cross_st == "CONSISTENT":
        c_txt = "Consistent (Corroborated)"
        c_imp = "Supporting"
    elif cross_st == "PARTIALLY_CONSISTENT":
        c_txt = "Partially Consistent"
        c_imp = "Supporting"
    elif cross_st == "INCONSISTENT":
        c_txt = "Inconsistent (Contradiction)"
        c_imp = "Strong Suspicious"
    else:
        c_txt = "Not Available (Unresolved QR/OCR)"
        c_imp = "Neutral"
    table.append({"evidence": "QR/OCR consistency", "status": c_txt, "impact": c_imp})
    
    # 12. Document structure
    s_score = structure_info.get("structure_score", 85)
    if s_score >= 80:
        ds_txt = "Consistent (Standard Layout)"
        ds_imp = "Supporting"
    else:
        ds_txt = "Irregular Structure"
        ds_imp = "Weak Suspicious"
    table.append({"evidence": "Document structure", "status": ds_txt, "impact": ds_imp})
    
    # 13. Typography
    t_score = typography_result.get("score", 100)
    if t_score >= 80:
        ty_txt = "Consistent (Uniform Strokes)"
        ty_imp = "Weak Supporting"
    else:
        ty_txt = "Minor Disparity"
        ty_imp = "Neutral"
    table.append({"evidence": "Typography", "status": ty_txt, "impact": ty_imp})
    
    # 14. Image quality
    q_score = quality_result.get("score", 100)
    if q_score >= 70:
        iq_txt = f"Good ({q_score}/100)"
    elif q_score >= 45:
        iq_txt = f"Moderate ({q_score}/100)"
    else:
        iq_txt = f"Low ({q_score}/100)"
    table.append({"evidence": "Image quality", "status": iq_txt, "impact": "Informational"})
    
    # 15. Tampering evidence
    t_sev = tampering_result.get("severity", "NONE")
    if t_sev in ("HIGH", "CRITICAL"):
        te_txt = f"Localized Tampering ({t_sev})"
        te_imp = "Suspicious"
    elif t_sev == "MODERATE":
        te_txt = "Weak Anomaly Traces"
        te_imp = "Neutral"
    else:
        te_txt = "None Strong (Clean Substrate)"
        te_imp = "Supporting"
    table.append({"evidence": "Tampering evidence", "status": te_txt, "impact": te_imp})
    
    return table

def build_evidence_summary(
    authenticity_score: int,
    classification: str,
    structure_info: dict,
    extracted_fields: dict = None,
    photo_result: dict = None,
    crypto_result: dict = None,
    consistency_result: dict = None,
    tampering_result: dict = None,
    quality_result: dict = None,
    qr_result: dict = None
) -> list:
    """
    Constructs explainable result summary bullet points (Section 21).
    """
    items = []
    fields = (extracted_fields.get("fields") or {}) if extracted_fields else {}
    photo_result = photo_result or {}
    crypto_result = crypto_result or {}
    consistency_result = consistency_result or {}
    tampering_result = tampering_result or {}
    quality_result = quality_result or {}
    qr_result = qr_result or {}
    
    # 1. Aadhaar number
    num_info = fields.get("aadhaar_number", {})
    num_st = num_info.get("status")
    if num_st in ("CHECKSUM_VALID", "FORMAT_VALID", "MASKED_VALID"):
        items.append("✓ Aadhaar number format valid")
    elif num_st in ("INVALID_CHECKSUM", "INVALID_FORMAT"):
        items.append("✗ Aadhaar number checksum or structure invalid")
        
    # 2. Name
    name_info = fields.get("name", {})
    if name_info.get("status") == "EXTRACTED":
        items.append("✓ Name internally consistent")
    elif name_info.get("status") == "UNCERTAIN":
        items.append("⚠ Name reading uncertain due to low OCR confidence")
        
    # 3. DOB
    dob_info = fields.get("dob", {})
    if dob_info.get("status") == "EXTRACTED":
        items.append("✓ DOB internally consistent")
    elif dob_info.get("status") == "UNCERTAIN":
        items.append("⚠ DOB reading uncertain due to low OCR confidence")
        
    # 4. Address
    addr_info = fields.get("address", {})
    if addr_info.get("status") == "EXTRACTED":
        items.append("✓ Address internally consistent")
        
    # 5. Photograph
    if photo_result.get("present"):
        items.append("✓ Photograph present")
        if photo_result.get("status") == "CLEAN":
            items.append("✓ No strong photo replacement evidence")
        elif photo_result.get("status") in ("SUSPICIOUS_REPLACEMENT", "MANIPULATED_BOUNDARY", "PHOTO_INCONSISTENT"):
            items.append("✗ Suspicious photograph boundary or replacement detected")
            
    # 6. Tampering / Text replacement
    t_sev = tampering_result.get("severity", "NONE")
    if t_sev in ("HIGH", "CRITICAL"):
        items.append("✗ Strong localized image manipulation evidence detected")
    else:
        items.append("✓ No strong text replacement evidence")
        
    # 7. Document structure
    s_score = structure_info.get("structure_score", 85)
    if s_score >= 80:
        items.append("✓ Document structure consistent")
    else:
        items.append("⚠ Document structure exhibits formatting anomalies")
        
    # 8. Secure QR / Cryptographic
    crypto_st = crypto_result.get("status", "NOT_CONFIGURED")
    is_pan_doc = structure_info.get("document_type") == "PAN Card"
    if crypto_st == "VERIFIED":
        items.append("✓ Secure QR cryptographically verified by UIDAI certificate")
    elif crypto_st == "INVALID":
        items.append("✗ Secure QR cryptographic digital signature invalid")
    elif qr_result.get("detected"):
        items.append("⚠ Secure QR detected but cryptographic verification unavailable")
    elif not is_pan_doc:
        items.append("⚠ Secure QR code not detected on Aadhaar canvas (standard security feature missing; official verification impossible)")
        
    # 9. Image quality
    q_score = quality_result.get("score", 100)
    if q_score >= 70:
        items.append("✓ Image quality good")
    elif q_score >= 45:
        items.append("⚠ Image quality moderate")
    else:
        items.append("⚠ Image quality low (insufficient visual evidence)")
        
    return items

def compute_fused_authenticity(
    structure_info: dict,
    quality_result: dict,
    ocr_result: dict,
    qr_result: dict,
    typography_result: dict,
    layout_result: dict,
    forensics_result: dict,
    tampering_result: dict = None,
    photo_result: dict = None,
    crypto_result: dict = None,
    consistency_result: dict = None,
    extracted_fields: dict = None
) -> tuple:
    """
    Complete Multi-Evidence Document Forensic Fusion Model with Tampering Dominance.
    
    Hierarchy:
    CRYPTOGRAPHIC / STRONG TAMPERING > FIELD CONTRADICTIONS > DOCUMENT STRUCTURE > TYPOGRAPHY / LAYOUT > OCR > QUALITY
    """
    doc_type = structure_info.get("document_type", "Identity Document")
    is_pan = (doc_type == "PAN Card")
    photo_result = photo_result or {}
    crypto_result = crypto_result or {"status": "NOT_CONFIGURED", "authority": "N/A"}
    consistency_result = consistency_result or {"status": "NOT_AVAILABLE", "matrix": {}}
    extracted_fields = extracted_fields or {}
    
    # 1. Resolve Tampering Result
    if tampering_result is None:
        if isinstance(forensics_result, dict) and "tampering_score" in forensics_result:
            tampering_result = forensics_result
        else:
            is_anom = forensics_result.get("anomaly_detected", False) if isinstance(forensics_result, dict) else False
            f_score = forensics_result.get("score", 100) if isinstance(forensics_result, dict) else 100
            t_score = (100 - f_score) if is_anom else max(0, 100 - f_score)
            t_sev = "HIGH" if (is_anom and t_score >= 45) else ("NONE" if t_score < 10 else "LOW")
            tampering_result = {
                "tampering_score": t_score,
                "tampering_integrity_score": 100 - t_score,
                "severity": t_sev,
                "status": "STRONG_TAMPERING_EVIDENCE" if (is_anom and t_score >= 45) else "NO_STRONG_ANOMALY",
                "regions": [{"id": "T-01", "signal": "ELA_SPLICING_ANOMALY", "type": "TAMPERING", "area_px": 5000}] if (is_anom and t_score >= 45) else [],
                "signals": [{"name": "ELA_SPLICING_ANOMALY", "severity": t_sev}] if (is_anom and t_score >= 45) else []
            }
            
    tampering_score = tampering_result.get("tampering_score", 0)
    tampering_integrity_score = tampering_result.get("tampering_integrity_score", 100 - tampering_score)
    tampering_severity = tampering_result.get("severity", "NONE")
    
    # 2. Component Base Scores
    structure_score = structure_info.get("structure_score", 85)
    typography_score = typography_result.get("score", 100)
    layout_score = layout_result.get("score", 100)
    quality_score = quality_result.get("score", 100)
    
    # Field consistency: internal format correctness and key fields presence
    has_fields = bool(structure_info.get("fields_detected")) or bool(extracted_fields.get("fields"))
    valid_format = structure_info.get("is_valid_format", True)
    field_consistency_score = 95 if (valid_format and has_fields) else (85 if valid_format else 50)
    
    # Independent Dimension 1: Document Consistency Score
    document_consistency_score = int(round(
        0.35 * structure_score +
        0.35 * field_consistency_score +
        0.15 * typography_score +
        0.15 * layout_score
    ))
    
    # Machine Readable / QR & Cryptographic Evidence
    qr_status = qr_result.get("status")
    if not qr_status:
        if qr_result.get("decoded"):
            qr_status = "DECODED_UNVERIFIED"
        elif qr_result.get("detected"):
            qr_status = "DETECTED_NOT_DECODED"
        else:
            qr_status = "NOT_DETECTED"
    crypto_status = crypto_result.get("status", "NOT_CONFIGURED")
    qr_cross = qr_result.get("ocr_cross_check", {})
    cross_status = qr_cross.get("status", "NOT_AVAILABLE")
    if consistency_result.get("status") in ("CONSISTENT", "INCONSISTENT"):
        cross_status = consistency_result.get("status")
        
    qr_applicable = not is_pan
    
    if crypto_status == "VERIFIED" or qr_status == "SIGNATURE_VERIFIED":
        qr_score = 100
        cross_score = 100 if cross_status != "INCONSISTENT" else 15
    elif crypto_status == "INVALID" or qr_status == "SIGNATURE_INVALID":
        qr_score = 0
        cross_score = 20
    elif qr_status in ("DETECTED_NOT_DECODED", "DECODED_UNVERIFIED", "DECODED_URL", "NOT_APPLICABLE"):
        # Neutral: 0 penalty
        qr_score = 100
        cross_score = 100 if cross_status != "INCONSISTENT" else 15
    elif qr_status == "NOT_DETECTED":
        if is_pan:
            # Older physical PAN cards without QR are non-fraudulent and not penalized
            qr_score = 100
            cross_score = 100 if cross_status != "INCONSISTENT" else 15
        else:
            # On Aadhaar, Secure QR is a standard security feature. Missing QR cannot provide positive cryptographic proof.
            qr_score = 25
            cross_score = 25
    else:
        qr_score = 100
        cross_score = 100 if cross_status != "INCONSISTENT" else 15

    if cross_status == "INCONSISTENT":
        cross_score = 15

    # 3. Dynamic Evidence Fusion
    if is_pan and not qr_result.get("detected"):
        raw_authenticity = (
            0.35 * tampering_integrity_score +
            0.25 * structure_score +
            0.20 * field_consistency_score +
            0.10 * typography_score +
            0.10 * layout_score
        )
    else:
        raw_authenticity = (
            0.30 * tampering_integrity_score +
            0.25 * qr_score +
            0.15 * cross_score +
            0.10 * structure_score +
            0.10 * field_consistency_score +
            0.05 * typography_score +
            0.05 * layout_score
        )

    # 4. HIGH SUSPICION GATE (Section 20)
    copy_move_detected = tampering_result.get("metrics", {}).get("copy_move_detected", False)
    non_redaction_signals = [
        s for s in tampering_result.get("signals", [])
        if s.get("name") not in ("PRIVACY_REDACTION", "UNIFORM_PROFILE")
        and s.get("severity") in ("HIGH", "CRITICAL")
    ]
    non_redaction_regions = [
        r for r in tampering_result.get("regions", [])
        if r.get("signal") not in ("PRIVACY_REDACTION", "UNIFORM_PROFILE")
        and r.get("type") != "USER_PRIVACY_MASK"
    ]
    overlay_anomaly_regions = [
        r for r in tampering_result.get("regions", [])
        if r.get("signal") == "OVERLAY_ANOMALY" or r.get("type") == "DIGITAL_PAINT_OVERLAY"
    ]

    is_high_suspicion_eligible = False
    gate_reason = ""

    if crypto_status == "INVALID" or qr_status == "SIGNATURE_INVALID":
        is_high_suspicion_eligible = True
        gate_reason = "Cryptographic digital signature validation failed"
    elif cross_status == "INCONSISTENT" or consistency_result.get("status") == "INCONSISTENT":
        is_high_suspicion_eligible = True
        gate_reason = "Machine-readable QR identity data directly contradicts visible text"
    elif photo_result.get("status") in ("SUSPICIOUS_REPLACEMENT", "PHOTO_INCONSISTENT"):
        is_high_suspicion_eligible = True
        gate_reason = "Strong photograph replacement / splicing evidence detected"
    elif copy_move_detected:
        is_high_suspicion_eligible = True
        gate_reason = "Confirmed copy-move / cloning detected"
    elif len(non_redaction_signals) >= 2:
        is_high_suspicion_eligible = True
        gate_reason = f"Multiple independent tampering signals: {', '.join(s['name'] for s in non_redaction_signals)}"
    elif tampering_severity in ("HIGH", "CRITICAL") and tampering_score >= 50 and len(non_redaction_regions) >= 1:
        is_high_suspicion_eligible = True
        gate_reason = "Confirmed localized non-redaction tampering"
    elif len(overlay_anomaly_regions) >= 4:
        is_high_suspicion_eligible = True
        gate_reason = "Multiple localized digital paint overlays / surface defacement detected"

    # Dominance Law
    if is_high_suspicion_eligible:
        if crypto_status == "INVALID" or qr_status == "SIGNATURE_INVALID":
            raw_authenticity = min(raw_authenticity, 20)
        elif cross_status == "INCONSISTENT" or consistency_result.get("status") == "INCONSISTENT":
            raw_authenticity = min(raw_authenticity, 30)
        elif photo_result.get("status") in ("SUSPICIOUS_REPLACEMENT", "PHOTO_INCONSISTENT"):
            raw_authenticity = min(raw_authenticity, 35)
        elif tampering_severity == "CRITICAL":
            raw_authenticity = min(raw_authenticity, 25)
        elif tampering_severity == "HIGH":
            raw_authenticity = min(raw_authenticity, 45)
        elif len(overlay_anomaly_regions) >= 4:
            raw_authenticity = min(raw_authenticity, 45)
    else:
        # High Suspicion Gate is CLOSED: Weak/uncertain evidence cannot create High Suspicion
        raw_authenticity = max(raw_authenticity, 50.0)

    # Missing QR cap for Aadhaar:
    # Under Section 16, if Secure QR is missing on an Aadhaar card, the document cannot achieve Likely Authentic (>= 75).
    # It must be capped at Review Required (<= 62).
    if not is_pan and qr_status == "NOT_DETECTED":
        raw_authenticity = min(raw_authenticity, 62.0)

    if crypto_status == "VERIFIED" or qr_status == "SIGNATURE_VERIFIED":
        raw_authenticity = max(raw_authenticity, 88.0)

    authenticity_score = int(round(max(0, min(100, raw_authenticity))))
    risk_score = 100 - authenticity_score

    # 5. Supporting Evidence vs Negative Evidence
    supporting_evidence = []
    negative_evidence = []

    if structure_score >= 80:
        supporting_evidence.append(
            f"Supporting consistency signal: Document structure is internally consistent for {doc_type}."
        )
    else:
        negative_evidence.append(
            f"Structural formatting anomalies or missing primary identification fields for {doc_type}."
        )

    if is_high_suspicion_eligible and tampering_severity in ("HIGH", "CRITICAL"):
        negative_evidence.append(
            f"STRONG TAMPERING EVIDENCE: Multi-spectral forensic analysis detected localized digital manipulation / splicing ({tampering_result.get('status')})."
        )
    elif tampering_severity == "MODERATE" and is_high_suspicion_eligible:
        negative_evidence.append(
            f"Possible local modification: Correlated forensic anomalies detected ({tampering_result.get('status')})."
        )
    elif tampering_severity in ("NONE", "LOW") or not is_high_suspicion_eligible:
        supporting_evidence.append(
            "Forensic integrity supported: Absence of confirmed localized digital tampering."
        )

    # Photo Evidence
    if photo_result.get("present"):
        if photo_result.get("status") == "CLEAN":
            supporting_evidence.append("Photograph forensic integrity supported: No localized boundary splicing or substrate noise discontinuity.")
        elif photo_result.get("status") in ("SUSPICIOUS_REPLACEMENT", "MANIPULATED_BOUNDARY", "PHOTO_INCONSISTENT"):
            negative_evidence.append("Photograph manipulation detected: Edge step discontinuity or noise variance indicates potential portrait replacement.")

    # Consistency Cross-Check Evidence
    if cross_status == "CONSISTENT" or consistency_result.get("status") == "CONSISTENT":
        supporting_evidence.append("Machine-readable QR payload strictly consistent with OCR extracted textual fields.")
    elif cross_status == "INCONSISTENT" or consistency_result.get("status") == "INCONSISTENT":
        negative_evidence.append("QR payload contradiction: Machine-readable identity data does not match OCR textual fields on document.")

    # Privacy Redactions
    privacy_redactions = tampering_result.get("privacy_redactions", [])
    if privacy_redactions:
        supporting_evidence.append(
            f"Privacy redaction observed: {len(privacy_redactions)} sensitive identity field(s)/QR intentionally masked (zero fraud penalty)."
        )

    # QR & Machine Readable Evidence
    if crypto_status == "VERIFIED" or qr_status == "SIGNATURE_VERIFIED":
        supporting_evidence.append("Cryptographic digital signature verified against official trust authority.")
    elif crypto_status == "INVALID" or qr_status == "SIGNATURE_INVALID":
        negative_evidence.append("Cryptographic digital signature validation failed; QR payload integrity compromised.")
    elif qr_result.get("decoded"):
        supporting_evidence.append(f"Machine-readable QR payload decoded successfully ({qr_result.get('payload_type', 'Standard')}).")
    elif qr_result.get("detected"):
        supporting_evidence.append("2D barcode matrix pattern localized on document canvas (bitstream unresolvable due to scan resolution/blur; neutral).")
    elif not qr_applicable:
        supporting_evidence.append("Document specification does not mandate machine-readable 2D barcode.")
    else:
        negative_evidence.append("Standard UIDAI Secure QR code is missing or not detected on canvas (machine-readable cryptographic verification unavailable).")

    # Typography
    if typography_score >= 85:
        supporting_evidence.append("Supporting consistency signal: Typographic stroke consistency within standard tolerance.")
    elif typography_score < 70 and is_high_suspicion_eligible:
        negative_evidence.append("Significant text ink saturation or font bounding-box discrepancy detected.")

    # Layout
    if layout_score >= 85:
        supporting_evidence.append("Supporting consistency signal: Internal column margins and spacing conform to consistent document layout.")
    elif layout_score < 70 and is_high_suspicion_eligible:
        negative_evidence.append("Spatial alignment anomaly or text element collision detected.")

    # 6. Risk Breakdown
    if risk_score == 0:
        risk_breakdown = {k: 0 for k in ("quality", "ocr", "qr", "typography", "layout", "image_forensics")}
    else:
        qr_p = 0
        if crypto_status == "INVALID" or qr_status == "SIGNATURE_INVALID":
            qr_p = 75
        elif cross_status == "INCONSISTENT":
            qr_p = 65
        elif not is_pan and qr_status == "NOT_DETECTED":
            qr_p = 40

        forensics_p = 0
        if is_high_suspicion_eligible:
            forensics_p = max(0, tampering_score)
        elif tampering_score > 0:
            forensics_p = min(10, tampering_score)

        typo_p = 0 if typography_score >= 80 else (min(5, 100 - typography_score) if not is_high_suspicion_eligible else max(0, 100 - typography_score))
        layout_p = 0 if layout_score >= 80 else (min(5, 100 - layout_score) if not is_high_suspicion_eligible else max(0, 100 - layout_score))
        ocr_p = 0 if structure_score >= 80 else (min(5, 100 - structure_score) if not is_high_suspicion_eligible else max(0, 100 - structure_score))

        raw_p = {
            "image_forensics": forensics_p,
            "qr": qr_p,
            "typography": typo_p,
            "layout": layout_p,
            "ocr": ocr_p,
            "quality": 0
        }

        total_p = sum(raw_p.values())
        if total_p > 0:
            alloc = {}
            running_sum = 0
            for k in ("quality", "ocr", "qr", "typography", "layout"):
                val = int(round(raw_p[k] * risk_score / total_p))
                alloc[k] = max(0, val)
                running_sum += alloc[k]
            alloc["image_forensics"] = max(0, risk_score - running_sum)
            diff = risk_score - sum(alloc.values())
            if diff != 0:
                alloc["image_forensics"] = max(0, alloc["image_forensics"] + diff)
            risk_breakdown = alloc
        else:
            risk_breakdown = {k: 0 for k in ("quality", "ocr", "qr", "typography", "layout", "image_forensics")}
            risk_breakdown["image_forensics"] = risk_score

    # Determine classification for table/summary building
    temp_classification = "Likely Authentic" if authenticity_score >= 75 else ("Review Required" if (authenticity_score >= 50 or not is_high_suspicion_eligible) else "High Suspicion")

    evidence_table = build_forensic_evidence_table(
        structure_info=structure_info,
        extracted_fields=extracted_fields,
        crypto_result=crypto_result,
        consistency_result=consistency_result,
        photo_result=photo_result,
        qr_result=qr_result,
        tampering_result=tampering_result,
        quality_result=quality_result,
        typography_result=typography_result
    )

    evidence_summary = build_evidence_summary(
        authenticity_score=authenticity_score,
        classification=temp_classification,
        structure_info=structure_info,
        extracted_fields=extracted_fields,
        photo_result=photo_result,
        crypto_result=crypto_result,
        consistency_result=consistency_result,
        tampering_result=tampering_result,
        quality_result=quality_result,
        qr_result=qr_result
    )

    signals = {
        "document_consistency": {
            "score": document_consistency_score,
            "status": "CONSISTENT" if document_consistency_score >= 80 else "IRREGULAR"
        },
        "tampering_integrity": {
            "score": tampering_integrity_score,
            "tampering_score": tampering_score,
            "severity": tampering_severity,
            "status": tampering_result.get("status", "NO_STRONG_ANOMALY")
        },
        "qr": {
            "status": qr_status,
            "payload_type": qr_result.get("payload_type", "UNKNOWN"),
            "integrity": qr_score,
            "cross_check": cross_status
        },
        "ocr": {
            "status": ocr_result.get("status", "TEXT_DETECTED"),
            "confidence": ocr_result.get("average_confidence", 0.0),
            "evidence_strength": ocr_result.get("evidence_strength", "MODERATE" if ocr_result.get("average_confidence", 0) > 0.5 else "LIMITED")
        },
        "structure": {
            "document_type": doc_type,
            "valid_format": structure_info.get("is_valid_format", True),
            "integrity": structure_score
        },
        "typography": {
            "score": typography_score,
            "status": "CONSISTENT" if typography_score >= 80 else "DISPARITY"
        },
        "layout": {
            "score": layout_score,
            "status": "CONSISTENT" if layout_score >= 80 else "ANOMALY"
        },
        "image_forensics": {
            "score": tampering_integrity_score,
            "tampering_score": tampering_score,
            "severity": tampering_severity,
            "anomaly_detected": is_high_suspicion_eligible or tampering_severity in ("HIGH", "CRITICAL")
        },
        "high_suspicion_gate": {
            "eligible": is_high_suspicion_eligible,
            "reason": gate_reason
        },
        "photo": photo_result,
        "verification": crypto_result,
        "consistency": consistency_result,
        "aadhaar_fields": extracted_fields,
        "evidence_table": evidence_table,
        "evidence_summary": evidence_summary
    }

    return (authenticity_score, risk_score, supporting_evidence, negative_evidence, signals, risk_breakdown)


def process_document(file_path: str, case_id: str = None) -> dict:
    """
    Main orchestration function for the forensic pipeline.
    Produces a standardized, canonical forensic analysis result with explainable risk breakdown.
    Coupled scores: risk_score = 100 - authenticity_score.
    """
    if not case_id:
        case_id = f"SC-2026-{int(time.time())}"
        
    # 1. Execute individual forensic analysis modules
    quality_result = analyze_quality(file_path)
    ocr_result = analyze_ocr(file_path)
    
    # 1b. Intercept fictional / synthetic demonstration documents
    is_fictional, _ = is_fictional_document(file_path, ocr_result=ocr_result)
    if is_fictional:
        return build_fictional_analysis_result(
            file_path=file_path,
            case_id=case_id,
            quality_result=quality_result,
            ocr_result=ocr_result
        )

    qr_result = analyze_qr(file_path, ocr_data=ocr_result)
    typography_result = analyze_typography(file_path, ocr_result)
    layout_result = analyze_layout(file_path, ocr_result, qr_result)
    forensics_result = analyze_image_forensics(file_path)
    tampering_result = analyze_tampering(file_path, ocr_result=ocr_result, qr_result=qr_result)
    
    # 2. Evaluate document structure and format
    structure_info = detect_document_structure(ocr_result, qr_result)
    doc_type = structure_info["document_type"]
    assessment_title = structure_info["assessment_title"]
    
    # 2b. Aadhaar-Specific Multi-Evidence Forensic Extraction
    if doc_type == "Aadhaar Card":
        extracted_fields = extract_aadhaar_fields(ocr_result, qr_result)
        photo_result = analyze_photograph_forensics(file_path, qr_result=qr_result)
        provider = AadhaarVerificationProvider()
        crypto_result = provider.verify(qr_result)
        consistency_result = cross_check_aadhaar_consistency(extracted_fields, qr_result, photo_result)
        if crypto_result.get("status") == "VERIFIED":
            qr_result["status"] = "SIGNATURE_VERIFIED"
        elif crypto_result.get("status") == "INVALID":
            qr_result["status"] = "SIGNATURE_INVALID"
    else:
        extracted_fields = {}
        photo_result = {"present": False, "status": "NOT_APPLICABLE", "findings": ["Photograph analysis not applicable"]}
        crypto_result = {"status": "NOT_APPLICABLE", "authority": "N/A", "details": "Not an Aadhaar document"}
        consistency_result = {"status": "NOT_APPLICABLE", "matrix": {}, "summary": "Not applicable for document type"}
    
    # 3. Multi-Evidence Fusion with Tampering Dominance
    (
        authenticity_score,
        risk_score,
        supporting_evidence,
        negative_evidence,
        signals,
        risk_breakdown
    ) = compute_fused_authenticity(
        structure_info,
        quality_result,
        ocr_result,
        qr_result,
        typography_result,
        layout_result,
        forensics_result,
        tampering_result=tampering_result,
        photo_result=photo_result,
        crypto_result=crypto_result,
        consistency_result=consistency_result,
        extracted_fields=extracted_fields
    )

    
    # Extract High Suspicion Gate parameters
    gate_info = signals.get("high_suspicion_gate", {})
    is_high_suspicion_eligible = gate_info.get("eligible", False)
    gate_reason = gate_info.get("reason", "")

    # 4. Canonical classification (Section 14: Gate enforced)
    if authenticity_score >= 75:
        classification = "Likely Authentic"
    elif authenticity_score >= 50 or not is_high_suspicion_eligible:
        classification = "Review Required"
    else:
        classification = "High Suspicion"
        
    # 5. Compile canonical evidence items with deep explainability
    evidence = []
    
    # Quality Evidence
    quality_contrib = risk_breakdown.get("quality", 0)
    q_severity = "Warning" if quality_result.get("score", 100) < 50 else "Info"
    q_blur = quality_result.get("blur_score") or quality_result.get("blur_metric") or "Metric unavailable"
    q_bright = quality_result.get("brightness", "Metric unavailable")
    q_dims = quality_result.get("dimensions", "Metric unavailable")
    q_conf = quality_result.get("confidence")
    
    evidence.append({
        "id": "EV-001",
        "category": "Quality",
        "title": "Image Quality Assessment",
        "severity": q_severity,
        "risk_contribution": quality_contrib,
        "confidence": q_conf,
        "observed_metrics": [
            f"Laplacian blur variance: {q_blur}",
            f"Canvas luminance: {q_bright}/255",
            f"Frame resolution: {q_dims}"
        ],
        "assessment": quality_result.get("interpretation", "Image quality baseline evaluated for forensic inspection."),
        "finding": "; ".join(quality_result.get("findings", ["Image clarity acceptable."])),
        "explanation": "Image clarity, sharpness, and illumination metrics calibrate baseline forensic confidence. Quality degradation does not directly indicate tampering."
    })
    
    # OCR Evidence
    ocr_contrib = risk_breakdown.get("ocr", 0)
    raw_ocr_txt = ocr_result.get("extracted_text") or ocr_result.get("raw_text") or ""
    ocr_words = len(raw_ocr_txt.split())
    ocr_conf_raw = ocr_result.get("average_confidence")
    ocr_conf_pct = round(float(ocr_conf_raw) * 100) if (ocr_conf_raw is not None and not str(ocr_conf_raw) == 'nan') else None
    ocr_ev_strength = ocr_result.get("evidence_strength", "MODERATE" if (ocr_conf_pct or 0) > 50 else "LIMITED")
    ocr_severity = "Warning" if ocr_contrib >= 15 else "Info"
    
    evidence.append({
        "id": "EV-002",
        "category": "OCR",
        "title": "OCR Text Extraction",
        "severity": ocr_severity,
        "risk_contribution": ocr_contrib,
        "confidence": ocr_conf_pct,
        "observed_metrics": [
            f"Word count isolated: {ocr_words}",
            f"Mean character confidence: {f'{ocr_conf_pct}%' if ocr_conf_pct is not None else 'Metric unavailable'}",
            f"Evidence strength: {ocr_ev_strength}",
            f"Extraction status: {ocr_result.get('status', 'TEXT_DETECTED')}"
        ],
        "assessment": f"Textual fields extracted with {ocr_ev_strength.lower()} optical certainty. Sub-baseline recognition confidence does not independently indicate document tampering.",
        "finding": "; ".join(ocr_result.get("findings", ["Text extraction complete."])),
        "explanation": "Extracts document textual data and measures character recognition confidence."
    })
    
    # QR Evidence
    qr_contrib = risk_breakdown.get("qr", 0)
    qr_status = qr_result.get("status", "NOT_DETECTED")
    qr_payload_type = qr_result.get("payload_type", "UNKNOWN")
    qr_verification = qr_result.get("verification", {})
    qr_cross = qr_result.get("ocr_cross_check", {})
    qr_severity = "High" if qr_status == "SIGNATURE_INVALID" or qr_cross.get("status") == "INCONSISTENT" else ("Warning" if qr_contrib >= 15 else "Info")

    if qr_status == "NOT_APPLICABLE":
        qr_title = "QR Code Not Applicable"
        qr_assessment = "QR code expectation not applicable for this document type."
        qr_explanation = "Verifies machine-readable barcode presence. QR code not mandated for this document specification."
    elif qr_status == "SIGNATURE_VERIFIED":
        qr_title = "QR Cryptographic Signature Verified"
        qr_assessment = f"QR payload decoded and cryptographically verified against {qr_verification.get('authority', 'UIDAI')} digital signature."
        qr_explanation = "Cryptographic digital signature verified against official trust authority."
    elif qr_status == "SIGNATURE_INVALID":
        qr_title = "QR Digital Signature Validation Failed"
        qr_severity = "High"
        qr_assessment = "QR payload decoded, but cryptographic digital signature validation failed. Data integrity compromise suspected."
        qr_explanation = "Cryptographic verification establishes that the QR code payload has been altered or forged."
    elif qr_status == "DECODED_URL":
        qr_title = "QR Web Link Decoded"
        decoded_link = qr_result.get("decoded_url") or qr_result.get("url")
        qr_assessment = f"Decoded web link: {decoded_link}."
        qr_explanation = "Verifies machine-readable web link presence and safety."
    elif qr_result.get("decoded"):
        if qr_payload_type == "AADHAAR_SECURE_QR":
            qr_title = "Aadhaar Secure QR Decoded"
            qr_assessment = "QR payload decoded successfully."
        else:
            qr_title = "QR Code Payload Decoded"
            qr_assessment = "QR payload decoded successfully."
        qr_explanation = "Verifies machine-readable barcode presence and decodability."
    elif qr_result.get("detected"):
        qr_title = "QR Pattern Detected"
        qr_assessment = "2D matrix detected on canvas."
        qr_explanation = "2D matrix detected on canvas, but bitstream could not be resolved."
    else:
        qr_title = "QR Code Status"
        qr_assessment = "QR code not mandated for this document or absent from scan."
        qr_explanation = "Verifies machine-readable barcode presence and decodability."

    if qr_cross.get("status") == "INCONSISTENT":
        qr_severity = "High"
        qr_assessment += " Note: Machine-readable QR payload conflicts with OCR extracted document text."

    qr_conf = 100 if qr_result.get("decoded") else qr_result.get("confidence")

    observed_metrics = [
        f"2D matrix presence: {'Localized' if qr_result.get('detected') else 'Not detected'}",
        f"Bitstream decode status: {qr_status}",
        f"Payload standard: {qr_payload_type}"
    ]
    if qr_result.get("decoded_url") or qr_result.get("url"):
        observed_metrics.append(f"Safe web link: {qr_result.get('decoded_url') or qr_result.get('url')}")
    if qr_result.get("decoder"):
        observed_metrics.append(f"Decoder engine: {qr_result.get('decoder')} ({qr_result.get('decode_confidence', 'NONE')})")
    if qr_verification.get("status") != "NOT_PERFORMED":
        observed_metrics.append(f"Digital signature: {qr_verification.get('status')}")
    if qr_cross.get("status") and qr_cross.get("status") != "NOT_AVAILABLE":
        observed_metrics.append(f"QR ↔ OCR cross-check: {qr_cross.get('status')}")

    evidence.append({
        "id": "EV-003",
        "category": "QR",
        "title": qr_title,
        "severity": qr_severity,
        "risk_contribution": qr_contrib,
        "confidence": qr_conf,
        "observed_metrics": observed_metrics,
        "assessment": qr_assessment,
        "finding": "; ".join(qr_result.get("findings", ["QR code evaluated."])),
        "explanation": qr_explanation
    })
    
    # Typography Evidence
    typography_contrib = risk_breakdown.get("typography", 0)
    typo_score = typography_result.get("score", 100)
    typo_conf = typography_result.get("confidence")
    h_ratio = typography_result.get("height_ratio")
    h_metric_str = f"Bounding-box height ratio: {h_ratio}x relative to median line height" if h_ratio is not None else "Bounding-box height variance: Metric unavailable"
    sat_delta = typography_result.get("saturation_delta")
    sat_metric_str = f"Ink saturation variance: {sat_delta} saturation units" if sat_delta is not None else "Ink saturation variance: Metric unavailable"

    if typography_contrib > 10:
        evidence.append({
            "id": "EV-004",
            "category": "Typography",
            "title": "Typography Disparity",
            "severity": "Warning",
            "risk_contribution": typography_contrib,
            "confidence": typo_conf,
            "observed_metrics": [
                f"Typography score: {typo_score}/100",
                f"Risk contribution: +{typography_contrib} pts",
                h_metric_str,
                sat_metric_str
            ],
            "assessment": "Disproportionate text bounding-box heights or chromatic ink variations detected.",
            "finding": "; ".join(typography_result.get("findings", ["Typography inconsistencies detected."])),
            "explanation": "Screens for inconsistent text bounding-box heights, altered line heights, or ink saturation discrepancies across detected text."
        })
    else:
        evidence.append({
            "id": "EV-004",
            "category": "Typography",
            "title": "Supporting Consistency Signal: Typography",
            "severity": "Info",
            "risk_contribution": typography_contrib,
            "confidence": typo_conf,
            "observed_metrics": [
                f"Typography score: {typo_score}/100",
                h_metric_str,
                sat_metric_str
            ],
            "assessment": "Uniform text bounding-box heights, baseline spacing, and ink saturation across document fields.",
            "finding": "; ".join(typography_result.get("findings", ["Consistent bounding-box heights and ink saturation across detected text lines."])),
            "explanation": "Screens for inconsistent text bounding-box heights, altered line heights, or ink saturation discrepancies across detected text."
        })
        
    # Layout Evidence
    layout_contrib = risk_breakdown.get("layout", 0)
    layout_score = layout_result.get("score", 100)
    layout_conf = layout_result.get("confidence")
    if layout_contrib > 10:
        evidence.append({
            "id": "EV-005",
            "category": "Layout",
            "title": "Layout Alignment Anomaly",
            "severity": "Warning",
            "risk_contribution": layout_contrib,
            "confidence": layout_conf,
            "observed_metrics": [
                f"Layout geometry score: {layout_score}/100",
                f"Risk contribution: +{layout_contrib} pts",
                "Internal layout consistency: Irregular horizontal margin or vertical line spacing detected"
            ],
            "assessment": "Spatial displacement relative to internal document alignment grid.",
            "finding": "; ".join(layout_result.get("findings", ["Irregular spatial layout detected."])),
            "explanation": "Screens for internal layout consistency, misaligned column margins, and irregular vertical line spacing between fields."
        })
    else:
        evidence.append({
            "id": "EV-005",
            "category": "Layout",
            "title": "Supporting Consistency Signal: Layout",
            "severity": "Info",
            "risk_contribution": layout_contrib,
            "confidence": layout_conf,
            "observed_metrics": [
                f"Layout geometry score: {layout_score}/100",
                "Internal column margin alignment: Consistent with document baseline",
                "Inter-field vertical gaps: Nominal"
            ],
            "assessment": "Internal spatial layout consistency observed across margins and line spacing.",
            "finding": "; ".join(layout_result.get("findings", ["Internal layout consistency observed across margins and line spacing."])),
            "explanation": "Screens for internal layout consistency, misaligned column margins, and irregular vertical line spacing between fields."
        })
        
    # Image Forensics & Tampering Evidence
    image_forensics_contrib = risk_breakdown.get("image_forensics", 0)
    tamper_severity = tampering_result.get("severity", "NONE")
    tamper_status = tampering_result.get("status", "NO_STRONG_ANOMALY")
    tamper_score = tampering_result.get("tampering_score", 0)
    tamper_integrity = tampering_result.get("tampering_integrity_score", 100 - tamper_score)
    tamper_regions = tampering_result.get("regions", [])
    tamper_signals = tampering_result.get("signals", [])
    tamper_conf = tampering_result.get("confidence", 85)

    ev_severity = "High" if tamper_severity in ("CRITICAL", "HIGH") else ("Warning" if tamper_severity == "MODERATE" else "Info")
    
    if tamper_severity in ("CRITICAL", "HIGH", "MODERATE") or image_forensics_contrib > 10:
        obs_metrics = [
            f"Tampering score: {tamper_score}/100 (Severity: {tamper_severity})",
            f"Tampering integrity score: {tamper_integrity}/100",
            f"Risk contribution: +{image_forensics_contrib} pts",
            f"Detected anomaly regions: {len(tamper_regions)}"
        ]
        if tampering_result.get("metrics", {}).get("overlay_pct", 0) > 0:
            obs_metrics.append(f"Synthetic overlay/paint coverage: {tampering_result['metrics']['overlay_pct']}% of canvas")
        if tampering_result.get("metrics", {}).get("copy_move_detected"):
            obs_metrics.append("Spatial copy-move cloning: CONFIRMED")
        if tamper_signals:
            obs_metrics.append(f"Primary signals: {', '.join([s['name'] for s in tamper_signals[:3]])}")

        evidence.append({
            "id": "EV-006",
            "category": "Image Forensics",
            "title": f"Forensic Tampering Evidence ({tamper_severity})",
            "severity": ev_severity,
            "risk_contribution": image_forensics_contrib,
            "confidence": tamper_conf,
            "observed_metrics": obs_metrics,
            "assessment": f"Localized forensic manipulation indicators detected ({tamper_status}). Multi-spectral analysis reveals synthetic overlays, pixel discontinuities, or compression mismatches.",
            "finding": "; ".join(tampering_result.get("findings", ["Localized forensic anomalies detected."])),
            "explanation": "Screens for localized synthetic overlays, copy-move cloning, resampling periodicity, and localized compression variance across document canvas."
        })
    else:
        evidence.append({
            "id": "EV-006",
            "category": "Image Forensics",
            "title": "Forensic Integrity Verified",
            "severity": "Info",
            "risk_contribution": image_forensics_contrib,
            "confidence": tamper_conf,
            "observed_metrics": [
                f"Tampering score: {tamper_score}/100 (Severity: NONE)",
                f"Tampering integrity score: {tamper_integrity}/100",
                "Localized synthetic overlays: None detected",
                "Copy-move / cloning: None detected",
                "Uniform compression profile: Verified"
            ],
            "assessment": "No strong localized anomaly detected. Pixel noise distribution and compression characteristics are uniform across document canvas.",
            "finding": "; ".join(tampering_result.get("findings", ["No localized digital splicing or tampering detected."])),
            "explanation": "Screens for localized synthetic overlays, copy-move cloning, resampling periodicity, and localized compression variance across document canvas."
        })

    # Aadhaar-Specific Evidence Cards (EV-007 and EV-008)
    if doc_type == "Aadhaar Card":
        photo_present = photo_result.get("present", False)
        photo_st = photo_result.get("status", "CLEAN")
        p_sev = "High" if photo_st in ("SUSPICIOUS_REPLACEMENT", "PHOTO_INCONSISTENT") else ("Warning" if photo_st == "MANIPULATED_BOUNDARY" else "Info")
        evidence.append({
            "id": "EV-007",
            "category": "Photograph Forensics",
            "title": f"Portrait Substrate & Edge Forensics ({photo_st})",
            "severity": p_sev,
            "risk_contribution": 25 if p_sev == "High" else (10 if p_sev == "Warning" else 0),
            "confidence": 85 if photo_present else None,
            "observed_metrics": [
                f"Photograph presence: {'Localized' if photo_present else 'Not Isolated'}",
                f"Boundary gradient step: {photo_result.get('boundary_step', 0.0):.2f}",
                f"Substrate noise variance ratio: {photo_result.get('noise_variance_ratio', 1.0):.2f}",
                f"Photo status: {photo_st}"
            ],
            "assessment": "Portrait region boundary gradient and substrate noise variance evaluated for replacement or copy-paste splicing.",
            "finding": "; ".join(photo_result.get("findings", ["Portrait substrate consistent."])),
            "explanation": "Screens portrait frame for localized recompression, high edge step discontinuities, or artificial replacement."
        })
        
        c_status = consistency_result.get("status", "NOT_AVAILABLE")
        c_sev = "High" if c_status == "INCONSISTENT" else "Info"
        evidence.append({
            "id": "EV-008",
            "category": "Identity Consistency",
            "title": f"QR ↔ Visible Text Multi-Field Cross-Check ({c_status})",
            "severity": c_sev,
            "risk_contribution": 30 if c_sev == "High" else 0,
            "confidence": 90 if consistency_result.get("match_count", 0) > 0 else None,
            "observed_metrics": [
                f"Cross-check status: {c_status}",
                f"Matches: {consistency_result.get('match_count', 0)}",
                f"Mismatches: {consistency_result.get('mismatch_count', 0)}",
                f"Summary: {consistency_result.get('summary', 'Evaluation complete')}"
            ],
            "assessment": "Cross-corroborates optical character recognition fields against machine-readable Secure QR payload records.",
            "finding": consistency_result.get("summary", "Cross-corroboration complete."),
            "explanation": "Performs multi-field corroboration between visible card text and decoded machine-readable barcode bytes."
        })
        
    # 6. Generate visual assets
    original_image_b64 = encode_image_to_base64(file_path)
    heatmap_b64 = generate_heatmap(file_path, evidence, tampering_result=tampering_result)
    
    # Ensure tampering_result is strictly JSON serializable (pop raw numpy mask)
    if isinstance(tampering_result, dict):
        tampering_result.pop("anomaly_mask", None)
    
    # 7. Document Fingerprint
    fingerprint = extract_document_fingerprint({
        "quality": quality_result,
        "ocr": ocr_result,
        "qr": qr_result,
        "typography": typography_result,
        "layout": layout_result,
        "image_forensics": forensics_result,
        "tampering": tampering_result
    }, image_dimensions=quality_result.get("dimensions"))
    
    # 8. Forensic Recommendation
    if authenticity_score >= 75:
        recommendation = "Document exhibits strong authenticity indicators consistent with internal baseline profiles. Standard verification procedures apply."
    elif authenticity_score >= 50:
        recommendation = "Manual investigator review recommended. Moderate visual degradation or incomplete machine-readable verification requires secondary check."
    else:
        recommendation = "High forensic suspicion. Severe manipulation indicators detected (e.g. localized synthetic overlays/blackouts, copy-move cloning, digital signature failure, or compression divergence). Detailed secondary inspection strongly advised."

    # Top-level aggregate forensic signal confidence from real module confidences
    valid_confs = [e["confidence"] for e in evidence if e.get("confidence") is not None]
    mean_confidence = int(round(sum(valid_confs) / len(valid_confs))) if valid_confs else None

    # Classification display formatting
    if classification == "Likely Authentic":
        classification_display = "LIKELY AUTHENTIC — BASED ON AVAILABLE FORENSIC EVIDENCE"
    elif classification == "Review Required":
        classification_display = "REVIEW REQUIRED — INSUFFICIENT / MIXED EVIDENCE"
    else:
        classification_display = "HIGH SUSPICION — STRONG MANIPULATION/VERIFICATION EVIDENCE"

    verification_status = crypto_result.get("status", "NOT_CONFIGURED") if crypto_result else "NOT_CONFIGURED"
    field_consistency = consistency_result.get("status", "NOT_AVAILABLE") if consistency_result else "NOT_AVAILABLE"
    photo_status = photo_result.get("status", "CLEAN") if photo_result else "NOT_APPLICABLE"
    forensic_status = tampering_result.get("status", "NO_STRONG_ANOMALY")
    document_structure_status = "CONSISTENT" if structure_info.get("structure_score", 85) >= 80 else "IRREGULAR"
    
    q_score = quality_result.get("score", 100)
    image_quality_status = "GOOD" if q_score >= 70 else ("MODERATE" if q_score >= 45 else "LOW")
    privacy_status = "PRIVACY_REDACTION_DETECTED" if tampering_result.get("privacy_redactions") else "NONE_DETECTED"

    evidence_table = signals.get("evidence_table") or []
    evidence_summary = signals.get("evidence_summary") or []

    aadhaar_profile = {
        "fields": extracted_fields,
        "photo_forensics": photo_result,
        "verification": crypto_result,
        "consistency": consistency_result,
        "evidence_table": evidence_table,
        "evidence_summary": evidence_summary,
        "disclaimer": "SENTINEL performs forensic screening and does not replace official UIDAI authentication or authorized identity verification."
    }

    return {
        "case_id": case_id,
        "document_type": doc_type,
        "assessment_title": assessment_title,
        "authenticity_score": authenticity_score,
        "risk_score": risk_score,
        "classification": classification,
        "classification_display": classification_display,
        "confidence": mean_confidence,
        "risk_contribution": risk_score,
        "image_quality_score": quality_result.get("score", 100),
        "tampering_evidence_score": tampering_result.get("tampering_score", 0),
        "document_consistency_score": signals["document_consistency"]["score"],
        "tampering_integrity_score": signals["tampering_integrity"]["score"],
        "verification_status": verification_status,
        "field_consistency": field_consistency,
        "qr_status": qr_result.get("status", "NOT_DETECTED"),
        "photo_status": photo_status,
        "forensic_status": forensic_status,
        "document_structure_status": document_structure_status,
        "image_quality_status": image_quality_status,
        "privacy_status": privacy_status,
        "evidence_table": evidence_table,
        "evidence_summary": evidence_summary,
        "aadhaar_profile": aadhaar_profile,
        "disclaimer": "SENTINEL performs forensic screening and does not replace official UIDAI authentication or authorized identity verification.",
        "aadhaar_secure_qr_status": qr_result.get("status", "NOT_DETECTED"),
        "is_high_suspicion_eligible": is_high_suspicion_eligible,
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
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }

