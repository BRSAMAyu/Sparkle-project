import json

from fastapi import APIRouter, Depends, Query
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.cache import cache_service
from app.models.user import User
from app.services.growth_dashboard_service import GrowthDashboardService
from app.services.progress_narrative_service import ProgressNarrativeService
from app.signals.growth_chronicle import GrowthChronicleService

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


# route-tier: authed
@router.get("/return-case-file")
async def get_return_case_file(
    rebuild: bool = Query(False, description="Bypass cache and rebuild from chronicle"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    GOAL-011: Return case file for users who have been away.

    Returns the user's confirmed long-term insights, pending review items, and
    chronicle summary so the system can pick up where it left off without
    treating returning users as new users. Falls back to chronicle rebuild if
    Redis cache is missing.
    """
    redis = cache_service.redis
    user_key = f"spine:return_case_file:{current_user.id}:latest"

    if not rebuild and redis is not None:
        try:
            cached = await redis.get(user_key)
            if cached:
                payload = json.loads(cached if isinstance(cached, str) else cached.decode())
                payload["source"] = "cache"
                return payload
        except Exception:  # noqa: BLE001
            pass

    chronicle = GrowthChronicleService(redis, db_session=db)
    case = await chronicle.build_return_case_file(str(current_user.id))
    case["source"] = "rebuild"

    if redis is not None:
        try:
            await redis.set(user_key, json.dumps(case, default=str), ex=7 * 24 * 3600)
        except Exception:  # noqa: BLE001
            logger.warning("growth: cache write failed for user_key=%s", user_key, exc_info=True)

    return case
