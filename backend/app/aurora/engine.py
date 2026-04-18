"""Aurora runtime helpers for deterministic routing and fallback handling."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from app.aurora.config import DEFAULT_AURORA_CONFIG, AuroraRuntimeConfig
from app.aurora.decision_fns import (
    BackboneRoutingDecision,
    MaterialityCheck,
    TriggerDispatch,
    build_fallback_decision,
    check_materiality,
    decide_backbone_route,
)
from app.aurora.decision_fns import (
    dispatch_trigger as resolve_trigger_dispatch,
)
from app.aurora.observability import record_decision, record_fallback, record_materiality, record_trigger_dispatch
from app.aurora.policy_loader import load_policy_version
from app.aurora.schemas import (
    AuroraPolicyVersion,
    AuroraPresenceLevel,
    DecisionBasis,
    DecisionMechanism,
    ImpactClass,
    InitiationType,
    InteractionModelVariant,
    SignalSnapshot,
    TransitionDecisionRecord,
    UXIntent,
)


@dataclass(frozen=True)
class AuroraDecisionContext:
    """Input bundle for Aurora routing helpers."""

    snapshot: SignalSnapshot | None
    trigger_point: str
    current_node: str
    policy_version: AuroraPolicyVersion | None = None
    candidate_node: str | None = None
    mode: str = field(default_factory=lambda: DEFAULT_AURORA_CONFIG.mode)
    prior_outputs: dict[str, Any] = field(default_factory=dict)


class AuroraEngine:
    """Small deterministic control-plane facade."""

    def __init__(self, config: AuroraRuntimeConfig | None = None) -> None:
        self.config = config or DEFAULT_AURORA_CONFIG

    def load_policy(
        self,
        policy_version: str | None = None,
        policy_path: str | Path | None = None,
    ) -> AuroraPolicyVersion:
        return load_policy_version(policy_version=policy_version, policy_path=policy_path)

    def materiality_check(self, snapshot: SignalSnapshot, policy: AuroraPolicyVersion) -> MaterialityCheck:
        check = check_materiality(snapshot, policy)
        record_materiality(trigger_point="pre-node-routing", outcome="pass" if check.should_route else "skip")
        return check

    def decide_backbone_route(self, context: AuroraDecisionContext) -> BackboneRoutingDecision:
        policy = context.policy_version or self.load_policy(context.snapshot.policy_version if context.snapshot else None)
        if context.snapshot is None:
            return BackboneRoutingDecision(
                should_stay=True,
                current_node=context.current_node,
                proposed_node=None,
                reason="missing_snapshot",
                materiality=MaterialityCheck(
                    should_route=False,
                    score=0.0,
                    threshold=float(policy.materiality_threshold),
                    basis=DecisionBasis.MIXED,
                ),
                route_kind="stay",
            )
        decision = decide_backbone_route(
            snapshot=context.snapshot,
            policy=policy,
            current_node=context.current_node,
            candidate_node=context.candidate_node,
        )
        record_decision(
            trigger_point=context.trigger_point,
            mechanism="deterministic",
            basis=decision.materiality.basis.value,
            mode=context.mode,
            outcome=decision.route_kind,
        )
        return decision

    def dispatch_trigger(self, trigger: str):
        dispatch: TriggerDispatch = resolve_trigger_dispatch(trigger)
        record_trigger_dispatch(
            initiation_type=dispatch.initiation_type.value,
            trigger_point=dispatch.trigger_point,
            dispatch_mode=dispatch.dispatch_mode,
        )
        return dispatch

    def build_fallback_decision(
        self,
        context: AuroraDecisionContext,
        reason: str,
        exception: Exception | None = None,
    ) -> TransitionDecisionRecord:
        snapshot_ref = context.snapshot.snapshot_hash if context.snapshot is not None else None
        user_id = context.snapshot.user_id if context.snapshot is not None else UUID(int=0)
        policy_version = context.snapshot.policy_version if context.snapshot is not None else None
        record = build_fallback_decision(
            user_id=user_id,
            snapshot_ref=snapshot_ref,
            policy_version=policy_version,
            reason=reason,
            trigger_point=context.trigger_point,
            exception=exception,
        )
        record_fallback(reason=reason, trigger_point=context.trigger_point, decision_id=str(record.id), enabled=True)
        return record

    def _build_stay_decision(
        self,
        context: AuroraDecisionContext,
        route: BackboneRoutingDecision,
    ) -> TransitionDecisionRecord:
        policy = context.policy_version or self.load_policy(context.snapshot.policy_version)
        impact_class = ImpactClass.LOW if not route.materiality.should_route else ImpactClass.MEDIUM
        return TransitionDecisionRecord(
            id=uuid4(),
            user_id=context.snapshot.user_id,
            created_at=context.snapshot.collected_at,
            decision_type="stay",
            proposed_transition=None,
            initiation_type=InitiationType.REACTIVE,
            decision_mechanism=DecisionMechanism.DETERMINISTIC,
            decision_basis=route.materiality.basis,
            input_snapshot_ref=context.snapshot.snapshot_hash,
            impact_class=impact_class,
            inference_knobs={"route_kind": route.route_kind, "reason": route.reason},
            capability_gate={"enabled": True, "stay": True, "route": context.current_node},
            interaction_model_variant=InteractionModelVariant.DEFAULT_CONVERSATION,
            rollback_anchor={
                "prev_focus_contract_version": 0,
                "prev_active_commitment_ids": [],
                "prev_claim_statuses": {},
                "policy_version_at_decision": policy.id,
            },
            evidence_refs=["aurora_route"],
            policy_version=policy.id,
            confirmed_by_user=None,
            user_feedback=None,
            ux_intent=UXIntent.ROUTINE,
            aurora_presence=AuroraPresenceLevel.AMBIENT,
        )

    def _build_transition_decision(
        self,
        context: AuroraDecisionContext,
        route: BackboneRoutingDecision,
    ) -> TransitionDecisionRecord:
        policy = context.policy_version or self.load_policy(context.snapshot.policy_version)
        if context.trigger_point == "pre-tool-selection":
            initiation_type = InitiationType.SCHEDULED
        elif context.trigger_point == "pre-response-formatting":
            initiation_type = InitiationType.ON_DEMAND
        else:
            initiation_type = InitiationType.REACTIVE
        return TransitionDecisionRecord(
            id=uuid4(),
            user_id=context.snapshot.user_id,
            created_at=context.snapshot.collected_at,
            decision_type="transition",
            proposed_transition=route.proposed_node,
            initiation_type=initiation_type,
            decision_mechanism=DecisionMechanism.DETERMINISTIC,
            decision_basis=route.materiality.basis,
            input_snapshot_ref=context.snapshot.snapshot_hash,
            impact_class=ImpactClass.HIGH if route.materiality.should_route else ImpactClass.MEDIUM,
            inference_knobs={"route_kind": route.route_kind},
            capability_gate={"enabled": True, "route": route.proposed_node},
            interaction_model_variant=InteractionModelVariant.DEFAULT_CONVERSATION,
            rollback_anchor={
                "prev_focus_contract_version": 0,
                "prev_active_commitment_ids": [],
                "prev_claim_statuses": {},
                "policy_version_at_decision": policy.id,
            },
            evidence_refs=["aurora_route"],
            policy_version=policy.id,
            confirmed_by_user=None,
            user_feedback=None,
            ux_intent=UXIntent.ACTIVE_ADJUSTMENT,
            aurora_presence=AuroraPresenceLevel.ACTIVE,
        )

    def safe_route(self, context: AuroraDecisionContext) -> TransitionDecisionRecord:
        """Best-effort fallback wrapper for callers that need a decision record."""

        try:
            route = self.decide_backbone_route(context)
        except Exception as exc:  # pragma: no cover - defensive wrapper
            return self.build_fallback_decision(context, reason="decision_failure", exception=exc)

        if context.snapshot is None:
            return self.build_fallback_decision(context, reason=route.reason)

        if route.should_stay or route.proposed_node is None:
            return self._build_stay_decision(context, route)

        return self._build_transition_decision(context, route)
