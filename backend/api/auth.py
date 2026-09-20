from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from auth.jwt import get_password_hash, verify_password, create_access_token, get_current_user
from database.repository import create_user, get_user_by_email

router = APIRouter()

class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

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
    user = await get_user_by_email(current_user["email"]) if "email" in current_user else None
    if not user:
        from database.repository import get_user_by_id
        user = await get_user_by_id(current_user["id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"id": user["id"], "name": user["name"], "email": user["email"], "role": user["role"], "created_at": user["created_at"]}

class ProfileUpdateRequest(BaseModel):
    name: str

@router.put("/me")
async def update_profile(req: ProfileUpdateRequest, current_user: dict = Depends(get_current_user)):
    from database.repository import update_user_profile, get_user_by_id
    await update_user_profile(current_user["id"], req.name)
    user = await get_user_by_id(current_user["id"])
    return {"id": user["id"], "name": user["name"], "email": user["email"], "role": user["role"], "created_at": user["created_at"]}
