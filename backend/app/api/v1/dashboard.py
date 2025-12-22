
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.services.dashboard_service import DashboardService

router = APIRouter()

@router.get("/status")
async def get_dashboard_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get Dashboard Status (Inner Weather, Flame, Sprint, Next Actions)
    """
    service = DashboardService(db)
    return await service.get_dashboard_status(user_id=current_user.id)
