from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from auth.jwt import get_current_user
from database.repository import create_report, get_report, list_reports, get_case
from reports.pdf_report import generate_pdf
import os

router = APIRouter()

@router.post("/{case_id}")
async def generate_case_report(case_id: str, current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    case = await get_case(user_id, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
        
    pdf_path = generate_pdf(case, current_user) # In a real implementation, we'd fetch the user properly, but for the demo we rely on get_current_user which contains name
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=500, detail="PDF generation failed")
        
    report = await create_report(user_id, case["id"], pdf_path)
    return report

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
