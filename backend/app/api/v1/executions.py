"""Executions API endpoints for OpenClaw integration."""

from __future__ import annotations

from datetime import timezone, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_superuser, get_current_user, get_optional_current_user
from app.db.session import get_db
from app.models.execution_intent import ExecutionIntent, ExecutionIntentStatus
from app.models.execution_record import ExecutionRecord
from app.models.user import User
from app.services.execution_profile_service import ExecutionProfileService
from app.services.execution_preference_service import ExecutionPreferenceService
from app.services.execution_result_validator import ExecutionResultValidator
from app.services.execution_schedule_service import ExecutionScheduleService
from app.services.execution_service import ExecutionService
from app.services.openclaw_connection_profile_service import OpenClawConnectionProfileService

router = APIRouter(prefix="/executions", tags=["executions"])


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class HandoffRequest(BaseModel):
    """Task handoff payload."""

    goal: str | None = Field(default=None, description="Override execution goal")
    instructions: list[str] | None = Field(default=None, description="Additional constraints")
    policy: dict[str, Any] | None = Field(default=None, description="Policy override")
    success_criteria: dict[str, Any] | None = Field(default=None, description="Success criteria override")
    result_contract: dict[str, Any] | None = Field(default=None, description="Result contract override")
    template_id: str | None = Field(default=None, description="Execution template id")
    preferred_node_id: str | None = Field(default=None, description="Preferred OpenClaw node id")
    source: str | None = Field(default=None, description="Invocation source")


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
    target_env: str | None = None
    status: str
    trust_level: str
    external_run_id: str | None
    goal: str
    template_id: str | None = None
    template_name: str | None = None
    strategy_variant: str | None = None
    target_node_id: str | None = None
    target_node_label: str | None = None
    approval_policy: str | None = None
    estimated_duration_seconds: int | None = None
    estimated_duration_minutes: int | None = None
    error_category: str | None
    error_message: str | None
    dispatched_at: str | None
    completed_at: str | None
    created_at: str | None


class ExecutionTemplateResponse(BaseModel):
    template_id: str
    name: str
    description: str
    execution_mode: str
    target_env: str
    match_score: float
    match_reasons: list[str]
    required_node_command: str | None = None


class ExecutionNodeResponse(BaseModel):
    node_id: str
    name: str
    platform: str
    connected: bool
    status: str
    active_runs: int = 0
    last_seen: str | None = None
    commands: list[str]
    caps: list[str]


class NodeInvokeRequest(BaseModel):
    command: str
    params: dict[str, Any] | None = None
    invoke_timeout_ms: int | None = None
    idempotency_key: str | None = None


class ExecutionQualityVariantResponse(BaseModel):
    variant_id: str
    variant_name: str
    is_control: bool
    configuration: dict[str, Any]
    sample_size: int
    success_rate: float
    avg_quality: float
    avg_latency: float


class ExecutionQualitySummaryResponse(BaseModel):
    experiment_id: str | None = None
    experiment_name: str
    status: str
    sample_size_collected: int
    variants: list[ExecutionQualityVariantResponse]


class ClassifyResponse(BaseModel):
    execution_mode: str
    target_env: str | None
    reason: str
    confidence: float
    risk_flags: list[str]


class ExecutionConnectionStatusResponse(BaseModel):
    openclaw_enabled: bool
    reachable: bool
    gateway_url: str | None = None
    transport: str | None = None
    ws_url: str | None = None
    connection_source: str | None = None
    latency_ms: int | None = None
    message: str | None = None
    capabilities: list[str] = Field(default_factory=list)
    connected_nodes: int
    supports_nodes: bool
    supports_templates: bool
    supports_quality_loop: bool
    degraded_user_count: int = 0
    degradation_threshold: int = 0


class ExecutionConnectionDiagnosticCheckResponse(BaseModel):
    key: str
    label: str
    status: str
    message: str
    suggestion: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class ExecutionConnectionDiagnosticResponse(BaseModel):
    reachable: bool
    overall_status: str
    summary: str
    generated_at: str
    transport: str | None = None
    connection_source: str | None = None
    gateway_url: str | None = None
    ws_url: str | None = None
    checks: list[ExecutionConnectionDiagnosticCheckResponse] = Field(default_factory=list)


class ExecutionConnectionProfileRequest(BaseModel):
    gateway_url: str = ""
    auth_token: str | None = None
    device_token: str | None = None
    transport: str = "responses_http"
    ws_url: str | None = None
    paired_at: str | None = None


class ExecutionConnectionProfileResponse(BaseModel):
    configured: bool
    gateway_url: str = ""
    auth_token: str | None = None
    device_token: str | None = None
    transport: str = "responses_http"
    ws_url: str | None = None
    paired_at: str | None = None


class ExecutionPreferenceRecommendationResponse(BaseModel):
    recommended_mode: str
    reason: str
    target_env: str | None = None
    confidence: float = 0.0


class ExecutionBudgetResponse(BaseModel):
    daily_token_limit: int | None = None
    monthly_token_limit: int | None = None
    daily_used: int = 0
    monthly_used: int = 0
    reset_date: str | None = None
    month_bucket: str | None = None


class ExecutionPreferencesRequest(BaseModel):
    mode: str = "balanced"
    custom_rules: dict[str, str] = Field(default_factory=dict)
    node_affinity: dict[str, str] = Field(default_factory=dict)
    notification_level: str = "essential"
    auto_extend_timeout: bool = True
    trust_auto_upgrade: bool = True
    execution_budget: ExecutionBudgetResponse = Field(default_factory=ExecutionBudgetResponse)


class ExecutionPreferencesResponse(BaseModel):
    mode: str
    custom_rules: dict[str, str]
    node_affinity: dict[str, str]
    notification_level: str
    auto_extend_timeout: bool
    trust_auto_upgrade: bool
    execution_budget: ExecutionBudgetResponse
    summary: str
    recommendations: list[ExecutionPreferenceRecommendationResponse] = Field(default_factory=list)


class ExecutionProfileTypeSummaryResponse(BaseModel):
    total: int
    succeeded: int
    success_rate: float


class ExecutionProfileSummaryResponse(BaseModel):
    days: int
    total_executions: int
    success_rate: float
    by_type: dict[str, ExecutionProfileTypeSummaryResponse]
    trust_distribution: dict[str, int]
    approval_request_count: int
    top_templates: list[list[Any]]
    estimated_time_saved_minutes: float | None = None
    delegation_trend: str


class ExecutionBatchRequest(BaseModel):
    intent_ids: list[str] = Field(default_factory=list)
    execution_strategy: str = "auto"


class ExecutionTaskBatchRequest(BaseModel):
    task_ids: list[str] = Field(default_factory=list)
    execution_strategy: str = "auto"


class ExecutionBatchItemResponse(BaseModel):
    intent_id: str
    task_id: str
    status: str | None = None
    target_env: str | None = None
    error_message: str | None = None


class ExecutionBatchResponse(BaseModel):
    batch_id: str
    status: str
    requested_strategy: str
    resolved_strategy: str
    task_ids: list[str] = Field(default_factory=list)
    intent_ids: list[str] = Field(default_factory=list)
    completed_count: int = 0
    failed_count: int = 0
    queued_count: int = 0
    items: list[ExecutionBatchItemResponse] = Field(default_factory=list)


class ExecutionScheduleRequest(BaseModel):
    task_id: str
    goal: str | None = None
    instructions: list[str] = Field(default_factory=list)
    policy: dict[str, Any] = Field(default_factory=dict)
    success_criteria: dict[str, Any] = Field(default_factory=dict)
    result_contract: dict[str, Any] = Field(default_factory=dict)
    template_id: str | None = None
    preferred_node_id: str | None = None
    trigger_type: str
    trigger_config: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True


class ExecutionScheduleResponse(BaseModel):
    id: str
    user_id: str
    task_id: str
    intent_template: dict[str, Any]
    trigger_type: str | None = None
    trigger_config: dict[str, Any]
    last_run_at: str | None = None
    next_run_at: str | None = None
    is_active: bool = True
    created_at: str | None = None
    updated_at: str | None = None


class ExecutionScheduleTickResponse(BaseModel):
    checked_at: str
    due_count: int = 0
    dispatched_count: int = 0
    items: list[dict[str, Any]] = Field(default_factory=list)


class ExecutionScheduleEventTriggerRequest(BaseModel):
    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)


class ExecutionRecordResponse(BaseModel):
    id: str
    execution_intent_id: str
    execution_status: str | None = None
    requires_confirmation: bool = False
    trust_level: str
    quality_score: float | None
    parsed_output: dict | None
    artifacts: list[Any]
    tool_calls_count: int = 0
    duration_ms: int | None
    validation_passed: int | None
    validation_total: int | None
    approval_requested: int | None
    error_category: str | None
    error_message: str | None
    result_preview: dict[str, Any] | None = None
    quality_warnings: list[dict[str, Any]] = Field(default_factory=list)
    replay_steps: list[dict[str, Any]] = Field(default_factory=list)
    comparison_summary: dict[str, Any] | None = None
    self_verification: dict[str, Any] | None = None
    error_suggestion: dict[str, Any] | None = None
    manual_steps: list[dict[str, Any]] = Field(default_factory=list)
    retry_action: dict[str, Any] | None = None


def _intent_to_response(intent: ExecutionIntent) -> ExecutionIntentResponse:
    payload = intent.to_dict()
    policy = payload.get("policy") or intent.policy or {}
    template_metadata = policy.get("template_metadata") or {}
    quality_strategy = policy.get("quality_strategy") or {}
    duration_estimate = policy.get("duration_estimate") or {}
    return ExecutionIntentResponse(
        id=payload["id"],
        task_id=payload["task_id"],
        plan_id=payload["plan_id"],
        execution_mode=payload["execution_mode"],
        executor=payload["executor"],
        target_env=payload["target_env"],
        status=payload["status"],
        trust_level=payload["trust_level"],
        external_run_id=payload["external_run_id"],
        goal=payload["goal"],
        template_id=template_metadata.get("template_id"),
        template_name=template_metadata.get("template_name"),
        strategy_variant=quality_strategy.get("variant_name"),
        target_node_id=policy.get("target_node_id"),
        target_node_label=policy.get("target_node_label"),
        approval_policy=policy.get("approval_policy"),
        estimated_duration_seconds=duration_estimate.get("estimated_seconds"),
        estimated_duration_minutes=duration_estimate.get("estimated_minutes"),
        error_category=payload["error_category"],
        error_message=payload["error_message"],
        dispatched_at=payload["dispatched_at"],
        completed_at=payload["completed_at"],
        created_at=payload["created_at"],
    )


async def _record_to_response(
    record: ExecutionRecord,
    *,
    db: AsyncSession,
) -> ExecutionRecordResponse:
    payload = record.to_dict()
    validator = ExecutionResultValidator()
    previous_record = None
    intent = None
    if record.task_id:
        previous_stmt = (
            select(ExecutionRecord)
            .where(
                ExecutionRecord.user_id == record.user_id,
                ExecutionRecord.task_id == record.task_id,
                ExecutionRecord.deleted_at.is_(None),
                ExecutionRecord.created_at < record.created_at,
            )
            .order_by(desc(ExecutionRecord.created_at))
            .limit(1)
        )
        previous_record = (await db.execute(previous_stmt)).scalar_one_or_none()
    intent = await db.get(ExecutionIntent, record.execution_intent_id)

    quality_warnings = []
    if isinstance(record.raw_response, dict):
        quality_warnings = list(record.raw_response.get("_sparkle_quality_warnings") or [])
    policy = (intent.policy if intent else {}) or {}
    if policy.get("contains_sensitive_data") is True and all(
        str(item.get("code") or "") != "contains_sensitive_data"
        for item in quality_warnings
        if isinstance(item, dict)
    ):
        risk = policy.get("_risk_assessment")
        matches = []
        if isinstance(risk, dict):
            matches = [
                item.get("label")
                for item in list(risk.get("sensitive_signals") or [])
                if isinstance(item, dict) and str(item.get("label") or "").strip()
            ]
        label_suffix = f"（{', '.join(matches[:3])}）" if matches else ""
        quality_warnings.append(
            {
                "code": "contains_sensitive_data",
                "severity": "warning",
                "message": f"本次执行涉及敏感数据{label_suffix}，请确认执行环境和结果回传链路是安全的。",
            }
        )

    preview_payload = validator.extract_preview(
        {
            "parsed_output": payload["parsed_output"],
            "output": (record.raw_response or {}).get("output"),
            "artifacts": payload["artifacts"],
        },
    )
    recovery = policy.get("error_recovery") if isinstance(policy, dict) else {}
    recovery = recovery if isinstance(recovery, dict) else {}
    return ExecutionRecordResponse(
        id=payload["id"],
        execution_intent_id=payload["execution_intent_id"],
        execution_status=intent.status.value if intent and intent.status else None,
        requires_confirmation=bool(intent and intent.status == ExecutionIntentStatus.WAITING_APPROVAL),
        trust_level=payload["trust_level"],
        quality_score=payload["quality_score"],
        parsed_output=payload["parsed_output"],
        artifacts=payload["artifacts"],
        tool_calls_count=int(payload.get("tool_calls_count", 0) or 0),
        duration_ms=payload["duration_ms"],
        validation_passed=payload.get("validation_passed"),
        validation_total=payload.get("validation_total"),
        approval_requested=payload.get("approval_requested"),
        error_category=payload["error_category"],
        error_message=payload["error_message"],
        result_preview=preview_payload,
        quality_warnings=quality_warnings,
        replay_steps=validator.build_replay_steps_from_raw_response(record.raw_response or {}),
        comparison_summary=validator.build_comparison_summary(
            current_record=record,
            previous_record=previous_record,
        ),
        self_verification=validator.build_self_verification(
            parsed_output=payload["parsed_output"],
            artifacts=payload["artifacts"],
            result_contract=(intent.result_contract if intent else {}) or {},
            quality_warnings=quality_warnings,
        ),
        error_suggestion=(
            {
                "suggestion": recovery.get("suggestion"),
                "recommended_action": recovery.get("recommended_action"),
                "retry_success_rate": recovery.get("retry_success_rate"),
                "recent_similar_failures": recovery.get("recent_similar_failures"),
            }
            if recovery
            else None
        ),
        manual_steps=[
            item for item in list(recovery.get("manual_steps") or []) if isinstance(item, dict)
        ],
        retry_action=(
            recovery.get("retry_action")
            if isinstance(recovery.get("retry_action"), dict)
            else None
        ),
    )


@router.get("/health")
async def execution_health(
    current_user: User | None = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ExecutionService(db=db)
    return await service.get_health(user_id=current_user.id if current_user else None)


@router.get("/connection/status", response_model=ExecutionConnectionStatusResponse)
async def execution_connection_status(
    current_user: User | None = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ExecutionService(db=db)
    health = await service.get_health(user_id=current_user.id if current_user else None)
    return ExecutionConnectionStatusResponse(
        openclaw_enabled=bool(health.get("openclaw_enabled")),
        reachable=bool(health.get("reachable")),
        gateway_url=health.get("gateway_url"),
        transport=health.get("transport"),
        ws_url=health.get("ws_url"),
        connection_source=health.get("connection_source"),
        latency_ms=health.get("latency_ms"),
        message=health.get("message"),
        capabilities=list(health.get("capabilities") or []),
        connected_nodes=int(health.get("connected_nodes", 0)),
        supports_nodes=bool(health.get("supports_nodes")),
        supports_templates=bool(health.get("supports_templates")),
        supports_quality_loop=bool(health.get("supports_quality_loop")),
        degraded_user_count=int(health.get("degraded_user_count", 0)),
        degradation_threshold=int(health.get("degradation_threshold", 0)),
    )


# route-tier: authed
@router.get("/connection/diagnose", response_model=ExecutionConnectionDiagnosticResponse)
async def execution_connection_diagnose(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ExecutionService(db=db)
    payload = await service.diagnose_connection(user_id=current_user.id)
    return ExecutionConnectionDiagnosticResponse(
        reachable=bool(payload.get("reachable")),
        overall_status=str(payload.get("overall_status") or "failed"),
        summary=str(payload.get("summary") or ""),
        generated_at=str(payload.get("generated_at") or ""),
        transport=payload.get("transport"),
        connection_source=payload.get("connection_source"),
        gateway_url=payload.get("gateway_url"),
        ws_url=payload.get("ws_url"),
        checks=[
            ExecutionConnectionDiagnosticCheckResponse(**check)
            for check in list(payload.get("checks") or [])
            if isinstance(check, dict)
        ],
    )


# route-tier: authed
@router.get("/connection/profile", response_model=ExecutionConnectionProfileResponse)
async def get_execution_connection_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = await OpenClawConnectionProfileService(db).get_profile(user_id=current_user.id)
    payload = profile.to_payload() if profile is not None else {"configured": False}
    return ExecutionConnectionProfileResponse(**payload)


# route-tier: authed
@router.put("/connection/profile", response_model=ExecutionConnectionProfileResponse)
async def update_execution_connection_profile(
    request: ExecutionConnectionProfileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = await OpenClawConnectionProfileService(db).save_profile(
        user_id=current_user.id,
        payload=request.model_dump(),
    )
    return ExecutionConnectionProfileResponse(**profile.to_payload())


# route-tier: authed
@router.get("/nodes", response_model=list[ExecutionNodeResponse])
async def list_execution_nodes(
    connected_only: bool = False,
    last_connected: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ExecutionService(db=db)
    nodes = await service.list_nodes(
        user_id=current_user.id,
        connected_only=connected_only,
        last_connected=last_connected,
    )
    return [ExecutionNodeResponse(**node) for node in nodes]


# route-tier: authed
@router.delete("/connection/profile", response_model=ExecutionConnectionProfileResponse)
async def delete_execution_connection_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await OpenClawConnectionProfileService(db).clear_profile(user_id=current_user.id)
    return ExecutionConnectionProfileResponse(configured=False)


# route-tier: authed
@router.get("/preferences", response_model=ExecutionPreferencesResponse)
async def get_execution_preferences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    payload = await ExecutionPreferenceService(db).get_preferences(user_id=current_user.id)
    return ExecutionPreferencesResponse(**payload)


# route-tier: authed
@router.put("/preferences", response_model=ExecutionPreferencesResponse)
async def update_execution_preferences(
    request: ExecutionPreferencesRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    payload = await ExecutionPreferenceService(db).save_preferences(
        user_id=current_user.id,
        payload=request.model_dump(),
    )
    return ExecutionPreferencesResponse(**payload)


@router.get("/profile/summary", response_model=ExecutionProfileSummaryResponse)
async def execution_profile_summary(
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    payload = await ExecutionProfileService(db).get_execution_profile(
        user_id=current_user.id,
        days=days,
    )
    return ExecutionProfileSummaryResponse(**payload)


# route-tier: authed
@router.get("/schedules", response_model=list[ExecutionScheduleResponse])
async def list_execution_schedules(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    schedules = await ExecutionScheduleService(db).list_schedules(user_id=current_user.id)
    return [ExecutionScheduleResponse(**schedule.to_dict()) for schedule in schedules]


# route-tier: authed
@router.post("/schedules", response_model=ExecutionScheduleResponse)
async def create_execution_schedule(
    request: ExecutionScheduleRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ExecutionScheduleService(db)
    try:
        schedule = await service.create_schedule(
            user_id=current_user.id,
            task_id=UUID(request.task_id),
            intent_template={
                "goal": request.goal,
                "instructions": request.instructions,
                "policy": request.policy,
                "success_criteria": request.success_criteria,
                "result_contract": request.result_contract,
                "template_id": request.template_id,
                "preferred_node_id": request.preferred_node_id,
            },
            trigger_type=request.trigger_type,
            trigger_config=request.trigger_config,
            is_active=request.is_active,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ExecutionScheduleResponse(**schedule.to_dict())


# route-tier: admin
@router.post("/schedules/tick", response_model=ExecutionScheduleTickResponse)
async def tick_execution_schedules(
    current_user: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    del current_user
    payload = await ExecutionScheduleService(db).tick_due_schedules()
    return ExecutionScheduleTickResponse(**payload)


# route-tier: authed
@router.post("/schedules/{schedule_id}/pause", response_model=ExecutionScheduleResponse)
async def pause_execution_schedule(
    schedule_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        schedule = await ExecutionScheduleService(db).pause_schedule(
            schedule_id=schedule_id,
            user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ExecutionScheduleResponse(**schedule.to_dict())


# route-tier: authed
@router.post("/schedules/{schedule_id}/resume", response_model=ExecutionScheduleResponse)
async def resume_execution_schedule(
    schedule_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        schedule = await ExecutionScheduleService(db).resume_schedule(
            schedule_id=schedule_id,
            user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ExecutionScheduleResponse(**schedule.to_dict())


# route-tier: authed
@router.delete("/schedules/{schedule_id}")
async def delete_execution_schedule(
    schedule_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        await ExecutionScheduleService(db).delete_schedule(
            schedule_id=schedule_id,
            user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"success": True}


# route-tier: admin
@router.post("/schedules/events/trigger", response_model=ExecutionScheduleTickResponse)
async def trigger_execution_schedule_event(
    request: ExecutionScheduleEventTriggerRequest,
    current_user: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    del current_user
    payload = await ExecutionScheduleService(db).trigger_event(
        event_type=request.event_type,
        payload=request.payload,
    )
    return ExecutionScheduleTickResponse(
        checked_at=_utcnow().isoformat(),
        due_count=int(payload.get("matched_count", 0)),
        dispatched_count=int(payload.get("dispatched_count", 0)),
        items=list(payload.get("items") or []),
    )


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
            template_id=request.template_id,
            preferred_node_id=request.preferred_node_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Execution handoff failed unexpectedly")
        raise HTTPException(status_code=500, detail="Internal execution error") from exc

    if str(request.source or "").strip() == "execution_suggestion":
        await ExecutionPreferenceService(db).record_delegation_suggestion_accepted(
            user_id=current_user.id,
        )

    return _intent_to_response(intent)


# route-tier: authed
@router.post("/tasks/handoff/batch", response_model=ExecutionBatchResponse)
async def handoff_task_batch(
    request: ExecutionTaskBatchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ExecutionService(db=db)
    try:
        payload = await service.handoff_tasks_batch(
            task_ids=[UUID(item) for item in request.task_ids],
            user_id=current_user.id,
            execution_strategy=request.execution_strategy,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ExecutionBatchResponse(
        **{
            **payload,
            "items": [ExecutionBatchItemResponse(**item) for item in payload.get("items", [])],
        }
    )


@router.get("/tasks/{task_id}/templates", response_model=list[ExecutionTemplateResponse])
async def list_execution_templates(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ExecutionService(db=db)
    try:
        templates = await service.list_templates(task_id=task_id, user_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [ExecutionTemplateResponse(**template) for template in templates]


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


# route-tier: authed
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
    return await _record_to_response(record, db=db) if record else None


# route-tier: authed
@router.post("/{intent_id}/retry", response_model=ExecutionIntentResponse)
async def retry_execution(
    intent_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ExecutionService(db=db)
    try:
        intent = await service.retry_intent(intent_id=intent_id, user_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _intent_to_response(intent)


# route-tier: authed
@router.post("/batch/handoff", response_model=ExecutionBatchResponse)
async def handoff_batch(
    request: ExecutionBatchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ExecutionService(db=db)
    try:
        payload = await service.dispatch_batch(
            intent_ids=[UUID(item) for item in request.intent_ids],
            user_id=current_user.id,
            execution_strategy=request.execution_strategy,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ExecutionBatchResponse(
        **{
            **payload,
            "items": [ExecutionBatchItemResponse(**item) for item in payload.get("items", [])],
        }
    )


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
    return await _record_to_response(record, db=db)


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
    return await _record_to_response(record, db=db)
