from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional, Any
from auth.jwt import get_current_user
from database.repository import create_case, get_case, list_cases

router = APIRouter()

class CaseRequest(BaseModel):
    title: str
    description: str = ""
    status: str = "Active"
    analysis_data: dict
    document_type: Optional[str] = None
    risk_score: Optional[int] = None
    classification: Optional[str] = None

@router.post("/")
async def save_case(req: CaseRequest, current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    analysis_data = req.analysis_data
    
    # Priority: top-level explicit field -> analysis_data field -> fallback
    risk_score_raw = req.risk_score if req.risk_score is not None else analysis_data.get('risk_score')
    if risk_score_raw is None:
        risk_score_raw = analysis_data.get('score', 0)
    try:
        risk_score = int(risk_score_raw)
    except (ValueError, TypeError):
        risk_score = 0

    document_type = req.document_type or analysis_data.get('document_type') or 'Aadhaar-like'
    classification = req.classification or analysis_data.get('classification') or 'Likely Authentic'
    
    case_data = {
        "user_id": user_id,
        "title": req.title,
        "description": req.description,
        "status": req.status or "Active",
        "document_type": document_type,
        "risk_score": risk_score,
        "classification": classification
    }
    
    case = await create_case(case_data, analysis_data)
    return {"message": "Case saved successfully", "case": case}

@router.get("/")
async def get_cases(current_user: dict = Depends(get_current_user)):
    cases = await list_cases(current_user["id"])
    return {"cases": cases}

@router.get("/{case_id}")
async def get_single_case(case_id: str, current_user: dict = Depends(get_current_user)):
    case = await get_case(current_user["id"], case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case

class NoteRequest(BaseModel):
    text: str

@router.post("/{case_id}/notes")
async def add_note(case_id: str, req: NoteRequest, current_user: dict = Depends(get_current_user)):
    from database.repository import create_case_note
    
    case = await get_case(current_user["id"], case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
        
    investigator_name = current_user.get("name") or current_user.get("username", "Investigator")
    note = await create_case_note(current_user["id"], case_id, req.text, investigator_name)
    return {"message": "Note added", "note": note}
