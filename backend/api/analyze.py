from fastapi import APIRouter, UploadFile, File, Form, HTTPException
import shutil
import os
import time
import sys

# Add backend dir to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from forensic.pipeline import process_document

router = APIRouter()

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "../data/uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/analyze")
async def analyze_document(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")
    
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Invalid file type. Only images are allowed.")
    
    # Save file temporarily
    file_path = os.path.join(UPLOAD_DIR, f"{int(time.time())}_{file.filename}")
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Process via pipeline
        result = process_document(file_path)
        
        return {
            "status": "success",
            "message": "File analyzed successfully",
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
