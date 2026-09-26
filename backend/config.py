"""
SENTINEL Centralized Environment & Configuration Module
Loads .env once at application startup and provides canonical, validated configuration.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Base paths
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

# Load .env file from project root or backend dir
env_path = PROJECT_ROOT / ".env"
if not env_path.exists():
    env_path = BASE_DIR / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

# Environment Mode
ENV_MODE = os.getenv("ENV_MODE", "development").strip().lower()
IS_PRODUCTION = ENV_MODE in ("production", "prod")

# Database Configuration
DATABASE_MODE = os.getenv("DATABASE_MODE", "sqlite").strip().lower()
MONGO_URL = os.getenv("MONGO_URL") or os.getenv("MONGODB_URI") or "mongodb://localhost:27017"
SQLITE_DB_PATH = os.getenv(
    "SQLITE_DB_PATH",
    str(PROJECT_ROOT / "data" / "sentinel.db")
)

# JWT Security Configuration
JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    if IS_PRODUCTION:
        raise RuntimeError("CRITICAL: JWT_SECRET environment variable must be set in production mode.")
    else:
        # Documented development fallback for non-production environments only
        JWT_SECRET = "sentinel-dev-only-jwt-secret-not-for-production-use-2026"
elif len(JWT_SECRET) < 16 and IS_PRODUCTION:
    raise RuntimeError("CRITICAL: JWT_SECRET must be at least 16 characters in production mode.")

ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
JWT_ALGORITHM = "HS256"

# Storage / Upload Directory
UPLOAD_DIR = os.getenv(
    "UPLOAD_DIR",
    str(PROJECT_ROOT / "data" / "uploads")
)
os.makedirs(UPLOAD_DIR, exist_ok=True)

# LLM API Keys & Model
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()

# Mail Service (Node.js Nodemailer Microservice)
MAIL_SERVICE_PORT = int(os.getenv("MAIL_SERVICE_PORT", "5001"))
MAIL_SERVICE_BASE_URL = os.getenv("MAIL_SERVICE_BASE_URL", f"http://localhost:{MAIL_SERVICE_PORT}").strip().rstrip('/')
MAIL_SERVICE_URL = os.getenv("MAIL_SERVICE_URL", f"{MAIL_SERVICE_BASE_URL}/api/contact").strip()
CONTACT_EMAIL = os.getenv("CONTACT_EMAIL", "investigations@sentinel-forensics.org").strip()
PASSWORD_RESET_TOKEN_EXPIRE_MINUTES = int(os.getenv("PASSWORD_RESET_TOKEN_EXPIRE_MINUTES", "15"))

# Application URLs & CORS Configuration
FRONTEND_URL = os.getenv("FRONTEND_URL", os.getenv("APP_BASE_URL", "http://localhost:3000")).strip().rstrip('/')
APP_BASE_URL = FRONTEND_URL
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", FRONTEND_URL).strip()

_raw_origins = os.getenv("ALLOWED_ORIGINS", f"{FRONTEND_ORIGIN},http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000,http://127.0.0.1:8000")
ALLOWED_ORIGINS = [orig.strip() for orig in _raw_origins.split(",") if orig.strip()]
if FRONTEND_ORIGIN and FRONTEND_ORIGIN not in ALLOWED_ORIGINS:
    ALLOWED_ORIGINS.append(FRONTEND_ORIGIN)
