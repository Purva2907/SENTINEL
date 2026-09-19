import cv2
import numpy as np

def enhance_image(image_path: str):
    """
    Enhance the image for OCR and QR processing.
    """
    try:
        img = cv2.imread(image_path)
        if img is None:
            return None
            
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Apply Gaussian blur to reduce noise
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        
        return {
            "status": "success",
            "resolution": img.shape
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
