"""Executions API endpoints for OpenClaw integration."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.config import settings
from app.db.session import get_db
from app.models.execution_intent import ExecutionIntent
from app.models.execution_record import ExecutionRecord
from app.models.user import User
from app.services.execution_service import ExecutionService

router = APIRouter(prefix="/executions", tags=["executions"])


class HandoffRequest(BaseModel):
    """Task handoff payload."""

    goal: str | None = Field(default=None, description="Override execution goal")
    instructions: list[str] | None = Field(default=None, description="Additional constraints")
    policy: dict[str, Any] | None = Field(default=None, description="Policy override")
    success_criteria: dict[str, Any] | None = Field(default=None, description="Success criteria override")
    result_contract: dict[str, Any] | None = Field(default=None, description="Result contract override")


class HandbackRequest(BaseModel):
    """Hand back a delegated task to the user."""

    reason: str | None = Field(default=None, description="Optional reason")


class RejectResultRequest(BaseModel):
    """Reject an execution result and hand the task back."""

    reason: str | None = Field(default=None, description="Optional rejection reason")


class ExecutionIntentResponse(BaseModel):
    """Execution intent response payload."""

    id: str
    task_id: str
    plan_id: str | None
    execution_mode: str
    executor: str
    status: str
    trust_level: str
    external_run_id: str | None
    goal: str
    error_category: str | None
    error_message: str | None
    dispatched_at: str | None
    completed_at: str | None
    created_at: str | None


class ClassifyResponse(BaseModel):
    execution_mode: str
    target_env: str | None
    reason: str
    confidence: float
    risk_flags: list[str]


class ExecutionRecordResponse(BaseModel):
    id: str
    execution_intent_id: str
    trust_level: str
    quality_score: float | None
    parsed_output: dict | None
    artifacts: list[Any]
    duration_ms: int | None
    validation_passed: int | None
    validation_total: int | None
    approval_requested: int | None
    error_category: str | None
    error_message: str | None


def _intent_to_response(intent: ExecutionIntent) -> ExecutionIntentResponse:
    payload = intent.to_dict()
    return ExecutionIntentResponse(
        id=payload["id"],
        task_id=payload["task_id"],
        plan_id=payload["plan_id"],
        execution_mode=payload["execution_mode"],
        executor=payload["executor"],
        status=payload["status"],
        trust_level=payload["trust_level"],
        external_run_id=payload["external_run_id"],
        goal=payload["goal"],
        error_category=payload["error_category"],
        error_message=payload["error_message"],
        dispatched_at=payload["dispatched_at"],
        completed_at=payload["completed_at"],
        created_at=payload["created_at"],
    )


def _record_to_response(record: ExecutionRecord) -> ExecutionRecordResponse:
    payload = record.to_dict()
    return ExecutionRecordResponse(
        id=payload["id"],
        execution_intent_id=payload["execution_intent_id"],
        trust_level=payload["trust_level"],
        quality_score=payload["quality_score"],
        parsed_output=payload["parsed_output"],
        artifacts=payload["artifacts"],
        duration_ms=payload["duration_ms"],
        validation_passed=payload.get("validation_passed"),
        validation_total=payload.get("validation_total"),
        approval_requested=payload.get("approval_requested"),
        error_category=payload["error_category"],
        error_message=payload["error_message"],
    )


@router.get("/health")
async def execution_health(
    db: AsyncSession = Depends(get_db),
):
    service = ExecutionService(db=db)
    return await service.get_health()


@router.post("/tasks/{task_id}/classify", response_model=ClassifyResponse)
async def classify_task(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ExecutionService(db=db)
    try:
        decision = await service.classify_task(task_id=task_id, user_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return ClassifyResponse(
        execution_mode=decision.execution_mode.value,
        target_env=decision.target_env.value if decision.target_env else None,
        reason=decision.reason,
        confidence=decision.confidence,
        risk_flags=decision.risk_flags,
    )


@router.post("/tasks/{task_id}/handoff", response_model=ExecutionIntentResponse)
async def handoff_task(
    task_id: UUID,
    request: HandoffRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not settings.OPENCLAW_ENABLED:
        raise HTTPException(status_code=503, detail="OpenClaw integration is not enabled")

    service = ExecutionService(db=db)
    try:
        intent = await service.handoff_to_openclaw(
            task_id=task_id,
            user_id=current_user.id,
            goal=request.goal,
            instructions=request.instructions,
            policy=request.policy,
            success_criteria=request.success_criteria,
            result_contract=request.result_contract,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Execution failed: {str(exc)}") from exc

    return _intent_to_response(intent)


@router.get("/{intent_id}", response_model=ExecutionIntentResponse)
async def get_execution(
    intent_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ExecutionService(db=db)
    try:
        intent = await service.get_intent(intent_id=intent_id, user_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _intent_to_response(intent)


@router.get("/{intent_id}/record", response_model=ExecutionRecordResponse | None)
async def get_execution_record(
    intent_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ExecutionService(db=db)
    try:
        record = await service.get_execution_record(intent_id=intent_id, user_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _record_to_response(record) if record else None


@router.get("/tasks/{task_id}/intents", response_model=list[ExecutionIntentResponse])
async def list_task_intents(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ExecutionService(db=db)
    try:
        intents = await service.list_task_intents(task_id=task_id, user_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [_intent_to_response(intent) for intent in intents]


@router.post("/{intent_id}/cancel", response_model=ExecutionIntentResponse)
async def cancel_execution(
    intent_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ExecutionService(db=db)
    try:
        intent = await service.cancel(intent_id=intent_id, user_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _intent_to_response(intent)


@router.post("/{intent_id}/handback", response_model=ExecutionIntentResponse)
async def handback_execution(
    intent_id: UUID,
    request: HandbackRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ExecutionService(db=db)
    try:
        intent = await service.handback(intent_id=intent_id, user_id=current_user.id, reason=request.reason)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _intent_to_response(intent)


@router.post("/records/{record_id}/confirm", response_model=ExecutionRecordResponse)
async def confirm_execution_result(
    record_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ExecutionService(db=db)
    try:
        record = await service.confirm_result(record_id=record_id, user_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _record_to_response(record)


@router.post("/records/{record_id}/reject", response_model=ExecutionRecordResponse)
async def reject_execution_result(
    record_id: UUID,
    request: RejectResultRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ExecutionService(db=db)
    try:
        record = await service.reject_result(
            record_id=record_id,
            user_id=current_user.id,
            reason=request.reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _record_to_response(record)
