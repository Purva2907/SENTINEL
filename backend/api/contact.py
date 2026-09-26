"""
FastAPI Contact Router & Bridge to Node.js Nodemailer Service
Provides /api/contact endpoint on FastAPI, forwarding requests to the
isolated Node.js Nodemailer microservice at http://localhost:5001.
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
import httpx
import os
import re
import logging

try:
    from backend.config import MAIL_SERVICE_URL, MAIL_SERVICE_PORT
except ImportError:
    from config import MAIL_SERVICE_URL, MAIL_SERVICE_PORT

router = APIRouter()
logger = logging.getLogger("sentinel.contact")

# Build target mail URL
_target_mail_url = MAIL_SERVICE_URL
if not _target_mail_url.endswith("/api/contact"):
    _target_mail_url = f"{_target_mail_url.rstrip('/')}/api/contact"

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

class ContactRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: str = Field(..., min_length=5, max_length=120)
    organization: str = Field(..., min_length=2, max_length=120)
    subject: str = Field(..., min_length=2, max_length=150)
    message: str = Field(..., min_length=10, max_length=3000)
    phone: str = Field(default="", max_length=30)

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        clean = v.strip()
        if not EMAIL_REGEX.match(clean):
            raise ValueError("Invalid email format")
        return clean

@router.post("/contact")
async def handle_contact_request(payload: ContactRequest, request: Request):
    """
    Validates and forwards contact/demo requests to the Node.js mail service.
    Returns real errors when mail service is offline, timing out, or failing.
    """
    clean_data = {
        "name": re.sub(r'<[^>]*>', '', payload.name).strip(),
        "email": payload.email.strip(),
        "organization": re.sub(r'<[^>]*>', '', payload.organization).strip(),
        "subject": re.sub(r'<[^>]*>', '', payload.subject).strip(),
        "message": re.sub(r'<[^>]*>', '', payload.message).strip(),
        "phone": re.sub(r'<[^>]*>', '', payload.phone).strip() if payload.phone else ""
    }

    client_ip = request.client.host if request.client else "127.0.0.1"

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            headers = {"x-forwarded-for": client_ip}
            res = await client.post(_target_mail_url, json=clean_data, headers=headers)
            if res.status_code == 200:
                return res.json()
            elif res.status_code == 429:
                raise HTTPException(status_code=429, detail="Rate limit exceeded. Please wait a few minutes before submitting again.")
            elif res.status_code in (500, 502, 503):
                raise HTTPException(status_code=res.status_code, detail="Mail service encountered an error. Please try again later.")
            else:
                data = res.json() if res.headers.get("content-type", "").startswith("application/json") else {}
                err_msg = data.get("error", "Unable to send message. Please try again.")
                raise HTTPException(status_code=res.status_code, detail=err_msg)
    except HTTPException:
        raise
    except httpx.TimeoutException:
        logger.error(f"Node mail service at {_target_mail_url} timed out.")
        raise HTTPException(status_code=504, detail="Mail service timed out. Please try again later.")
    except (httpx.ConnectError, httpx.NetworkError) as net_err:
        logger.error(f"Node mail service at {_target_mail_url} is unreachable: {net_err}")
        raise HTTPException(status_code=503, detail="Mail delivery service is currently offline. Please try again later.")
    except Exception as exc:
        logger.error(f"Unexpected error forwarding to mail service: {exc}")
        raise HTTPException(status_code=500, detail="Internal server error processing contact request.")
