import os
import cv2
import numpy as np
from typing import Dict, Any, Optional, Tuple, List

# ==============================================================================
# PHOTOGRAPH FORENSICS & MANIPULATION ENGINE
# ==============================================================================

def locate_photograph_region(img: np.ndarray) -> Optional[Dict[str, int]]:
    """
    Locates the portrait photograph region on an Aadhaar canvas.
    Standard Aadhaar layout places the cardholder photograph on the left side:
      x approx 3% - 40% of canvas width
      y approx 15% - 65% of canvas height
    Employs OpenCV Haar Cascade face detection with fallback to geometric template heuristic.
    """
    if img is None:
        return None
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img

    # 1. Attempt Face Detection via Haar Cascade
    try:
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        face_cascade = cv2.CascadeClassifier(cascade_path)
        faces = face_cascade.detectMultiScale(
            gray, 
            scaleFactor=1.1, 
            minNeighbors=4, 
            minSize=(int(w * 0.08), int(h * 0.10))
        )
        for (fx, fy, fw, fh) in faces:
            # Check if face is in expected portrait half (typically left 50% of document)
            if fx < w * 0.55 and fy < h * 0.70:
                # Expand box slightly to encompass full photograph frame
                pad_x = int(fw * 0.18)
                pad_y = int(fh * 0.25)
                bx = max(0, fx - pad_x)
                by = max(0, fy - pad_y)
                bw = min(w - bx, fw + 2 * pad_x)
                bh = min(h - by, fh + 2 * pad_y)
                return {"x": bx, "y": by, "w": bw, "h": bh, "method": "FACE_CASCADE"}
    except Exception:
        pass

    # 2. Geometric Template Fallback: Left portrait quadrant
    gx = int(w * 0.05)
    gy = int(h * 0.20)
    gw = int(w * 0.28)
    gh = int(h * 0.42)
    
    # Verify standard color variance in this region to confirm presence
    roi = gray[gy:gy+gh, gx:gx+gw]
    if roi.size > 0 and float(np.std(roi)) > 15.0:
        return {"x": gx, "y": gy, "w": gw, "h": gh, "method": "GEOMETRIC_TEMPLATE"}

    return None

def analyze_photo_boundary_discontinuity(
    gray: np.ndarray, 
    photo_box: Dict[str, int]
) -> Tuple[bool, float, str]:
    """
    Checks if the photograph border exhibits an unnatural edge gradient step
    indicative of a digital cut-and-paste or overlaid rectangular photo.
    """
    h, w = gray.shape[:2]
    px, py, pw, ph = photo_box["x"], photo_box["y"], photo_box["w"], photo_box["h"]
    
    # Calculate Sobel edge gradient magnitude
    sobelx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    sobely = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    grad_mag = cv2.magnitude(sobelx, sobely)

    # Sample borders
    b_top = grad_mag[max(0, py-2):min(h, py+3), px:px+pw]
    b_bot = grad_mag[max(0, py+ph-3):min(h, py+ph+2), px:px+pw]
    b_left = grad_mag[py:py+ph, max(0, px-2):min(w, px+3)]
    b_right = grad_mag[py:py+ph, max(0, px+pw-3):min(w, px+pw+2)]

    border_means = []
    for b in (b_top, b_bot, b_left, b_right):
        if b.size > 0:
            border_means.append(float(np.mean(b)))

    mean_boundary_step = float(np.mean(border_means)) if border_means else 0.0
    
    # Natural printed documents have smooth antialiased borders (gradient < 45)
    # Spliced/pasted photos exhibit sharp pixel edge discontinuities (> 75)
    is_discontinuous = mean_boundary_step > 75.0
    details = f"Boundary gradient step: {mean_boundary_step:.1f} ({'sharp discontinuity' if is_discontinuous else 'uniform substrate transition'})."
    return is_discontinuous, mean_boundary_step, details

def analyze_photo_noise_consistency(
    gray: np.ndarray, 
    photo_box: Dict[str, int]
) -> Tuple[bool, float, str]:
    """
    Measures whether high-frequency noise variance in the photo region
    deviates drastically from the adjacent card substrate (indicating foreign origin).
    """
    h, w = gray.shape[:2]
    px, py, pw, ph = photo_box["x"], photo_box["y"], photo_box["w"], photo_box["h"]

    # Compute Laplacian high-frequency noise map
    lap = cv2.Laplacian(gray, cv2.CV_32F)
    photo_lap = lap[py:py+ph, px:px+pw]

    # Sample background substrate from center/right of document
    bg_x0 = min(w - 50, px + pw + 20)
    bg_x1 = min(w, bg_x0 + pw)
    bg_lap = lap[py:py+ph, bg_x0:bg_x1]

    if photo_lap.size == 0 or bg_lap.size == 0:
        return False, 1.0, "Insufficient pixels for noise ratio computation."

    photo_noise_var = float(np.var(photo_lap))
    bg_noise_var = max(0.5, float(np.var(bg_lap)))

    ratio = photo_noise_var / bg_noise_var
    # Photographic portraits naturally have higher texture than flat paper,
    # but a ratio > 8.0 or < 0.1 indicates splicing from a totally different resolution/compression source
    is_noise_inconsistent = (ratio > 8.0 or ratio < 0.12)
    details = f"Photo/substrate noise ratio: {ratio:.2f} ({'inconsistent foreign noise profile' if is_noise_inconsistent else 'uniform image source profile'})."
    return is_noise_inconsistent, ratio, details

def analyze_photograph_forensics(
    img: Any, 
    qr_photo_data: Optional[bytes] = None,
    qr_result: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Complete photograph forensic evaluation:
    1. Photograph region presence & localization
    2. Edge boundary discontinuity check
    3. Noise variance ratio vs document substrate
    4. Splicing / replacement indicator
    5. QR photo cross-check if official Secure QR provided photo data
    
    Returns structured analysis dictionary.
    Does NOT query external face databases.
    """
    if isinstance(img, str):
        if os.path.exists(img):
            img = cv2.imread(img)
        else:
            img = None

    if qr_result and not qr_photo_data:
        demographics = qr_result.get("demographics") or {}
        qr_photo_data = demographics.get("photo") or qr_result.get("photo_bytes")

    if img is None:

        return {
            "status": "NOT_AVAILABLE",
            "present": False,
            "region": None,
            "boundary_discontinuity": False,
            "noise_inconsistent": False,
            "manipulation_severity": "NONE",
            "photo_match_status": "PHOTO_NOT_AVAILABLE",
            "risk_contribution": 0,
            "details": "Document image unavailable for photograph forensic evaluation."
        }

    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img

    # 1. Locate photograph region
    photo_box = locate_photograph_region(img)
    if not photo_box:
        return {
            "status": "PHOTO_ABSENT",
            "present": False,
            "region": None,
            "boundary_discontinuity": False,
            "noise_inconsistent": False,
            "manipulation_severity": "NONE",
            "photo_match_status": "PHOTO_NOT_AVAILABLE",
            "risk_contribution": 5,
            "details": "Photograph region not detected in standard portrait quadrant."
        }

    # 2. Check boundary gradient discontinuity
    is_boundary_anom, b_step, b_details = analyze_photo_boundary_discontinuity(gray, photo_box)

    # 3. Check noise consistency against substrate
    is_noise_anom, noise_ratio, n_details = analyze_photo_noise_consistency(gray, photo_box)

    # 4. QR photo cross-check (if Secure QR payload decrypted photograph)
    photo_match_status = "PHOTO_NOT_AVAILABLE"
    match_details = "Secure QR demographic payload did not provide trusted photograph bytes."
    if qr_photo_data:
        try:
            # Decode QR photo bytes into numpy image
            nparr = np.frombuffer(qr_photo_data, np.uint8)
            qr_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if qr_img is not None:
                # Compare visible photo crop with QR photo using normalized histogram correlation
                px, py, pw, ph = photo_box["x"], photo_box["y"], photo_box["w"], photo_box["h"]
                vis_crop = img[py:py+ph, px:px+pw]
                vis_resized = cv2.resize(vis_crop, (qr_img.shape[1], qr_img.shape[0]))
                
                hsv_vis = cv2.cvtColor(vis_resized, cv2.COLOR_BGR2HSV)
                hsv_qr = cv2.cvtColor(qr_img, cv2.COLOR_BGR2HSV)
                
                hist_vis = cv2.calcHist([hsv_vis], [0, 1], None, [30, 32], [0, 180, 0, 256])
                hist_qr = cv2.calcHist([hsv_qr], [0, 1], None, [30, 32], [0, 180, 0, 256])
                cv2.normalize(hist_vis, hist_vis, 0, 1, cv2.NORM_MINMAX)
                cv2.normalize(hist_qr, hist_qr, 0, 1, cv2.NORM_MINMAX)
                
                sim = cv2.compareHist(hist_vis, hist_qr, cv2.HISTCMP_CORREL)
                if sim >= 0.55:
                    photo_match_status = "PHOTO_CONSISTENT"
                    match_details = f"Visible photograph correlates with official QR decoded portrait (similarity: {sim:.2f})."
                else:
                    photo_match_status = "PHOTO_INCONSISTENT"
                    match_details = f"Visible photograph contradicts official QR decoded portrait (similarity: {sim:.2f})."
        except Exception:
            photo_match_status = "PHOTO_UNVERIFIED"
            match_details = "QR photograph decoding encountered unhandled decompression exception."

    # 5. Determine overall manipulation severity
    manipulation_severity = "NONE"
    risk_contrib = 0
    if photo_match_status == "PHOTO_INCONSISTENT":
        manipulation_severity = "CRITICAL"
        risk_contrib = 30
        status = "SUSPICIOUS_REPLACEMENT"
        finding = f"CRITICAL: Visible cardholder photo contradicts QR-encoded portrait. {match_details}"
    elif is_boundary_anom and is_noise_anom:
        manipulation_severity = "HIGH"
        risk_contrib = 25
        status = "SUSPICIOUS_REPLACEMENT"
        finding = f"HIGH: Multi-spectral evidence of photo replacement. {b_details} {n_details}"
    elif is_boundary_anom:
        manipulation_severity = "MODERATE"
        risk_contrib = 10
        status = "MANIPULATED_BOUNDARY"
        finding = f"Moderate boundary step detected around photograph frame. {b_details}"
    elif is_noise_anom:
        manipulation_severity = "LOW"
        risk_contrib = 5
        status = "NOISE_VARIANCE"
        finding = f"Minor noise disparity in portrait substrate. {n_details}"
    else:
        status = "CLEAN"
        risk_contrib = 0
        finding = "Photograph region is internally consistent with document substrate (no boundary discontinuity or splicing)."

    return {
        "status": status,
        "present": True,
        "region": photo_box,
        "boundary_discontinuity": is_boundary_anom,
        "noise_inconsistent": is_noise_anom,
        "manipulation_severity": manipulation_severity,
        "photo_match_status": photo_match_status,
        "risk_contribution": risk_contrib,
        "details": finding,
        "findings": [finding]
    }
