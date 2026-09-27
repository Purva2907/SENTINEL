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

MAX_IMAGE_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB
ALLOWED_FORMATS = {"JPEG", "JPG", "PNG", "WEBP", "PDF"}

def validate_and_decode_image(file_bytes: bytes) -> Tuple[np.ndarray, str, str]:
    """
    Validates actual image or PDF document content:
    1. Checks byte size limits (up to 25MB).
    2. Detects PDF documents via magic header (%PDF):
       - Parses and validates structure using PyMuPDF.
       - Rejects password-encrypted PDFs.
       - Renders primary specimen page (page 0) at 200 DPI into OpenCV BGR matrix.
       - Returns (cv2_image, ".png", "application/pdf").
    3. For image formats (JPEG, PNG, WEBP):
       - Validates image integrity using PIL Image.verify().
       - Reopens image and validates format.
       - Decodes image with OpenCV.
       - Returns (cv2_image, verified_extension, normalized_mime_type).
    Raises HTTPException(400) on malformed, oversized, or unsupported documents.
    """
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    if len(file_bytes) > MAX_IMAGE_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File exceeds maximum allowed size of {MAX_IMAGE_SIZE_BYTES // (1024*1024)}MB."
        )

    # 1. Check for PDF document header
    is_pdf = file_bytes.startswith(b"%PDF") or b"%PDF-" in file_bytes[:1024]
    if is_pdf:
        try:
            import pymupdf
            doc = pymupdf.open(stream=file_bytes, filetype="pdf")
            if doc.is_encrypted:
                if not doc.authenticate(""):
                    raise HTTPException(
                        status_code=400,
                        detail="Password-protected PDF documents are not supported for forensic screening."
                    )
            if len(doc) == 0:
                raise HTTPException(status_code=400, detail="Uploaded PDF document contains no pages.")

            # Render primary examination page (page 0) at 200 DPI for forensic analysis
            page = doc[0]
            pix = page.get_pixmap(dpi=200)
            img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)

            if pix.n == 4:
                cv_img = cv2.cvtColor(img_array, cv2.COLOR_RGBA2BGR)
            elif pix.n == 3:
                cv_img = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
            else:
                cv_img = cv2.cvtColor(img_array, cv2.COLOR_GRAY2BGR)

            doc.close()

            if cv_img is None or cv_img.size == 0:
                raise HTTPException(status_code=400, detail="Failed to rasterize PDF page into computer vision matrix.")

            return cv_img, ".png", "application/pdf"
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Corrupted or invalid PDF document: {str(e)}")

    # 2. PIL verify to catch truncated / corrupt byte streams
    try:
        pil_img = Image.open(io.BytesIO(file_bytes))
        pil_img.verify()
    except Exception:
        raise HTTPException(status_code=400, detail="Corrupted, truncated, or invalid image stream.")

    # 3. Reopen image to inspect format
    try:
        pil_img = Image.open(io.BytesIO(file_bytes))
        fmt = (pil_img.format or "").upper()
        if fmt not in ALLOWED_FORMATS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported image format: {fmt}. Allowed formats: PDF, JPEG, PNG, WEBP."
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Image inspection failed: {str(e)}")

    # 4. Decode with OpenCV
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
    - Validates document/image content and decoding.
    - Computes cryptographic SHA-256 digest of original upload.
    - Generates immutable evidence ID.
    - Persists file using safe UUID storage filename.
    - For PDF uploads, securely archives the original PDF and creates a high-res
      rasterized specimen image for downstream computer vision analysis.
    - Assembles canonical chain of custody record.
    Returns: (internal_file_path, chain_of_custody_dict)
    """
    cv_img, ext, mime = validate_and_decode_image(file_bytes)

    sha256_hash = hashlib.sha256(file_bytes).hexdigest()
    ts = int(time.time())
    evidence_uuid = uuid.uuid4().hex
    evidence_id = f"EVID-{ts}-{evidence_uuid[:6].upper()}"

    os.makedirs(upload_dir, exist_ok=True)

    # Safe original filename without path traversal or directory components
    default_name = "specimen.pdf" if mime == "application/pdf" else "specimen.jpg"
    safe_original_name = os.path.basename(original_filename or default_name)
    safe_original_name = "".join(c for c in safe_original_name if c.isalnum() or c in "._- ")
    if not safe_original_name:
        safe_original_name = f"specimen{'.pdf' if mime == 'application/pdf' else ext}"

    page_count = 1
    if mime == "application/pdf":
        # Save raw original PDF
        raw_pdf_filename = f"evidence_{ts}_{evidence_uuid}.pdf"
        raw_pdf_path = os.path.join(upload_dir, raw_pdf_filename)
        with open(raw_pdf_path, "wb") as buffer:
            buffer.write(file_bytes)

        # Save rasterized specimen image for CV forensic modules
        safe_stored_filename = f"evidence_{ts}_{evidence_uuid}.png"
        file_path = os.path.join(upload_dir, safe_stored_filename)
        cv2.imwrite(file_path, cv_img)

        try:
            import pymupdf
            with pymupdf.open(stream=file_bytes, filetype="pdf") as pdf_doc:
                page_count = len(pdf_doc)
        except Exception:
            page_count = 1
    else:
        safe_stored_filename = f"evidence_{ts}_{evidence_uuid}{ext}"
        file_path = os.path.join(upload_dir, safe_stored_filename)
        with open(file_path, "wb") as buffer:
            buffer.write(file_bytes)

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
        "format": "PDF" if mime == "application/pdf" else ext.replace(".", "").upper(),
        "status": "TAMPER_FREE"
    }

    if mime == "application/pdf":
        chain_of_custody["pdf_path"] = os.path.abspath(raw_pdf_path)
        chain_of_custody["page_count"] = page_count

    return file_path, chain_of_custody

def sanitize_custody_for_client(custody: dict) -> dict:
    """Removes server-side internal physical file paths before returning to clients."""
    if not custody or not isinstance(custody, dict):
        return {}
    clean = custody.copy()
    clean.pop("file_path", None)
    clean.pop("pdf_path", None)
    return clean
