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
        
    # 5. Compile canonical evidence items
    evidence = []
    
    # Quality Evidence
    q_severity = "High" if quality_contrib >= 10 else ("Warning" if quality_contrib > 0 else "Info")
    evidence.append({
        "id": "EV-001",
        "category": "Quality",
        "title": "Image Quality Assessment",
        "severity": q_severity,
        "risk_contribution": quality_contrib,
        "finding": "; ".join(quality_result.get("findings", ["Image clarity acceptable."])),
        "explanation": "Image clarity, sharpness, and illumination metrics calibrate baseline forensic confidence."
    })
    
    # OCR Evidence
    ocr_severity = "High" if ocr_contrib >= 10 else ("Warning" if ocr_contrib > 0 else "Info")
    evidence.append({
        "id": "EV-002",
        "category": "OCR",
        "title": "OCR Text Extraction",
        "severity": ocr_severity,
        "risk_contribution": ocr_contrib,
        "finding": "; ".join(ocr_result.get("findings", ["Text extraction complete."])),
        "explanation": "Extracts document textual data and measures character recognition confidence."
    })
    
    # QR Evidence
    qr_severity = "High" if qr_contrib >= 15 else ("Warning" if qr_contrib > 0 else "Info")
    qr_title = "QR Code Verification" if qr_result.get("decoded") else ("QR Pattern Detected (Unreadable)" if qr_result.get("detected") else "QR Code Missing")
    evidence.append({
        "id": "EV-003",
        "category": "QR",
        "title": qr_title,
        "severity": qr_severity,
        "risk_contribution": qr_contrib,
        "finding": "; ".join(qr_result.get("findings", ["QR code verified."])),
        "explanation": "Verifies machine-readable barcode presence, format consistency, and payload integrity."
    })
    
    # Typography Evidence
    if typography_contrib > 0:
        evidence.append({
            "id": "EV-004",
            "category": "Typography",
            "title": "Typography Disparity",
            "severity": "High" if typography_contrib >= 15 else "Warning",
            "risk_contribution": typography_contrib,
            "finding": "; ".join(typography_result.get("findings", ["Typography inconsistencies detected."])),
            "explanation": "Identifies inconsistent font sizes, altered line heights, or chromatic text ink discrepancies."
        })
    else:
        evidence.append({
            "id": "EV-004",
            "category": "Typography",
            "title": "Typographic Consistency",
            "severity": "Info",
            "risk_contribution": 0,
            "finding": "; ".join(typography_result.get("findings", ["Consistent font sizing and ink appearance across document fields."])),
            "explanation": "Verified uniform font family, sizing, and ink density across document fields."
        })
        
    # Layout Evidence
    if layout_contrib > 0:
        evidence.append({
            "id": "EV-005",
            "category": "Layout",
            "title": "Layout Alignment Anomaly",
            "severity": "High" if layout_contrib >= 12 else "Warning",
            "risk_contribution": layout_contrib,
            "finding": "; ".join(layout_result.get("findings", ["Irregular spatial layout detected."])),
            "explanation": "Screens for misaligned column margins and irregular vertical line spacing between fields."
        })
    else:
        evidence.append({
            "id": "EV-005",
            "category": "Layout",
            "title": "Standard Layout Geometry",
            "severity": "Info",
            "risk_contribution": 0,
            "finding": "; ".join(layout_result.get("findings", ["Standard field margins and uniform line spacing."])),
            "explanation": "Standard document margin alignment and uniform line spacing confirmed."
        })
        
    # Image Forensics / ELA Evidence
    if image_forensics_contrib > 0:
        evidence.append({
            "id": "EV-006",
            "category": "Image Forensics",
            "title": "Error Level Analysis (ELA) Anomaly",
            "severity": "High",
            "risk_contribution": image_forensics_contrib,
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
            "finding": "; ".join(forensics_result.get("findings", ["Uniform compression artifact distribution across document canvas."])),
            "explanation": "No localized compression divergence or digital splicing boundaries detected."
        })
        
    # 6. Generate visual assets
    original_image_b64 = encode_image_to_base64(file_path)
    heatmap_b64 = generate_heatmap(file_path, evidence)
    
    # 7. Forensic Recommendation
    if risk_score < 35:
        recommendation = "Document screening indicates standard consistency with baseline forensic profiles. Standard verification procedures apply."
    elif risk_score < 70:
        recommendation = "Manual investigator review recommended. Moderate visual or structural anomalies were detected."
    else:
        recommendation = "High forensic suspicion. Multiple severe indicators flagged (e.g. compression divergence, barcode discrepancies, or typography mismatch). Detailed secondary inspection strongly advised."

    return {
        "case_id": case_id,
        "document_type": "Aadhaar-like",
        "risk_score": risk_score,
        "classification": classification,
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
        "recommendation": recommendation,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
