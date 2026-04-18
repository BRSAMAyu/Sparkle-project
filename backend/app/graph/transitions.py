"""Transition policy evaluation for the Aurora graph runtime."""

from __future__ import annotations

from dataclasses import dataclass

from app.aurora.schemas import ImpactClass, TransitionDecisionRecord
from app.graph.backbone import BackbonePathResolver


_STRONG_SIGNAL_BASIS = {
    "commitment_conflict",
    "energy_drop",
    "partner_signal",
}


@dataclass(frozen=True, slots=True)
class TransitionEvaluation:
    """Outcome of a transition policy evaluation."""

    allow: bool
    target_node_id: str
    is_backbone_transition: bool
    reason: str


class TransitionPolicyEngine:
    """Evaluate whether a TDR is allowed to move the graph."""

    def evaluate(
        self,
        decision: TransitionDecisionRecord,
        current_node_id: str,
        resolver: BackbonePathResolver,
    ) -> TransitionEvaluation:
        proposed_target = decision.proposed_transition or current_node_id

        if proposed_target == current_node_id or decision.decision_type.lower() in {"stay", "no_op"}:
            return TransitionEvaluation(
                allow=True,
                target_node_id=current_node_id,
                is_backbone_transition=True,
                reason="stay_on_current_node",
            )

        if not resolver.has_node(proposed_target):
            return TransitionEvaluation(
                allow=False,
                target_node_id=current_node_id,
                is_backbone_transition=False,
                reason="unknown_target_node_rejected",
            )

        is_backbone = resolver.is_backbone_transition(current_node_id, proposed_target)

        if is_backbone:
            return TransitionEvaluation(
                allow=True,
                target_node_id=proposed_target,
                is_backbone_transition=True,
                reason="default_backbone_step",
            )

        if decision.impact_class in {ImpactClass.HIGH, ImpactClass.CRITICAL} or decision.decision_basis.value in _STRONG_SIGNAL_BASIS:
            return TransitionEvaluation(
                allow=True,
                target_node_id=proposed_target,
                is_backbone_transition=False,
                reason="strong_signal_allows_off_backbone_transition",
            )

        return TransitionEvaluation(
            allow=False,
            target_node_id=current_node_id,
            is_backbone_transition=False,
            reason="off_backbone_transition_rejected",
        )
