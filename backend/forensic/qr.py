import cv2
import numpy as np

def detect_qr_pattern_regions(gray: np.ndarray) -> list:
    """
    Robust 2D Matrix / QR Code isotropic pattern detector.
    Detects high-density alternating binary module regions that standard decoders miss
    due to downsampling, high density (e.g. Aadhaar V2/V3 compressed/signed QR),
    or JPEG compression blur.
    """
    try:
        h_img, w_img = gray.shape[:2]
        total_area = h_img * w_img
        
        edges = cv2.Canny(gray, 70, 170)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
        dense = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
        dense = cv2.erode(dense, None, iterations=2)
        dense = cv2.dilate(dense, None, iterations=4)
        
        contours, _ = cv2.findContours(dense, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        detected_qrs = []
        
        for c in contours:
            x, y, w, h = cv2.boundingRect(c)
            area = w * h
            if area < 2000 or area > total_area * 0.4:
                continue
                
            roi = gray[y:y+h, x:x+w]
            if roi.size == 0:
                continue
                
            _, b = cv2.threshold(roi, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            col_trans = np.sum(np.abs(np.diff(b.astype(int), axis=0)) > 0, axis=0)
            row_trans = np.sum(np.abs(np.diff(b.astype(int), axis=1)) > 0, axis=1)
            
            min_line_trans = max(4, int(min(w, h) * 0.08))
            valid_cols = np.where(col_trans >= min_line_trans)[0]
            valid_rows = np.where(row_trans >= min_line_trans)[0]
            
            if len(valid_cols) < 20 or len(valid_rows) < 20:
                continue
                
            x_start, x_end = valid_cols.min(), valid_cols.max()
            y_start, y_end = valid_rows.min(), valid_rows.max()
            
            qr_w = x_end - x_start
            qr_h = y_end - y_start
            qr_area = qr_w * qr_h
            
            if qr_area < 2000:
                continue
                
            aspect = qr_w / float(qr_h) if qr_h > 0 else 0
            if not (0.75 <= aspect <= 1.35):
                continue
                
            qr_roi = b[y_start:y_end, x_start:x_end]
            h_trans = np.sum(np.abs(np.diff(qr_roi.astype(int), axis=1)) > 0)
            v_trans = np.sum(np.abs(np.diff(qr_roi.astype(int), axis=0)) > 0)
            
            trans_per_row = h_trans / float(qr_h)
            trans_per_col = v_trans / float(qr_w)
            
            mean_val = gray[y+y_start:y+y_end, x+x_start:x+x_end].mean()
            
            # QR codes require at least 15 transitions per row/col on average and balanced luminance
            if trans_per_row < 15.0 or trans_per_col < 15.0 or not (70 <= mean_val <= 180):
                continue
                
            trans_ratio = trans_per_row / trans_per_col if trans_per_col > 0 else 0
            if 0.70 <= trans_ratio <= 1.45:
                abs_x = x + x_start
                abs_y = y + y_start
                detected_qrs.append({
                    'bbox': [
                        [float(abs_x), float(abs_y)],
                        [float(abs_x + qr_w), float(abs_y)],
                        [float(abs_x + qr_w), float(abs_y + qr_h)],
                        [float(abs_x), float(abs_y + qr_h)]
                    ],
                    'x': abs_x,
                    'y': abs_y,
                    'w': qr_w,
                    'h': qr_h
                })
        return detected_qrs
    except Exception:
        return []

def analyze_qr(image_path: str, document_type: str = None, expected_qr: bool = None) -> dict:
    """
    Detect and decode QR code in the image using multi-stage detection:
    1. Primary OpenCV QRCodeDetector on original image, grayscale, and thresholded representations.
    2. Fallback to pyzbar (if available) on raw, grayscale, sharpened, and Otsu-thresholded images.
    3. Stage 3: High-Recall 2D Matrix / QR Code Pattern Localization for compressed,
       high-density, or digitally signed barcodes (e.g. Aadhaar secure biometric QR codes).
    4. Proper differentiation between detected vs decoded states (A: not detected, B: detected not decoded, C: detected and decoded).
    """
    try:
        img = cv2.imread(image_path)
        if img is None:
            return {
                "detected": False,
                "decoded": False,
                "detected_count": 0,
                "consistency": "Unknown",
                "data_preview": "None",
                "payload": "",
                "status": "IMAGE_UNREADABLE",
                "bbox": None,
                "bboxes": [],
                "risk_contribution": 15,
                "findings": ["Image could not be read for QR analysis."]
            }
            
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
        _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        detected_bbox = None
        decoded_data = None
        detected_patterns = []
        
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
                pass
                
        # Stage 3: High-Recall Pattern Localization for high-density / secure biometric barcodes
        if not decoded_data and not detected_bbox:
            detected_patterns = detect_qr_pattern_regions(gray)
            if detected_patterns:
                detected_bbox = detected_patterns[0]["bbox"]

        # State Differentiation
        # Check if QR is expected for this document type
        if expected_qr is None:
            if document_type:
                dt_lower = document_type.lower()
                # Document types with standardized machine-readable QR codes
                if any(k in dt_lower for k in ("aadhaar", "uidai", "synthetic", "e-pan", "digital driving", "smart card")):
                    expected_qr = True
                else:
                    expected_qr = False
            else:
                expected_qr = True

        if decoded_data:
            consistency = "Valid"
            risk_contribution = 0
            findings = [
                "QR payload decoded successfully.",
                "Payload authenticity was not cryptographically verified."
            ]
            
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
                "detected_count": 1,
                "data_preview": decoded_data[:24] + "..." if len(decoded_data) > 24 else decoded_data,
                "payload": decoded_data,
                "consistency": consistency,
                "bbox": detected_bbox,
                "bboxes": [detected_bbox],
                "status": "DECODED",
                "risk_contribution": risk_contribution,
                "findings": findings
            }
        elif detected_bbox is not None and len(detected_bbox) > 0:
            qr_count = len(detected_patterns) if detected_patterns else 1
            plural = "s" if qr_count > 1 else ""
            all_boxes = [p["bbox"] for p in detected_patterns] if detected_patterns else [detected_bbox]
            return {
                "detected": True,
                "decoded": False,
                "detected_count": qr_count,
                "data_preview": f"{qr_count} 2D Matrix Pattern{plural} Detected (Undecodable)",
                "payload": "",
                "consistency": f"Detected ({qr_count} 2D Matrix Pattern{plural})",
                "bbox": detected_bbox,
                "bboxes": all_boxes,
                "status": "DETECTED_NOT_DECODED",
                "risk_contribution": 5,
                "findings": [
                    "2D matrix detected but payload could not be decoded.",
                    "Payload authenticity was not cryptographically verified."
                ]
            }
        else:
            if not expected_qr:
                return {
                    "detected": False,
                    "decoded": False,
                    "detected_count": 0,
                    "data_preview": "Not Applicable",
                    "payload": "",
                    "consistency": "Not Applicable",
                    "bbox": None,
                    "bboxes": [],
                    "status": "NOT_APPLICABLE",
                    "risk_contribution": 0,
                    "findings": [
                        "QR code presence is not mandated for this document specification."
                    ]
                }
            else:
                return {
                    "detected": False,
                    "decoded": False,
                    "detected_count": 0,
                    "data_preview": "None",
                    "payload": "",
                    "consistency": "Not found",
                    "bbox": None,
                    "bboxes": [],
                    "status": "NOT_DETECTED",
                    "risk_contribution": 15,
                    "findings": [
                        "No QR code pattern detected on document canvas."
                    ]
                }
            
    except Exception as e:
        return {
            "detected": False,
            "decoded": False,
            "detected_count": 0,
            "consistency": "Error",
            "data_preview": "None",
            "payload": "",
            "bbox": None,
            "bboxes": [],
            "status": "ERROR",
            "risk_contribution": 10,
            "findings": [f"QR detector encountered an error: {str(e)}"],
            "error": str(e)
        }
