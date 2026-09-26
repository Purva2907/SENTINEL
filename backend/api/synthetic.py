from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import os
import hashlib
import time

from auth.jwt import get_current_user
from forensic.synthetic_lab import (
    generate_synthetic_test_case, WATERMARK_TEXT, SYNTHETIC_DIR
)
from forensic.pipeline import process_document

router = APIRouter()

class GenerateSampleRequest(BaseModel):
    document_type: str = "Synthetic ID"
    manipulations: List[str] = []
    severity: int = Field(50, ge=1, le=100)
    seed: Optional[int] = None

class AnalyzeSampleRequest(BaseModel):
    document_type: str = "Synthetic ID"
    manipulations: List[str] = []
    severity: int = Field(50, ge=1, le=100)
    seed: Optional[int] = None

@router.get("/manipulations")
async def list_manipulations():
    """Lists the available controlled manipulation modules with technical descriptions."""
    return {
        "watermark": WATERMARK_TEXT,
        "available_manipulations": [
            {
                "id": "typography_alteration",
                "name": "Typography Disparity",
                "category": "Typography",
                "description": "Scales up font size and modifies stroke weight on credential fields."
            },
            {
                "id": "kerning_distortion",
                "name": "Kerning & Spacing Distortion",
                "category": "Typography",
                "description": "Applies non-uniform character gap spacing across text lines."
            },
            {
                "id": "layout_shift",
                "name": "Layout Geometry Displacement",
                "category": "Layout",
                "description": "Displaces demographic block coordinates off the template alignment grid."
            },
            {
                "id": "image_splice",
                "name": "Synthetic Image Patch Splice",
                "category": "Image Forensics",
                "description": "Injects a secondary graphic patch creating localized compression and ELA anomalies."
            },
            {
                "id": "qr_corruption",
                "name": "2D Matrix QR Corruption",
                "category": "QR",
                "description": "Overlays noise over the 2D barcode matrix, impairing optical decoding."
            },
            {
                "id": "blur",
                "name": "Substrate Gaussian Blur",
                "category": "Quality",
                "description": "Simulates out-of-focus capture or artificial document blurring."
            },
            {
                "id": "jpeg_compression",
                "name": "JPEG Re-compression Artifacts",
                "category": "Image Forensics",
                "description": "Re-encodes canvas with high quantization error to trigger ELA heatmaps."
            },
            {
                "id": "illumination_change",
                "name": "Illumination & Exposure Shift",
                "category": "Quality",
                "description": "Applies non-linear gamma and bright spotlight luminance overexposure."
            }
        ]
    }

@router.post("/generate")
async def generate_sample(req: GenerateSampleRequest, current_user: dict = Depends(get_current_user)):
    """
    Generates a controlled synthetic test document with specified manipulations.
    Safety: Visibly watermarked as synthetic; fictional identities only.
    """
    try:
        sample = generate_synthetic_test_case(
            doc_type=req.document_type,
            manipulations=req.manipulations,
            severity=req.severity,
            seed=req.seed
        )
        return {
            "success": True,
            "message": "Synthetic test document generated successfully.",
            "sample": sample
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")

@router.post("/analyze")
async def generate_and_analyze(req: AnalyzeSampleRequest, current_user: dict = Depends(get_current_user)):
    """
    ONE-CLICK SYNTHETIC FORENSICS PIPELINE TEST:
    1. Generates the synthetic document with chosen manipulation parameters.
    2. Immediately passes the generated file through SENTINEL's actual forensic pipeline.
    3. Returns both injected parameters and detected forensic signals for correlation.
    """
    try:
        # Step 1: Generate synthetic test sample
        sample = generate_synthetic_test_case(
            doc_type=req.document_type,
            manipulations=req.manipulations,
            severity=req.severity,
            seed=req.seed
        )

        file_path = sample["file_path"]

        # Step 2: Pass through EXISTING SENTINEL pipeline
        analysis_result = process_document(file_path)

        # Attach Chain of Custody Record
        with open(file_path, "rb") as f:
            file_bytes = f.read()
        sha256_hash = hashlib.sha256(file_bytes).hexdigest()

        investigator_name = current_user.get("name") or "Investigator"
        from forensic.evidence import sanitize_custody_for_client
        raw_custody = {
            "evidence_id": f"EVID-SYN-{sample['sample_id'][:12]}",
            "sha256_hash": sha256_hash,
            "ingestion_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "investigator_id": current_user["id"],
            "investigator_name": investigator_name,
            "analysis_version": "2.1.0",
            "original_filename": f"{sample['sample_id']}.jpg",
            "stored_filename": os.path.basename(file_path),
            "file_path": os.path.abspath(file_path),
            "file_size": len(file_bytes),
            "mime_type": "image/jpeg",
            "status": "TAMPER_FREE"
        }
        analysis_result["chain_of_custody"] = sanitize_custody_for_client(raw_custody)

        # Step 3: Compute correlation between injected manipulations and detected signals
        injected = [m.get("manipulation") for m in sample["manipulations_injected"]]
        detected_signals = []

        if analysis_result["risk_breakdown"]["typography"] > 0:
            detected_signals.append("Typography Disparity Flagged")
        if analysis_result["risk_breakdown"]["layout"] > 0:
            detected_signals.append("Layout Anomaly Flagged")
        if analysis_result["risk_breakdown"]["image_forensics"] > 0:
            detected_signals.append("ELA Compression Anomaly Flagged")
        if analysis_result["risk_breakdown"]["qr"] > 0:
            detected_signals.append("QR Verification Flagged")
        if analysis_result["risk_breakdown"]["quality"] > 0:
            detected_signals.append("Image Quality Warning Flagged")

        return {
            "success": True,
            "sample_metadata": {
                "sample_id": sample["sample_id"],
                "evidence_id": f"EVID-SYN-{sample['sample_id'][:12]}",
                "document_type": sample["document_type"],
                "watermark": sample["watermark"],
                "seed": sample["seed"],
                "severity": sample["severity"],
                "injected_manipulations": sample["manipulations_injected"],
                "original_image": sample["original_image"],
                "manipulated_image": sample["manipulated_image"],
                "stored_filename": os.path.basename(file_path)
            },
            "analysis": analysis_result,
            "correlation": {
                "injected_count": len(injected),
                "detected_signal_count": len(detected_signals),
                "detected_signals": detected_signals,
                "risk_score": analysis_result["risk_score"],
                "classification": analysis_result["classification"]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline execution failed: {str(e)}")
