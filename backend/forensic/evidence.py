"""
Centralized Evidence Ingestion & Forensic Image Content Validation
Validates image byte streams, enforces size limits, decodes via OpenCV/PIL,
generates SHA-256 digests, stores evidence using safe UUID filenames,
and creates verifiable chain of custody records.
"""

import io
import os
import time
import uuid
import hashlib
from typing import Tuple, Dict, Any
from PIL import Image
import cv2
import numpy as np
from fastapi import HTTPException

MAX_IMAGE_SIZE_BYTES = 15 * 1024 * 1024  # 15 MB
ALLOWED_FORMATS = {"JPEG", "JPG", "PNG", "WEBP"}

def validate_and_decode_image(file_bytes: bytes) -> Tuple[np.ndarray, str, str]:
    """
    Validates actual image content:
    1. Checks byte size limits.
    2. Validates image integrity using PIL Image.verify().
    3. Reopens image and validates format.
    4. Decodes image with OpenCV.
    5. Returns (cv2_image, verified_extension, normalized_mime_type).
    Raises HTTPException(400) on malformed, oversized, or unsupported images.
    """
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    if len(file_bytes) > MAX_IMAGE_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File exceeds maximum allowed size of {MAX_IMAGE_SIZE_BYTES // (1024*1024)}MB."
        )

    # 1. PIL verify to catch truncated / corrupt byte streams
    try:
        pil_img = Image.open(io.BytesIO(file_bytes))
        pil_img.verify()
    except Exception:
        raise HTTPException(status_code=400, detail="Corrupted, truncated, or invalid image stream.")

    # 2. Reopen image to inspect format
    try:
        pil_img = Image.open(io.BytesIO(file_bytes))
        fmt = (pil_img.format or "").upper()
        if fmt not in ALLOWED_FORMATS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported image format: {fmt}. Allowed formats: JPEG, PNG, WEBP."
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Image inspection failed: {str(e)}")

    # 3. Decode with OpenCV
    nparr = np.frombuffer(file_bytes, np.uint8)
    cv_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if cv_img is None or cv_img.size == 0:
        raise HTTPException(status_code=400, detail="Failed to decode image data into computer vision matrix.")

    ext = ".jpg" if fmt in ("JPEG", "JPG") else f".{fmt.lower()}"
    mime = "image/jpeg" if fmt in ("JPEG", "JPG") else f"image/{fmt.lower()}"

    return cv_img, ext, mime

def ingest_evidence(
    file_bytes: bytes,
    original_filename: str,
    investigator: dict,
    upload_dir: str
) -> Tuple[str, Dict[str, Any]]:
    """
    Centralized Evidence Ingestion Pipeline:
    - Validates image content and decoding.
    - Computes cryptographic SHA-256 digest.
    - Generates immutable evidence ID.
    - Persists file using safe UUID storage filename (never raw user filename).
    - Assembles canonical chain of custody record.
    Returns: (internal_file_path, chain_of_custody_dict)
    """
    _, ext, mime = validate_and_decode_image(file_bytes)

    sha256_hash = hashlib.sha256(file_bytes).hexdigest()
    ts = int(time.time())
    evidence_uuid = uuid.uuid4().hex
    evidence_id = f"EVID-{ts}-{evidence_uuid[:6].upper()}"

    safe_stored_filename = f"evidence_{ts}_{evidence_uuid}{ext}"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, safe_stored_filename)

    with open(file_path, "wb") as buffer:
        buffer.write(file_bytes)

    # Safe original filename without path traversal or directory components
    safe_original_name = os.path.basename(original_filename or "specimen.jpg")
    safe_original_name = "".join(c for c in safe_original_name if c.isalnum() or c in "._- ")
    if not safe_original_name:
        safe_original_name = f"specimen{ext}"

    chain_of_custody = {
        "evidence_id": evidence_id,
        "sha256_hash": sha256_hash,
        "ingestion_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "investigator_id": investigator.get("id", "anonymous"),
        "investigator_name": investigator.get("name") or "Investigator",
        "analysis_version": "2.1.0",
        "original_filename": safe_original_name,
        "stored_filename": safe_stored_filename,
        "file_path": os.path.abspath(file_path),
        "file_size": len(file_bytes),
        "mime_type": mime,
        "status": "TAMPER_FREE"
    }

    return file_path, chain_of_custody

def sanitize_custody_for_client(custody: dict) -> dict:
    """Removes server-side internal physical file paths before returning to clients."""
    if not custody or not isinstance(custody, dict):
        return {}
    clean = custody.copy()
    clean.pop("file_path", None)
    return clean
