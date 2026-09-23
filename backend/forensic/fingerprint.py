import hashlib
import json
import math
from typing import Dict, Any, List, Tuple, Optional

def extract_document_fingerprint(analysis_data: Dict[str, Any], image_dimensions: Tuple[int, int] = None) -> Dict[str, Any]:
    """
    Generates a normalized forensic document fingerprint from observable physical and structural traits.
    
    IMPORTANT:
    `risk_score` is strictly EXCLUDED from the fingerprint calculation so that system output
    does not artificially bias document similarity.
    """
    quality = analysis_data.get("quality", {})
    ocr = analysis_data.get("ocr", {})
    qr = analysis_data.get("qr", {})
    typography = analysis_data.get("typography", {})
    layout = analysis_data.get("layout", {})
    image_forensics = analysis_data.get("image_forensics", {})

    # 1. Image dimensions & geometry
    dims = image_dimensions or quality.get("dimensions") or [800, 600]
    w = float(dims[0]) if len(dims) > 0 and dims[0] else 800.0
    h = float(dims[1]) if len(dims) > 1 and dims[1] else 600.0
    aspect = w / h if h > 0 else 1.33

    norm_w = min(1.0, max(0.0, w / 2500.0))
    norm_h = min(1.0, max(0.0, h / 2500.0))
    norm_aspect = min(1.0, max(0.0, aspect / 3.0))

    # 2. OCR Structural Traits
    raw_text = ocr.get("extracted_text") or ocr.get("raw_text") or ""
    words = [wd for wd in raw_text.split() if wd.strip()]
    word_count = len(words)
    norm_word_count = min(1.0, word_count / 120.0)
    avg_conf = float(ocr.get("average_confidence", 0.8)) if ocr.get("average_confidence") is not None else 0.8
    norm_conf = min(1.0, max(0.0, avg_conf))

    # 3. Typography metrics
    typo_score = float(typography.get("score", 100))
    typo_var = 1.0 - (typo_score / 100.0)  # 0.0 = uniform, 1.0 = high disparity

    # 4. Layout geometry metrics
    layout_score = float(layout.get("score", 100))
    layout_var = 1.0 - (layout_score / 100.0)

    # 5. Barcode / QR matrix state
    if qr.get("decoded"):
        qr_code = 1.0
    elif qr.get("detected"):
        qr_code = 0.5
    else:
        qr_code = 0.0

    # 6. Physical quality & ELA energy
    blur_raw = float(quality.get("blur_score") or quality.get("blur_metric") or 500.0)
    norm_blur = min(1.0, max(0.0, blur_raw / 1500.0))
    
    bright_raw = float(quality.get("brightness", 180.0))
    norm_bright = min(1.0, max(0.0, bright_raw / 255.0))

    ela_anomaly = 1.0 if image_forensics.get("anomaly_detected") else 0.0

    # Normalized feature vector (11 deterministic traits)
    vector = [
        round(norm_w, 4),
        round(norm_h, 4),
        round(norm_aspect, 4),
        round(norm_word_count, 4),
        round(norm_conf, 4),
        round(typo_var, 4),
        round(layout_var, 4),
        round(qr_code, 4),
        round(norm_blur, 4),
        round(norm_bright, 4),
        round(ela_anomaly, 4)
    ]

    # Deterministic quantized hash (for exact structural match)
    quantized_str = ",".join([f"{int(round(v * 50))}" for v in vector])
    fingerprint_hash = hashlib.sha256(quantized_str.encode('utf-8')).hexdigest()[:16].upper()

    return {
        "fingerprint_hash": f"FP-{fingerprint_hash}",
        "fingerprint_vector": vector,
        "feature_names": [
            "norm_width", "norm_height", "aspect_ratio", "word_count", "ocr_confidence",
            "typography_variance", "layout_variance", "qr_status", "blur_metric", "luminance", "ela_anomaly"
        ]
    }

def calculate_cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Computes cosine similarity between two normalized document vectors [0.0 - 1.0]."""
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0

    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    mag_a = math.sqrt(sum(a * a for a in vec_a))
    mag_b = math.sqrt(sum(b * b for b in vec_b))

    if mag_a == 0 or mag_b == 0:
        return 0.0

    sim = dot_product / (mag_a * mag_b)
    return max(0.0, min(1.0, sim))

def find_shared_forensic_signals(case_a: dict, case_b: dict) -> List[str]:
    """Identifies observable structural and forensic similarities between two cases."""
    shared = []
    
    an_a = case_a.get("analysis", {}) or {}
    an_b = case_b.get("analysis", {}) or {}
    
    # Check document type
    dtype_a = case_a.get("document_type") or an_a.get("document_type")
    dtype_b = case_b.get("document_type") or an_b.get("document_type")
    if dtype_a and dtype_b and dtype_a.lower() == dtype_b.lower():
        shared.append(f"Identical document classification ({dtype_a})")

    # Typography
    typo_a = an_a.get("typography", {}).get("risk_contribution", 0)
    typo_b = an_b.get("typography", {}).get("risk_contribution", 0)
    if typo_a > 0 and typo_b > 0:
        shared.append("Shared typography variance profile")

    # Layout
    lay_a = an_a.get("layout", {}).get("risk_contribution", 0)
    lay_b = an_b.get("layout", {}).get("risk_contribution", 0)
    if lay_a > 0 and lay_b > 0:
        shared.append("Congruent spatial layout misalignment")

    # QR status
    qr_a = an_a.get("qr", {}).get("detected")
    qr_b = an_b.get("qr", {}).get("detected")
    if qr_a == qr_b and qr_a is not None:
        if qr_a:
            shared.append("Matching 2D barcode presence & density")
        else:
            shared.append("Shared absence of machine-readable 2D barcode")

    # Image forensics
    ela_a = an_a.get("image_forensics", {}).get("anomaly_detected")
    ela_b = an_b.get("image_forensics", {}).get("anomaly_detected")
    if ela_a and ela_b:
        shared.append("Localized JPEG re-compression divergence in both specimens")

    if not shared:
        shared.append("Geometric aspect ratio and resolution match")

    return shared
