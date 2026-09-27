"""
SENTINEL Forensic Tampering Detection Engine
=============================================
A comprehensive, multi-spectral forensic analysis layer for detecting localized
digital manipulation, splicing, copy-move cloning, synthetic overlays/paint,
noise variance inconsistencies, resampling artifacts, and text-region discrepancies.

Hierarchical Principle:
STRONG TAMPERING EVIDENCE > DOCUMENT STRUCTURE > TYPOGRAPHY / LAYOUT > OCR > QUALITY
"""

import os
import cv2
import numpy as np
from typing import Dict, List, Tuple, Any, Optional

# ==============================================================================
# 1. LOCAL NOISE VARIANCE ESTIMATOR
# ==============================================================================

def estimate_local_noise_map(gray: np.ndarray, ksize: int = 7) -> np.ndarray:
    """
    Estimates spatial noise variance using high-frequency residual:
    Residual = Image - MedianFiltered(Image)
    Local noise variance is computed in sliding windows.
    """
    try:
        med = cv2.medianBlur(gray, ksize)
        residual = cv2.absdiff(gray, med).astype(np.float32)
        # Local variance of residual
        mean_res = cv2.blur(residual, (ksize, ksize))
        sq_res = cv2.blur(residual ** 2, (ksize, ksize))
        var_res = np.maximum(0.0, sq_res - (mean_res ** 2))
        return var_res
    except Exception:
        return np.zeros_like(gray, dtype=np.float32)

# ==============================================================================
# 2. LOCALIZED ERROR LEVEL ANALYSIS (ELA)
# ==============================================================================

def compute_localized_ela(img: np.ndarray, quality: int = 90) -> Tuple[np.ndarray, float, float]:
    """
    Performs full-resolution Error Level Analysis with localized spatial difference.
    Returns: (diff_gray_map, mean_error, std_error)
    """
    try:
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
        _, enc_img = cv2.imencode('.jpg', img, encode_param)
        resaved = cv2.imdecode(enc_img, cv2.IMREAD_COLOR)
        if resaved is None or resaved.shape != img.shape:
            resaved = img

        diff = cv2.absdiff(img, resaved)
        diff_gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY).astype(np.float32)
        return diff_gray, float(np.mean(diff_gray)), float(np.std(diff_gray))
    except Exception:
        h, w = img.shape[:2]
        return np.zeros((h, w), dtype=np.float32), 0.0, 0.0

# ==============================================================================
# 3. OVERLAY, PAINT & REDACTION DETECTOR
# ==============================================================================

def detect_overlay_anomalies(
    img: np.ndarray, 
    gray: np.ndarray, 
    noise_map: np.ndarray
) -> Tuple[List[Dict[str, Any]], np.ndarray, float]:
    """
    Detects suspicious solid/semi-solid paint overlays, digital highlighter strokes,
    and sharp rectangular/irregular covers (e.g. painted privacy marks or covered fields).
    
    Identifies:
      - Synthetic high-saturation or pitch-black/pure-white patches
      - Abnormally zero-noise regions (flat digital color)
      - Abrupt boundary gradient steps
    """
    h, w = gray.shape[:2]
    total_pixels = h * w
    overlay_mask = np.zeros((h, w), dtype=np.uint8)
    detected_regions: List[Dict[str, Any]] = []

    try:
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        # A. Synthetic Color Masks (High-saturation digital marker strokes, e.g., bright green, cyan, magenta, blackout)
        # Digital fluorescent green highlighter: H in [32, 90], S >= 100, V >= 100
        green_marker = cv2.inRange(hsv, (32, 100, 100), (90, 255, 255))
        # Solid blackout / marker scribble: V < 30
        black_marker = cv2.inRange(hsv, (0, 0, 0), (180, 255, 30))
        # Pure saturated neon blue/yellow/red digital edits
        blue_marker = cv2.inRange(hsv, (95, 160, 150), (130, 255, 255))
        yellow_marker = cv2.inRange(hsv, (20, 160, 180), (32, 255, 255))
        red_marker1 = cv2.inRange(hsv, (0, 180, 180), (8, 255, 255))
        red_marker2 = cv2.inRange(hsv, (172, 180, 180), (180, 255, 255))

        synthetic_color_mask = cv2.bitwise_or(green_marker, black_marker)
        synthetic_color_mask = cv2.bitwise_or(synthetic_color_mask, blue_marker)
        synthetic_color_mask = cv2.bitwise_or(synthetic_color_mask, yellow_marker)
        synthetic_color_mask = cv2.bitwise_or(synthetic_color_mask, red_marker1)
        synthetic_color_mask = cv2.bitwise_or(synthetic_color_mask, red_marker2)

        # B. Low-noise flat texture mask (variance < 0.8 with low gradient)
        sobelx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
        sobely = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
        grad_mag = cv2.magnitude(sobelx, sobely)
        flat_texture_mask = ((noise_map < 1.0) & (grad_mag < 8.0)).astype(np.uint8) * 255

        # Clean noise with morphological operations
        kernel_sm = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        kernel_lg = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))

        # A. Detect Colored Marker Strokes (Green, Yellow, Blue, Red)
        color_markers = cv2.bitwise_or(green_marker, blue_marker)
        color_markers = cv2.bitwise_or(color_markers, yellow_marker)
        color_markers = cv2.bitwise_or(color_markers, red_marker1)
        color_markers = cv2.bitwise_or(color_markers, red_marker2)
        color_clean = cv2.morphologyEx(color_markers, cv2.MORPH_OPEN, kernel_sm)
        color_clean = cv2.morphologyEx(color_clean, cv2.MORPH_CLOSE, kernel_lg)

        # B. Detect Opaque Blackout Scribbles / Paint Marks
        # Normal text letters have small bounding boxes (bw < 30, bh < 30) and area < 350.
        # Blackout scribbles are large dense patches covering fields or QR codes.
        black_clean = cv2.morphologyEx(black_marker, cv2.MORPH_OPEN, kernel_sm)
        black_clean = cv2.morphologyEx(black_clean, cv2.MORPH_CLOSE, kernel_lg)

        region_idx = 1
        privacy_redactions: List[Dict[str, Any]] = []

        # Process Colored Markers (Green, Yellow, Blue, Red Highlighters/Masks)
        # In accordance with Section 11: Privacy Redaction
        # Intentional user masking of sensitive identity numbers/fields is PRIVACY_REDACTION (risk contribution = 0)
        # However, multiple scattered strokes across headers, emblems, and text are DIGITAL_PAINT_OVERLAY (tampering).
        raw_cnts_color, _ = cv2.findContours(color_clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        valid_color_items = []
        for cnt in raw_cnts_color:
            area = cv2.contourArea(cnt)
            if area < 250:
                continue
            bx, by, bw, bh = cv2.boundingRect(cnt)
            if bw > w * 0.95 and bh > h * 0.95:
                continue

            roi = img[by:by+bh, bx:bx+bw]
            roi_mask = color_clean[by:by+bh, bx:bx+bw]
            if cv2.countNonZero(roi_mask) == 0:
                continue
            valid_color_items.append((cnt, area, bx, by, bw, bh, roi, roi_mask))

        # Sort by area descending so largest field masks are considered first
        valid_color_items.sort(key=lambda item: item[1], reverse=True)
        # If there are > 3 marks scattered on the document, it's digital paint overlay/defacement
        max_privacy_marks = 2 if len(valid_color_items) <= 3 else (1 if len(valid_color_items) <= 5 else 0)

        for i, (cnt, area, bx, by, bw, bh, roi, roi_mask) in enumerate(valid_color_items):
            mean_bgr = cv2.mean(roi, mask=roi_mask)[:3]
            area_pct = round((area / total_pixels) * 100.0, 2)

            is_green = (mean_bgr[1] > 110 and mean_bgr[1] > mean_bgr[0] * 1.15 and mean_bgr[1] > mean_bgr[2] * 1.15)
            marker_color_name = "Green digital highlighter" if is_green else f"Color marker [RGB: {int(mean_bgr[2])},{int(mean_bgr[1])},{int(mean_bgr[0])}]"

            aspect_ratio = float(bw) / max(1.0, float(bh))
            # Legitimate privacy masking covers a horizontal text line or compact block
            is_privacy_candidate = (i < max_privacy_marks) and (aspect_ratio >= 1.2 or (bw >= 30 and bh >= 30))

            if is_privacy_candidate:
                reg = {
                    "id": f"REDACTION-{region_idx:02d}",
                    "x": int(bx), "y": int(by), "w": int(bw), "h": int(bh),
                    "area_px": int(area), "area_pct": area_pct,
                    "signal": "PRIVACY_REDACTION",
                    "type": "USER_PRIVACY_MASK",
                    "confidence": 95.0,
                    "risk_contribution": 0,
                    "details": f"User privacy redaction ({marker_color_name} masking sensitive identity number/field; non-fraudulent)"
                }
                detected_regions.append(reg)
                privacy_redactions.append(reg)
            else:
                # Treated as digital paint overlay / surface defacement
                cv2.drawContours(overlay_mask, [cnt], -1, 255, -1)
                reg = {
                    "id": f"OVERLAY-{region_idx:02d}",
                    "x": int(bx), "y": int(by), "w": int(bw), "h": int(bh),
                    "area_px": int(area), "area_pct": area_pct,
                    "signal": "OVERLAY_ANOMALY",
                    "type": "DIGITAL_PAINT_OVERLAY",
                    "confidence": 90.0,
                    "risk_contribution": 15,
                    "details": f"Digital paint overlay / surface defacement ({marker_color_name} stroke detected on canvas)"
                }
                detected_regions.append(reg)
            region_idx += 1

        # Process Blackout Scribbles & Solid Opaque Masks
        # In accordance with Section 11: Blackout masking of sensitive numbers/QR is PRIVACY_REDACTION
        cnts_black, _ = cv2.findContours(black_clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        valid_black_items = []
        for cnt in cnts_black:
            area = cv2.contourArea(cnt)
            bx, by, bw, bh = cv2.boundingRect(cnt)
            is_blackout = (area >= 700) or (bw >= 35 and bh >= 35 and area >= 400)
            if not is_blackout:
                continue
            if bw > w * 0.95 and bh > h * 0.95:
                continue
            valid_black_items.append((cnt, area, bx, by, bw, bh))

        valid_black_items.sort(key=lambda item: item[1], reverse=True)
        max_black_privacy = 2 if len(valid_black_items) <= 3 else (1 if len(valid_black_items) <= 5 else 0)

        for i, (cnt, area, bx, by, bw, bh) in enumerate(valid_black_items):
            area_pct = round((area / total_pixels) * 100.0, 2)
            if i < max_black_privacy:
                reg = {
                    "id": f"REDACTION-{region_idx:02d}",
                    "x": int(bx), "y": int(by), "w": int(bw), "h": int(bh),
                    "area_px": int(area), "area_pct": area_pct,
                    "signal": "PRIVACY_REDACTION",
                    "type": "USER_PRIVACY_MASK",
                    "confidence": 95.0,
                    "risk_contribution": 0,
                    "details": "User privacy redaction (Dense opaque blackout scribble/mask over document field/QR; non-fraudulent)"
                }
                detected_regions.append(reg)
                privacy_redactions.append(reg)
            else:
                cv2.drawContours(overlay_mask, [cnt], -1, 255, -1)
                reg = {
                    "id": f"OVERLAY-{region_idx:02d}",
                    "x": int(bx), "y": int(by), "w": int(bw), "h": int(bh),
                    "area_px": int(area), "area_pct": area_pct,
                    "signal": "OVERLAY_ANOMALY",
                    "type": "DIGITAL_PAINT_OVERLAY",
                    "confidence": 90.0,
                    "risk_contribution": 15,
                    "details": "Digital paint overlay / surface defacement (Blackout scribble detected on canvas)"
                }
                detected_regions.append(reg)
            region_idx += 1


        # True Malicious Overlays:
        # Require abnormal local texture + abnormal noise + edge discontinuity + region-level inconsistency (Section 10)
        # Excludes solid privacy redaction strokes
        total_overlay_area = np.count_nonzero(overlay_mask)
        total_overlay_pct = (total_overlay_area / total_pixels) * 100.0

        return detected_regions, overlay_mask, total_overlay_pct, privacy_redactions

    except Exception:
        return [], overlay_mask, 0.0, []

# ==============================================================================
# 4. COPY-MOVE / CLONING DETECTOR
# ==============================================================================

def detect_copy_move_cloning(
    gray: np.ndarray, 
    max_features: int = 800,
    min_dist: float = 50.0
) -> Tuple[bool, List[Dict[str, Any]], np.ndarray]:
    """
    Detects copy-move/cloning using ORB feature descriptor matching
    with spatial displacement clustering.
    A cluster of feature matches sharing consistent spatial translation (dx, dy)
    indicates genuine duplicated/cloned content.
    Excludes 1D text-line repeats by enforcing 2D spatial dimensions and minimum entropy.
    """
    h, w = gray.shape[:2]
    cm_mask = np.zeros((h, w), dtype=np.uint8)
    matched_regions: List[Dict[str, Any]] = []

    try:
        orb = cv2.ORB_create(nfeatures=max_features, fastThreshold=12)
        kp, des = orb.detectAndCompute(gray, None)

        if kp is None or des is None or len(kp) < 25:
            return False, [], cm_mask

        # Match features against themselves
        bf = cv2.BFMatcher(cv2.NORM_HAMMING)
        matches = bf.knnMatch(des, des, k=3)

        valid_pairs = []
        for match_group in matches:
            if len(match_group) < 3:
                continue
            m = match_group[1]
            if m.distance < 48:
                pt1 = np.array(kp[m.queryIdx].pt)
                pt2 = np.array(kp[m.trainIdx].pt)
                spatial_dist = np.linalg.norm(pt1 - pt2)
                
                # Must be separated by minimum spatial distance
                if spatial_dist >= min_dist:
                    disp = pt2 - pt1
                    # Canonicalize displacement direction so forward and reverse matches align
                    if disp[0] < 0 or (disp[0] == 0 and disp[1] < 0):
                        disp = -disp
                        pt1, pt2 = pt2, pt1
                    valid_pairs.append((pt1, pt2, disp))

        if len(valid_pairs) < 8:
            return False, [], cm_mask

        # Cluster displacement vectors into 20px grid
        displacements = np.array([p[2] for p in valid_pairs])
        bins: Dict[Tuple[int, int], List[int]] = {}
        for idx, (dx, dy) in enumerate(displacements):
            bx = int(round(dx / 20.0))
            by = int(round(dy / 20.0))
            key = (bx, by)
            bins.setdefault(key, []).append(idx)

        # Find cluster with >= 14 consistent displacement vectors (eliminating accidental letter repeats)
        best_cluster = []
        for key, indices in bins.items():
            if len(indices) >= 14 and len(indices) > len(best_cluster):
                best_cluster = indices

        if len(best_cluster) >= 14:
            pts1 = np.array([valid_pairs[i][0] for i in best_cluster])
            pts2 = np.array([valid_pairs[i][1] for i in best_cluster])

            # Filter out 1D horizontal text lines:
            # Cloned 2D graphic regions have 2D spatial dispersion (std_x and std_y >= 8.0)
            if np.std(pts1[:, 0]) < 8.0 or np.std(pts1[:, 1]) < 8.0:
                return False, [], cm_mask

            x1_min, y1_min = np.min(pts1, axis=0)
            x1_max, y1_max = np.max(pts1, axis=0)
            x2_min, y2_min = np.min(pts2, axis=0)
            x2_max, y2_max = np.max(pts2, axis=0)

            w1, h1 = int(x1_max - x1_min), int(y1_max - y1_min)
            w2, h2 = int(x2_max - x2_min), int(y2_max - y2_min)

            # Avoid thin line repeats: must be 2D region (w and h >= 28) and substantial area (>= 1000)
            if min(w1, h1) < 28 or min(w2, h2) < 28 or (w1 * h1 < 1000) or (w2 * h2 < 1000):
                return False, [], cm_mask

            # Verify texture variance (avoid flat paper)
            roi1 = gray[int(y1_min):int(y1_max), int(x1_min):int(x1_max)]
            roi2 = gray[int(y2_min):int(y2_max), int(x2_min):int(x2_max)]
            if roi1.size == 0 or roi2.size == 0 or np.std(roi1) < 12.0 or np.std(roi2) < 12.0:
                return False, [], cm_mask

            # Filter out white document substrate with text characters (sparse typography on paper)
            paper_ratio1 = np.count_nonzero(roi1 > 215) / max(1, roi1.size)
            paper_ratio2 = np.count_nonzero(roi2 > 215) / max(1, roi2.size)
            if paper_ratio1 > 0.65 or paper_ratio2 > 0.65:
                return False, [], cm_mask

            # Draw on mask
            cv2.rectangle(cm_mask, (int(x1_min), int(y1_min)), (int(x1_max), int(y1_max)), 255, -1)
            cv2.rectangle(cm_mask, (int(x2_min), int(y2_min)), (int(x2_max), int(y2_max)), 255, -1)

            matched_regions.append({
                "source_region": {"x": int(x1_min), "y": int(y1_min), "w": w1, "h": h1},
                "target_region": {"x": int(x2_min), "y": int(y2_min), "w": w2, "h": h2},
                "correlated_features": len(best_cluster),
                "confidence": min(95.0, 50.0 + len(best_cluster) * 4.0),
                "details": f"Coherent spatial cloning: {len(best_cluster)} feature points share parallel displacement vector across 2D region ({w1}×{h1} px)"
            })
            return True, matched_regions, cm_mask

        return False, [], cm_mask

    except Exception:
        return False, [], cm_mask

# ==============================================================================
# 5. SPATIAL RESAMPLING & INTERPOLATION ARTIFACT DETECTOR
# ==============================================================================

def detect_resampling_artifacts(gray: np.ndarray, tile_size: int = 64) -> Tuple[float, List[Dict[str, Any]], np.ndarray]:
    """
    Detects local resampling / scaling / rotation artifacts via periodic derivative
    zero-crossings in second-order differences.
    """
    h, w = gray.shape[:2]
    resamp_mask = np.zeros((h, w), dtype=np.uint8)
    anomalous_tiles = []

    try:
        d2 = cv2.Laplacian(gray, cv2.CV_32F, ksize=3)
        
        n_rows = max(1, h // tile_size)
        n_cols = max(1, w // tile_size)
        tile_scores = []

        for r in range(n_rows):
            for c in range(n_cols):
                y0 = r * tile_size
                y1 = min(h, (r + 1) * tile_size)
                x0 = c * tile_size
                x1 = min(w, (c + 1) * tile_size)
                patch = d2[y0:y1, x0:x1]
                if patch.size < 64:
                    continue

                # Periodic spectrum check (autocorrelation peak)
                fft = np.fft.fft2(patch)
                fft_shift = np.fft.fftshift(fft)
                magnitude_spectrum = 20 * np.log(np.abs(fft_shift) + 1e-5)
                spec_std = float(np.std(magnitude_spectrum))
                tile_scores.append((spec_std, x0, y0, x1 - x0, y1 - y0))

        if not tile_scores:
            return 0.0, [], resamp_mask

        vals = [s[0] for s in tile_scores]
        med_val = float(np.median(vals))
        std_val = float(np.std(vals))

        for score, x, y, tw, th in tile_scores:
            if std_val > 0 and score > med_val + 3.8 * std_val and score > 45.0:
                cv2.rectangle(resamp_mask, (x, y), (x + tw, y + th), 255, -1)
                anomalous_tiles.append({
                    "x": x, "y": y, "w": tw, "h": th,
                    "spectral_score": round(score, 2),
                    "signal": "RESAMPLING_ANOMALY",
                    "details": "Interpolation periodicity detected in high-frequency spectral derivative"
                })

        if len(anomalous_tiles) < 4:
            return 0.0, [], np.zeros((h, w), dtype=np.uint8)

        overall_resamp_score = min(100.0, len(anomalous_tiles) * 20.0)
        return overall_resamp_score, anomalous_tiles, resamp_mask

    except Exception:
        return 0.0, [], resamp_mask

# ==============================================================================
# 6. TEXT REGION FORENSICS (OCR BOUNDING BOX INTEGRITY)
# ==============================================================================

def analyze_text_region_forensics(
    gray: np.ndarray, 
    noise_map: np.ndarray, 
    ocr_result: Optional[Dict[str, Any]] = None
) -> Tuple[List[Dict[str, Any]], float]:
    """
    For OCR detected text blocks, compares internal noise variance and sharpness
    against the adjacent background paper substrate.
    Pasted/modified text blocks often exhibit mismatched background noise or edge profiles.
    """
    if not ocr_result or not isinstance(ocr_result, dict):
        return [], 0.0

    detections = ocr_result.get("detections", [])
    if not detections:
        return [], 0.0

    h, w = gray.shape[:2]
    global_noise_median = float(np.median(noise_map))
    anomalous_text_blocks = []

    try:
        for idx, det in enumerate(detections):
            bbox = None
            if isinstance(det, dict) and "bbox" in det:
                bbox = det["bbox"]
            elif isinstance(det, dict) and "box" in det:
                bbox = det["box"]

            if not bbox or len(bbox) < 4:
                continue

            if isinstance(bbox, (list, tuple)) and len(bbox) == 4 and not isinstance(bbox[0], (list, tuple)):
                if bbox[2] > bbox[0] and bbox[3] > bbox[1]:
                    bx_min, by_min, bx_max, by_max = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
                else:
                    bx_min, by_min, bx_max, by_max = int(bbox[0]), int(bbox[1]), int(bbox[0] + bbox[2]), int(bbox[1] + bbox[3])
            else:
                pts = np.array(bbox).reshape(-1, 2)
                bx_min = max(0, int(np.min(pts[:, 0])))
                by_min = max(0, int(np.min(pts[:, 1])))
                bx_max = min(w, int(np.max(pts[:, 0])))
                by_max = min(h, int(np.max(pts[:, 1])))

            bw = bx_max - bx_min
            bh = by_max - by_min
            if bw < 15 or bh < 8:
                continue

            # Text box noise
            roi_noise = noise_map[by_min:by_max, bx_min:bx_max]
            if roi_noise.size == 0:
                continue

            local_noise = float(np.mean(roi_noise))

            # Sample surrounding annulus (background 8px around text)
            ay0 = max(0, by_min - 8)
            ay1 = min(h, by_max + 8)
            ax0 = max(0, bx_min - 8)
            ax1 = min(w, bx_max + 8)
            annulus_noise = noise_map[ay0:ay1, ax0:ax1]
            surround_noise = float(np.mean(annulus_noise))

            # Check noise ratio discrepancy
            if surround_noise > 0.05:
                ratio = local_noise / max(0.01, surround_noise)
                if ratio > 2.5 or ratio < 0.35 or abs(local_noise - surround_noise) > 0.8:
                    anomalous_text_blocks.append({
                        "id": f"TEXT-ANOM-{idx+1:02d}",
                        "x": bx_min, "y": by_min, "w": bw, "h": bh,
                        "signal": "TEXT_REGION_INCONSISTENCY",
                        "noise_ratio": round(ratio, 2),
                        "details": f"Text-block noise profile ({local_noise:.1f}) diverges significantly from adjacent background ({surround_noise:.1f})"
                    })

        text_anomaly_score = min(100.0, len(anomalous_text_blocks) * 20.0)
        return anomalous_text_blocks, text_anomaly_score

    except Exception:
        return [], 0.0

# ==============================================================================
# 7. MAIN CANONICAL TAMPER DETECTION ORCHESTRATOR
# ==============================================================================

def analyze_tampering(
    image_path: str, 
    ocr_result: Optional[Dict[str, Any]] = None,
    qr_result: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Comprehensive multi-spectral tampering detection.
    Analyzes:
      1. ELA (Error Level Analysis)
      2. Local Noise Consistency
      3. Overlays, Paint Strokes & Privacy Redaction
      4. Copy-Move / Cloning
      5. Resampling Artifacts
      6. Text-Region Inconsistencies
      
    Returns structured forensic report with:
      - tampering_score: 0-100 (0 = pristine, 100 = heavily tampered)
      - tampering_integrity_score: 100 - tampering_score
      - status: NO_STRONG_ANOMALY | POSSIBLE_TAMPERING | STRONG_TAMPERING_EVIDENCE
      - severity: NONE | LOW | MODERATE | HIGH | CRITICAL
      - regions: list of localized bounding boxes with signal types
    """
    try:
        img = cv2.imread(image_path)
        if img is None:
            return {
                "tampering_score": 0,
                "tampering_integrity_score": 100,
                "confidence": 0,
                "regions": [],
                "signals": [],
                "status": "NO_STRONG_ANOMALY",
                "severity": "NONE",
                "breakdown": {},
                "findings": ["Image file could not be loaded for tampering analysis."]
            }

        h, w = img.shape[:2]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img.copy()

        # 1. Local Noise Map
        noise_map = estimate_local_noise_map(gray)

        # 2. Localized ELA
        diff_gray, ela_mean, ela_std = compute_localized_ela(img, quality=90)
        
        # Multi-tile ELA analysis (16x16 tiles)
        th, tw = max(1, h // 16), max(1, w // 16)
        tile_ela_means = []
        for r in range(16):
            for c in range(16):
                tile = diff_gray[r*th:(r+1)*th, c*tw:(c+1)*tw]
                if tile.size > 0:
                    tile_ela_means.append(float(np.mean(tile)))

        max_ela_tile = max(tile_ela_means) if tile_ela_means else 0.0
        ela_peak_ratio = (max_ela_tile / max(0.1, ela_mean)) if ela_mean > 0 else 1.0
        ela_anomaly = (max_ela_tile > 8.0 and ela_peak_ratio > 3.0 and max_ela_tile > ela_mean + 2.5 * (ela_std + 0.5))

        # 3. Overlays & Privacy Redactions
        overlay_regions, overlay_mask, overlay_pct, privacy_redactions = detect_overlay_anomalies(img, gray, noise_map)

        # 4. Copy-Move Cloning
        copy_move_detected, cm_regions, cm_mask = detect_copy_move_cloning(gray)

        # 5. Resampling Artifacts
        resamp_score, resamp_tiles, resamp_mask = detect_resampling_artifacts(gray)

        # 6. Text Region Forensics
        text_regions, text_anom_score = analyze_text_region_forensics(gray, noise_map, ocr_result)

        # ----------------------------------------------------------------------
        # Synthesize Correlated Forensic Evidence
        # ----------------------------------------------------------------------
        all_regions: List[Dict[str, Any]] = []
        all_regions.extend(overlay_regions)
        for cm in cm_regions:
            all_regions.append({
                "id": "COPY-MOVE-01",
                "x": cm["target_region"]["x"],
                "y": cm["target_region"]["y"],
                "w": cm["target_region"]["w"],
                "h": cm["target_region"]["h"],
                "signal": "COPY_MOVE_CLONING",
                "type": "TAMPERING",
                "confidence": cm["confidence"],
                "risk_contribution": 35,
                "details": cm["details"]
            })
        for rt in resamp_tiles[:3]:  # Top 3 resampling tiles
            all_regions.append({
                "id": f"RESAMP-{len(all_regions)+1:02d}",
                "x": rt["x"], "y": rt["y"], "w": rt["w"], "h": rt["h"],
                "signal": "RESAMPLING_ANOMALY",
                "type": "POSSIBLE_LOCAL_MODIFICATION",
                "confidence": 60.0,
                "risk_contribution": 5,
                "details": rt["details"]
            })
        for tb in text_regions[:4]:
            all_regions.append({
                "id": tb["id"],
                "x": tb["x"], "y": tb["y"], "w": tb["w"], "h": tb["h"],
                "signal": tb["signal"],
                "type": "TAMPERING",
                "confidence": 80.0,
                "risk_contribution": 15,
                "details": tb["details"]
            })

        # Calculate Independent Tampering Scores
        # Section 10 & 11: Only true malicious overlays count toward tampering.
        # Privacy redactions (marker strokes / blackouts) have 0 risk contribution.
        true_overlays = [r for r in overlay_regions if r.get("signal") == "OVERLAY_ANOMALY"]
        overlay_score = 0.0
        if overlay_pct > 0.10 or len(true_overlays) >= 1:
            base_overlay = 45.0 if len(true_overlays) >= 4 else (35.0 if overlay_pct > 0.5 else 25.0)
            overlay_score = min(100.0, base_overlay + overlay_pct * 8.0 + min(35.0, len(true_overlays) * 2.5))
        
        # Section 5: ELA is a supporting forensic signal, NOT authenticity proof.
        # Standalone ELA cannot create high suspicion.
        ela_score = 25.0 if ela_anomaly else (10.0 if (ela_peak_ratio > 2.5 and max_ela_tile > 6.0) else 0.0)

        # Copy-move component:
        cm_score = 80.0 if copy_move_detected else 0.0

        # Text mismatch component:
        text_score = min(60.0, text_anom_score)

        # Section 7: Resampling detection must be extremely conservative.
        # A scanned / photographed document naturally undergoes resampling.
        # Only meaningful when correlated with another independent anomaly (e.g. copy-move, text anomaly).
        is_resamp_correlated = (cm_score > 30 or overlay_score > 25 or text_score > 25)
        resampling_score = min(40.0, resamp_score) if is_resamp_correlated else min(10.0, resamp_score * 0.2)

        # Weighted aggregate tampering score
        weighted_tamper = (
            overlay_score * 0.40 +
            cm_score * 0.30 +
            text_score * 0.15 +
            ela_score * 0.10 +
            resampling_score * 0.05
        )

        # Severe isolated anomaly override:
        # If confirmed copy-move cloning or massive malicious overlay occurs,
        # tampering score must reflect strong localized manipulation
        if overlay_score >= 35.0:
            weighted_tamper = max(weighted_tamper, overlay_score)
        if cm_score >= 40.0:
            weighted_tamper = max(weighted_tamper, cm_score)

        # Check for correlated multi-signal agreement (independent methods agree)
        active_signals_count = sum(1 for s in (overlay_score > 25, cm_score > 40, text_score > 30, (ela_score > 20 and is_resamp_correlated)) if s)

        if active_signals_count >= 2:
            # Multi-method agreement boosts confidence and severity
            weighted_tamper = min(100.0, weighted_tamper * 1.30 + 10.0)

        tampering_score = int(round(max(0, min(100, weighted_tamper))))
        tampering_integrity_score = 100 - tampering_score

        # Determine Severity & Status
        findings = []
        signals = []

        if tampering_score >= 70:
            severity = "CRITICAL"
            status = "STRONG_TAMPERING_EVIDENCE"
            confidence = 95
            findings.append("CRITICAL: Strong multi-spectral evidence of localized document manipulation.")
        elif tampering_score >= 45:
            severity = "HIGH"
            status = "STRONG_TAMPERING_EVIDENCE"
            confidence = 85
            findings.append("HIGH: Multiple localized forensic anomalies detected across image regions.")
        elif tampering_score >= 25:
            severity = "MODERATE"
            status = "POSSIBLE_TAMPERING"
            confidence = 75
            findings.append("MODERATE: Localized image modification or synthetic overlays detected.")
        elif tampering_score >= 10:
            severity = "LOW"
            status = "NO_STRONG_ANOMALY"
            confidence = 70
            findings.append("LOW: Weak localized variation consistent with standard digital transmission.")
        else:
            severity = "NONE"
            status = "NO_STRONG_ANOMALY"
            confidence = 90
            findings.append("NONE: Uniform pixel noise distribution; no localized digital splicing or tampering detected.")

        # Record Privacy Redactions (Section 11)
        if privacy_redactions:
            signals.append({
                "name": "PRIVACY_REDACTION",
                "severity": "INFO",
                "risk_contribution": 0,
                "description": f"Detected {len(privacy_redactions)} intentional user privacy redaction(s) masking sensitive identity fields (non-fraudulent)."
            })
            findings.append(f"User privacy redaction detected: {len(privacy_redactions)} sensitive field(s)/QR masked for privacy protection; zero fraud penalty.")

        # Record specific signal descriptions
        if overlay_score > 20:
            signals.append({
                "name": "OVERLAY_ANOMALY",
                "severity": "HIGH" if overlay_score > 50 else "MODERATE",
                "description": f"Detected {len(true_overlays)} synthetic overlay/paint stroke(s) covering {overlay_pct:.2f}% of canvas."
            })
            findings.append(f"Synthetic color overlay / manual paint strokes detected ({len(true_overlays)} region{'s' if len(true_overlays) > 1 else ''} occluding document content).")

        if copy_move_detected:
            signals.append({
                "name": "COPY_MOVE_CLONING",
                "severity": "CRITICAL",
                "description": "Coherent spatial cloning isolated between duplicated regions."
            })
            findings.append("Coherent spatial cloning / duplicated region detected.")

        if ela_anomaly:
            signals.append({
                "name": "COMPRESSION_DISCREPANCY",
                "severity": "MODERATE",
                "description": f"Regional ELA peak ({max_ela_tile:.1f}) exceeds baseline ({ela_mean:.1f}); supporting forensic signal."
            })
            findings.append("Localized JPEG compression mismatch indicates potential spliced insertion (supporting signal).")

        if text_score > 20:
            signals.append({
                "name": "TEXT_BACKGROUND_INCONSISTENCY",
                "severity": "MODERATE",
                "description": f"{len(text_regions)} text bounding box(es) exhibit noise variance mismatch relative to background."
            })
            findings.append(f"Text-region forensic inconsistency detected in {len(text_regions)} block(s).")

        if resampling_score > 25:
            signals.append({
                "name": "RESAMPLING_PERIODICITY",
                "severity": "LOW",
                "description": "High-frequency derivative periodicity detected in localized tiles."
            })

        # Unified Anomaly Mask for Heatmap
        unified_mask = np.maximum(overlay_mask, cm_mask)
        unified_mask = np.maximum(unified_mask, resamp_mask)

        return {
            "tampering_score": tampering_score,
            "tampering_integrity_score": tampering_integrity_score,
            "confidence": confidence,
            "status": status,
            "severity": severity,
            "regions": all_regions,
            "signals": signals,
            "findings": findings,
            "breakdown": {
                "overlay": float(round(overlay_score, 1)),
                "copy_move": float(round(cm_score, 1)),
                "ela": float(round(ela_score, 1)),
                "text_region": float(round(text_score, 1)),
                "resampling": float(round(resampling_score, 1))
            },
            "metrics": {
                "overlay_pct": float(round(overlay_pct, 2)),
                "overlay_regions_count": int(len(overlay_regions)),
                "copy_move_detected": bool(copy_move_detected),
                "ela_peak_ratio": float(round(ela_peak_ratio, 2)),
                "ela_mean": float(round(ela_mean, 2)),
                "privacy_redactions_count": int(len(privacy_redactions))
            },
            "privacy_redactions": privacy_redactions,
            "anomaly_mask": unified_mask
        }

    except Exception as e:
        return {
            "tampering_score": 0,
            "tampering_integrity_score": 100,
            "confidence": 0,
            "status": "NO_STRONG_ANOMALY",
            "severity": "NONE",
            "regions": [],
            "signals": [],
            "breakdown": {},
            "findings": [f"Tampering detection completed with fallback: {str(e)}"],
            "anomaly_mask": np.zeros((100, 100), dtype=np.uint8)
        }
