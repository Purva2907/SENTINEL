import os
import numpy as np

# Cache reader instance at module level to avoid slow re-initialization
_cached_reader = None

def get_reader():
    global _cached_reader
    if _cached_reader is None:
        try:
            import easyocr
            _cached_reader = easyocr.Reader(['en'], gpu=False)
        except Exception:
            _cached_reader = False
    return _cached_reader

def analyze_ocr(image_path: str) -> dict:
    """
    Extract text using EasyOCR and compute genuine confidence metrics.
    Ensures average_confidence is strictly finite and non-NaN.
    """
    try:
        reader = get_reader()
        if not reader:
            return {
                "extracted_text": "",
                "raw_text": "",
                "confidence": 0.0,
                "average_confidence": 0.0,
                "character_count": 0,
                "detections_count": 0,
                "detections": [],
                "success": False,
                "status": "OCR_ENGINE_UNAVAILABLE",
                "risk_contribution": 5,
                "findings": ["OCR engine unavailable for text extraction."]
            }
            
        result = reader.readtext(image_path)
        
        if not result or len(result) == 0:
            return {
                "extracted_text": "",
                "raw_text": "",
                "confidence": 0.0,
                "average_confidence": 0.0,
                "character_count": 0,
                "detections_count": 0,
                "detections": [],
                "success": True,
                "status": "NO_TEXT_RECOVERED",
                "risk_contribution": 15,
                "findings": ["No text detected on document canvas."]
            }
            
        detections = []
        texts = []
        confidences = []
        
        for res in result:
            if not res or len(res) < 2:
                continue
            bbox_raw = res[0]
            text = str(res[1]).strip() if res[1] is not None else ""
            if not text:
                continue
            conf = float(res[2]) if len(res) > 2 and res[2] is not None else 0.0
            if np.isnan(conf) or np.isinf(conf):
                conf = 0.0
            conf = max(0.0, min(1.0, conf))
            
            bbox_formatted = [[float(p[0]), float(p[1])] for p in bbox_raw] if bbox_raw else []
            detections.append({
                "text": text,
                "confidence": round(conf, 3),
                "bbox": bbox_formatted
            })
            texts.append(text)
            confidences.append(conf)
        
        raw_text = " ".join(texts)
        if not confidences or len(raw_text.strip()) == 0:
            return {
                "extracted_text": "",
                "raw_text": "",
                "confidence": 0.0,
                "average_confidence": 0.0,
                "character_count": 0,
                "detections_count": 0,
                "detections": [],
                "success": True,
                "status": "NO_TEXT_RECOVERED",
                "risk_contribution": 15,
                "findings": ["No readable text extracted."]
            }
            
        avg_conf = float(np.mean(confidences))
        if np.isnan(avg_conf) or np.isinf(avg_conf):
            avg_conf = 0.0
        avg_conf = max(0.0, min(1.0, float(avg_conf)))
        
        risk_contribution = 0
        findings = []
        if avg_conf < 0.45:
            risk_contribution = 10
            findings.append(f"Low OCR text extraction confidence ({avg_conf * 100:.1f}%)")
        elif avg_conf < 0.70:
            risk_contribution = 5
            findings.append(f"Moderate OCR recognition confidence ({avg_conf * 100:.1f}%)")
        else:
            findings.append(f"High OCR recognition clarity ({avg_conf * 100:.1f}%)")
            
        findings.append(f"Extracted {len(texts)} text elements ({len(raw_text)} characters)")
        
        return {
            "extracted_text": raw_text[:80] + "..." if len(raw_text) > 80 else raw_text,
            "raw_text": raw_text,
            "confidence": round(avg_conf, 2),
            "average_confidence": round(avg_conf, 2),
            "character_count": len(raw_text),
            "detections_count": len(texts),
            "detections": detections,
            "success": True,
            "status": "TEXT_DETECTED",
            "risk_contribution": risk_contribution,
            "findings": findings
        }
    except Exception as e:
        return {
            "extracted_text": "",
            "raw_text": "",
            "confidence": 0.0,
            "average_confidence": 0.0,
            "character_count": 0,
            "detections_count": 0,
            "detections": [],
            "success": False,
            "status": "OCR_FAILED",
            "risk_contribution": 8,
            "findings": [f"OCR analysis encountered an exception: {str(e)}"],
            "error": str(e)
        }
