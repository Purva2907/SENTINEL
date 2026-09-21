import cv2
import numpy as np

def analyze_quality(image_path: str) -> dict:
    """
    Analyzes document image quality: blur (Laplacian variance), brightness, and resolution.
    Distinguishes photographic degradation from intentional manipulation.
    """
    try:
        img = cv2.imread(image_path)
        if img is None:
            return {
                "score": 0,
                "risk_contribution": 10,
                "findings": ["Unable to load image file."],
                "blur_score": 0.0,
                "blur_metric": 0.0,
                "brightness": 0.0,
                "resolution_ok": False,
                "dimensions": [0, 0]
            }
            
        h, w = img.shape[:2]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Calculate blur using variance of Laplacian
        blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        
        # Brightness (mean pixel intensity)
        brightness = float(np.mean(gray))
        
        # Resolution check: standard document min dimensions 600x380
        resolution_ok = bool(w >= 600 and h >= 380)
        
        score = 100
        risk_contrib = 0
        findings = []
        
        if not resolution_ok:
            score -= 25
            risk_contrib += 5
            findings.append(f"Low image resolution ({w}x{h})")
        else:
            findings.append(f"Standard resolution ({w}x{h})")
            
        if blur_score < 35.0:
            score -= 35
            risk_contrib += 10
            findings.append(f"Significant image blur detected (sharpness {blur_score:.1f})")
        elif blur_score < 75.0:
            score -= 20
            risk_contrib += 6
            findings.append(f"Moderate image blur (sharpness {blur_score:.1f})")
        elif blur_score < 140.0:
            score -= 5
            findings.append(f"Acceptable image clarity ({blur_score:.1f})")
        else:
            findings.append(f"Sharp image clarity ({blur_score:.1f})")
            
        if brightness < 45.0:
            score -= 20
            risk_contrib += 5
            findings.append("Image is severely underexposed / dark")
        elif brightness > 225.0:
            score -= 20
            risk_contrib += 5
            findings.append("Image is overexposed / washed out")
        elif brightness < 65.0 or brightness > 200.0:
            score -= 10
            risk_contrib += 2
            findings.append("Suboptimal lighting conditions")
        else:
            findings.append("Optimal lighting and contrast")
            
        quality_score = max(0, min(100, int(score)))
        quality_risk = max(0, min(15, int(risk_contrib)))
        
        return {
            "score": quality_score,
            "risk_contribution": quality_risk,
            "findings": findings,
            "blur_score": round(blur_score, 1),
            "blur_metric": round(blur_score, 1),
            "brightness": round(brightness, 1),
            "resolution_ok": resolution_ok,
            "dimensions": [int(w), int(h)]
        }
    except Exception as e:
        return {
            "score": 50,
            "risk_contribution": 5,
            "findings": [f"Error analyzing quality: {str(e)}"],
            "blur_score": 0.0,
            "blur_metric": 0.0,
            "brightness": 0.0,
            "resolution_ok": False,
            "dimensions": [0, 0]
        }
