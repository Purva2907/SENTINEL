import cv2
import numpy as np

def analyze_qr(image_path: str) -> dict:
    """
    Detect and decode QR code in the image using multi-stage detection:
    1. Primary OpenCV QRCodeDetector on original image, grayscale, and thresholded representations.
    2. Fallback to pyzbar (if available) on raw, grayscale, sharpened, and Otsu-thresholded images.
    3. Proper differentiation between detected vs decoded states (A: not detected, B: detected not decoded, C: detected and decoded).
    """
    try:
        img = cv2.imread(image_path)
        if img is None:
            return {
                "detected": False,
                "decoded": False,
                "consistency": "Unknown",
                "data_preview": "None",
                "payload": "",
                "status": "IMAGE_UNREADABLE",
                "bbox": None,
                "risk_contribution": 15,
                "findings": ["Image could not be read for QR analysis."]
            }
            
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
        _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        detected_bbox = None
        decoded_data = None
        
        # Stage 1: OpenCV QRCodeDetector across original, grayscale, and otsu
        try:
            detector = cv2.QRCodeDetector()
            # 1a. Original image
            data, bbox, _ = detector.detectAndDecode(img)
            if bbox is not None and len(bbox) > 0:
                detected_bbox = bbox.tolist()
            if data and len(data.strip()) > 0:
                decoded_data = data.strip()
                
            # 1b. Grayscale if not decoded
            if not decoded_data:
                data_g, bbox_g, _ = detector.detectAndDecode(gray)
                if bbox_g is not None and len(bbox_g) > 0:
                    detected_bbox = bbox_g.tolist()
                if data_g and len(data_g.strip()) > 0:
                    decoded_data = data_g.strip()
                    
            # 1c. Otsu threshold if not decoded
            if not decoded_data:
                data_o, bbox_o, _ = detector.detectAndDecode(otsu)
                if bbox_o is not None and len(bbox_o) > 0:
                    detected_bbox = bbox_o.tolist()
                if data_o and len(data_o.strip()) > 0:
                    decoded_data = data_o.strip()
                    
            # 1d. Multi detector fallback if single did not find
            if not decoded_data and not detected_bbox:
                retval, decoded_info, points, _ = detector.detectAndDecodeMulti(img)
                if points is not None and len(points) > 0:
                    detected_bbox = points[0].tolist()
                    for info in decoded_info:
                        if info and len(info.strip()) > 0:
                            decoded_data = info.strip()
                            break
        except Exception:
            pass
            
        # Stage 2: PyZbar Fallback if not decoded
        if not decoded_data:
            try:
                from pyzbar.pyzbar import decode as pyzbar_decode
                
                barcodes = pyzbar_decode(img)
                if not barcodes:
                    barcodes = pyzbar_decode(gray)
                if not barcodes:
                    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
                    sharp = cv2.filter2D(gray, -1, kernel)
                    barcodes = pyzbar_decode(sharp)
                if not barcodes:
                    barcodes = pyzbar_decode(otsu)
                        
                for barcode in barcodes:
                    if barcode.type in ('QRCODE', 'I25', 'CODE128', 'DATA_MATRIX'):
                        data_str = barcode.data.decode('utf-8', errors='ignore').strip()
                        if data_str:
                            decoded_data = data_str
                            detected_bbox = [[float(p.x), float(p.y)] for p in barcode.polygon] if barcode.polygon else []
                            break
                        else:
                            detected_bbox = [[float(p.x), float(p.y)] for p in barcode.polygon] if barcode.polygon else []
            except Exception:
                # pyzbar optional; continue with OpenCV findings
                pass
                
        # State Differentiation
        if decoded_data:
            consistency = "Valid"
            risk_contribution = 0
            findings = ["QR code detected and successfully decoded."]
            
            if len(decoded_data) < 3:
                consistency = "Suspicious (Truncated)"
                risk_contribution = 10
                findings.append("Decoded QR payload is unusually brief / truncated.")
            elif "SENTINEL" in decoded_data or "DEMO" in decoded_data or "HTTP" in decoded_data.upper() or "ID" in decoded_data.upper():
                consistency = "Valid"
                findings.append(f"Payload format conforms to document reference: {decoded_data[:24]}...")
            else:
                findings.append(f"Payload decoded: {decoded_data[:24]}...")
                
            return {
                "detected": True,
                "decoded": True,
                "data_preview": decoded_data[:24] + "..." if len(decoded_data) > 24 else decoded_data,
                "payload": decoded_data,
                "consistency": consistency,
                "bbox": detected_bbox,
                "status": "DECODED",
                "risk_contribution": risk_contribution,
                "findings": findings
            }
        elif detected_bbox is not None and len(detected_bbox) > 0:
            return {
                "detected": True,
                "decoded": False,
                "data_preview": "Unreadable payload",
                "payload": "",
                "consistency": "Detected (Unreadable)",
                "bbox": detected_bbox,
                "status": "DETECTED_NOT_DECODED",
                "risk_contribution": 15,
                "findings": [
                    "QR code pattern detected on canvas, but payload could not be decoded.",
                    "Potential barcode damage, heavy compression distortion, or tampering."
                ]
            }
        else:
            return {
                "detected": False,
                "decoded": False,
                "data_preview": "None",
                "payload": "",
                "consistency": "Not found",
                "bbox": None,
                "status": "NOT_DETECTED",
                "risk_contribution": 15,
                "findings": [
                    "No QR code pattern detected on document canvas.",
                    "Official document templates typically mandate embedded machine-readable barcodes."
                ]
            }
            
    except Exception as e:
        return {
            "detected": False,
            "decoded": False,
            "consistency": "Error",
            "data_preview": "None",
            "payload": "",
            "bbox": None,
            "status": "ERROR",
            "risk_contribution": 10,
            "findings": [f"QR detector encountered an error: {str(e)}"],
            "error": str(e)
        }
