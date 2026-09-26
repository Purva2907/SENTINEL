import os
from datetime import datetime, timezone, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from database.repository import get_user_by_id

ALGORITHM = "HS256"

def get_secret_key() -> str:
    secret = os.getenv("JWT_SECRET")
    env_mode = os.getenv("ENV_MODE", "development").lower().strip()
    if not secret:
        if env_mode in ("production", "prod"):
            raise RuntimeError("CRITICAL: JWT_SECRET must be configured in production environment.")
        return "sentinel-dev-only-jwt-secret-not-for-production-use-2026"
    if len(secret) < 16 and env_mode in ("production", "prod"):
        raise RuntimeError("CRITICAL: JWT_SECRET must be at least 16 characters in production environment.")
    return secret

def get_access_token_expire_minutes() -> int:
    try:
        return int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
    except (ValueError, TypeError):
        return 1440

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=get_access_token_expire_minutes())
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, get_secret_key(), algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, get_secret_key(), algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await get_user_by_id(user_id)
    if not user:
        # Strictly reject users no longer active or present in the database.
        # Never fabricate a synthetic user identity from JWT claims.
        raise credentials_exception

    return user
