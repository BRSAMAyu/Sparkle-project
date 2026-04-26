from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.cache import cache_service
from app.models.user import User
from app.services.growth_dashboard_service import GrowthDashboardService
from app.services.progress_narrative_service import ProgressNarrativeService

router = APIRouter()


# route-tier: authed
@router.get("/dashboard")
async def get_growth_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the focused growth snapshot used by the home experience."""
    service = GrowthDashboardService(db)
    return await service.build_snapshot(current_user.id, user=current_user)


# route-tier: authed
@router.get("/daily-context-line")
async def get_daily_context_line(
    force_refresh: bool = Query(False, description="Bypass today's cached line and regenerate"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return today's cached context-aware Home greeting line."""
    service = GrowthDashboardService(db)
    return await service.get_daily_context_line(
        current_user.id,
        user=current_user,
        force_refresh=force_refresh,
    )


# route-tier: authed
@router.get("/weekly-narrative")
async def get_weekly_growth_narrative(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return this week's cached growth story for the Insights page."""
    service = ProgressNarrativeService(db, redis=cache_service.redis, cache=cache_service)
    narrative = await service.get_weekly_narrative(current_user.id)
    return narrative.to_dict() if hasattr(narrative, "to_dict") else narrative


# route-tier: authed
@router.post("/weekly-narrative/generate")
async def generate_weekly_growth_narrative(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Regenerate this week's growth story for testing and manual refresh."""
    service = ProgressNarrativeService(db, redis=cache_service.redis, cache=cache_service)
    narrative = await service.get_weekly_narrative(current_user.id, force=True)
    return narrative.to_dict() if hasattr(narrative, "to_dict") else narrative
