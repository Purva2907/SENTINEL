import os

def analyze_ocr(image_path: str) -> dict:
    """
    Extract text using EasyOCR/Tesseract.
    """
    # For hackathon robust demo, we fallback to a safe mock if library fails
    try:
        import easyocr
        reader = easyocr.Reader(['en'], gpu=False)
        result = reader.readtext(image_path)
        
        extracted = " ".join([res[1] for res in result])
        
        return {
            "extracted_text": extracted[:50] + "..." if len(extracted) > 50 else extracted,
            "confidence": 0.85,
            "success": True
        }
    except Exception as e:
        return {
            "extracted_text": "OCR Failed or not installed properly",
            "confidence": 0.0,
            "success": False,
            "error": str(e)
        }
