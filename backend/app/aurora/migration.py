"""Aurora cohort cutover helpers for replacing legacy dual-core routing."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import timezone, datetime
from typing import Any, Iterable
from uuid import UUID, uuid4

from app.aurora.engine import AuroraDecisionContext, AuroraEngine
from app.aurora.observability import record_shadow_divergence, record_shadow_hook
from app.aurora.policy_loader import load_policy_version
from app.aurora.schemas import (
    AuroraPresenceLevel,
    DecisionBasis,
    ImpactClass,
    SignalSnapshot,
    TransitionDecisionRecord,
    UXIntent,
)
from app.config import aurora_flags
from app.orchestration.dual_core_router import DualCoreDecision, DualCoreRoutingInput, dual_core_router


@dataclass(frozen=True)
class AuroraCutoverState:
    """Resolved cutover mode for a user."""

    mode: str
    reason: str


@dataclass(frozen=True)
class AuroraProjectedDualCoreResult:
    """Aurora decision plus its projection back into the legacy dual-core surface."""

    cutover_state: AuroraCutoverState
    snapshot: SignalSnapshot
    transition_decision: TransitionDecisionRecord
    projected_decision: DualCoreDecision


@dataclass(frozen=True)
class ShadowHookObservation:
    """Shadow-only comparison payload for pre-tool and pre-response hooks."""

    hook_point: str
    trigger_point: str
    legacy_mode: str
    aurora_mode: str
    agreed: bool
    divergence_reason: str | None
    routing_result: AuroraProjectedDualCoreResult


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _normalize_ids(values: Iterable[str]) -> set[str]:
    return {str(value).strip() for value in values if str(value).strip()}


def _cohort_hit(user_id: str, percent: int) -> bool:
    if percent <= 0:
        return False
    if percent >= 100:
        return True
    digest = hashlib.sha256(user_id.encode("utf-8")).hexdigest()
    bucket = int(digest[:8], 16) % 100
    return bucket < percent


def resolve_cutover_state(user_id: str) -> AuroraCutoverState:
    """Resolve whether the user is on legacy, shadow, or active Aurora path."""

    normalized_user_id = str(user_id).strip()
    active_ids = _normalize_ids(aurora_flags.AURORA_ACTIVE_USER_IDS)
    shadow_ids = _normalize_ids(aurora_flags.AURORA_SHADOW_USER_IDS)

    active_selector_present = bool(active_ids) or aurora_flags.AURORA_ACTIVE_COHORT_PERCENT > 0
    shadow_selector_present = bool(shadow_ids) or aurora_flags.AURORA_SHADOW_COHORT_PERCENT > 0

    active_hit = normalized_user_id in active_ids or _cohort_hit(
        normalized_user_id,
        aurora_flags.AURORA_ACTIVE_COHORT_PERCENT,
    )
    shadow_hit = normalized_user_id in shadow_ids or _cohort_hit(
        normalized_user_id,
        aurora_flags.AURORA_SHADOW_COHORT_PERCENT,
    )

    if aurora_flags.AURORA_ACTIVE:
        if active_selector_present:
            if active_hit:
                return AuroraCutoverState(mode="active", reason="active_cohort_selected")
        else:
            return AuroraCutoverState(mode="active", reason="global_active_enabled")

    if aurora_flags.AURORA_SHADOW_MODE:
        if shadow_selector_present:
            if shadow_hit:
                return AuroraCutoverState(mode="shadow", reason="shadow_cohort_selected")
        else:
            return AuroraCutoverState(mode="shadow", reason="global_shadow_enabled")

    return AuroraCutoverState(mode="legacy", reason="aurora_disabled_for_user")


def build_shadow_snapshot_from_routing_input(
    routing_input: DualCoreRoutingInput,
    *,
    user_id: str,
    policy_version: str = "v1.0",
    collected_at: datetime | None = None,
) -> SignalSnapshot:
    """Translate dual-core routing signals into a minimal Aurora snapshot."""

    now = collected_at or _utcnow()
    summary_parts: list[str] = [routing_input.intent]
    if routing_input.primary_challenge_area:
        summary_parts.append(str(routing_input.primary_challenge_area))
    if routing_input.procrastination_pattern:
        summary_parts.append("拖延回避")
    if routing_input.cognitive_mode_suggested:
        summary_parts.append("概念混淆")
    if routing_input.emotional_block_detected:
        summary_parts.append("need help regroup")
    if routing_input.plan_health_status == "critical" and not routing_input.emotional_block_detected:
        summary_parts.append("commitment_conflict")
    if routing_input.current_guidance:
        summary_parts.append(routing_input.current_guidance)

    core_signals: dict[str, Any] = {
        "routing_summary": " ".join(part for part in summary_parts if part).strip(),
        "intent": routing_input.intent,
        "intent_confidence": routing_input.intent_confidence,
    }
    enhanced_signals: dict[str, Any] = {
        "information_sufficient": routing_input.information_sufficient,
        "primary_challenge_area": routing_input.primary_challenge_area,
        "recent_sentiment_distribution": routing_input.recent_sentiment_distribution,
        "recent_task_feedback_distribution": routing_input.recent_task_feedback_distribution,
        "behavior_pattern_names": routing_input.behavior_pattern_names[:5],
        "behavior_pattern_details": routing_input.behavior_pattern_details[:2],
        "behavior_pattern_types": routing_input.behavior_pattern_types,
        "plan_health_status": routing_input.plan_health_status,
    }

    if routing_input.emotional_block_detected:
        enhanced_signals["energy_state"] = "sharp_drop"
    if routing_input.procrastination_pattern:
        enhanced_signals["behavioral_signal"] = "procrastination_pattern"
    if routing_input.cognitive_mode_suggested:
        enhanced_signals["knowledge_gap"] = "concept_confusion"
    if routing_input.plan_health_status == "critical" and not routing_input.emotional_block_detected:
        core_signals["commitment_conflict"] = "routing_plan_health_critical"

    snapshot_hash = hashlib.sha256(
        "|".join(
            [
                normalized for normalized in (
                    user_id,
                    routing_input.intent,
                    str(routing_input.intent_confidence),
                    str(routing_input.primary_challenge_area),
                    str(routing_input.plan_health_status),
                    str(routing_input.procrastination_pattern),
                    str(routing_input.cognitive_mode_suggested),
                    str(routing_input.emotional_block_detected),
                )
            ]
        ).encode("utf-8")
    ).hexdigest()[:16]

    return SignalSnapshot(
        snapshot_hash=f"aurora_dual_core_{snapshot_hash}",
        user_id=UUID(str(user_id)),
        collected_at=now,
        scenario_pack_id="dual_core_shadow@v1.0",
        policy_version=policy_version if policy_version.startswith("aurora_policy@") else f"aurora_policy@{policy_version}",
        core_signals=core_signals,
        enhanced_signals=enhanced_signals,
        optional_signals={"routing_profile": routing_input.routing_profile},
        total_tokens=1200,
        budget_limit=4000,
    )


def _flatten_signals(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value.lower(),)
    if isinstance(value, dict):
        flattened: list[str] = []
        for key, inner in value.items():
            flattened.extend(_flatten_signals(key))
            flattened.extend(_flatten_signals(inner))
        return tuple(flattened)
    if isinstance(value, (list, tuple, set)):
        flattened: list[str] = []
        for item in value:
            flattened.extend(_flatten_signals(item))
        return tuple(flattened)
    return (str(value).lower(),)


def project_aurora_to_dual_core_mode(
    snapshot: SignalSnapshot,
    decision: TransitionDecisionRecord,
    routing_input: DualCoreRoutingInput | None = None,
) -> str:
    """Project Aurora's richer outputs back into legacy dual-core mode space."""

    signal_text = " ".join(
        _flatten_signals(snapshot.core_signals)
        + _flatten_signals(snapshot.enhanced_signals)
        + _flatten_signals(snapshot.optional_signals)
    )

    if decision.ux_intent in {UXIntent.HOLDING, UXIntent.RECONCILIATION, UXIntent.IDENTITY_MOMENT, UXIntent.META_SURFACE}:
        return "cognitive_first"
    if decision.aurora_presence == AuroraPresenceLevel.META_SURFACE:
        return "cognitive_first"
    if decision.decision_basis in {DecisionBasis.ENERGY_DROP, DecisionBasis.PARTNER_SIGNAL}:
        return "cognitive_first"
    if routing_input is not None:
        if routing_input.cognitive_mode_suggested:
            return "cognitive_first"
        if routing_input.procrastination_pattern:
            return "cognitive_first"
        if routing_input.emotional_block_detected:
            return "cognitive_first"
        if routing_input.primary_challenge_area == "emotional" and not routing_input.information_sufficient:
            return "cognitive_first"
        if (
            routing_input.intent in {"plan", "task", "sprint_plan"}
            and routing_input.information_sufficient
            and not routing_input.procrastination_pattern
            and not routing_input.cognitive_mode_suggested
            and not routing_input.emotional_block_detected
        ):
            if routing_input.has_active_plan:
                return "execution_first"
        if routing_input.intent == "chat" and not routing_input.has_active_plan:
            return "balanced"
    if any(token in signal_text for token in ("概念", "讲清", "confused", "知识点", "讲解", "不懂")):
        return "cognitive_first"
    if decision.decision_type == "stay" and any(
        token in signal_text for token in ("不想", "拖", "开工", "help", "pause", "regroup", "完美")
    ):
        return "cognitive_first"
    if decision.decision_type == "transition":
        if decision.decision_basis in {DecisionBasis.COMMITMENT_CONFLICT, DecisionBasis.SCHEDULE_CONSTRAINT}:
            return "execution_first"
        return "cognitive_first"
    if any(token in signal_text for token in ("计划", "拆成", "安排", "冲刺任务", "task list", "每天三步", "25分钟")):
        return "execution_first"
    if any(token in signal_text for token in ("随便聊聊", "聊聊", "状态")) or decision.decision_basis == DecisionBasis.MIXED:
        return "balanced"
    return "balanced"


def _build_projected_decision(
    routing_input: DualCoreRoutingInput,
    transition_decision: TransitionDecisionRecord,
    projected_mode: str,
) -> DualCoreDecision:
    if projected_mode == "cognitive_first":
        if transition_decision.decision_basis == DecisionBasis.ENERGY_DROP:
            reason = "Aurora 检测到明显状态阻力，先走认知支持路径。"
        elif transition_decision.decision_basis == DecisionBasis.PARTNER_SIGNAL:
            reason = "Aurora 收到外部伙伴信号，先做状态校准和支持。"
        else:
            reason = "Aurora 判断当前更适合先澄清状态或理解卡点，再推进执行。"
        cognitive_adjustments = [
            "先降低当前心理或理解摩擦，再进入任务推进。",
        ]
        execution_constraints = []
    elif projected_mode == "execution_first":
        reason = "Aurora 判断当前目标与约束已足够清晰，优先推进执行路径。"
        cognitive_adjustments = []
        execution_constraints = []
        if routing_input.session_length_preference and routing_input.session_length_preference <= 30:
            execution_constraints.append(
                f"将当前推进收敛为 {routing_input.session_length_preference} 分钟内可执行的短冲刺。"
            )
        if transition_decision.decision_type == "transition":
            execution_constraints.append("允许立即切换到新的执行节点或重规划节点。")
    else:
        reason = "Aurora 判断当前需要在轻量理解支持和执行推进之间保持平衡。"
        cognitive_adjustments = ["保留轻量的状态确认，但不过度打断执行。"]
        execution_constraints = ["优先给出低摩擦、可直接接住的下一步。"]

    return DualCoreDecision(
        mode=projected_mode,
        reason=reason,
        cognitive_adjustments=cognitive_adjustments,
        execution_constraints=execution_constraints,
        routing_debug={
            "source": "aurora_projection",
            "aurora_decision_type": transition_decision.decision_type,
            "aurora_basis": transition_decision.decision_basis.value,
            "aurora_impact_class": transition_decision.impact_class.value,
            "aurora_presence": transition_decision.aurora_presence.value,
        },
    )


def route_dual_core_via_aurora(
    routing_input: DualCoreRoutingInput,
    *,
    user_id: str,
    current_node: str = "dual_core_shadow",
    candidate_node: str | None = None,
    trigger_point: str = "pre-node-routing",
    policy_version: str = "v1.0",
    engine: AuroraEngine | None = None,
) -> AuroraProjectedDualCoreResult:
    """Run Aurora over a routing input and project the result into legacy mode semantics."""

    loaded_policy = load_policy_version(policy_version)
    snapshot = build_shadow_snapshot_from_routing_input(
        routing_input,
        user_id=user_id,
        policy_version=loaded_policy.id,
    )
    engine = engine or AuroraEngine()
    transition_decision = engine.safe_route(
        AuroraDecisionContext(
            snapshot=snapshot,
            trigger_point=trigger_point,
            current_node=current_node,
            candidate_node=candidate_node,
            policy_version=loaded_policy,
        )
    )
    projected_mode = project_aurora_to_dual_core_mode(snapshot, transition_decision, routing_input=routing_input)
    projected_decision = _build_projected_decision(routing_input, transition_decision, projected_mode)
    return AuroraProjectedDualCoreResult(
        cutover_state=AuroraCutoverState(mode="shadow", reason="projection_only"),
        snapshot=snapshot,
        transition_decision=transition_decision,
        projected_decision=projected_decision,
    )


def _shadow_only_hook_enabled() -> bool:
    return aurora_flags.AURORA_SHADOW_MODE and not aurora_flags.AURORA_ACTIVE


def _prepare_shadow_hook_observation(
    routing_input: DualCoreRoutingInput,
    *,
    user_id: str,
    hook_point: str,
    trigger_point: str,
    current_node: str = "dual_core_shadow",
    candidate_node: str | None = None,
    policy_version: str = "v1.0",
    enabled: bool | None = None,
) -> ShadowHookObservation | None:
    shadow_only_enabled = _shadow_only_hook_enabled()
    if enabled is not None:
        shadow_only_enabled = shadow_only_enabled and bool(enabled)
    if not shadow_only_enabled:
        return None

    routing_result = route_dual_core_via_aurora(
        routing_input,
        user_id=user_id,
        current_node=current_node,
        candidate_node=candidate_node,
        trigger_point=trigger_point,
        policy_version=policy_version,
    )
    legacy_decision = dual_core_router.route(routing_input)
    aurora_mode = routing_result.projected_decision.mode
    agreed = legacy_decision.mode == aurora_mode
    divergence_reason = None if agreed else f"legacy={legacy_decision.mode}, aurora={aurora_mode}"

    record_shadow_hook(
        hook_point=hook_point,
        trigger_point=trigger_point,
        outcome="aligned" if agreed else "diverged",
        enabled=True,
    )
    record_shadow_divergence_if_needed(
        legacy_decision=legacy_decision,
        aurora_decision=routing_result.projected_decision,
        trigger_point=trigger_point,
        enabled=True,
    )
    return ShadowHookObservation(
        hook_point=hook_point,
        trigger_point=trigger_point,
        legacy_mode=legacy_decision.mode,
        aurora_mode=aurora_mode,
        agreed=agreed,
        divergence_reason=divergence_reason,
        routing_result=routing_result,
    )


def prepare_shadow_pre_tool_selection_hook(
    routing_input: DualCoreRoutingInput,
    *,
    user_id: str,
    current_node: str = "dual_core_shadow",
    candidate_node: str | None = None,
    policy_version: str = "v1.0",
    enabled: bool | None = None,
) -> ShadowHookObservation | None:
    """Prepare a shadow-only hook for pre-tool-selection routing."""

    return _prepare_shadow_hook_observation(
        routing_input,
        user_id=user_id,
        hook_point="pre-tool-selection",
        trigger_point="pre-tool-selection",
        current_node=current_node,
        candidate_node=candidate_node,
        policy_version=policy_version,
        enabled=enabled,
    )


def prepare_shadow_pre_response_formatting_hook(
    routing_input: DualCoreRoutingInput,
    *,
    user_id: str,
    current_node: str = "dual_core_shadow",
    candidate_node: str | None = None,
    policy_version: str = "v1.0",
    enabled: bool | None = None,
) -> ShadowHookObservation | None:
    """Prepare a shadow-only hook for pre-response-formatting routing."""

    return _prepare_shadow_hook_observation(
        routing_input,
        user_id=user_id,
        hook_point="pre-response-formatting",
        trigger_point="pre-response-formatting",
        current_node=current_node,
        candidate_node=candidate_node,
        policy_version=policy_version,
        enabled=enabled,
    )


def record_shadow_divergence_if_needed(
    *,
    legacy_decision: DualCoreDecision,
    aurora_decision: DualCoreDecision,
    trigger_point: str,
    enabled: bool = True,
) -> bool:
    """Emit a shadow divergence metric when Aurora and legacy disagree."""

    if legacy_decision.mode == aurora_decision.mode:
        return False
    signal = f"{legacy_decision.mode}_vs_{aurora_decision.mode}"
    record_shadow_divergence(signal=signal, trigger_point=trigger_point, enabled=enabled)
    return True
