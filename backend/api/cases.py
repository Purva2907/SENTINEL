from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from auth.jwt import get_current_user
from database.repository import create_case, get_case, list_cases

router = APIRouter()

class CaseRequest(BaseModel):
    title: str
    description: str = ""
    status: str = "Active"
    analysis_data: dict

@router.post("")
async def save_case(req: CaseRequest, current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    analysis_data = req.analysis_data
    
    case_data = {
        "user_id": user_id,
        "title": req.title,
        "description": req.description,
        "status": req.status,
        "document_type": analysis_data.get('classification', 'Unknown'),
        "risk_score": analysis_data.get('risk_score', 0),
        "classification": analysis_data.get('classification', 'Unknown')
    }
    
    case = await create_case(case_data, analysis_data)
    return {"message": "Case saved successfully", "case": case}

@router.get("")
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
