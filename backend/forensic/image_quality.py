import cv2
import numpy as np

def analyze_quality(image_path: str) -> dict:
    try:
        img = cv2.imread(image_path)
        if img is None:
            return {"score": 0, "findings": ["Invalid image"]}
            
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Calculate blur using variance of Laplacian
        blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
        
        # Brightness
        brightness = np.mean(gray)
        
        score = 80
        findings = []
        
        if blur_score < 100:
            score -= 20
            findings.append("Image appears blurred")
        else:
            findings.append("Good sharpness")
            
        if brightness < 50:
            score -= 10
            findings.append("Image is too dark")
        elif brightness > 200:
            score -= 10
            findings.append("Image is overexposed")
            
        return {
            "score": max(0, min(100, score)),
            "findings": findings,
            "blur_metric": float(blur_score),
            "brightness": float(brightness)
        }
    except Exception as e:
        return {"score": 0, "findings": [f"Error analyzing quality: {str(e)}"]}
