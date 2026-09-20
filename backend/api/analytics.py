from fastapi import APIRouter, Depends
from auth.jwt import get_current_user
from database.repository import get_analytics

router = APIRouter()

@router.get("/")
async def get_dashboard_stats(current_user: dict = Depends(get_current_user)):
    stats = await get_analytics(current_user["id"])
    if stats.get("total_investigations", 0) == 0:
        return {
            "total_investigations": 0,
            "average_risk": 0.0,
            "classification": {
                "likely_authentic": 0,
                "review_required": 0,
                "high_suspicion": 0
            },
            "document_types": {}
        }
    return stats
