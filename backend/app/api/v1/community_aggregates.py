from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_superuser, get_current_user
from app.db.session import get_db
from app.models.community_privacy import CommunityAggregateSignal, PrivacyBudgetLedger
from app.models.user import User
from app.services.community_signal_bridge import CommunitySignalBridge

router = APIRouter(prefix="/community/aggregates", tags=["community-aggregates"])


class CommunityAggregateResponse(BaseModel):
    signal_id: str
    cohort_key: str
    cohort_criteria: dict[str, Any]
    signal_type: str
    stat_name: str
    cohort_size: int
    min_cohort_size: int
    privacy_tier: str
    pattern: dict[str, Any]
    observation: dict[str, Any]
    privacy_cost: float
    status: str
    generated_at: datetime


class CommunityAggregateAnalyzeRequest(BaseModel):
    cohort_criteria: dict[str, str] = Field(default_factory=dict)
    stat_name: str = "avg_completion_rate"
    query_type: str = "pattern_mining"
    signal_type: str = "community_cohort_pattern"
    values: list[float | dict[str, Any]]


# route-tier: authed
@router.get("", response_model=list[CommunityAggregateResponse])
async def list_community_aggregates(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser),
    signal_type: str | None = Query(default=None),
    status: str = Query(default="candidate"),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[CommunityAggregateResponse]:
    """Admin aggregate view.

    Rows are already anonymized; this endpoint still requires superuser access
    because it exposes platform-level aggregate governance state.
    """
    _ = current_user
    stmt = (
        select(CommunityAggregateSignal)
        .where(CommunityAggregateSignal.deleted_at.is_(None), CommunityAggregateSignal.status == status)
        .order_by(desc(CommunityAggregateSignal.generated_at))
        .limit(limit)
    )
    if signal_type:
        stmt = stmt.where(CommunityAggregateSignal.signal_type == signal_type)
    rows = (await db.execute(stmt)).scalars().all()
    return [_aggregate_response(row) for row in rows]


# route-tier: authed
@router.get("/insights", response_model=list[CommunityAggregateResponse])
async def list_my_anonymous_community_insights(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    signal_type: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
) -> list[CommunityAggregateResponse]:
    """User-visible anonymous insights.

    The user sees only candidate aggregate observations that can be corrected or
    ignored. No raw contributor data is exposed.
    """
    bridge = CommunitySignalBridge(db)
    if not await bridge._community_intelligence_enabled(current_user.id):
        return []
    since = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=14)
    stmt = (
        select(CommunityAggregateSignal)
        .where(
            CommunityAggregateSignal.deleted_at.is_(None),
            CommunityAggregateSignal.status == "candidate",
            CommunityAggregateSignal.generated_at >= since,
        )
        .order_by(desc(CommunityAggregateSignal.generated_at))
        .limit(limit)
    )
    if signal_type:
        stmt = stmt.where(CommunityAggregateSignal.signal_type == signal_type)
    rows = (await db.execute(stmt)).scalars().all()
    return [_aggregate_response(row) for row in rows]


# route-tier: authed
@router.post("/analyze")
async def analyze_community_aggregate(
    payload: CommunityAggregateAnalyzeRequest,
    *,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser),
) -> dict[str, Any]:
    """Admin/manual trigger for a privacy-preserving aggregate.

    Production collectors can call the bridge directly; this endpoint gives QA
    and admin workflows a controlled way to validate the complete privacy
    envelope.
    """
    result = await CommunitySignalBridge(db).build_privacy_preserving_cohort_signal(
        requester_user_id=current_user.id,
        cohort_criteria=payload.cohort_criteria,
        stat_name=payload.stat_name,
        contributor_values=payload.values,
        query_type=payload.query_type,
        signal_type=payload.signal_type,
    )
    await db.commit()
    return result


# route-tier: authed
@router.get("/budget-ledger")
async def list_privacy_budget_ledger(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser),
    subject_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[dict[str, Any]]:
    _ = current_user
    stmt = (
        select(PrivacyBudgetLedger)
        .where(PrivacyBudgetLedger.deleted_at.is_(None))
        .order_by(desc(PrivacyBudgetLedger.spent_at))
        .limit(limit)
    )
    if subject_id:
        stmt = stmt.where(PrivacyBudgetLedger.subject_id == subject_id)
    rows = (await db.execute(stmt)).scalars().all()
    return [
        {
            "subject_id": row.subject_id,
            "subject_type": row.subject_type,
            "query_type": row.query_type,
            "epsilon_spent": row.epsilon_spent,
            "max_epsilon": row.max_epsilon,
            "remaining_epsilon": row.remaining_epsilon,
            "window_key": row.window_key,
            "allowed": row.allowed,
            "denial_reason": row.denial_reason,
            "spent_at": row.spent_at,
        }
        for row in rows
    ]


def _aggregate_response(row: CommunityAggregateSignal) -> CommunityAggregateResponse:
    return CommunityAggregateResponse(
        signal_id=row.signal_id,
        cohort_key=row.cohort_key,
        cohort_criteria=row.cohort_criteria or {},
        signal_type=row.signal_type,
        stat_name=row.stat_name,
        cohort_size=row.cohort_size,
        min_cohort_size=row.min_cohort_size,
        privacy_tier=row.privacy_tier,
        pattern=row.pattern or {},
        observation=row.observation or {},
        privacy_cost=row.privacy_cost,
        status=row.status,
        generated_at=row.generated_at,
    )
