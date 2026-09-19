from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api import analyze, auth, cases, reports, chatbot, analytics
from database.repository import init_db

app = FastAPI(
    title="SENTINEL API",
    description="AI-Powered Document Forensics API",
    version="1.0.0"
)

# CORS config
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For hackathon demo
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    await init_db()

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(analyze.router, prefix="/api", tags=["analyze"])
app.include_router(cases.router, prefix="/api/cases", tags=["cases"])
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])
app.include_router(chatbot.router, prefix="/api/chat", tags=["chat"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])

@app.get("/api/health")
def health_check():
    from database.repository import backend as db_backend
    return {"status": "ok", "message": "SENTINEL API is running", "database": db_backend or "initializing"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
