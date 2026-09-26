from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
import json

from auth.jwt import get_current_user
from database.repository import (
    create_case, get_case, list_cases, create_case_note, get_case_notes,
    verify_case_custody, add_case_timeline_event, update_case_status
)
from forensic.fingerprint import (
    extract_document_fingerprint,
    calculate_cosine_similarity,
    find_shared_forensic_signals
)
from forensic.evidence import sanitize_custody_for_client

router = APIRouter()

def sanitize_case_for_client(case: dict) -> dict:
    if not case or not isinstance(case, dict):
        return case
    c = dict(case)
    c.pop("file_path", None)
    if "chain_of_custody" in c and isinstance(c["chain_of_custody"], dict):
        c["chain_of_custody"] = sanitize_custody_for_client(c["chain_of_custody"])
    return c

class CaseCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    document_type: Optional[str] = Field(None, max_length=100)
    status: Optional[str] = Field(default="Active")
    risk_score: Optional[int] = None
    classification: Optional[str] = None
    analysis: Optional[dict] = None
    analysis_data: Optional[dict] = None

    @field_validator("status")
    @classmethod
    def validate_initial_status(cls, v: Optional[str]) -> str:
        if not v:
            return "Active"
        allowed = {"Active", "Under Review", "Closed"}
        if v not in allowed:
            raise ValueError(f"Invalid status '{v}'. Allowed: {', '.join(allowed)}")
        return v

@router.post("")
@router.post("/")
async def create_new_case(req: CaseCreateRequest, current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    analysis_data = req.analysis or req.analysis_data or {}
    
    risk_score = req.risk_score if req.risk_score is not None else int(analysis_data.get("risk_score", 0))
    classification = req.classification or analysis_data.get("classification", "Unknown")
    doc_type = req.document_type or analysis_data.get("document_type", "Unknown")

    case_data = {
        "user_id": user_id,
        "title": req.title.strip(),
        "description": req.description.strip() if req.description else "",
        "document_type": doc_type,
        "status": req.status or "Active",
        "risk_score": risk_score,
        "classification": classification,
        "investigator_name": current_user.get("name") or "Investigator"
    }

    case = await create_case(case_data, analysis_data)
    return {"message": "Case created successfully", "case": sanitize_case_for_client(case)}

@router.get("")
@router.get("/")
async def get_cases(current_user: dict = Depends(get_current_user)):
    cases = await list_cases(current_user["id"])
    return {"cases": [sanitize_case_for_client(c) for c in cases]}

@router.get("/{case_id}")
async def get_single_case(case_id: str, current_user: dict = Depends(get_current_user)):
    case = await get_case(current_user["id"], case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return sanitize_case_for_client(case)

class StatusUpdateRequest(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        allowed = {"Active", "Under Review", "Closed"}
        clean = (v or "").strip()
        if clean not in allowed:
            raise ValueError(f"Invalid status '{v}'. Allowed statuses: {', '.join(allowed)}")
        return clean

@router.patch("/{case_id}/status")
async def change_case_status(case_id: str, req: StatusUpdateRequest, current_user: dict = Depends(get_current_user)):
    case = await get_case(current_user["id"], case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    inv_name = current_user.get("name") or "Investigator"
    try:
        await update_case_status(current_user["id"], case_id, req.status, inv_name)
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    return {"success": True, "message": f"Case status updated to '{req.status}'"}

class NoteRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        clean = (v or "").strip()
        if not clean:
            raise ValueError("Note text cannot be empty or whitespace only.")
        return clean

@router.post("/{case_id}/notes")
async def add_note(case_id: str, req: NoteRequest, current_user: dict = Depends(get_current_user)):
    case = await get_case(current_user["id"], case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
        
    investigator_name = current_user.get("name") or current_user.get("username", "Investigator")
    try:
        note = await create_case_note(current_user["id"], case['id'], req.text, investigator_name)
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    return {"message": "Note added", "note": note}

# --- EVIDENCE CHAIN OF CUSTODY VERIFICATION ---
@router.get("/{case_id}/verify-custody")
async def verify_custody(case_id: str, current_user: dict = Depends(get_current_user)):
    """
    Cryptographic Evidence Chain of Custody Integrity Check.
    Re-reads stored evidence bytes, computes SHA-256 digest, and asserts integrity.
    Does NOT claim identity authenticity; verifies that stored evidence bytes have not been altered.
    """
    investigator_name = current_user.get("name") or "Investigator"
    res = await verify_case_custody(current_user["id"], case_id, investigator_name)
    if not res.get("success") and res.get("status") == "NOT_FOUND":
        raise HTTPException(status_code=404, detail="Case not found")
    return res

# --- SIMILAR CASE DETECTION ---
@router.get("/{case_id}/similar")
async def get_similar_cases(case_id: str, current_user: dict = Depends(get_current_user)):
    """
    Finds archived investigations sharing measurable forensic characteristics with this document.
    Compares normalized fingerprint vectors; excludes the current case; strictly scopes to user's authorized docket.
    Canonical contract: similarity_score is returned on a 0-100 percentage scale (e.g. 91.0).
    """
    target_case = await get_case(current_user["id"], case_id)
    if not target_case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Extract target vector
    target_fp = target_case.get("fingerprint") or {}
    target_vec = target_fp.get("fingerprint_vector")
    if not target_vec:
        # Generate on the fly from analysis data
        target_fp = extract_document_fingerprint(target_case.get("analysis", {}))
        target_vec = target_fp.get("fingerprint_vector")

    all_cases = await list_cases(current_user["id"])
    target_uuid = target_case.get("id")
    target_human_id = target_case.get("case_id")

    similar_matches = []

    for other_summary in all_cases:
        other_uuid = other_summary.get("id")
        other_human_id = other_summary.get("case_id")
        # Exclude current case
        if other_uuid == target_uuid or (target_human_id and other_human_id == target_human_id):
            continue

        # Fetch other case details for fingerprint
        other_full = await get_case(current_user["id"], other_uuid)
        if not other_full:
            continue

        other_fp = other_full.get("fingerprint") or {}
        other_vec = other_fp.get("fingerprint_vector")
        if not other_vec:
            other_fp = extract_document_fingerprint(other_full.get("analysis", {}))
            other_vec = other_fp.get("fingerprint_vector")

        if target_vec and other_vec:
            sim = calculate_cosine_similarity(target_vec, other_vec)
            # Canonical representation: 0-100 percentage (e.g. 91.0)
            score_0_100 = round(float(sim * 100.0), 1)
            if score_0_100 >= 40.0:  # Minimum threshold for similarity report
                shared = find_shared_forensic_signals(target_case, other_full)
                similar_matches.append({
                    "id": other_full.get("id"),
                    "case_id": other_full.get("case_id"),
                    "title": other_full.get("title", "Untitled Case"),
                    "document_type": other_full.get("document_type", "Document"),
                    "similarity_score": score_0_100,
                    "similarity_label": f"{score_0_100}% Forensic Similarity",
                    "risk_score": other_full.get("risk_score", 0),
                    "classification": other_full.get("classification", "Unknown"),
                    "status": other_full.get("status", "Active"),
                    "shared_signals": shared,
                    "created_at": other_full.get("created_at")
                })

    similar_matches.sort(key=lambda x: x["similarity_score"], reverse=True)

    return {
        "success": True,
        "case_id": target_case.get("case_id"),
        "total_similar_found": len(similar_matches),
        "similar_cases": similar_matches[:6]
    }
