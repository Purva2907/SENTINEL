from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import sys
import os
import json

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from chatbot.fallback import generate_fallback_response
from database.repository import get_case
from auth.jwt import get_current_user

router = APIRouter()

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str = Field(..., max_length=1000)
    history: List[ChatMessage] = []
    context: Dict[str, Any] = {}
    case_id: Optional[str] = None

SYSTEM_PROMPT = """You are SENTINEL AI, a forensic investigation assistant explaining document-forensics screening results.
Your role is to:
- explain evidence, risk scores, forensic signals, OCR, QR analysis, and image quality
- explain uncertainty and manual-review recommendations
- use ONLY the supplied SENTINEL context
- never invent forensic results
- clearly state when information is unavailable

NEVER claim:
- government authentication
- UIDAI database access
- PAN database access
- official verification
- 100% fake detection or 100% authenticity
- guaranteed detection

Use terms such as "forensic screening", "risk indicator", "evidence", "signal", "manual review", and "analysis result".
Be concise, professional, and analytical."""

@router.post("")
async def chat_with_assistant(request: ChatRequest, current_user: dict = Depends(get_current_user)):
    ctx = request.context
    
    if request.case_id:
        case = await get_case(current_user["id"], request.case_id)
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
        ctx = case.get('analysis', {})
        # Merge case level metadata if available
        ctx['case_title'] = case.get('title')
        ctx['status'] = case.get('status')
        
    if not ctx:
        ctx = {}

    api_key = os.getenv("OPENAI_API_KEY")
    
    # Validation constraints
    if len(request.history) > 20:
        request.history = request.history[-20:]
        
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Empty message")

    if api_key and OpenAI:
        try:
            client = OpenAI(api_key=api_key)
            
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            
            # Inject context
            if ctx:
                context_str = json.dumps(ctx, default=str)
                # truncate context if too large (safety)
                if len(context_str) > 10000:
                    context_str = context_str[:10000] + "... [truncated]"
                messages.append({"role": "system", "content": f"Current Forensic Context: {context_str}"})
            else:
                messages.append({"role": "system", "content": "No active forensic analysis is available. Instruct the user to upload a document or open a case."})
            
            for msg in request.history:
                messages.append({"role": msg.role, "content": msg.content})
                
            messages.append({"role": "user", "content": request.message})
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                max_tokens=500,
                temperature=0.3
            )
            
            return {
                "success": True,
                "response": response.choices[0].message.content,
                "source": "llm"
            }
        except Exception as e:
            # Fallback on LLM failure
            pass

    # Local Fallback Execution
    answer = generate_fallback_response(request.message, ctx)
    return {
        "success": True,
        "response": answer,
        "source": "fallback"
    }
