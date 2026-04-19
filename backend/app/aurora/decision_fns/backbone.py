"""Deterministic backbone-routing helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from app.aurora.schemas import AuroraPolicyVersion, SignalSnapshot

from .materiality import MaterialityCheck, check_materiality


class RoutingMode(StrEnum):
    """Stage 4 conversation routing split."""

    DIRECT = "direct"
    WORKFLOW = "workflow"
    TASK_ASSISTANT = "task_assistant"


_PLANNING_MARKERS = {
    "规划",
    "计划",
    "拆成",
    "拆解",
    "路径",
    "checkpoint",
    "重排",
    "workflow",
    "plan",
    "replan",
}

_TASK_ASSISTANT_MARKERS = {
    "当前这张任务卡",
    "当前任务",
    "直接带我",
    "带我进入",
    "陪我做",
    "开始做",
    "进入任务",
    "不要再讲大道理",
    "drill",
    "task card",
}


@dataclass(frozen=True)
class BackboneRoutingDecision:
    """Backbone stay/transition verdict."""

    should_stay: bool
    current_node: str
    proposed_node: str | None
    reason: str
    materiality: MaterialityCheck
    route_kind: str = field(default="stay")
    routing_mode: RoutingMode = field(default=RoutingMode.DIRECT)


def _classify_routing_mode(snapshot: SignalSnapshot, materiality: MaterialityCheck) -> RoutingMode:
    message = str(snapshot.core_signals.get("user_message") or "").strip().lower()
    optional = snapshot.optional_signals
    enhanced = snapshot.enhanced_signals
    core = snapshot.core_signals

    if optional.get("task_card_id") or any(marker.lower() in message for marker in _TASK_ASSISTANT_MARKERS):
        return RoutingMode.TASK_ASSISTANT

    if (
        materiality.should_route
        or any(marker.lower() in message for marker in _PLANNING_MARKERS)
        or int(optional.get("structural_topic_turns") or 0) >= 2
        or bool(enhanced.get("frustration_signal"))
        or bool(enhanced.get("repeated_failure"))
        or bool(core.get("commitment_conflict"))
    ):
        return RoutingMode.WORKFLOW

    return RoutingMode.DIRECT


def decide_backbone_route(
    snapshot: SignalSnapshot,
    policy: AuroraPolicyVersion,
    current_node: str,
    candidate_node: str | None = None,
) -> BackboneRoutingDecision:
    """Stay on the current node unless a strong signal crosses policy materiality."""

    materiality = check_materiality(snapshot, policy)
    routing_mode = _classify_routing_mode(snapshot, materiality)
    if not materiality.should_route:
        return BackboneRoutingDecision(
            should_stay=True,
            current_node=current_node,
            proposed_node=None,
            reason="materiality_below_threshold",
            materiality=materiality,
            route_kind="stay",
            routing_mode=routing_mode,
        )

    if candidate_node:
        return BackboneRoutingDecision(
            should_stay=False,
            current_node=current_node,
            proposed_node=candidate_node,
            reason=f"materiality_{materiality.basis.value}",
            materiality=materiality,
            route_kind="transition",
            routing_mode=routing_mode,
        )

    return BackboneRoutingDecision(
        should_stay=True,
        current_node=current_node,
        proposed_node=None,
        reason="strong_signal_without_candidate",
        materiality=materiality,
        route_kind="stay",
        routing_mode=routing_mode,
    )
