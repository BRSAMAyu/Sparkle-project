"""Privacy-preserving community aggregate API."""
from __future__ import annotations

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.models.community_privacy import CommunityAggregateSignal
from app.models.user import User
from app.services.community_signal_bridge import CommunitySignalBridge

router = APIRouter(prefix="/community", tags=["community-aggregates"])


class CommunityAggregateResponse(BaseModel):
    computed: bool = True
    reason: str | None = None
    aggregates: list[dict] = Field(default_factory=list)


@router.get("/aggregates", response_model=CommunityAggregateResponse)
async def get_community_aggregates(
    group_id: UUID | None = Query(default=None),
    view: Literal["user", "admin"] = Query(default="user"),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> CommunityAggregateResponse:
    """Return anonymous community insight or admin aggregate details.

    Regular users only receive already-anonymized insight fields. Admin view
    includes privacy metadata and still never exposes individual rows.
    """
    admin_view = view == "admin"
    if admin_view and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="admin aggregate view required")

    bridge = CommunitySignalBridge(db)
    if group_id is not None:
        result = await bridge.build_group_task_completion_aggregate(
            group_id=group_id,
            requester_user_id=current_user.id,
        )
        if not result.get("computed", True):
            return CommunityAggregateResponse(
                computed=False,
                reason=str(result.get("reason") or "aggregate_unavailable"),
                aggregates=[],
            )
        if not admin_view:
            record = await bridge.db.get(CommunityAggregateSignal, UUID(result["id"]))
            if record is None:
                raise HTTPException(status_code=404, detail="aggregate disappeared before read")
            result = bridge._aggregate_to_dict(record, admin=False)  # noqa: SLF001 - canonical redaction path
        return CommunityAggregateResponse(aggregates=[result])

    aggregates = await bridge.list_aggregate_signals(
        viewer_user_id=current_user.id,
        admin=admin_view,
        limit=limit,
    )
    return CommunityAggregateResponse(aggregates=aggregates)
