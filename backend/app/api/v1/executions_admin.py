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
