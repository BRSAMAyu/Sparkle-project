from fastapi import APIRouter

router = APIRouter()

@router.get("/daily")
async def get_daily_stats():
    return {"data": {}}
