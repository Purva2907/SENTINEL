from fastapi import APIRouter, Depends
from auth.jwt import get_current_user
from database.repository import get_analytics

router = APIRouter()

@router.get("/")
async def get_dashboard_stats(current_user: dict = Depends(get_current_user)):
    stats = await get_analytics(current_user["id"])
    return stats
