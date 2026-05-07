"""
Core: execution
Phase: plan
Stage: P2 — Scenario Pack REST API endpoints.

Read-only endpoints for built-in scenario packs (loaded from JSON manifests),
plus assignment and progress tracking for authenticated users.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User

router = APIRouter(prefix="/scenario-packs", tags=["scenario-packs"])

# Lazy-loaded singleton registry — loaded once on first access.
_registry = None


def _get_registry():
    global _registry
    if _registry is None:
        from app.scenario_packs.registry import load_default_registry
        _registry = load_default_registry()
    return _registry


# ── Response Models ────────────────────────────────────────────────────────


class PackSummary(BaseModel):
    id: str
    name: str
    version: str
    description: str
    horizon_days: int
    node_count: int
    goal_type: str = ""
    author: str = ""


class PackDetail(PackSummary):
    applicability_conditions: list[str] = []
    backbone_nodes: list[dict[str, Any]] = []
    readiness_criteria: dict[str, Any] = {}
    default_strategies: dict[str, str] = {}
    ux_mappings: dict[str, Any] = {}


class PackAssignRequest(BaseModel):
    goal_id: str = Field(min_length=1)


class PackAssignResponse(BaseModel):
    goal_id: str
    pack_id: str
    assigned: bool


class JourneyProgress(BaseModel):
    pack_id: str | None = None
    pack_name: str | None = None
    current_node: str | None = None
    current_node_index: int = 0
    total_nodes: int = 0
    day_number: int = 0
    horizon_days: int = 0
    is_on_backbone: bool = True


# ── Goal type → scenario pack mapping ─────────────────────────────────────

_GOAL_TYPE_PACK_MAP: dict[str, str] = {
    "exam": "exam_prep_14d@v1.0",
    "project": "project_sprint_7d@v1.0",
    "job_search": "job_search_14d@v1.0",
    "fitness": "fitness_foundation_14d@v1.0",
    "startup": "career_pivot_30d@v1.0",
}


def _best_pack_for_goal_type(goal_type: str) -> str | None:
    return _GOAL_TYPE_PACK_MAP.get(goal_type)


def _pack_horizon(manifest) -> int:
    profile = manifest.target_user_profile or {}
    return int(profile.get("horizon_days", 0))


# ── Endpoints ──────────────────────────────────────────────────────────────


@router.get("", response_model=list[PackSummary])
async def list_packs() -> list[PackSummary]:
    """List all built-in scenario packs (public, no auth required)."""
    registry = _get_registry()
    results: list[PackSummary] = []
    for manifest in registry.list():
        profile = manifest.target_user_profile or {}
        goal_type = str(profile.get("goal", ""))
        results.append(PackSummary(
            id=manifest.id,
            name=manifest.name,
            version=manifest.version,
            description=manifest.description,
            horizon_days=_pack_horizon(manifest),
            node_count=len(manifest.backbone_nodes),
            goal_type=goal_type,
            author=manifest.author,
        ))
    return results


@router.get("/{pack_id}", response_model=PackDetail)
async def get_pack(pack_id: str) -> PackDetail:
    """Get full detail for a single built-in scenario pack."""
    registry = _get_registry()
    manifest = registry.get_by_id(pack_id)
    if manifest is None:
        raise HTTPException(status_code=404, detail="Pack not found")
    profile = manifest.target_user_profile or {}
    goal_type = str(profile.get("goal", ""))
    return PackDetail(
        id=manifest.id,
        name=manifest.name,
        version=manifest.version,
        description=manifest.description,
        horizon_days=_pack_horizon(manifest),
        node_count=len(manifest.backbone_nodes),
        goal_type=goal_type,
        author=manifest.author,
        applicability_conditions=manifest.applicability_conditions,
        backbone_nodes=[_serialize_node(n) for n in manifest.backbone_nodes],
        readiness_criteria={k: _serialize_criterion(v) for k, v in manifest.readiness_criteria.items()},
        default_strategies=manifest.default_strategies,
        ux_mappings=manifest.ux_mappings,
    )


@router.post("/{pack_id}/assign", response_model=PackAssignResponse)
async def assign_pack(
    pack_id: str,
    payload: PackAssignRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PackAssignResponse:
    """Assign a scenario pack to a user's existing goal."""
    registry = _get_registry()
    manifest = registry.get_by_id(pack_id)
    if manifest is None:
        raise HTTPException(status_code=404, detail="Pack not found")

    from app.models.goal import Goal
    goal = await db.get(Goal, uuid.UUID(payload.goal_id))
    if goal is None or str(goal.user_id) != str(current_user.id):
        raise HTTPException(status_code=404, detail="Goal not found")

    goal.domain_pack_id = pack_id
    goal.source_metadata = goal.source_metadata or {}
    goal.source_metadata["scenario_pack_assigned_at"] = datetime.now(timezone.utc).isoformat()
    await db.flush()

    # Store initial journey state in Redis for progress tracking.
    try:
        from app.core.cache import cache_service
        first_node = manifest.backbone_nodes[0].node_id if manifest.backbone_nodes else ""
        state_key = f"spine:scenario_journey:{current_user.id}:{goal.id}"
        import json
        await cache_service.redis.set(
            state_key,
            json.dumps({
                "pack_id": pack_id,
                "current_node": first_node,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "is_on_backbone": True,
            }),
            ex=90 * 24 * 3600,
        )
    except Exception:
        logger.warning("assign_pack: redis state write failed", exc_info=True)

    await db.commit()
    return PackAssignResponse(goal_id=payload.goal_id, pack_id=pack_id, assigned=True)


@router.get("/progress/{goal_id}", response_model=JourneyProgress)
async def get_progress(
    goal_id: str,
    current_user: User = Depends(get_current_user),
) -> JourneyProgress:
    """Get the user's journey progress for a specific goal."""
    registry = _get_registry()

    try:
        from app.core.cache import cache_service
        import json
        state_key = f"spine:scenario_journey:{current_user.id}:{goal_id}"
        raw = await cache_service.redis.get(state_key)
        if raw is None:
            return JourneyProgress()
        state = json.loads(raw)
    except Exception:
        return JourneyProgress()

    pack_id = state.get("pack_id", "")
    manifest = registry.get_by_id(pack_id) if pack_id else None
    if manifest is None:
        return JourneyProgress(pack_id=pack_id)

    current_node = state.get("current_node", "")
    node_index = 0
    for idx, node in enumerate(manifest.backbone_nodes):
        if node.node_id == current_node:
            node_index = idx
            break

    # Calculate day number from started_at.
    day_number = 0
    started_at = state.get("started_at")
    if started_at:
        try:
            started = datetime.fromisoformat(started_at)
            day_number = (datetime.now(timezone.utc) - started).days + 1
        except (ValueError, TypeError):
            pass

    return JourneyProgress(
        pack_id=pack_id,
        pack_name=manifest.name,
        current_node=current_node,
        current_node_index=node_index,
        total_nodes=len(manifest.backbone_nodes),
        day_number=day_number,
        horizon_days=_pack_horizon(manifest),
        is_on_backbone=state.get("is_on_backbone", True),
    )


# ── Helpers ────────────────────────────────────────────────────────────────


def _serialize_node(node) -> dict[str, Any]:
    return {
        "node_id": node.node_id,
        "node_persona": node.node_persona,
        "exit_conditions": node.exit_conditions,
        "neighbors": node.neighbors,
        "ux_mapping": node.ux_mapping,
    }


def _serialize_criterion(crit) -> dict[str, Any]:
    return {
        "signal_type": crit.signal_type,
        "minimum_confidence": crit.minimum_confidence,
        "required": crit.required,
    }
