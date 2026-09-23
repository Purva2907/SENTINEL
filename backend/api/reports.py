from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from typing import Optional
import os
import shutil
import time
import uuid

from auth.jwt import get_current_user
from database.repository import create_report, get_report, list_reports, get_case, create_case
from reports.pdf_report import generate_pdf
from forensic.pipeline import process_document

router = APIRouter()

UPLOAD_DIR = os.getenv("UPLOAD_DIR", os.path.join(os.path.dirname(__file__), "..", "..", "data", "uploads"))
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload")
async def create_report_from_upload(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    document_type: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user)
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")
    
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Invalid file type. Only image files (JPG, PNG, WEBP) are supported.")
    
    user_id = current_user["id"]
    timestamp = int(time.time())
    safe_filename = f"{timestamp}_{uuid.uuid4().hex[:6]}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # 1. Execute forensic pipeline
        result = process_document(file_path)
        
        # 2. Extract risk metrics
        risk_score = int(result.get("risk_score", 0))
        classification = result.get("classification", "Likely Authentic")
        doc_type = document_type or result.get("document_type") or "Aadhaar-like"
        case_title = title.strip() if title and title.strip() else f"Direct Intake: {file.filename}"
        case_desc = description.strip() if description and description.strip() else f"Automated forensic report generated from file upload: {file.filename}"
        
        # 3. Create case entry
        case_data = {
            "user_id": user_id,
            "title": case_title,
            "description": case_desc,
            "document_type": doc_type,
            "status": "Active",
            "risk_score": risk_score,
            "classification": classification
        }
        case = await create_case(case_data, result)
        
        # Attach analysis so PDF generator has full evidence log
        case["analysis"] = result
        
        # 4. Generate unique report PDF
        report_id = f"RPT-2026-{str(uuid.uuid4().hex)[:4].upper()}"
        pdf_path = generate_pdf(case, current_user, report_id=report_id)
        if not os.path.exists(pdf_path):
            raise HTTPException(status_code=500, detail="PDF generation failed")
            
        # 5. Persist report record
        report = await create_report(user_id, case.get("case_id", case["id"]), pdf_path, report_id=report_id)
        
        return {
            "status": "success",
            "message": "Forensic report created successfully",
            "report": report,
            "case": case,
            "download_url": f"/api/reports/{report['id']}/download"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report creation failed: {str(e)}")

@router.post("/{case_id}")
async def generate_case_report(case_id: str, current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    case = await get_case(user_id, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
        
    report_id = f"RPT-2026-{str(uuid.uuid4().hex)[:4].upper()}"
    pdf_path = generate_pdf(case, current_user, report_id=report_id)
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=500, detail="PDF generation failed")
        
    report = await create_report(user_id, case.get("case_id", case["id"]), pdf_path, report_id=report_id)
    return report

@router.get("")
@router.get("/")
async def get_reports_list(current_user: dict = Depends(get_current_user)):
    reports = await list_reports(current_user["id"])
    return {"reports": reports}

@router.get("/{report_id}/download")
async def download_report(report_id: str, current_user: dict = Depends(get_current_user)):
    report = await get_report(current_user["id"], report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
        
    if not os.path.exists(report["file_path"]):
        raise HTTPException(status_code=404, detail="Report file missing")
        
    return FileResponse(report["file_path"], media_type="application/pdf", filename=f"{report['report_id']}.pdf")
