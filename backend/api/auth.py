from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional
from auth.jwt import get_password_hash, verify_password, create_access_token, get_current_user
from database.repository import create_user, get_user_by_email, get_user_by_id, update_user_profile, update_user_password

router = APIRouter()

class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class ProfileUpdateRequest(BaseModel):
    name: str
    department: Optional[str] = None
    badge_number: Optional[str] = None
    avatar: Optional[str] = None

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
