from __future__ import annotations

import logging
from datetime import date as date_type
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_superuser, get_current_user, get_db
from app.aurora.core_session import AuroraCoreSessionService
from app.aurora.predicted_reply_engine import PredictedReplyOptionEngine
from app.aurora.runtime_v1.service import AuroraRuntimeV1Service
from app.aurora.runtime_v1.state import AuroraEnergyStore
from app.aurora.runtime_v1.telemetry import AuroraDecisionTelemetryService
from app.core.cache import cache_service
from app.models.user import User
from app.services.aurora_calibration_card_service import AuroraCalibrationCardService
from app.services.aurora_control_surface_service import AuroraControlSurfaceService  # noqa: F401 (used in predicted-options)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/aurora", tags=["aurora"])


# ── Request / Response models ──────────────────────────────────────────────────

class CalibrationCardRespondRequest(BaseModel):
    response: Literal["confirm", "incorrect", "mute"]
    reason: str | None = None
    corrected_assumption: str | None = None


class DailyStartupResponse(BaseModel):
    message: str
    today_focus: str
    estimated_minutes: int
    adjustment_reason: str


class ComebackContextResponse(BaseModel):
    title: str
    message: str
    days_away: int
    days_remaining: int
    subject: str
    next_task_title: str
    recent_task_summary: str
    light_restart_suggestion: str
    plan_id: str


class CoreSessionStartRequest(BaseModel):
    conversation_id: str | None = None
    surface: str = "aurora_modeling"
    session_type: str = "user_initiated"
    scope: str | None = None
    wake_reasons: list[str] = Field(default_factory=list)
    band_status: str = "calibration_available"


class CoreSessionRespondRequest(BaseModel):
    session_id: str
    content: str
    option_id: str | None = None
    semantic_value: str | None = None
    model_write_effect: dict[str, Any] | None = None
    is_freeform: bool = False


class ChipSelectedTelemetryRequest(BaseModel):
    chip_id: str
    telemetry_id: str
    semantic_value: str
    is_freeform: bool = False
    is_disconfirming: bool = False
    context_source: str = ""
    band_status: str = ""
    conversation_id: str | None = None
    session_id: str | None = None
    group_id: str = ""
    freeform_text: str = ""


# ── Existing endpoints ─────────────────────────────────────────────────────────

# route-tier: authed
@router.get("/daily-startup", response_model=DailyStartupResponse)
async def get_daily_startup(
    plan_id: str = Query(..., min_length=1),
    user_id: UUID | None = Query(default=None),
    session_date: date_type | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DailyStartupResponse:
    resolved_user_id = user_id or current_user.id
    if str(resolved_user_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot request daily startup for another user",
        )

    service = AuroraRuntimeV1Service(cache_service.redis)
    try:
        payload = await service.get_daily_startup_message(
            active_db=db,
            user_id=resolved_user_id,
            plan_id=plan_id,
            session_date=session_date,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    return DailyStartupResponse(**payload)


# route-tier: authed
@router.get("/comeback-context")
async def get_comeback_context(
    user_id: UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    resolved_user_id = user_id or current_user.id
    if str(resolved_user_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot request comeback context for another user",
        )

    service = AuroraRuntimeV1Service(cache_service.redis)
    payload = await service.get_comeback_context(
        active_db=db,
        user_id=resolved_user_id,
    )
    if payload is None:
        return {}
    return ComebackContextResponse(**payload).model_dump()


# route-tier: authed
@router.get("/calibration-cards")
async def get_calibration_cards(
    plan_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = AuroraCalibrationCardService(db, cache_service.redis)
    return await service.list_cards(user_id=current_user.id, plan_id=plan_id)


# route-tier: authed
@router.post("/calibration-cards/{card_id}/respond")
async def respond_calibration_card(
    payload: CalibrationCardRespondRequest,
    card_id: str = Path(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = AuroraCalibrationCardService(db, cache_service.redis)
    try:
        return await service.respond(
            user_id=current_user.id,
            card_id=card_id,
            response=payload.response,
            reason=payload.reason,
            corrected_assumption=payload.corrected_assumption,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


# route-tier: admin
@router.get("/telemetry/summary")
async def get_aurora_telemetry_summary(
    days: int = Query(30, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser),
) -> dict[str, Any]:
    del current_user
    return await AuroraDecisionTelemetryService(db).build_summary(days=days)


# ── New: Core Session endpoints ────────────────────────────────────────────────

# route-tier: authed
@router.post("/core-session/start")
async def start_core_session(
    payload: CoreSessionStartRequest,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Start or retrieve an active L3 Aurora Core Session for this user."""
    service = AuroraCoreSessionService(cache_service.redis)
    try:
        session = await service.start_session(
            user_id=str(current_user.id),
            conversation_id=payload.conversation_id,
            surface=payload.surface,
            session_type=payload.session_type,
            scope=payload.scope,
            wake_reasons=payload.wake_reasons,
            band_status=payload.band_status,
        )
    except Exception as exc:
        logger.exception("Failed to start Aurora core session")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start Aurora core session",
        ) from exc

    # Record L3 session start in energy store
    energy_store = AuroraEnergyStore(cache_service.redis)
    try:
        await energy_store.record_l3_session(current_user.id)
    except Exception:
        pass

    return session.to_dict()


# route-tier: authed
@router.post("/core-session/respond")
async def respond_core_session(
    payload: CoreSessionRespondRequest,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Process a user response in an active Aurora Core Session."""
    service = AuroraCoreSessionService(cache_service.redis)
    try:
        session = await service.respond(
            user_id=str(current_user.id),
            session_id=payload.session_id,
            content=payload.content,
            option_id=payload.option_id,
            semantic_value=payload.semantic_value,
            model_write_effect=payload.model_write_effect,
            is_freeform=payload.is_freeform,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    return session.to_dict()


# route-tier: authed
@router.get("/core-session/current")
async def get_current_core_session(
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get the user's current active Aurora Core Session, if any."""
    service = AuroraCoreSessionService(cache_service.redis)
    session = await service.get_active_session(str(current_user.id))
    if session is None:
        return {"active": False, "session": None}
    return {"active": True, "session": session.to_dict()}


# route-tier: authed
@router.post("/core-session/{session_id}/close")
async def close_core_session(
    session_id: str = Path(...),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Close an active Aurora Core Session (user-initiated exit)."""
    service = AuroraCoreSessionService(cache_service.redis)
    try:
        session = await service.close_session(
            user_id=str(current_user.id),
            session_id=session_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    return session.to_dict()


# ── New: Predicted reply options endpoint ──────────────────────────────────────

# route-tier: authed
@router.get("/predicted-options")
async def get_predicted_options(
    conversation_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get Aurora-generated predicted reply options for the current state."""
    snapshot = await AuroraControlSurfaceService(db, cache_service.redis).build_snapshot(
        user_id=current_user.id,
        conversation_id=conversation_id,
    )
    return {
        "predicted_reply_options": snapshot.get("predicted_reply_options", []),
        "band_status": snapshot.get("overall_status", "sensing"),
        "energy_level": snapshot.get("energy_level", "L0"),
    }


# ── New: Chip selected telemetry ───────────────────────────────────────────────

# route-tier: authed
@router.post("/telemetry/chip-selected")
async def record_chip_selected(
    payload: ChipSelectedTelemetryRequest,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Record that the user selected a predicted reply chip.

    This feeds into Aurora's model update pipeline. Freeform corrections
    and disconfirming selections are especially important signal sources.
    """
    redis = cache_service.redis
    import json as _json
    import time
    correction_result = None

    if redis is not None:
        telemetry_key = f"aurora:chip_telemetry:{current_user.id}"
        record = {
            "chip_id": payload.chip_id,
            "telemetry_id": payload.telemetry_id,
            "semantic_value": payload.semantic_value,
            "is_freeform": payload.is_freeform,
            "is_disconfirming": payload.is_disconfirming,
            "context_source": payload.context_source,
            "band_status": payload.band_status,
            "conversation_id": payload.conversation_id,
            "session_id": payload.session_id,
            "group_id": payload.group_id,
            "freeform_text": payload.freeform_text,
            "ts": time.time(),
        }
        try:
            await redis.lpush(telemetry_key, _json.dumps(record, ensure_ascii=False))
            await redis.ltrim(telemetry_key, 0, 199)
            await redis.expire(telemetry_key, 7 * 24 * 3600)
        except Exception:
            pass

        # T3.3.2-T3.3.3: Correction feedback loop
        if payload.is_disconfirming or payload.is_freeform:
            try:
                from app.aurora.runtime_v1.correction_feedback import CorrectionFeedbackProcessor
                processor = CorrectionFeedbackProcessor(redis)
                correction_result = await processor.process(
                    user_id=str(current_user.id),
                    semantic_value=payload.semantic_value,
                    is_disconfirming=payload.is_disconfirming,
                    is_freeform=payload.is_freeform,
                    freeform_text=payload.freeform_text,
                    telemetry_id=payload.telemetry_id,
                    context_source=payload.context_source,
                )
            except Exception:
                logger.exception("Correction feedback processing failed")

    response = {"recorded": True, "semantic_value": payload.semantic_value}
    if correction_result is not None:
        response["correction_result"] = correction_result.to_dict()
    return response


# ── Signal-to-Action Spine: Receipt endpoints ──────────────────────────────────


class SpineReceiptActionRequest(BaseModel):
    receipt_id: str
    action: Literal["confirm", "correct", "dismiss"]


# route-tier: authed
@router.get("/spine/receipt")
async def get_spine_receipt(
    current_user: User = Depends(get_current_user),
) -> dict[str, Any] | None:
    """Get the latest UserVisibleReceipt for the current user."""
    from app.signals.spine_orchestrator import SpineOrchestrator

    redis = cache_service.redis
    if redis is None:
        return {"active": False}
    spine = SpineOrchestrator(redis)
    receipt = await spine.get_latest_receipt(str(current_user.id))
    if receipt is None:
        return {"active": False}
    result = receipt.to_dict()
    result["active"] = True
    return result


# route-tier: authed
@router.post("/spine/receipt/action")
async def submit_spine_receipt_action(
    payload: SpineReceiptActionRequest,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Submit user action on a Receipt (confirm / correct / dismiss)."""
    from app.signals.spine_orchestrator import SpineOrchestrator

    redis = cache_service.redis
    if redis is None:
        return {"processed": False}
    spine = SpineOrchestrator(redis)
    await spine.handle_user_receipt_action(
        user_id=str(current_user.id),
        receipt_id=payload.receipt_id,
        action=payload.action,
    )
    return {"processed": True, "action": payload.action}


# ── Causal Audit Timeline ──────────────────────────────────────────────


class CausalTimelineEntry(BaseModel):
    trace_id: str
    created_at: str
    event_summary: str
    signal: dict[str, Any] | None = None
    state_patches: list[dict[str, Any]] = Field(default_factory=list)
    policy_decision: dict[str, Any] | None = None
    directives: list[dict[str, Any]] = Field(default_factory=list)
    receipt: dict[str, Any] | None = None
    outcome: dict[str, Any] | None = None
    card: dict[str, Any] | None = None  # P1-1: TimelineCard for UI rendering


class CausalTimelineResponse(BaseModel):
    entries: list[CausalTimelineEntry]
    total: int


class TimelineCardCorrectionRequest(BaseModel):
    trace_id: str
    card_id: str
    action: str  # "confirm" | "correct" | "partial" | "dismiss"
    user_explanation: str | None = None


# route-tier: authed
@router.get("/spine/timeline")
async def get_causal_timeline(
    limit: int = Query(default=10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
) -> CausalTimelineResponse:
    """Get the Causal Audit Timeline for the current user (Spec Section 19)."""
    import json

    from app.signals.causal_trace_store import CausalTraceStore
    from app.signals.outcome_recorder import OutcomeRecorder
    from app.signals.timeline_card_renderer import TimelineCardRenderer
    from app.signals.types import ActionableSignal, PolicyDecision, UserVisibleReceipt

    redis = cache_service.redis
    if redis is None:
        return CausalTimelineResponse(entries=[], total=0)

    store = CausalTraceStore(redis)
    traces = await store.get_user_traces(str(current_user.id), limit=limit)
    renderer = TimelineCardRenderer()

    entries: list[CausalTimelineEntry] = []
    for trace in traces:
        # Build signal summary
        signal_data = None
        if trace.signal_ids:
            raw = await redis.get(f"spine:signal:{trace.signal_ids[0]}")
            if raw:
                signal_data = ActionableSignal.from_dict(json.loads(raw)).to_dict()

        # Build policy summary
        policy_data = None
        if trace.policy_decision_id:
            raw = await redis.get(f"spine:policy:{trace.policy_decision_id}")
            if raw:
                policy_data = PolicyDecision.from_dict(json.loads(raw)).to_dict()

        # Build directive summaries — fetch each by individual key
        directives = []
        for did in trace.directive_ids:
            raw = await redis.get(f"spine:directive_by_id:{did}")
            if raw:
                directives.append(json.loads(raw))

        # Build receipt summary
        receipt_data = None
        if trace.receipt_ids:
            raw = await redis.get(f"spine:receipt_by_id:{trace.receipt_ids[0]}")
            if not raw:
                # Fallback to user's latest receipt
                raw = await redis.get(f"spine:receipt:{str(current_user.id)}:latest")
            if raw:
                receipt_data = UserVisibleReceipt.from_dict(json.loads(raw)).to_dict()

        # Build outcome summary
        outcome_data = None
        try:
            recorder = OutcomeRecorder(redis)
            outcome = await recorder.get_outcome_for_trace(trace.trace_id)
            if outcome:
                outcome_data = outcome.to_dict()
        except Exception:
            pass

        # Human-readable event summary
        event_parts = []
        if signal_data:
            event_parts.append(f"信号: {signal_data.get('claim', '?')}")
        if policy_data:
            event_parts.append(f"策略: {policy_data.get('primary_strategy', '?')}")
        event_summary = " → ".join(event_parts) if event_parts else "系统事件"

        # P1-1: Render timeline card
        card_data = None
        try:
            card = renderer.render_card(
                trace_id=trace.trace_id,
                signal_data=signal_data,
                policy_data=policy_data,
                directives=directives,
                receipt_data=receipt_data,
                outcome_data=outcome_data,
                mode="compact",
                timestamp=trace.created_at,
            )
            if card:
                card_data = card.to_dict()
        except Exception:
            pass

        entries.append(CausalTimelineEntry(
            trace_id=trace.trace_id,
            created_at=trace.created_at,
            event_summary=event_summary,
            signal=signal_data,
            state_patches=[],
            policy_decision=policy_data,
            directives=directives,
            receipt=receipt_data,
            outcome=outcome_data,
            card=card_data,
        ))

    return CausalTimelineResponse(entries=entries, total=len(entries))


# route-tier: authed
@router.get("/spine/state")
async def get_spine_state(
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get the current ActionableStatePacket for the user (Spec Section 3)."""
    from app.signals.spine_orchestrator import SpineOrchestrator

    redis = cache_service.redis
    if redis is None:
        return {"active": False}
    spine = SpineOrchestrator(redis)
    packet = await spine.build_state_packet(user_id=str(current_user.id))
    if packet is None:
        return {"active": False}
    result = packet.to_dict()
    result["active"] = True
    return result


# route-tier: authed
@router.get("/spine/status-band")
async def get_spine_status_band(
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Demo Experience Point #10: Aurora 状态带 — 策略风险 / 资料感知。

    Returns structured status band summary for Flutter to render the aurora status bar.
    Fields: strategy_risk, material_aware, execution_risk, stale_guard,
            has_active_directive, active_claims, active_state_keys,
            directive_summary, band_severity.
    """
    from app.signals.spine_orchestrator import SpineOrchestrator

    redis = cache_service.redis
    if redis is None:
        return {
            "strategy_risk": False,
            "material_aware": False,
            "execution_risk": False,
            "stale_guard": False,
            "has_active_directive": False,
            "active_claims": [],
            "active_state_keys": [],
            "directive_summary": None,
            "band_severity": "none",
            "band_status": "sensing",
            "band_label": "轻量感知中",
            "band_summary": "Aurora 正在轻量感知，参考当前上下文优化回复。",
            "band_energy": "L0",
            "correction_options": [],
            "cooldown_remaining_seconds": None,
            "cooldown_can_override": False,
        }
    spine = SpineOrchestrator(redis)
    return await spine.get_status_band_summary(user_id=str(current_user.id))


# route-tier: authed
@router.get("/spine/metrics")
async def get_spine_metrics(
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get Decision Realization Score metrics (Spec Section 22)."""
    from app.signals.spine_metrics import SpineMetricsCollector

    redis = cache_service.redis
    if redis is None:
        return {}
    collector = SpineMetricsCollector(redis)
    return await collector.snapshot()


# route-tier: authed
@router.post("/spine/timeline/correct")
async def correct_timeline_card(
    request: TimelineCardCorrectionRequest,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """User corrects a timeline card judgment (P1-1: Causal Timeline UI)."""
    import json as json_mod

    from app.signals.spine_orchestrator import SpineOrchestrator

    redis = cache_service.redis
    if redis is None:
        return {"status": "error", "message": "service unavailable"}

    spine = SpineOrchestrator(redis)

    if request.action == "correct":
        # User says judgment was wrong → clear directive, record correction
        await spine.trace_store.clear_active_directive(str(current_user.id))
        await spine.metrics.record_retraction()
        await spine.metrics.record_outcome_recorded(effective=False)

        # Record correction to self_model
        try:
            from app.signals.self_model import SparkleSelfModelService
            await SparkleSelfModelService(redis).record_user_correction(
                user_id=str(current_user.id),
                signal_id=f"card_correct:{request.card_id}",
                reason=request.user_explanation or "user_corrected_timeline_card",
                source="timeline_card",
            )
        except Exception:
            pass

    elif request.action == "confirm":
        await spine.metrics.record_outcome_recorded(effective=True)
    elif request.action == "partial":
        await spine.metrics.record_outcome_recorded(effective=False)
    elif request.action == "dismiss":
        pass

    # Store the correction action
    await redis.set(
        f"spine:card_action:{request.card_id}",
        json_mod.dumps({
            "action": request.action,
            "user_id": str(current_user.id),
            "trace_id": request.trace_id,
            "user_explanation": request.user_explanation,
        }),
        ex=72 * 3600,
    )

    return {"status": "ok", "action": request.action}


# route-tier: authed
@router.get("/spine/goals")
async def get_spine_goals(
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get all active goals + arbitration result (P3-3 MultiGoal).

    Returns the user's active goals ranked by urgency, with conflict detection
    and time-split recommendation. Used by Flutter goal overview UI.
    """
    from app.signals.spine_orchestrator import SpineOrchestrator

    redis = cache_service.redis
    if redis is None:
        return {"goals": [], "arbitration": None, "active": False}

    spine = SpineOrchestrator(redis)
    try:
        arbitration = await spine.arbitrate_goals(user_id=str(current_user.id))
        if arbitration is None:
            return {"goals": [], "arbitration": None, "active": False}
        return {
            "active": True,
            "goals": [g.to_dict() for g in arbitration.prioritized_goals],
            "arbitration": {
                "primary_goal_id": arbitration.primary_goal_id,
                "time_split": arbitration.recommended_time_split,
                "conflicts": arbitration.conflicts,
                "rationale": arbitration.rationale,
            },
        }
    except Exception:
        return {"goals": [], "arbitration": None, "active": False}


# route-tier: authed
@router.get("/spine/goal-graph/{goal_id}")
async def get_goal_graph(
    goal_id: str,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get the GoalWorldGraph for a specific goal (P3-1 GoalWorldGraph).

    Returns nodes (knowledge/capability/artifact/habit/feedback/relationship),
    edges (prerequisite/enables/blocks), bottleneck node if any, and focus suggestions.
    """
    from app.signals.spine_orchestrator import SpineOrchestrator

    redis = cache_service.redis
    if redis is None:
        return {"active": False, "nodes": [], "edges": []}

    spine = SpineOrchestrator(redis)
    try:
        graph = await spine.get_goal_graph(user_id=str(current_user.id), goal_id=goal_id)
        if graph is None:
            return {"active": False, "nodes": [], "edges": []}

        bottleneck = graph.find_bottleneck()
        suggestions = await spine.get_goal_focus_suggestions(
            user_id=str(current_user.id), goal_id=goal_id
        )
        return {
            "active": True,
            "goal_id": goal_id,
            "nodes": [
                {
                    "node_id": n.node_id,
                    "node_type": n.node_type,
                    "label": n.label,
                    "mastery": n.mastery,
                    "is_bottleneck": n.node_id == (bottleneck.node_id if bottleneck else ""),
                }
                for n in graph.nodes.values()
            ],
            "edges": [
                {
                    "from_node": e.from_node_id,
                    "to_node": e.to_node_id,
                    "edge_type": e.edge_type,
                }
                for e in graph.edges
            ],
            "bottleneck_node_id": bottleneck.node_id if bottleneck else None,
            "focus_suggestions": suggestions or [],
            "deferred_nodes": await spine.get_goal_deferred_nodes(
                user_id=str(current_user.id),
                goal_id=goal_id,
                focus_ids={s["node_id"] for s in (suggestions or [])},
            ),
        }
    except Exception:
        return {"active": False, "nodes": [], "edges": []}


# route-tier: authed
@router.post("/spine/external-event")
async def submit_external_event(
    request: dict[str, Any],
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Submit an external event to the Spine (P3-6 ExternalIntegrationGateway).

    Accepts events from: calendar, file, email, github, tool.
    All external data enters the Spine as a controlled ExternalRawEvent.
    """
    from app.signals.spine_orchestrator import SpineOrchestrator

    redis = cache_service.redis
    if redis is None:
        return {"status": "error", "message": "service unavailable"}

    source = str(request.get("source", ""))
    source_detail = str(request.get("source_detail", ""))
    raw_payload = request.get("payload", {})
    goal_id = request.get("goal_id")
    integration_id = str(request.get("integration_id", ""))

    if not source:
        return {"status": "error", "message": "source is required"}

    spine = SpineOrchestrator(redis)
    trace = await spine.on_external_event(
        user_id=str(current_user.id),
        source=source,
        source_detail=source_detail,
        raw_payload=raw_payload if isinstance(raw_payload, dict) else {},
        goal_id=goal_id,
        integration_id=integration_id,
    )

    return {
        "status": "ok",
        "trace_id": trace.trace_id if trace else None,
        "signal_triggered": trace is not None,
    }


# route-tier: authed
@router.get("/spine/source-tray")
async def get_source_tray_state(
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Demo Experience Point #5: 用户能手动选择资料参与本轮。

    Returns the current SourceTrayState for the user — what materials
    are included/excluded and whether the user has overridden auto-mode.
    """
    from app.signals.spine_orchestrator import SpineOrchestrator

    redis = cache_service.redis
    if redis is None:
        return {"mode": "auto", "selections": [], "available_sources": []}
    spine = SpineOrchestrator(redis)
    return await spine.get_source_tray_state(user_id=str(current_user.id))


# route-tier: authed
@router.post("/spine/source-tray/select")
async def set_source_tray_selection(
    request: dict[str, Any],
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Demo Experience Point #5: User manually selects which sources enter AI context.

    Body: {
      "selections": [{"source_id": "...", "action": "include|exclude|auto",
                      "scope": "this_turn|this_task|today|this_goal",
                      "user_initiated": true}],
      "mode": "manual_only|auto|no_materials"
    }

    Iron Rule: Only writes to Redis session state. No long-term DB writes.
    """
    from app.signals.spine_orchestrator import SpineOrchestrator

    redis = cache_service.redis
    if redis is None:
        return {"status": "error", "message": "service unavailable"}

    spine = SpineOrchestrator(redis)
    selections = request.get("selections", [])
    mode = str(request.get("mode", "manual_only"))

    state = await spine.set_source_tray_selection(
        user_id=str(current_user.id),
        selections=selections if isinstance(selections, list) else [],
        mode=mode,
    )
    return {"status": "ok", "state": state}


# ── T3.4.4: Aurora communication preferences ────────────────────────────────────

_AURORA_PREF_KEYS = {
    "aurora_analysis_depth": {"light", "deep"},
    "aurora_directness": {"direct", "guided"},
    "aurora_explanation_level": {"detailed", "brief"},
    "aurora_pressure_style": {"gentle", "motivating"},
}

_DEFAULT_AURORA_PREFS: dict[str, str] = {
    "aurora_analysis_depth": "deep",
    "aurora_directness": "guided",
    "aurora_explanation_level": "detailed",
    "aurora_pressure_style": "motivating",
}


class AuroraPreferencesRequest(BaseModel):
    aurora_analysis_depth: str | None = None   # "light" | "deep"
    aurora_directness: str | None = None        # "direct" | "guided"
    aurora_explanation_level: str | None = None  # "detailed" | "brief"
    aurora_pressure_style: str | None = None     # "gentle" | "motivating"


# route-tier: authed
@router.get("/preferences")
async def get_aurora_preferences(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get Aurora communication preferences. Returns all 4 prefs with defaults for unset values."""
    from app.aurora.runtime_v1.user_preferences import AuroraUserPreferencesService

    service = AuroraUserPreferencesService(db)
    prefs = await service.get(user_id=current_user.id)
    return {"preferences": prefs, "defaults": dict(_DEFAULT_AURORA_PREFS)}


# route-tier: authed
@router.put("/preferences")
async def update_aurora_preferences(
    body: AuroraPreferencesRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Update Aurora communication preferences. Only provided fields are changed."""
    from app.aurora.runtime_v1.user_preferences import AuroraUserPreferencesService

    updates: dict[str, str] = {}
    for key in _AURORA_PREF_KEYS:
        value = getattr(body, key, None)
        if value is not None:
            valid = _AURORA_PREF_KEYS[key]
            if value not in valid:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"{key} must be one of: {', '.join(sorted(valid))}",
                )
            updates[key] = value

    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one preference must be provided",
        )

    service = AuroraUserPreferencesService(db)
    prefs = await service.update(user_id=current_user.id, preferences=updates)
    return {"preferences": prefs, "updated_keys": list(updates.keys())}


