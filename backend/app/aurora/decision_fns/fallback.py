"""Fallback decision helpers for Aurora."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from loguru import logger

from app.aurora.observability import record_fallback
from app.aurora.schemas import (
    AuroraPresenceLevel,
    DecisionBasis,
    DecisionMechanism,
    ImpactClass,
    InitiationType,
    InteractionModelVariant,
    TransitionDecisionRecord,
    UXIntent,
)


def build_fallback_decision(
    *,
    user_id: UUID,
    snapshot_ref: str | None,
    policy_version: str | None,
    reason: str,
    trigger_point: str,
    exception: Exception | None = None,
) -> TransitionDecisionRecord:
    """Build a schema-valid NO_OP fallback record and emit an internal alert."""

    fallback_snapshot_ref = snapshot_ref or "aurora_fallback_snapshot"
    fallback_policy_version = policy_version or "aurora_policy@v1.0"
    decision_id = uuid4()
    record = TransitionDecisionRecord(
        id=decision_id,
        user_id=user_id,
        created_at=datetime.now(UTC),
        decision_type="no_op",
        proposed_transition=None,
        initiation_type=InitiationType.REACTIVE,
        decision_mechanism=DecisionMechanism.DETERMINISTIC,
        decision_basis=DecisionBasis.MIXED,
        input_snapshot_ref=fallback_snapshot_ref,
        impact_class=ImpactClass.LOW,
        inference_knobs={"fallback": True, "reason": reason},
        capability_gate={"enabled": False, "reason": reason},
        interaction_model_variant=InteractionModelVariant.DEFAULT_CONVERSATION,
        rollback_anchor={
            "prev_focus_contract_version": 0,
            "prev_active_commitment_ids": [],
            "prev_claim_statuses": {},
            "policy_version_at_decision": fallback_policy_version,
        },
        evidence_refs=["aurora_fallback"],
        policy_version=fallback_policy_version,
        confirmed_by_user=False,
        user_feedback=None,
        ux_intent=UXIntent.ROUTINE,
        aurora_presence=AuroraPresenceLevel.AMBIENT,
    )
    record_fallback(reason=reason, trigger_point=trigger_point, decision_id=str(decision_id))
    logger.bind(
        component="aurora",
        event="fallback_decision",
        reason=reason,
        trigger_point=trigger_point,
        snapshot_ref=fallback_snapshot_ref,
    ).warning("Aurora fallback decision emitted")
    if exception is not None:
        logger.bind(component="aurora", event="fallback_exception", reason=reason).opt(exception=exception).debug(
            "Aurora fallback captured exception"
        )
    return record
