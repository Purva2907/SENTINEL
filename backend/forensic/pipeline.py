import os
import time
from .image_quality import analyze_quality
from .ocr import analyze_ocr
from .qr import analyze_qr
from .typography import analyze_typography
from .layout import analyze_layout
from .heatmap import generate_heatmap, analyze_image_forensics, encode_image_to_base64

def process_document(file_path: str, case_id: str = None) -> dict:
    """
    Main orchestration function for the forensic pipeline.
    Produces a standardized, canonical forensic analysis result with explainable risk breakdown.
    """
    if not case_id:
        case_id = f"SC-2026-{int(time.time())}"
        
    # 1. Execute individual forensic analysis modules
    quality_result = analyze_quality(file_path)
    ocr_result = analyze_ocr(file_path)
    qr_result = analyze_qr(file_path)
    typography_result = analyze_typography(file_path, ocr_result)
    layout_result = analyze_layout(file_path, ocr_result, qr_result)
    forensics_result = analyze_image_forensics(file_path)
    
    # 2. Extract component risk contributions
    quality_contrib = int(quality_result.get("risk_contribution", 0))
    ocr_contrib = int(ocr_result.get("risk_contribution", 0))
    qr_contrib = int(qr_result.get("risk_contribution", 0))
    typography_contrib = int(typography_result.get("risk_contribution", 0))
    layout_contrib = int(layout_result.get("risk_contribution", 0))
    image_forensics_contrib = int(forensics_result.get("risk_contribution", 0))
    
    # 3. Calculate canonical, finite risk score [0, 100]
    total_risk = (
        quality_contrib +
        ocr_contrib +
        qr_contrib +
        typography_contrib +
        layout_contrib +
        image_forensics_contrib
    )
    risk_score = max(0, min(100, int(round(total_risk))))
    
    # 4. Canonical classification
    if risk_score < 35:
        classification = "Likely Authentic"
    elif risk_score < 70:
        classification = "Review Required"
    else:
        classification = "High Suspicion"
        
    # 5. Compile canonical evidence items with deep explainability
    evidence = []
    
    # Quality Evidence
    q_severity = "High" if quality_contrib >= 10 else ("Warning" if quality_contrib > 0 else "Info")
    q_blur = quality_result.get("blur_score") or quality_result.get("blur_metric") or "Metric unavailable"
    q_bright = quality_result.get("brightness", "Metric unavailable")
    q_dims = quality_result.get("dimensions", "Metric unavailable")
    q_conf = quality_result.get("confidence")  # None if module does not calculate confidence
    
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
        "assessment": "Substrate clarity and illumination baseline verified for forensic inspection." if quality_contrib == 0 else "Image degradation or low-resolution capture impairs forensic certainty.",
        "finding": "; ".join(quality_result.get("findings", ["Image clarity acceptable."])),
        "explanation": "Image clarity, sharpness, and illumination metrics calibrate baseline forensic confidence."
    })
    
    # OCR Evidence
    ocr_severity = "High" if ocr_contrib >= 10 else ("Warning" if ocr_contrib > 0 else "Info")
    raw_ocr_txt = ocr_result.get("extracted_text") or ocr_result.get("raw_text") or ""
    ocr_words = len(raw_ocr_txt.split())
    ocr_conf_raw = ocr_result.get("average_confidence")
    ocr_conf_pct = round(float(ocr_conf_raw) * 100) if (ocr_conf_raw is not None and not str(ocr_conf_raw) == 'nan') else None
    
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
            f"Extraction status: {ocr_result.get('status', 'TEXT_DETECTED')}"
        ],
        "assessment": "Textual fields extracted with high optical certainty." if ocr_contrib == 0 else "Sub-baseline character recognition confidence or low contrast text isolated.",
        "finding": "; ".join(ocr_result.get("findings", ["Text extraction complete."])),
        "explanation": "Extracts document textual data and measures character recognition confidence."
    })
    
    # QR Evidence
    qr_severity = "High" if qr_contrib >= 15 else ("Warning" if qr_contrib > 0 else "Info")
    if qr_result.get("status") == "NOT_APPLICABLE":
        qr_title = "QR Code Not Applicable"
    elif qr_result.get("decoded"):
        qr_title = "QR Code Verification"
    elif qr_result.get("detected"):
        qr_title = "QR Pattern Detected (Unreadable)"
    else:
        qr_title = "QR Code Missing"

    # Only decoded QR has cryptographic/bitstream certainty (100); otherwise null
    qr_conf = 100 if qr_result.get("decoded") else qr_result.get("confidence")
    
    if qr_result.get("status") == "NOT_APPLICABLE":
        qr_assessment = "QR code expectation not applicable for this document type."
    elif qr_result.get("decoded"):
        qr_assessment = "QR payload decoded successfully. Payload authenticity was not cryptographically verified."
    elif qr_result.get("detected"):
        qr_assessment = "2D matrix detected but payload could not be decoded. Payload authenticity was not cryptographically verified."
    else:
        qr_assessment = "Mandatory 2D machine-readable credential barcode is absent."

    evidence.append({
        "id": "EV-003",
        "category": "QR",
        "title": qr_title,
        "severity": qr_severity,
        "risk_contribution": qr_contrib,
        "confidence": qr_conf,
        "observed_metrics": [
            f"2D matrix presence: {'Localized' if qr_result.get('detected') else 'Not detected'}",
            f"Bitstream decode status: {'Successfully decoded' if qr_result.get('decoded') else ('Detected but undecodable' if qr_result.get('detected') else 'Not detected')}",
            f"Format standard: {qr_result.get('payload_type', '2D Matrix Barcode' if qr_result.get('detected') else 'None')}"
        ],
        "assessment": qr_assessment,
        "finding": "; ".join(qr_result.get("findings", ["QR code evaluated."])),
        "explanation": "Verifies machine-readable barcode presence and decodability. Payload authenticity was not cryptographically verified."
    })
    
    # Typography Evidence
    typo_score = typography_result.get("score", 100)
    typo_conf = typography_result.get("confidence")  # None if module does not calculate confidence
    h_ratio = typography_result.get("height_ratio")
    h_metric_str = f"Bounding-box height ratio: {h_ratio}x relative to median line height" if h_ratio is not None else "Bounding-box height variance: Metric unavailable"
    sat_delta = typography_result.get("saturation_delta")
    sat_metric_str = f"Ink saturation variance: {sat_delta} saturation units" if sat_delta is not None else "Ink saturation variance: Metric unavailable"

    if typography_contrib > 0:
        evidence.append({
            "id": "EV-004",
            "category": "Typography",
            "title": "Typography Disparity",
            "severity": "High" if typography_contrib >= 15 else "Warning",
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
            "title": "Typographic Consistency",
            "severity": "Info",
            "risk_contribution": 0,
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
    layout_score = layout_result.get("score", 100)
    layout_conf = layout_result.get("confidence")  # None if module does not calculate confidence
    if layout_contrib > 0:
        evidence.append({
            "id": "EV-005",
            "category": "Layout",
            "title": "Layout Alignment Anomaly",
            "severity": "High" if layout_contrib >= 12 else "Warning",
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
            "title": "Internal Layout Consistency",
            "severity": "Info",
            "risk_contribution": 0,
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
        
    # Image Forensics / ELA Evidence
    ela_anomaly = forensics_result.get("anomaly_detected", False)
    ela_conf = forensics_result.get("confidence")  # None if module does not calculate confidence
    ela_mean_val = forensics_result.get("ela_mean", "Metric unavailable")
    ela_std_val = forensics_result.get("ela_std", "Metric unavailable")

    if image_forensics_contrib > 0:
        evidence.append({
            "id": "EV-006",
            "category": "Image Forensics",
            "title": "Error Level Analysis (ELA) Anomaly",
            "severity": "High",
            "risk_contribution": image_forensics_contrib,
            "confidence": ela_conf,
            "observed_metrics": [
                f"Quantization error mean: {ela_mean_val}",
                f"Quantization error std: {ela_std_val}",
                f"Risk contribution: +{image_forensics_contrib} pts",
                "Localized compression profile mismatch across pixel tiles"
            ],
            "assessment": "JPEG quantization divergence indicates potential localized digital splicing or graphic modification.",
            "finding": "; ".join(forensics_result.get("findings", ["Localized compression anomaly detected."])),
            "explanation": "JPEG recompression divergence indicates potential digital splicing or regional graphic insertion."
        })
    else:
        evidence.append({
            "id": "EV-006",
            "category": "Image Forensics",
            "title": "Uniform Compression Profile",
            "severity": "Info",
            "risk_contribution": 0,
            "confidence": ela_conf,
            "observed_metrics": [
                f"Quantization error mean: {ela_mean_val}",
                f"Quantization error std: {ela_std_val}",
                "Localized recompression anomaly: None detected"
            ],
            "assessment": "No localized compression divergence detected across document canvas.",
            "finding": "; ".join(forensics_result.get("findings", ["Uniform compression artifact distribution across document canvas."])),
            "explanation": "No localized compression divergence detected across document canvas."
        })
        
    # 6. Generate visual assets
    original_image_b64 = encode_image_to_base64(file_path)
    heatmap_b64 = generate_heatmap(file_path, evidence)
    
    # 7. Document Fingerprint (Measurable characteristics, risk_score excluded)
    from .fingerprint import extract_document_fingerprint
    fingerprint = extract_document_fingerprint({
        "quality": quality_result,
        "ocr": ocr_result,
        "qr": qr_result,
        "typography": typography_result,
        "layout": layout_result,
        "image_forensics": forensics_result
    }, image_dimensions=quality_result.get("dimensions"))
    
    # 8. Forensic Recommendation
    if risk_score < 35:
        recommendation = "Document screening indicates standard consistency with baseline forensic profiles. Standard verification procedures apply."
    elif risk_score < 70:
        recommendation = "Manual investigator review recommended. Moderate visual or structural anomalies were detected."
    else:
        recommendation = "High forensic suspicion. Multiple severe indicators flagged (e.g. compression divergence, barcode discrepancies, or typography mismatch). Detailed secondary inspection strongly advised."

    # Top-level aggregate forensic signal confidence from real module confidences
    valid_confs = [e["confidence"] for e in evidence if e.get("confidence") is not None]
    mean_confidence = int(round(sum(valid_confs) / len(valid_confs))) if valid_confs else None

    return {
        "case_id": case_id,
        "document_type": "Aadhaar-like",
        "risk_score": risk_score,
        "classification": classification,
        "confidence": mean_confidence,
        "risk_contribution": total_risk,
        "quality": quality_result,
        "ocr": ocr_result,
        "qr": qr_result,
        "typography": typography_result,
        "layout": layout_result,
        "image_forensics": forensics_result,
        "risk_breakdown": {
            "quality": quality_contrib,
            "ocr": ocr_contrib,
            "qr": qr_contrib,
            "typography": typography_contrib,
            "layout": layout_contrib,
            "image_forensics": image_forensics_contrib
        },
        "evidence": evidence,
        "original_image": original_image_b64,
        "heatmap": heatmap_b64,
        "fingerprint": fingerprint,
        "recommendation": recommendation,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
