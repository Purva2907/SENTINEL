from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import sys
import os
import re
import json
import httpx
from dotenv import load_dotenv

load_dotenv()

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from chatbot.fallback import generate_fallback_response
from database.repository import get_case, list_cases
from auth.jwt import get_current_user

router = APIRouter()

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str = Field(..., max_length=2000)
    history: List[ChatMessage] = []
    context: Dict[str, Any] = {}
    case_id: Optional[str] = None
    target_case_name: Optional[str] = None

SYSTEM_PROMPT = """You are SENTINEL AI, a world-class digital forensic investigation assistant and copilot.
You operate with the conversational fluency, politeness, and interactivity of ChatGPT, combined with deep technical forensics expertise.

Key Behaviors:
1. Conversational & Polite: If the user says "thank you", "thanks", "good job", or greets you, respond warmly, politely, and proactively suggest relevant forensic next steps or cross-case insights.
2. Multi-Case Awareness: You have access to the investigator's active cases docket. When the user asks about ANY other case (by title, document type like Passport/PAN/Voter ID, or Case ID like SC-2026-XXXX), summarize, explain, or compare that case against the current active case.
3. Deep Forensic Explainability: Explain risk scores, ELA splicing heatmaps, typography kerning/disparities, layout margins, OCR confidence, and QR payload status.
4. Summary on Demand: When the user asks for a summary or if token limits are referenced, produce a concise, high-impact executive dossier.
5. Integrity & Boundaries: Never claim official government authentication, UIDAI backend access, or 100% guaranteed authenticity/fakeness. Use terms like "forensic screening", "risk indicator", "tampering signal", and "manual review".
6. Docket Scoping: All case references must originate strictly from the investigator's authorized docket provided in context. If the user asks about a case that is not in their docket, state clearly: 'No matching case was found in your accessible docket.' Never invent or fabricate Case IDs or cases.

Format responses cleanly using Markdown bullet points, bold highlights, and tables where appropriate."""

async def call_gemini(api_key: str, system_prompt: str, history: List[ChatMessage], message: str, context_data: dict) -> Optional[str]:
    """Call Google Gemini Flash API (Free Tier with high RPM)."""
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        
        contents = []
        # Build prompt narrative
        intro_text = system_prompt + "\n\nFORENSIC CONTEXT:\n" + json.dumps(context_data, default=str)[:8000]
        contents.append({"role": "user", "parts": [{"text": intro_text}]})
        contents.append({"role": "model", "parts": [{"text": "Understood. I am SENTINEL AI, ready to assist with forensic investigations and case cross-referencing."}]})
        
        for msg in history[-8:]:
            role = "user" if msg.role == "user" else "model"
            contents.append({"role": role, "parts": [{"text": msg.content}]})
            
        contents.append({"role": "user", "parts": [{"text": message}]})

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json={
                "contents": contents,
                "generationConfig": {
                    "temperature": 0.35,
                    "maxOutputTokens": 800
                }
            })
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates and "content" in candidates[0]:
                    parts = candidates[0]["content"].get("parts", [])
                    if parts and "text" in parts[0]:
                        return parts[0]["text"]
            elif resp.status_code == 429:
                # Token or quota exhaustion specifically
                return "TOKEN_LIMIT_EXHAUSTED"
    except Exception:
        pass
    return None

async def call_groq(api_key: str, system_prompt: str, history: List[ChatMessage], message: str, context_data: dict) -> Optional[str]:
    """Call Groq Cloud API (Free Fast Tier)."""
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        messages = [
            {"role": "system", "content": system_prompt + "\n\nFORENSIC CONTEXT:\n" + json.dumps(context_data, default=str)[:8000]}
        ]
        for msg in history[-8:]:
            messages.append({"role": msg.role, "content": msg.content})
        messages.append({"role": "user", "content": message})

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                url,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": messages,
                    "max_tokens": 800,
                    "temperature": 0.3
                }
            )
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"]
            elif resp.status_code == 429:
                return "TOKEN_LIMIT_EXHAUSTED"
    except Exception:
        pass
    return None

@router.post("")
@router.post("/")
async def chat_with_assistant(request: ChatRequest, current_user: dict = Depends(get_current_user)):
    ctx = dict(request.context) if request.context else {}
    
    if not request.message or not request.message.strip():
        raise HTTPException(status_code=400, detail="Empty message")

    if len(request.history) > 20:
        request.history = request.history[-20:]

    # 1. Fetch user's cases for multi-case intelligence
    user_cases = await list_cases(current_user["id"])
    cases_lookup = {c.get("case_id"): c for c in user_cases if c.get("case_id")}
    for c in user_cases:
        if c.get("id"):
            cases_lookup[c.get("id")] = c

    # 2. Resolve Active Case
    if request.case_id:
        case = await get_case(current_user["id"], request.case_id)
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
        case_analysis = case.get('analysis', {})
        if isinstance(case_analysis, dict):
            ctx.update(case_analysis)
        ctx['case_id'] = case.get('case_id')
        ctx['case_title'] = case.get('title')
        ctx['status'] = case.get('status')
        ctx['risk_score'] = case.get('risk_score', ctx.get('risk_score', 0))
        ctx['classification'] = case.get('classification', ctx.get('classification', 'Unknown'))
        ctx['document_type'] = case.get('document_type', ctx.get('document_type', 'Unknown'))

    # 3. Detect if user is asking about ANOTHER case
    referenced_case = None
    query_lower = request.message.lower()
    
    # Check by target_case_name parameter if provided
    if request.target_case_name:
        for c in user_cases:
            if request.target_case_name.lower() in (c.get("title", "") + " " + c.get("case_id", "")).lower():
                referenced_case = await get_case(current_user["id"], c["id"])
                break
        if not referenced_case:
            # Check if it was asking about active case
            if not (ctx and request.target_case_name.lower() in (ctx.get("case_title", "") + " " + ctx.get("case_id", "")).lower()):
                return {
                    "success": True,
                    "response": "No matching case was found in your accessible docket.",
                    "source": "docket_scope"
                }

    # Check query for explicit Case ID (e.g. SC-2026-XXXX)
    case_id_match = re.search(r"\b(SC-\d{4}-[A-Z0-9]+)\b", request.message, re.IGNORECASE)
    if case_id_match:
        found_cid = case_id_match.group(1).upper()
        if found_cid in cases_lookup and (not request.case_id or found_cid != ctx.get('case_id')):
            referenced_case = await get_case(current_user["id"], cases_lookup[found_cid]["id"])
        elif (not ctx or ctx.get('case_id') != found_cid) and found_cid not in cases_lookup:
            return {
                "success": True,
                "response": "No matching case was found in your accessible docket.",
                "source": "docket_scope"
            }

    # Check query for document types or keywords matching another case
    if not referenced_case:
        for c in user_cases:
            cid = c.get("case_id")
            if cid and cid == ctx.get("case_id"):
                continue  # skip current active case
            title = c.get("title", "").lower()
            dtype = c.get("document_type", "").lower()
            
            # Match keywords
            if (dtype and dtype in query_lower) or (title and any(w in query_lower for w in title.split() if len(w) > 3)):
                referenced_case = await get_case(current_user["id"], c["id"])
                break

    # Build concise cases summary for context
    cases_summary = [
        {
            "case_id": c.get("case_id"),
            "title": c.get("title"),
            "document_type": c.get("document_type"),
            "risk_score": c.get("risk_score"),
            "classification": c.get("classification"),
            "status": c.get("status")
        }
        for c in user_cases
    ]

    llm_context = {
        "active_case": ctx if ctx else None,
        "referenced_case": {
            "title": referenced_case.get("title"),
            "case_id": referenced_case.get("case_id"),
            "document_type": referenced_case.get("document_type"),
            "risk_score": referenced_case.get("risk_score"),
            "classification": referenced_case.get("classification"),
            "status": referenced_case.get("status"),
            "evidence": referenced_case.get("analysis", {}).get("evidence", []) if referenced_case.get("analysis") else []
        } if referenced_case else None,
        "investigator_docket_cases": cases_summary
    }

    # 4. Check for Free / Configured LLM Providers
    def clean_api_key(key_name: str) -> Optional[str]:
        val = os.getenv(key_name)
        if not val:
            return None
        val = val.strip()
        if val.startswith("#") or not val:
            return None
        if " #" in val:
            val = val.split(" #")[0].strip()
        return val if len(val) >= 15 else None

    gemini_key = clean_api_key("GEMINI_API_KEY") or clean_api_key("LLM_API_KEY")
    groq_key = clean_api_key("GROQ_API_KEY")
    openai_key = clean_api_key("OPENAI_API_KEY")

    # Priority 1: Google Gemini Flash (Free Tier)
    if gemini_key:
        llm_reply = await call_gemini(gemini_key, SYSTEM_PROMPT, request.history, request.message, llm_context)
        if llm_reply == "TOKEN_LIMIT_EXHAUSTED":
            fallback_text = generate_fallback_response(request.message, ctx, user_cases, referenced_case)
            return {
                "success": True,
                "response": f"*(Notice: Token/quota limit reached. Generated comprehensive forensic summary below)*\n\n{fallback_text}",
                "source": "summary_fallback"
            }
        elif llm_reply:
            return {
                "success": True,
                "response": llm_reply,
                "source": "gemini"
            }

    # Priority 2: Groq Cloud (Free Tier)
    if groq_key:
        llm_reply = await call_groq(groq_key, SYSTEM_PROMPT, request.history, request.message, llm_context)
        if llm_reply == "TOKEN_LIMIT_EXHAUSTED":
            fallback_text = generate_fallback_response(request.message, ctx, user_cases, referenced_case)
            return {
                "success": True,
                "response": f"*(Notice: Token/quota limit reached. Generated comprehensive forensic summary below)*\n\n{fallback_text}",
                "source": "summary_fallback"
            }
        elif llm_reply:
            return {
                "success": True,
                "response": llm_reply,
                "source": "groq"
            }

    # Priority 3: OpenAI Async (if key provided)
    if openai_key and AsyncOpenAI:
        try:
            client = AsyncOpenAI(api_key=openai_key)
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            messages.append({"role": "system", "content": f"Forensic Context: {json.dumps(llm_context, default=str)[:8000]}"})
            for msg in request.history[-10:]:
                messages.append({"role": msg.role, "content": msg.content})
            messages.append({"role": "user", "content": request.message})

            response = await client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                messages=messages,
                max_tokens=600,
                temperature=0.3
            )
            return {
                "success": True,
                "response": response.choices[0].message.content,
                "source": "llm"
            }
        except Exception as e:
            err_status = getattr(e, "status_code", None)
            err_str = str(e).lower()
            if err_status == 429 or "429" in err_str or "quota" in err_str or "rate_limit" in err_str:
                fallback_text = generate_fallback_response(request.message, ctx, user_cases, referenced_case)
                return {
                    "success": True,
                    "response": f"*(Notice: Token/quota limit reached. Switched to autonomous forensic summary)*\n\n{fallback_text}",
                    "source": "summary_fallback"
                }
            # Other errors (401, 403, 5xx, timeouts) do not emit quota warning and fall through to local engine

    # 5. Local Autonomous Forensic Intelligence Engine (Zero Token / Offline / Instant)
    answer = generate_fallback_response(request.message, ctx, all_cases=user_cases, referenced_case=referenced_case)
    return {
        "success": True,
        "response": answer,
        "source": "fallback"
    }
