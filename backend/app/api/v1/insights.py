from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user
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
