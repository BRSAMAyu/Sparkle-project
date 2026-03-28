"""Admin endpoints for OpenClaw execution infrastructure."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_superuser, get_db
from app.api.v1.executions import (
    ExecutionNodeResponse,
    ExecutionQualitySummaryResponse,
    ExecutionQualityVariantResponse,
)
from app.services.execution_profile_service import ExecutionProfileService
from app.services.execution_service import ExecutionService

router = APIRouter(
    prefix="/admin/executions",
    tags=["executions-admin"],
    dependencies=[Depends(get_current_active_superuser)],
)


class AdminExecutionHealthResponse(BaseModel):
    openclaw_enabled: bool
    gateway_url: str | None = None
    transport: str | None = None
    ws_url: str | None = None
    reachable: bool
    supports_approvals: bool
    ingestion_layer: str
    connected_nodes: int
    supports_nodes: bool
    supports_templates: bool
    supports_quality_loop: bool


class AdminExecutionDashboardResponse(BaseModel):
    total_executions: int
    success_rate: float
    connected_nodes: int
    trust_distribution: dict[str, int]
    template_distribution: list[list[str | int]]
    by_type: dict[str, dict[str, float | int]]
    approval_request_count: int
    delegation_trend: str


@router.get("/health", response_model=AdminExecutionHealthResponse)
async def execution_admin_health(
    db: AsyncSession = Depends(get_db),
):
    service = ExecutionService(db=db)
    return AdminExecutionHealthResponse(**(await service.get_health()))


@router.get("/nodes", response_model=list[ExecutionNodeResponse])
async def list_execution_nodes(
    connected_only: bool = True,
    last_connected: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    service = ExecutionService(db=db)
    nodes = await service.list_nodes(connected_only=connected_only, last_connected=last_connected)
    return [ExecutionNodeResponse(**node) for node in nodes]


@router.get("/quality/summary", response_model=ExecutionQualitySummaryResponse)
async def execution_quality_summary(
    db: AsyncSession = Depends(get_db),
):
    service = ExecutionService(db=db)
    summary = await service.get_quality_summary()
    variants = [
        ExecutionQualityVariantResponse(**variant)
        for variant in summary.get("variants", [])
    ]
    return ExecutionQualitySummaryResponse(
        experiment_id=summary.get("experiment_id"),
        experiment_name=summary.get("experiment_name", "openclaw_execution_strategy_v1"),
        status=summary.get("status", "missing"),
        sample_size_collected=int(summary.get("sample_size_collected", 0)),
        variants=variants,
    )


@router.get("/dashboard", response_model=AdminExecutionDashboardResponse)
async def execution_dashboard(
    days: int = 30,
    db: AsyncSession = Depends(get_db),
):
    service = ExecutionService(db=db)
    health = await service.get_health()
    profile = await ExecutionProfileService(db).get_execution_profile_for_all_users(days=days)
    return AdminExecutionDashboardResponse(
        total_executions=int(profile.get("total_executions", 0)),
        success_rate=float(profile.get("success_rate", 0.0)),
        connected_nodes=int(health.get("connected_nodes", 0)),
        trust_distribution=dict(profile.get("trust_distribution", {})),
        template_distribution=list(profile.get("top_templates", [])),
        by_type=dict(profile.get("by_type", {})),
        approval_request_count=int(profile.get("approval_request_count", 0)),
        delegation_trend=str(profile.get("delegation_trend", "stable")),
    )
