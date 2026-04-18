"""Deterministic backbone-routing helpers."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.aurora.schemas import AuroraPolicyVersion, SignalSnapshot

from .materiality import MaterialityCheck, check_materiality


@dataclass(frozen=True)
class BackboneRoutingDecision:
    """Backbone stay/transition verdict."""

    should_stay: bool
    current_node: str
    proposed_node: str | None
    reason: str
    materiality: MaterialityCheck
    route_kind: str = field(default="stay")


def decide_backbone_route(
    snapshot: SignalSnapshot,
    policy: AuroraPolicyVersion,
    current_node: str,
    candidate_node: str | None = None,
) -> BackboneRoutingDecision:
    """Stay on the current node unless a strong signal crosses policy materiality."""

    materiality = check_materiality(snapshot, policy)
    if not materiality.should_route:
        return BackboneRoutingDecision(
            should_stay=True,
            current_node=current_node,
            proposed_node=None,
            reason="materiality_below_threshold",
            materiality=materiality,
            route_kind="stay",
        )

    if candidate_node:
        return BackboneRoutingDecision(
            should_stay=False,
            current_node=current_node,
            proposed_node=candidate_node,
            reason=f"materiality_{materiality.basis.value}",
            materiality=materiality,
            route_kind="transition",
        )

    return BackboneRoutingDecision(
        should_stay=True,
        current_node=current_node,
        proposed_node=None,
        reason="strong_signal_without_candidate",
        materiality=materiality,
        route_kind="stay",
    )

