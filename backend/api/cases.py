from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional, Any, List
import json
from auth.jwt import get_current_user
from database.repository import (
    create_case, get_case, list_cases, create_case_note,
    verify_case_custody, add_case_timeline_event, update_case_status
)
from forensic.fingerprint import (
    extract_document_fingerprint, calculate_cosine_similarity, find_shared_forensic_signals
)

router = APIRouter()

class CaseRequest(BaseModel):
    title: str
    description: str = ""
    status: str = "Active"
    analysis_data: dict
    document_type: Optional[str] = None
    risk_score: Optional[int] = None
    classification: Optional[str] = None

@router.post("")
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
    
    # Ensure fingerprint is present in analysis_data
    if "fingerprint" not in analysis_data:
        analysis_data["fingerprint"] = extract_document_fingerprint(analysis_data)
        
    case_data = {
        "user_id": user_id,
        "title": req.title,
        "description": req.description,
        "status": req.status or "Active",
        "document_type": document_type,
        "risk_score": risk_score,
        "classification": classification,
        "investigator_name": current_user.get("name") or "Investigator"
    }
    
    case = await create_case(case_data, analysis_data)
    return {"message": "Case saved successfully", "case": case}

@router.get("")
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

class StatusUpdateRequest(BaseModel):
    status: str

@router.patch("/{case_id}/status")
async def change_case_status(case_id: str, req: StatusUpdateRequest, current_user: dict = Depends(get_current_user)):
    case = await get_case(current_user["id"], case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    inv_name = current_user.get("name") or "Investigator"
    await update_case_status(current_user["id"], case_id, req.status, inv_name)
    return {"success": True, "message": f"Case status updated to '{req.status}'"}

class NoteRequest(BaseModel):
    text: str

@router.post("/{case_id}/notes")
async def add_note(case_id: str, req: NoteRequest, current_user: dict = Depends(get_current_user)):
    case = await get_case(current_user["id"], case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
        
    investigator_name = current_user.get("name") or current_user.get("username", "Investigator")
    note = await create_case_note(current_user["id"], case['id'], req.text, investigator_name)
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
            pct = int(round(sim * 100))
            if pct >= 40:  # Minimum threshold for similarity report
                shared = find_shared_forensic_signals(target_case, other_full)
                similar_matches.append({
                    "id": other_full.get("id"),
                    "case_id": other_full.get("case_id"),
                    "title": other_full.get("title", "Untitled Case"),
                    "document_type": other_full.get("document_type", "Document"),
                    "similarity_score": pct,
                    "similarity_label": f"{pct}% Forensic Similarity",
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
