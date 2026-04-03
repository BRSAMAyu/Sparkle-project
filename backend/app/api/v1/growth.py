from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.services.growth_dashboard_service import GrowthDashboardService

router = APIRouter()


@router.get("/dashboard")
async def get_growth_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the focused growth snapshot used by the home experience."""
    service = GrowthDashboardService(db)
    return await service.build_snapshot(current_user.id, user=current_user)
