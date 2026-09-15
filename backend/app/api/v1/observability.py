from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_current_active_superuser
from app.core.cache import cache_service
from app.models.user import User
from app.orchestration.run_ledger import RunLedgerStore
from app.services.achievement_reward_observability import AchievementRewardObservability

router = APIRouter(
    prefix="/admin/observability",
    tags=["observability"],
    dependencies=[Depends(get_current_active_superuser)],
)


@router.get("/runs/{trace_id}")
async def get_run_ledger(trace_id: str, _: User = Depends(get_current_active_superuser)):
    if not cache_service.redis:
        raise HTTPException(status_code=503, detail="Redis unavailable")
    summary = await RunLedgerStore.load_summary(cache_service.redis, trace_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Trace not found")
    events = await RunLedgerStore.load_events(cache_service.redis, trace_id)
    return {
        "trace_id": trace_id,
        "summary": summary,
        "events": events,
        "event_count": len(events),
    }


@router.get("/responses/{response_id}")
async def get_run_ledger_by_response(response_id: str, _: User = Depends(get_current_active_superuser)):
    if not cache_service.redis:
        raise HTTPException(status_code=503, detail="Redis unavailable")
    trace_id = await RunLedgerStore.get_trace_id_for_response(cache_service.redis, response_id)
    if not trace_id:
        raise HTTPException(status_code=404, detail="Response trace not found")
    summary = await RunLedgerStore.load_summary(cache_service.redis, trace_id)
    events = await RunLedgerStore.load_events(cache_service.redis, trace_id)
    return {
        "trace_id": trace_id,
        "response_id": response_id,
        "summary": summary,
        "events": events,
        "event_count": len(events),
    }


# route-tier: internal
@router.get("/achievement-photon-compensations")
async def get_achievement_photon_compensations(
    limit: int = Query(default=20, ge=1, le=100),
    _: User = Depends(get_current_active_superuser),
):
    return await AchievementRewardObservability.get_dashboard_payload(limit=limit)
