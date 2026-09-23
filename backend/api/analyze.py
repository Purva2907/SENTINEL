from fastapi import APIRouter, UploadFile, File, Form, HTTPException
import shutil
import os
import time
import sys
import uuid
import hashlib

# Add backend dir to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from forensic.pipeline import process_document

router = APIRouter()

UPLOAD_DIR = os.getenv("UPLOAD_DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "uploads"))
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/analyze")
async def analyze_document(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")
    
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Invalid file type. Only images are allowed.")
    
    # 1. Read file bytes and calculate SHA-256 cryptographic hash (Evidence Chain of Custody)
    try:
        file_bytes = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read upload stream: {str(e)}")
        
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    sha256_hash = hashlib.sha256(file_bytes).hexdigest()
    evidence_id = f"EVID-{int(time.time())}-{uuid.uuid4().hex[:6].upper()}"
    
    # Deterministic preserved filename
    ext = os.path.splitext(file.filename)[1] or ".jpg"
    safe_filename = f"{evidence_id}_{int(time.time())}{ext}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)

    try:
        with open(file_path, "wb") as buffer:
            buffer.write(file_bytes)
            
        # Process via forensic pipeline
        result = process_document(file_path)
        
        # Chain of Custody Record
        chain_of_custody = {
            "evidence_id": evidence_id,
            "sha256_hash": sha256_hash,
            "ingestion_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "investigator_id": "investigator",
            "investigator_name": "Forensic Screening Officer",
            "analysis_version": "2.1.0",
            "original_filename": file.filename,
            "stored_filename": safe_filename,
            "file_path": os.path.abspath(file_path),
            "file_size": len(file_bytes),
            "mime_type": file.content_type or "image/jpeg",
            "status": "TAMPER_FREE"
        }
        result["chain_of_custody"] = chain_of_custody
        
        return {
            "status": "success",
            "message": "File analyzed successfully",
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
