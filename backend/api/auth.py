from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field, field_validator
from typing import Optional
import re
import secrets
import hashlib
import datetime
import time
import httpx
import logging
from collections import defaultdict

from auth.jwt import get_password_hash, verify_password, create_access_token, get_current_user
from database.repository import (
    create_user, get_user_by_email, get_user_by_id, update_user_profile, update_user_password,
    create_password_reset_token, get_password_reset_token, invalidate_user_reset_tokens, consume_password_reset_token
)
try:
    from backend.config import MAIL_SERVICE_BASE_URL, FRONTEND_URL, PASSWORD_RESET_TOKEN_EXPIRE_MINUTES
except ImportError:
    from config import MAIL_SERVICE_BASE_URL, FRONTEND_URL, PASSWORD_RESET_TOKEN_EXPIRE_MINUTES

router = APIRouter()
logger = logging.getLogger("sentinel.auth")

# In-memory rate limiting for password reset requests: max 3 per 15 minutes per IP or email
_reset_rate_limit_records = defaultdict(list)
RESET_RATE_LIMIT_WINDOW_SEC = 15 * 60
RESET_RATE_LIMIT_MAX_ATTEMPTS = 3

def check_reset_rate_limit(key: str) -> bool:
    now = time.time()
    cutoff = now - RESET_RATE_LIMIT_WINDOW_SEC
    attempts = [t for t in _reset_rate_limit_records[key] if t > cutoff]
    if len(attempts) >= RESET_RATE_LIMIT_MAX_ATTEMPTS:
        _reset_rate_limit_records[key] = attempts
        return False
    attempts.append(now)
    _reset_rate_limit_records[key] = attempts
    return True

def clear_reset_rate_limits():
    """Testing helper to clear rate limit store."""
    _reset_rate_limit_records.clear()

class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., min_length=3, max_length=150)
    password: str = Field(..., min_length=4)

class LoginRequest(BaseModel):
    email: str
    password: str

class ProfileUpdateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    department: Optional[str] = None
    badge_number: Optional[str] = None
    avatar: Optional[str] = None

    @field_validator("avatar")
    @classmethod
    def validate_avatar(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return ""
        val = v.strip()
        if not val:
            return ""
        if val.startswith("icon:"):
            parts = val[5:].split("|", 1)
            icon_name = parts[0].strip()
            if not re.match(r'^[a-zA-Z0-9_\-]+$', icon_name):
                raise ValueError("Invalid avatar icon identifier.")
            if len(val) > 250:
                raise ValueError("Avatar icon descriptor exceeds maximum length.")
            return val
        elif val.startswith("data:image/"):
            if not re.match(r'^data:image\/(jpeg|jpg|png|webp);base64,[A-Za-z0-9+/=]+$', val):
                raise ValueError("Invalid avatar image data format. Only JPEG, PNG, and WEBP base64 streams are accepted.")
            if len(val) > 350000:
                raise ValueError("Avatar payload exceeds maximum size limit (256KB).")
            return val
        else:
            raise ValueError("Avatar must be an approved icon descriptor ('icon:...') or valid base64 data URI ('data:image/...').")

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

@router.post("/register")
async def register(req: RegisterRequest):
    existing = await get_user_by_email(req.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
        
    hashed = get_password_hash(req.password)
    user = await create_user(req.name, req.email, hashed)
    
    return {"message": "User registered successfully"}

@router.post("/login")
async def login(req: LoginRequest):
    user = await get_user_by_email(req.email)
    if not user or not verify_password(req.password, user['password_hash']):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
        
    access_token = create_access_token(data={"sub": user["id"], "name": user["name"]})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return {
        "id": current_user["id"],
        "name": current_user.get("name", "Investigator"),
        "email": current_user.get("email", ""),
        "role": current_user.get("role", "investigator"),
        "department": current_user.get("department", "Forensic Screening Unit"),
        "badge_number": current_user.get("badge_number", f"SEN-{current_user['id'][:4].upper()}"),
        "avatar": current_user.get("avatar", ""),
        "created_at": current_user.get("created_at", "")
    }

@router.put("/profile")
async def update_profile(req: ProfileUpdateRequest, current_user: dict = Depends(get_current_user)):
    clean_name = req.name.strip()
    if not clean_name:
        raise HTTPException(status_code=400, detail="Name cannot be empty")
        
    updated = await update_user_profile(
        user_id=current_user["id"],
        name=clean_name,
        department=req.department.strip() if req.department else None,
        badge_number=req.badge_number.strip() if req.badge_number else None,
        avatar=req.avatar
    )
    
    return {
        "status": "success",
        "message": "Profile updated successfully",
        "user": {
            "id": updated["id"],
            "name": updated.get("name"),
            "email": updated.get("email"),
            "role": updated.get("role"),
            "department": updated.get("department"),
            "badge_number": updated.get("badge_number"),
            "avatar": updated.get("avatar", ""),
            "created_at": updated.get("created_at")
        }
    }

@router.post("/change-password")
async def change_password(req: ChangePasswordRequest, current_user: dict = Depends(get_current_user)):
    if len(req.new_password) < 6:
        raise HTTPException(status_code=400, detail="New password must be at least 6 characters")
        
    user_record = await get_user_by_id(current_user["id"])
    if not user_record or not verify_password(req.current_password, user_record.get("password_hash", "")):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
        
    new_hash = get_password_hash(req.new_password)
    await update_user_password(current_user["id"], new_hash)
    
    return {"status": "success", "message": "Password updated successfully"}

class ForgotPasswordRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=150)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        clean = v.strip().lower()
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', clean):
            raise ValueError("Invalid email format")
        return clean

class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=16, max_length=256)
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search(r'[A-Z]', v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r'[a-z]', v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r'[0-9]', v):
            raise ValueError("Password must contain at least one number")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>\-_+=\[\]~`/\\]', v):
            raise ValueError("Password must contain at least one special character")
        return v

@router.post("/forgot-password")
async def forgot_password(req: ForgotPasswordRequest, request: Request):
    """
    Initiates password recovery for an account without leaking whether the email exists.
    Generates a cryptographically random, single-use token with a 15-minute expiration,
    stores its SHA-256 hash in the database, and dispatches a reset link via Nodemailer.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    
    if not check_reset_rate_limit(f"ip:{client_ip}") or not check_reset_rate_limit(f"email:{req.email}"):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Maximum 3 password reset requests permitted per 15 minutes."
        )

    generic_response = {
        "success": True,
        "message": "If an account exists for this email, a password reset link has been sent."
    }

    user = await get_user_by_email(req.email)
    if not user:
        # Non-existent account: return generic response to prevent account enumeration
        return generic_response

    # Generate cryptographically secure one-time token
    raw_token = secrets.token_urlsafe(48)
    token_hash = hashlib.sha256(raw_token.encode('utf-8')).hexdigest()
    expires_at = (
        datetime.datetime.now(datetime.timezone.utc) + 
        datetime.timedelta(minutes=PASSWORD_RESET_TOKEN_EXPIRE_MINUTES)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Invalidate previous unused reset tokens for this user
    await invalidate_user_reset_tokens(user["id"])

    # Store hashed token in DB (never store plaintext)
    await create_password_reset_token(user["id"], token_hash, expires_at)

    reset_url = f"{FRONTEND_URL}/reset-password.html?token={raw_token}"

    # Forward to Nodemailer microservice
    try:
        mail_target = f"{MAIL_SERVICE_BASE_URL}/api/mail/password-reset"
        async with httpx.AsyncClient(timeout=8.0) as client:
            res = await client.post(
                mail_target,
                json={
                    "email": req.email,
                    "resetUrl": reset_url,
                    "recipientName": user.get("name", "")
                },
                headers={"x-forwarded-for": client_ip}
            )
            if res.status_code == 200:
                logger.info(f"Password reset email dispatched for account user_id={user['id'][:8]}...")
            elif res.status_code == 429:
                raise HTTPException(
                    status_code=429,
                    detail="Mail service rate limit exceeded. Please wait a few minutes before submitting again."
                )
            else:
                logger.error(f"Mail service returned {res.status_code} while sending password reset email.")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Mail delivery service is currently unavailable. Please try again later."
                )
    except HTTPException:
        raise
    except (httpx.ConnectError, httpx.NetworkError) as net_err:
        logger.error(f"Mail service connection error: {net_err}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Mail delivery service is currently offline. Please try again later."
        )
    except httpx.TimeoutException:
        logger.error("Mail service timed out sending password reset email.")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Mail delivery service timed out. Please try again later."
        )
    except Exception as exc:
        logger.error(f"Unexpected error sending reset email: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while dispatching the password reset email."
        )

    return generic_response

@router.post("/reset-password")
async def reset_password(req: ResetPasswordRequest):
    """
    Consumes a valid, non-expired password reset token and updates the user's password.
    Enforces password complexity, single-use token lifecycle, and immediate token invalidation.
    """
    token_hash = hashlib.sha256(req.token.strip().encode('utf-8')).hexdigest()
    token_record = await get_password_reset_token(token_hash)

    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset token."
        )

    if bool(token_record.get("used")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This password reset token has already been used."
        )

    expires_at_str = token_record.get("expires_at", "")
    try:
        expires_at = datetime.datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
        now = datetime.datetime.now(datetime.timezone.utc)
        if now > expires_at:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password reset token has expired."
            )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token expiration timestamp."
        )

    user_id = token_record.get("user_id")
    user = await get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account associated with this token no longer exists."
        )

    # Hash new password with existing bcrypt/passlib system
    new_hash = get_password_hash(req.new_password)
    await update_user_password(user_id, new_hash)
    await consume_password_reset_token(token_hash)

    logger.info(f"Password successfully reset for user_id={user_id[:8]}...")
    return {
        "success": True,
        "message": "Password reset successfully. You can now sign in with your new password."
    }
