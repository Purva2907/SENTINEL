from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from typing import Optional
from datetime import datetime, timezone
import os
import uuid

from auth.jwt import get_current_user
from database.repository import create_report, get_report, list_reports, get_case, create_case
from reports.pdf_report import generate_pdf
from forensic.pipeline import process_document
from forensic.evidence import ingest_evidence, sanitize_custody_for_client

router = APIRouter()

UPLOAD_DIR = os.getenv("UPLOAD_DIR", os.path.join(os.path.dirname(__file__), "..", "..", "data", "uploads"))
os.makedirs(UPLOAD_DIR, exist_ok=True)

def generate_dynamic_report_id() -> str:
    year = datetime.now(timezone.utc).year
    return f"RPT-{year}-{str(uuid.uuid4().hex)[:4].upper()}"

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

    try:
        file_bytes = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read upload stream: {str(e)}")

    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # 1. Centralized evidence ingestion (validates image content, SHA-256, safe storage)
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
        raise HTTPException(status_code=400, detail=f"Evidence intake rejected: {str(e)}")

    try:
        # 2. Execute forensic screening pipeline
        result = process_document(file_path)
        result["chain_of_custody"] = custody

        # 3. Extract risk metrics
        risk_score = int(result.get("risk_score", 0))
        classification = result.get("classification", "Likely Authentic")
        doc_type = document_type or result.get("document_type") or "Aadhaar-like"
        safe_name = custody.get("original_filename", file.filename)
        case_title = title.strip() if title and title.strip() else f"Direct Intake: {safe_name}"
        case_desc = description.strip() if description and description.strip() else f"Automated forensic report generated from file upload: {safe_name}"

        # 4. Create case entry with full custody data
        case_data = {
            "user_id": current_user["id"],
            "title": case_title,
            "description": case_desc,
            "document_type": doc_type,
            "status": "Active",
            "risk_score": risk_score,
            "classification": classification,
            "evidence_id": custody.get("evidence_id"),
            "sha256_hash": custody.get("sha256_hash"),
            "file_path": file_path,
            "file_size": custody.get("file_size"),
            "mime_type": custody.get("mime_type"),
            "investigator_name": current_user.get("name") or "Investigator"
        }
        case = await create_case(case_data, result)

        # Attach analysis so PDF generator has full evidence log
        case["analysis"] = result

        # 5. Generate unique report PDF with dynamic UTC year
        report_id = generate_dynamic_report_id()
        pdf_path = generate_pdf(case, current_user, report_id=report_id)
        if not os.path.exists(pdf_path):
            raise HTTPException(status_code=500, detail="PDF generation failed")

        # 6. Persist report record
        report = await create_report(current_user["id"], case.get("case_id", case["id"]), pdf_path, report_id=report_id)

        # Sanitize client representation (prevent path disclosure)
        client_case = dict(case)
        client_case.pop("file_path", None)
        if "chain_of_custody" in client_case:
            client_case["chain_of_custody"] = sanitize_custody_for_client(client_case["chain_of_custody"])

        client_report = dict(report)
        client_report.pop("file_path", None)

        return {
            "status": "success",
            "message": "Forensic report created successfully",
            "report": client_report,
            "case": client_case,
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

    report_id = generate_dynamic_report_id()
    pdf_path = generate_pdf(case, current_user, report_id=report_id)
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=500, detail="PDF generation failed")

    report = await create_report(user_id, case.get("case_id", case["id"]), pdf_path, report_id=report_id)
    client_report = dict(report)
    client_report.pop("file_path", None)
    return client_report

@router.get("")
@router.get("/")
async def get_reports_list(current_user: dict = Depends(get_current_user)):
    reports = await list_reports(current_user["id"])
    clean_reports = []
    for r in reports:
        cr = dict(r)
        cr.pop("file_path", None)
        clean_reports.append(cr)
    return {"reports": clean_reports}

@router.get("/{report_id}/download")
async def download_report(report_id: str, current_user: dict = Depends(get_current_user)):
    report = await get_report(current_user["id"], report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    if not os.path.exists(report["file_path"]):
        raise HTTPException(status_code=404, detail="Report file missing")

    return FileResponse(report["file_path"], media_type="application/pdf", filename=f"{report['report_id']}.pdf")
