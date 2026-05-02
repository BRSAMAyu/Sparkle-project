"""P4-RES Research Mode API — dashboard, proposals, and improvement metrics.

Production endpoints for the continuous improvement loop, serving stored
research dashboards and proposal data.
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.api.deps import get_current_user
from app.core.cache import cache_service
from app.models.user import User

router = APIRouter(prefix="/research", tags=["research"])


@router.get("/dashboard")
async def get_research_dashboard(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get the latest research dashboard snapshot for the current user.

    Returns aggregated P4 metrics: active experiments, completed experiments,
    evidence distribution, quality health, benchmark pass rate, marketplace
    statistics, community cohort data, and improvement loop metrics.
    """
    redis = cache_service.redis
    if redis is None:
        raise HTTPException(status_code=503, detail="Redis unavailable")

    key = f"spine:research_dashboard:{current_user.id}:latest"
    raw = await redis.get(key)
    if raw is None:
        return {
            "dashboard_id": "",
            "generated_at": "",
            "user_id": str(current_user.id),
            "note": "no_dashboard_yet",
            "active_experiments": 0,
            "completed_experiments": 0,
            "total_episodes_collected": 0,
            "total_users_reached": 0,
            "evidence_distribution": {},
            "average_evidence_grade": 0.0,
            "quality_health": "unknown",
            "quality_score": 0.0,
            "iron_law_violations": 0,
            "marketplace_cards": 0,
            "marketplace_adoptions": 0,
            "average_card_effectiveness": 0.0,
            "active_cohorts": 0,
            "cohort_members_total": 0,
            "federated_insights": 0,
            "benchmark_pass_rate": 0.0,
            "regression_scenarios": 0,
            "proposals_active": 0,
            "proposals_completed": 0,
            "proposals_promoted": 0,
            "total_proposals": 0,
            "total_conclusions": 0,
        }

    return json.loads(raw if isinstance(raw, str) else raw.decode())


@router.get("/gaps")
async def get_research_gaps(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get the latest detected research gaps for the current user."""
    redis = cache_service.redis
    if redis is None:
        raise HTTPException(status_code=503, detail="Redis unavailable")

    key = f"spine:research_gaps:{current_user.id}:latest"
    raw = await redis.get(key)
    if raw is None:
        return {"user_id": str(current_user.id), "gaps": [], "note": "no_gaps_detected"}

    gaps = json.loads(raw if isinstance(raw, str) else raw.decode())
    return {"user_id": str(current_user.id), "gaps": gaps if isinstance(gaps, list) else [gaps]}


@router.get("/proposals")
async def get_research_proposals(
    request: Request,
    current_user: User = Depends(get_current_user),
    status: str | None = Query(None, description="Filter by proposal status"),
) -> dict[str, Any]:
    """List research proposals from the latest dashboard snapshot."""
    redis = cache_service.redis
    if redis is None:
        raise HTTPException(status_code=503, detail="Redis unavailable")

    dashboard_key = f"spine:research_dashboard:{current_user.id}:latest"
    raw = await redis.get(dashboard_key)
    if raw is None:
        return {"user_id": str(current_user.id), "proposals": [], "total": 0}

    dashboard = json.loads(raw if isinstance(raw, str) else raw.decode())
    proposals = dashboard.get("proposals", [])
    if status:
        proposals = [p for p in proposals if p.get("status") == status]

    return {"user_id": str(current_user.id), "proposals": proposals, "total": len(proposals)}
