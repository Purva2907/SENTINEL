import cv2
import numpy as np
import base64
import os
from typing import Dict, Any, List, Tuple
from .heatmap import encode_image_to_base64

def compute_visual_difference_percentage(img_path_a: str, img_path_b: str, diff_threshold: int = 25) -> float:
    """
    Computes genuine visual difference percentage between two document specimens.
    
    Formula:
      1. Align Specimen B to Specimen A dimensions (w, h).
      2. Convert both aligned images to grayscale.
      3. Compute absolute per-pixel difference matrix: D = |I_A - I_B|.
      4. Filter out subtle JPEG compression noise by applying grayscale threshold (D > diff_threshold).
      5. Count significant discrepancy pixels: N_diff = count(D > diff_threshold).
      6. visual_difference_pct = (N_diff / (w * h)) * 100.0.

    Returns:
      Float value strictly bounded in [0.0, 100.0].
      - Identical images: exactly 0.0%
      - Minor localized differences: > 0.0%
      - Drastically distinct images: materially higher percentage.
    """
    if not img_path_a or not img_path_b or not os.path.exists(img_path_a) or not os.path.exists(img_path_b):
        return 0.0

    img_a = cv2.imread(img_path_a)
    img_b = cv2.imread(img_path_b)
    if img_a is None or img_b is None:
        return 0.0

    h_a, w_a = img_a.shape[:2]
    img_b_resized = cv2.resize(img_b, (w_a, h_a), interpolation=cv2.INTER_AREA)

    gray_a = cv2.cvtColor(img_a, cv2.COLOR_BGR2GRAY)
    gray_b = cv2.cvtColor(img_b_resized, cv2.COLOR_BGR2GRAY)

    abs_diff = cv2.absdiff(gray_a, gray_b)
    diff_pixels = int(np.count_nonzero(abs_diff > diff_threshold))
    total_pixels = h_a * w_a

    if total_pixels == 0:
        return 0.0

    pct = (diff_pixels / float(total_pixels)) * 100.0
    return round(float(pct), 2)

def generate_visual_diff_heatmap(img_path_a: str, img_path_b: str) -> str:
    """
    Computes OpenCV absolute difference between two document specimens and renders
    a high-contrast thermal difference heatmap.
    """
    if not img_path_a or not img_path_b or not os.path.exists(img_path_a) or not os.path.exists(img_path_b):
        return ""

    img_a = cv2.imread(img_path_a)
    img_b = cv2.imread(img_path_b)
    
    if img_a is None or img_b is None:
        return ""

    # Align dimensions of Specimen B to Specimen A
    h_a, w_a = img_a.shape[:2]
    img_b_resized = cv2.resize(img_b, (w_a, h_a), interpolation=cv2.INTER_AREA)

    # Compute absolute pixel difference across color channels
    diff = cv2.absdiff(img_a, img_b_resized)
    gray_diff = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)

    # Amplify difference signal
    amplified = cv2.normalize(gray_diff, None, 0, 255, cv2.NORM_MINMAX)
    
    # Apply thermal colormap (JET) for clear visual inspection
    colormap = cv2.applyColorMap(amplified, cv2.COLORMAP_JET)

    # Blend slightly with grayscale base for context
    gray_base = cv2.cvtColor(img_a, cv2.COLOR_BGR2GRAY)
    gray_base_bgr = cv2.cvtColor(gray_base, cv2.COLOR_GRAY2BGR)
    blended = cv2.addWeighted(gray_base_bgr, 0.35, colormap, 0.65, 0)

    # Encode to base64
    _, buf = cv2.imencode('.jpg', blended, [cv2.IMWRITE_JPEG_QUALITY, 90])
    return "data:image/jpeg;base64," + base64.b64encode(buf).decode('utf-8')

def compare_ocr_texts(text_a: str, text_b: str) -> Dict[str, Any]:
    """
    Performs neutral word-level and structural text differential analysis.
    Uses neutral terminology ('Text Difference Detected', 'Matching Characters').
    """
    words_a = [w.strip() for w in text_a.split() if w.strip()]
    words_b = [w.strip() for w in text_b.split() if w.strip()]

    set_a = set(w.lower() for w in words_a)
    set_b = set(w.lower() for w in words_b)

    common = set_a.intersection(set_b)
    unique_a = set_a.difference(set_b)
    unique_b = set_b.difference(set_a)

    total_unique = len(set_a.union(set_b))
    word_overlap_pct = round((len(common) / total_unique * 100), 1) if total_unique > 0 else 100.0

    return {
        "word_overlap_percentage": word_overlap_pct,
        "word_count_a": len(words_a),
        "word_count_b": len(words_b),
        "matching_words_count": len(common),
        "words_unique_to_a": list(unique_a)[:20],
        "words_unique_to_b": list(unique_b)[:20],
        "status": "Text Difference Detected" if (unique_a or unique_b) else "Matching Textual Content"
    }

def compare_two_documents(analysis_a: Dict[str, Any], analysis_b: Dict[str, Any], file_path_a: str = None, file_path_b: str = None) -> Dict[str, Any]:
    """
    Master comparative analysis function for two document specimens.
    Calculates genuine pixel difference percentage using the absolute pixel difference matrix.
    Uses neutral, defensible forensic language.
    """
    # 1. Risk score variance
    score_a = int(analysis_a.get("risk_score", 0))
    score_b = int(analysis_b.get("risk_score", 0))
    risk_diff = abs(score_a - score_b)

    cls_a = analysis_a.get("classification", "Unknown")
    cls_b = analysis_b.get("classification", "Unknown")

    # 2. Dimensions & Aspect
    dims_a = analysis_a.get("quality", {}).get("dimensions", [800, 600])
    dims_b = analysis_b.get("quality", {}).get("dimensions", [800, 600])

    # 3. OCR Text Diff
    txt_a = analysis_a.get("ocr", {}).get("extracted_text") or analysis_a.get("ocr", {}).get("raw_text") or ""
    txt_b = analysis_b.get("ocr", {}).get("extracted_text") or analysis_b.get("ocr", {}).get("raw_text") or ""
    ocr_diff = compare_ocr_texts(txt_a, txt_b)

    # 4. Forensic Signal Matrix Differences
    breakdown_a = analysis_a.get("risk_breakdown", {})
    breakdown_b = analysis_b.get("risk_breakdown", {})

    pillar_deltas = {}
    for pillar in ["quality", "ocr", "qr", "typography", "layout", "image_forensics"]:
        val_a = breakdown_a.get(pillar, 0)
        val_b = breakdown_b.get(pillar, 0)
        pillar_deltas[pillar] = {
            "score_a": val_a,
            "score_b": val_b,
            "delta": val_b - val_a,
            "status": "Signal Difference Detected" if val_a != val_b else "Matching Signal Threshold"
        }

    # 5. Visual Diff Heatmap & Genuine Visual Difference Percentage
    diff_heatmap = ""
    visual_difference_pct = 0.0
    if file_path_a and file_path_b and os.path.exists(file_path_a) and os.path.exists(file_path_b):
        try:
            diff_heatmap = generate_visual_diff_heatmap(file_path_a, file_path_b)
            visual_difference_pct = compute_visual_difference_percentage(file_path_a, file_path_b)
        except Exception:
            pass

    return {
        "risk_differential": {
            "specimen_a_score": score_a,
            "specimen_b_score": score_b,
            "variance": risk_diff,
            "classification_a": cls_a,
            "classification_b": cls_b
        },
        "dimensional_comparison": {
            "dimensions_a": dims_a,
            "dimensions_b": dims_b,
            "resolution_match": dims_a == dims_b
        },
        "text_differential": ocr_diff,
        "forensic_signals_differential": pillar_deltas,
        "visual_difference_heatmap": diff_heatmap,
        "visual_difference_pct": visual_difference_pct,
        "summary": f"Comparative evaluation complete. Specimen A scored {score_a}/100 ({cls_a}) while Specimen B scored {score_b}/100 ({cls_b}) with a risk variance of {risk_diff} points."
    }
