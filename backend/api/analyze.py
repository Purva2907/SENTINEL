from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
import os
import sys

# Add backend dir to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from forensic.pipeline import process_document
from forensic.evidence import ingest_evidence, sanitize_custody_for_client
from auth.jwt import get_current_user

router = APIRouter()

UPLOAD_DIR = os.getenv("UPLOAD_DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "uploads"))
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/analyze")
async def analyze_document(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Authenticated Document Analysis Intake:
    Requires valid investigator JWT credentials.
    Performs actual image content validation, SHA-256 cryptographic digest calculation,
    safe evidence ingestion, and full forensic pipeline screening.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")

    try:
        file_bytes = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read upload stream: {str(e)}")

    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # Ingest evidence with actual image validation, SHA-256 calculation, and safe storage
    try:
        file_path, custody = ingest_evidence(
            file_bytes=file_bytes,
            original_filename=file.filename,
            investigator=current_user,
            upload_dir=UPLOAD_DIR
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Evidence ingestion error: {str(e)}")

    try:
        # Execute forensic pipeline
        result = process_document(file_path)

        # Sanitize chain of custody for client presentation (no internal path disclosure)
        client_custody = sanitize_custody_for_client(custody)
        result["chain_of_custody"] = client_custody

        return {
            "status": "success",
            "message": "File analyzed successfully",
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Forensic analysis failed: {str(e)}")
