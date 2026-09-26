import os
import time
import random
import uuid
import base64
import hashlib
import cv2
import numpy as np
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from typing import Dict, Any, List, Tuple

# Storage directory for synthetic test samples
SYNTHETIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "synthetic")
os.makedirs(SYNTHETIC_DIR, exist_ok=True)

WATERMARK_TEXT = "SYNTHETIC DEMO — NOT A REAL GOVERNMENT DOCUMENT"

def get_font(size: int = 16, bold: bool = False):
    """Fallback font loader using default or common system truetype fonts."""
    font_paths = [
        "C:\\Windows\\Fonts\\arialbd.ttf" if bold else "C:\\Windows\\Fonts\\arial.ttf",
        "C:\\Windows\\Fonts\\segoeui.ttf",
        "C:\\Windows\\Fonts\\calibri.ttf"
    ]
    for p in font_paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()

def create_base_synthetic_document(doc_type: str = "Synthetic ID", seed: int = None) -> Image.Image:
    """
    Renders a pristine, fictional synthetic credential canvas.
    All data is completely fictional and visibly watermarked.
    """
    if seed is not None:
        random.seed(seed)

    w, h = 850, 540
    img = Image.new("RGB", (w, h), color=(248, 250, 252))
    draw = ImageDraw.Draw(img)

    # Document Header Band
    if "PAN" in doc_type.upper():
        header_color = (26, 86, 160)
        card_title = "SYNTHETIC TAXPAYER SPECIMEN"
        sub_title = "FICTIONAL CARD — DEMONSTRATION USE ONLY"
    elif "PASSPORT" in doc_type.upper():
        header_color = (15, 30, 60)
        card_title = "SYNTHETIC TRAVEL CREDENTIAL"
        sub_title = "SPECIMEN PASSPORT DATA PAGE"
    else:
        header_color = (16, 120, 100)
        card_title = "SYNTHETIC IDENTITY SPECIMEN"
        sub_title = "SENTINEL FORENSIC TEST SPECIMEN"

    draw.rectangle([(0, 0), (w, 75)], fill=header_color)
    f_title = get_font(22, bold=True)
    f_sub = get_font(12)
    draw.text((30, 16), card_title, fill=(255, 255, 255), font=f_title)
    draw.text((30, 46), sub_title, fill=(200, 230, 225), font=f_sub)

    # Subtle Guilloche / Border Grid
    draw.rectangle([(15, 15), (w - 15, h - 15)], outline=(203, 213, 225), width=2)
    for x in range(30, w - 30, 80):
        draw.line([(x, 85), (x, h - 30)], fill=(241, 245, 249), width=1)

    # Synthetic Photo Box
    photo_box = [(40, 110), (200, 310)]
    draw.rectangle(photo_box, fill=(226, 232, 240), outline=(148, 163, 184), width=2)
    draw.ellipse([(90, 140), (150, 200)], fill=(148, 163, 184))
    draw.pieslice([(70, 210), (170, 310)], 0, 180, fill=(100, 116, 139))
    f_photo = get_font(11)
    draw.text((65, 280), "PHOTO SPECIMEN", fill=(71, 85, 105), font=f_photo)

    # Fictional Demographic Identity Data
    f_lbl = get_font(12, bold=True)
    f_val = get_font(16)
    f_bold_val = get_font(20, bold=True)

    fictional_records = {
        "Name": "Aarav Demo",
        "Document ID": "SYN-DEMO-001",
        "DOB": "01/01/2000",
        "Gender": "Male",
        "Address": "Flat 101, Test Regency, Forensic Way, Mumbai - 400001",
        "Issued": "15/01/2026"
    }

    fields = [
        ("REGISTERED NAME / पूर्ण नाव", fictional_records["Name"]),
        ("CREDENTIAL NUMBER / ओळख क्रमांक", fictional_records["Document ID"]),
        ("DATE OF BIRTH / जन्म तारीख", fictional_records["DOB"]),
        ("GENDER / लिंग", fictional_records["Gender"]),
        ("RESIDENTIAL ADDRESS / पत्ता", fictional_records["Address"]),
    ]

    cur_y = 110
    for label, val in fields:
        draw.text((230, cur_y), label, fill=(100, 116, 139), font=f_lbl)
        cur_y += 18
        if "CREDENTIAL NUMBER" in label:
            draw.text((230, cur_y), val, fill=(15, 23, 42), font=f_bold_val)
            cur_y += 32
        else:
            draw.text((230, cur_y), val, fill=(30, 41, 59), font=f_val)
            cur_y += 28

    # Genuine Synthetic 2D QR Code using qrcode library
    import qrcode
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=4,
        border=4,
    )
    qr.add_data("SENTINEL-DEMO-001")
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    
    qr_w, qr_h = 120, 120
    qr_img_resized = qr_img.resize((qr_w, qr_h), Image.Resampling.NEAREST)
    qr_x, qr_y = w - 160, h - 165

    draw.rectangle([(qr_x - 3, qr_y - 3), (qr_x + qr_w + 3, qr_y + qr_h + 3)], fill=(255, 255, 255), outline=(100, 116, 139), width=1)
    img.paste(qr_img_resized, (qr_x, qr_y))
    f_qr = get_font(9)
    draw.text((qr_x + 6, qr_y + qr_h + 5), "SYNTHETIC QR (DEMO)", fill=(100, 116, 139), font=f_qr)

    # Mandatory Visible Synthetic Watermarks
    f_wm = get_font(13, bold=True)
    draw.text((30, h - 35), WATERMARK_TEXT, fill=(225, 29, 72), font=f_wm)
    draw.text((30, h - 20), "GENERATED FOR CONTROLLED FORENSIC TESTING ONLY", fill=(148, 163, 184), font=get_font(10))

    return img

def apply_manipulation(
    image: Image.Image,
    manipulation_type: str,
    severity: int = 50,
    seed: int = None
) -> Tuple[Image.Image, Dict[str, Any]]:
    """
    Applies a deterministic, controlled manipulation to the synthetic canvas.
    Severity ranges from 1 to 100.
    """
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)

    sev_factor = max(0.01, min(1.0, severity / 100.0))
    img = image.copy()
    w, h = img.size
    draw = ImageDraw.Draw(img)

    meta = {"manipulation": manipulation_type, "severity": severity}

    if manipulation_type == "typography_alteration":
        # Overwrite text with a mismatched font size and weight
        box = [(225, 175), (550, 215)]
        draw.rectangle(box, fill=(248, 250, 252))
        f_alt = get_font(int(14 + sev_factor * 16), bold=True)
        draw.text((230, 178), "SYN-DEMO-ALTERED-99", fill=(15, 23, 42), font=f_alt)
        meta["detail"] = f"Font scaled up by {round(1.0 + sev_factor * 1.5, 2)}x with inconsistent stroke weight."

    elif manipulation_type == "kerning_distortion":
        # Disrupted character spacing in Name line
        box = [(225, 125), (500, 155)]
        draw.rectangle(box, fill=(248, 250, 252))
        f_kern = get_font(16)
        # Draw letters with irregular wide gaps
        x_pos = 230
        for char in "A a  r   a    v   D  e  m o":
            draw.text((x_pos, 128), char, fill=(30, 41, 59), font=f_kern)
            x_pos += int(10 + sev_factor * 18)
        meta["detail"] = f"Character spacing expanded irregularly ({round(sev_factor * 3.5, 1)}x baseline variance)."

    elif manipulation_type == "layout_shift":
        # Shift a major bounding block off-grid
        shift_px = int(15 + sev_factor * 45)
        crop_box = (220, 270, 700, 360)
        region = img.crop(crop_box)
        draw.rectangle([(220, 270), (700, 360)], fill=(248, 250, 252))
        img.paste(region, (220 + shift_px, 270 + shift_px // 2))
        meta["detail"] = f"Address field cluster displaced by {shift_px}px horizontally and {shift_px // 2}px vertically."

    elif manipulation_type == "image_splice":
        # Paste an anomalous spliced graphic patch into the document canvas
        splice_w = int(100 + sev_factor * 60)
        splice_h = int(60 + sev_factor * 40)
        patch = Image.new("RGB", (splice_w, splice_h), color=(240, 245, 255))
        p_draw = ImageDraw.Draw(patch)
        p_draw.rectangle([(0, 0), (splice_w - 1, splice_h - 1)], outline=(30, 64, 175), width=2)
        p_draw.text((10, 15), "SPLICED PATCH", fill=(30, 64, 175), font=get_font(12, bold=True))
        p_draw.text((10, 35), "DIGITAL INSERTION", fill=(71, 85, 105), font=get_font(9))
        
        # Paste near center-right
        img.paste(patch, (w - splice_w - 60, 110))
        meta["detail"] = f"Injected synthetic graphic patch ({splice_w}x{splice_h}px) with independent quantization profile."

    elif manipulation_type in ("qr_corruption", "qr_tamper"):
        # Corrupt the actual synthetic QR matrix zone (located at w - 160, h - 165, size 120x120)
        qr_x, qr_y = w - 160, h - 165
        qr_size = 120
        corrupt_w = int(30 + sev_factor * 85)
        corrupt_h = int(30 + sev_factor * 85)
        draw.rectangle([(qr_x + 5, qr_y + 5), (qr_x + corrupt_w, qr_y + corrupt_h)], fill=(248, 250, 252))
        for _ in range(int(30 + sev_factor * 100)):
            rx = random.randint(qr_x, qr_x + qr_size)
            ry = random.randint(qr_y, qr_y + qr_size)
            draw.rectangle([(rx, ry), (rx + 4, ry + 4)], fill=(0, 0, 0))
        meta["detail"] = f"2D barcode matrix payload corrupted across {corrupt_w}x{corrupt_h}px block."

    elif manipulation_type == "blur":
        # Apply Gaussian blur
        radius = 1.0 + sev_factor * 6.0
        img = img.filter(ImageFilter.GaussianBlur(radius=radius))
        meta["detail"] = f"Gaussian substrate blur applied with radius={round(radius, 2)}."

    elif manipulation_type == "jpeg_compression":
        # Save to buffer with low JPEG quality
        quality_factor = max(10, int(95 - sev_factor * 85))
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=quality_factor)
        buf.seek(0)
        img = Image.open(buf).convert("RGB")
        meta["detail"] = f"JPEG re-compression artifacts injected (Quality factor: {quality_factor}/100)."

    elif manipulation_type == "illumination_change":
        # Non-linear exposure brightness
        enhancer = ImageEnhance.Brightness(img)
        factor = 1.0 + sev_factor * 0.8  # overexpose
        img = enhancer.enhance(factor)
        meta["detail"] = f"Luminance illumination overexposure adjusted by factor of {round(factor, 2)}x."

    return img, meta

def generate_synthetic_test_case(
    doc_type: str = "Synthetic ID",
    manipulations: List[str] = None,
    severity: int = 50,
    seed: int = None
) -> Dict[str, Any]:
    """
    Generates a full controlled synthetic test sample with pristine baseline,
    applied manipulations, reproducible seed, and saved evidence file.
    """
    if seed is None:
        seed = int(time.time() * 1000) % 1000000

    base_img = create_base_synthetic_document(doc_type, seed=seed)
    current_img = base_img.copy()

    manipulations_applied = []
    if manipulations:
        for m in manipulations:
            current_img, meta = apply_manipulation(current_img, m, severity=severity, seed=seed)
            manipulations_applied.append(meta)

    # Save to disk
    sample_id = f"SYN-{int(time.time())}-{uuid.uuid4().hex[:6].upper()}"
    file_path = os.path.join(SYNTHETIC_DIR, f"{sample_id}.jpg")
    current_img.save(file_path, "JPEG", quality=95)

    # Encode both pristine and manipulated to Base64
    buf_base = BytesIO()
    base_img.save(buf_base, format="JPEG", quality=90)
    base_b64 = "data:image/jpeg;base64," + base64.b64encode(buf_base.getvalue()).decode("utf-8")

    buf_manip = BytesIO()
    current_img.save(buf_manip, format="JPEG", quality=90)
    manip_b64 = "data:image/jpeg;base64," + base64.b64encode(buf_manip.getvalue()).decode("utf-8")

    cleanup_old_synthetic_files()

    return {
        "sample_id": sample_id,
        "document_type": doc_type,
        "seed": seed,
        "severity": severity,
        "synthetic": True,
        "watermark": WATERMARK_TEXT,
        "file_path": file_path,
        "original_image": base_b64,
        "manipulated_image": manip_b64,
        "manipulations_injected": manipulations_applied,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }

def cleanup_old_synthetic_files(retention_seconds: int = 7200, max_files: int = 40):
    """
    Retention policy for synthetic test specimens.
    Prunes files older than retention_seconds and keeps directory capped at max_files.
    """
    try:
        now = time.time()
        files = []
        for fname in os.listdir(SYNTHETIC_DIR):
            fpath = os.path.join(SYNTHETIC_DIR, fname)
            if os.path.isfile(fpath):
                files.append((fpath, os.path.getmtime(fpath)))
        
        for fpath, mtime in files:
            if now - mtime > retention_seconds:
                try:
                    os.remove(fpath)
                except OSError:
                    pass
        
        remaining = [f for f in os.listdir(SYNTHETIC_DIR) if os.path.isfile(os.path.join(SYNTHETIC_DIR, f))]
        if len(remaining) > max_files:
            sorted_files = sorted(
                [(os.path.join(SYNTHETIC_DIR, f), os.path.getmtime(os.path.join(SYNTHETIC_DIR, f))) for f in remaining],
                key=lambda x: x[1]
            )
            for fpath, _ in sorted_files[:len(remaining) - max_files]:
                try:
                    os.remove(fpath)
                except OSError:
                    pass
    except Exception:
        pass

SUPPORTED_MANIPULATIONS = [
    "typography_alteration",
    "kerning_distortion",
    "layout_shift",
    "image_splice",
    "qr_corruption",
    "blur",
    "jpeg_compression",
    "illumination_change"
]

def generate_synthetic_document(doc_type: str = "Synthetic ID", seed: Any = None) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Direct helper returning (OpenCV BGR numpy array, metadata dictionary)
    with strict safety watermark and fictional identity parameters.
    """
    int_seed = None
    if seed is not None:
        if isinstance(seed, str):
            int_seed = int(hashlib.md5(seed.encode()).hexdigest()[:8], 16)
        else:
            int_seed = int(seed)

    pil_img = create_base_synthetic_document(doc_type=doc_type, seed=int_seed)
    cv2_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

    metadata = {
        "synthetic": True,
        "watermark": WATERMARK_TEXT,
        "document_type": doc_type,
        "seed": seed,
        "identity": {
            "name": "Aarav Demo",
            "doc_id": "SYN-DEMO-001",
            "dob": "01/01/2000",
            "address": "Synthetic Test Address, Block-4, Sandbox City",
            "qr_payload": "SENTINEL-DEMO-001"
        }
    }
    return cv2_img, metadata

def apply_manipulations(
    image_input: Any,
    manipulations: List[str],
    severity: int = 50,
    seed: Any = None
) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
    """
    Direct helper accepting numpy/PIL, applying a list of manipulations,
    and returning (OpenCV BGR numpy array, metadata_list).
    """
    if isinstance(image_input, np.ndarray):
        pil_img = Image.fromarray(cv2.cvtColor(image_input, cv2.COLOR_BGR2RGB))
    else:
        pil_img = image_input.copy()

    int_seed = None
    if seed is not None:
        if isinstance(seed, str):
            int_seed = int(hashlib.md5(seed.encode()).hexdigest()[:8], 16)
        else:
            int_seed = int(seed)

    details = []
    for m in manipulations:
        pil_img, meta = apply_manipulation(pil_img, m, severity=severity, seed=int_seed)
        details.append(meta)

    result_cv2 = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    return result_cv2, details
