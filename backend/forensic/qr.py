import cv2

def analyze_qr(image_path: str) -> dict:
    """
    Detect and decode QR code in the image.
    """
    try:
        img = cv2.imread(image_path)
        if img is None:
            return {"detected": False, "consistency": "Unknown"}
            
        detector = cv2.QRCodeDetector()
        data, bbox, _ = detector.detectAndDecode(img)
        
        if bbox is not None and len(data) > 0:
            return {
                "detected": True,
                "data_preview": data[:20] + "..." if len(data) > 20 else data,
                "consistency": "Valid",
                "bbox": bbox.tolist()
            }
        else:
            return {
                "detected": False,
                "consistency": "Not found"
            }
    except Exception as e:
        return {"detected": False, "error": str(e)}
