from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from chatbot.fallback import generate_fallback_response
from database.repository import get_case
from auth.jwt import get_current_user

router = APIRouter()

class ChatRequest(BaseModel):
    query: str
    context: dict = None
    case_id: str = None

@router.post("/")
async def chat_with_assistant(request: ChatRequest, current_user: dict = Depends(get_current_user)):
    ctx = request.context
    
    if request.case_id:
        case = await get_case(current_user["id"], request.case_id)
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
        ctx = case.get('analysis', {})
        
    if not ctx:
        ctx = {}

    answer = generate_fallback_response(request.query, ctx)
    return {"answer": answer}
