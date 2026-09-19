from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user, get_db
from app.core.cache import cache_service
from app.models.user import User
from app.services.directive_audit_service import RecentDirectiveAuditService

router = APIRouter()


# route-tier: authed
@router.get("/recent-directives", response_model=dict[str, Any])
async def get_recent_directives(
    limit: int = Query(default=20, ge=1, le=50),
    directive_type: str | None = Query(default=None, description="Filter by canonical or display directive type"),
    hours: int | None = Query(default=None, ge=1, le=24 * 90, description="Only include directives in this window"),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Return recent Causal Control directive decisions for the current user."""
    redis = cache_service.redis
    if redis is None:
        return {"data": [], "meta": {"total": 0, "limit": limit}}

    entries = await RecentDirectiveAuditService(redis).list_recent_directives(
        user_id=str(current_user.id),
        limit=limit,
        directive_type=directive_type,
        hours=hours,
    )
    return {
        "data": entries,
        "meta": {
            "total": len(entries),
            "limit": limit,
            "directive_type": directive_type,
            "hours": hours,
        },
    }


# route-tier: authed
@router.get("/understanding-depth", response_model=dict[str, Any])
async def get_understanding_depth(
    days: int = Query(default=7, ge=7, le=30, description="Trend window: 7 or 30 days"),
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
) -> dict[str, Any]:
    """Return the daily understanding-depth baseline trend for the current user.

    数据飞轮 MVP：每日离线聚合的"越用越懂用户"0-1 合成分（understanding_depth_daily），
    含近 7/30 天趋势与各维度分量（memory_injection/personalization/non_correction/
    non_repeat）。无活动日不落行，前端按日期补零即可。
    """
    from app.services.understanding_depth_metric_service import UnderstandingDepthMetricService

    window = 30 if days >= 30 else 7
    service = UnderstandingDepthMetricService(db)
    rows = await service.get_trend(user_id=current_user.id, days=window)
    data = [
        {
            "date": row.metric_date.isoformat(),
            "score": row.score,
            "components": row.components or {},
            "context_pack_runs": row.context_pack_runs,
            "chat_turns": row.chat_turns,
        }
        for row in rows
    ]
    latest = data[-1] if data else None
    return {
        "data": data,
        "meta": {
            "window_days": window,
            "days": days,
            "total": len(data),
            "latest": latest,
            "definition_version": "v0.1",
        },
    }
