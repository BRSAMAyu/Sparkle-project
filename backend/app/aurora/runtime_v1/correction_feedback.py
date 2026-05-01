"""
Core: execution
Phase: adapt
Stage: T3.3.2-T3.3.3 Correction Feedback Processor — closes the loop between
user disconfirmation and model state update.

When a user selects a disconfirming predicted reply option, this processor:
1. Lowers hypothesis confidence in the relevant StateEntry
2. Records the correction in self_model via SparkleSelfModelService
3. Persists the correction via AuroraSelfCorrector
4. Returns CorrectionResult with affected states for immediate feedback

Correcting (disconfirming) lowers confidence by 0.15.
Confirming boosts confidence by 0.05.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from loguru import logger

from app.signals.types import _uid


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@dataclass
class CorrectionResult:
    """Result of processing a user correction (confirmation or disconfirmation)."""

    correction_id: str = ""
    telemetry_id: str = ""
    action: str = ""  # "confirmed" | "disconfirmed" | "freeform_correction"
    affected_state_keys: list[str] = field(default_factory=list)
    new_confidence: dict[str, float] = field(default_factory=dict)
    self_model_updated: bool = False
    correction_recorded: bool = False
    user_visible_effect: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "correction_id": self.correction_id,
            "telemetry_id": self.telemetry_id,
            "action": self.action,
            "affected_state_keys": self.affected_state_keys,
            "new_confidence": self.new_confidence,
            "self_model_updated": self.self_model_updated,
            "correction_recorded": self.correction_recorded,
            "user_visible_effect": self.user_visible_effect,
        }


# Maps semantic_value to the state_key(s) it affects.
# When a disconfirming option is selected, these states get their confidence lowered.
_SEMANTIC_TO_STATE_KEYS: dict[str, list[str]] = {
    "temporary_time_conflict": ["task_granularity_fit"],
    "knowledge_blocker": ["knowledge_bottleneck"],
    "carelessness": ["transfer_failure"],
    "ambiguous_question": ["transfer_failure"],
    "skip_material": ["material_utilization"],
    "deep_mastery": ["goal_mode"],
    "risk_temporary": ["execution_consistency"],
    "risk_wrong_diagnosis": ["execution_consistency"],
    "risk_false_positive": ["affective_pressure", "execution_consistency"],
    "risk_overstated": ["execution_consistency"],
    "strategy_too_aggressive": ["strategy_confidence"],
    "strategy_too_conservative": ["strategy_confidence"],
    "strategy_adjust_needed": ["strategy_confidence"],
    "goal_has_changed": ["goal_mode"],
    "not_now": ["aurora_wake_intent"],
    "scope_ok_low_motivation": ["affective_pressure"],
    "time_overrun_not_task": ["execution_consistency"],
    "time_overrun_today_only": ["execution_consistency"],
    "difficulty_mismatch": ["knowledge_bottleneck"],
    "genuinely_fatigued": ["affective_pressure"],
    "avoidance_not_disengaged": ["growth_momentum"],
    "freeform_correction": [],  # free-form targets resolved at runtime
    "judgment_denied": ["strategy_confidence"],
    "judgment_incorrect": ["strategy_confidence"],
    "not_right_direction": ["strategy_confidence"],
    "calibration_dismissed": ["aurora_wake_intent"],
}


# Maps disconfirming semantic values to routing-profile adjustments.
# Keys are semantic_values that indicate the user disagrees with the current
# routing stance. Values drive RoutingProfileService.record_session_outcome().
_ROUTING_CORRECTION_MAP: dict[str, dict[str, Any]] = {
    "strategy_too_aggressive": {"route_mode": "execution_first", "execution_suggestion_ignored": True},
    "strategy_adjust_needed": {"route_mode": "execution_first", "execution_suggestion_ignored": True},
    "avoidance_not_disengaged": {"route_mode": "execution_first", "execution_suggestion_ignored": True},
    "scope_ok_low_motivation": {"route_mode": "execution_first", "execution_suggestion_ignored": True},
    "genuinely_fatigued": {"route_mode": "cognitive_first", "frustration_after_cognitive": True},
    "strategy_too_conservative": {"route_mode": "cognitive_first", "frustration_after_cognitive": True},
}


class CorrectionFeedbackProcessor:
    """T3.3.2-T3.3.3: Processes user option selections and feeds corrections back
    into StateRegister and self_model.

    Confidence deltas:
    - Disconfirmation: -0.15 (floor 0.05)
    - Confirmation: +0.05 (ceiling 1.0)
    """

    CONFIDENCE_DECREASE = 0.15
    CONFIDENCE_INCREASE = 0.05

    def __init__(self, redis_client: Any, db_session_factory: Any = None):
        self.redis = redis_client
        self.db_session_factory = db_session_factory

    async def process(
        self,
        *,
        user_id: str,
        semantic_value: str,
        is_disconfirming: bool = False,
        is_freeform: bool = False,
        freeform_text: str = "",
        telemetry_id: str = "",
        context_source: str = "",
    ) -> CorrectionResult:
        """Process a user option selection.

        Disconfirming selections trigger the full correction feedback loop.
        Confirming selections receive a modest confidence boost.
        Freeform corrections create an open-ended correction entry.
        """
        result = CorrectionResult(
            correction_id=_uid("corr"),
            telemetry_id=telemetry_id,
            action="confirmed",
        )

        if is_disconfirming or is_freeform:
            result.action = "freeform_correction" if is_freeform else "disconfirmed"
            await self._process_disconfirmation(
                user_id=user_id,
                semantic_value=semantic_value,
                freeform_text=freeform_text,
                context_source=context_source,
                result=result,
            )
        else:
            await self._process_confirmation(
                user_id=user_id,
                semantic_value=semantic_value,
                result=result,
            )

        await self._update_bayesian_policy(
            user_id=user_id,
            is_disconfirming=is_disconfirming,
            is_freeform=is_freeform,
        )
        result.user_visible_effect = self._build_user_visible_effect(
            semantic_value=semantic_value,
            result=result,
        )
        return result

    def _build_user_visible_effect(
        self,
        *,
        semantic_value: str,
        result: CorrectionResult,
    ) -> dict[str, Any]:
        """Small product-facing receipt for status surfaces."""
        return {
            "visible": result.action in {"disconfirmed", "freeform_correction"},
            "semantic_value": semantic_value,
            "action": result.action,
            "affected_state_keys": result.affected_state_keys,
            "updated_at": _utcnow().isoformat(),
        }

    async def _update_bayesian_policy(
        self,
        *,
        user_id: str,
        is_disconfirming: bool,
        is_freeform: bool,
    ) -> None:
        """Feed explicit correction chips into Aurora's Stage 23 learner."""
        if self.redis is None:
            return
        try:
            from app.aurora.bayesian import AuroraBayesianLearner

            await AuroraBayesianLearner(self.redis).record_correction(
                user_id=user_id,
                is_disconfirming=is_disconfirming,
                is_freeform=is_freeform,
            )
        except Exception:
            logger.debug("CorrectionFeedback: Bayesian policy update failed", exc_info=True)

    async def _process_disconfirmation(
        self,
        *,
        user_id: str,
        semantic_value: str,
        freeform_text: str,
        context_source: str,
        result: CorrectionResult,
    ) -> None:
        """Execute the full disconfirmation pipeline."""
        from app.aurora.runtime_v1.aurora_spine_confluence import AuroraSelfCorrector
        from app.signals.state_register import StateRegister

        state_keys = _SEMANTIC_TO_STATE_KEYS.get(semantic_value, [])

        # 1. Lower StateRegister confidence for affected states
        register = StateRegister(self.redis)
        reason = freeform_text if freeform_text else f"User disconfirmed: {semantic_value}"
        for sk in state_keys:
            try:
                updated = await register.lower_confidence(
                    user_id,
                    sk,
                    amount=self.CONFIDENCE_DECREASE,
                    reason=reason,
                )
                if updated is not None:
                    result.affected_state_keys.append(sk)
                    result.new_confidence[sk] = updated.confidence
            except Exception:
                logger.debug(
                    "CorrectionFeedback: state lower_confidence failed key={}",
                    sk,
                    exc_info=True,
                )

        # 2. Record in self_model
        try:
            from app.aurora.runtime_v1.self_model import SparkleSelfModelService

            self_model = SparkleSelfModelService(self.redis)
            correction_context = {
                "semantic_value": semantic_value,
                "freeform_text": freeform_text,
                "context_source": context_source,
            }
            await self_model.record_user_correction(
                user_id=user_id,
                correction_text=json.dumps(correction_context, ensure_ascii=False),
                user_context_payload={"source": "predicted_reply_chip"},
            )
            result.self_model_updated = True
        except Exception:
            logger.debug("CorrectionFeedback: self_model update failed", exc_info=True)

        # 3. Persist correction via AuroraSelfCorrector
        try:
            corrector = AuroraSelfCorrector(self.redis)
            correction = await corrector.apply_correction(
                user_id=user_id,
                original_claim=f"Aurora hypothesis: {semantic_value}",
                corrected_claim=freeform_text or f"User rejected: {semantic_value}",
                reason=reason,
                state_patches=[
                    {
                        "state_key": sk,
                        "action": "lower_confidence",
                        "amount": self.CONFIDENCE_DECREASE,
                    }
                    for sk in state_keys
                ],
            )
            result.correction_id = correction.correction_id
            result.correction_recorded = True
        except Exception:
            logger.debug("CorrectionFeedback: correction persist failed", exc_info=True)

        # 4. Update routing profile so corrections change future routing behavior
        await self._update_routing_profile(user_id, semantic_value)

        logger.info(
            "CorrectionFeedback: disconfirmation user={} semantic={} affected_states={}",
            user_id,
            semantic_value,
            result.affected_state_keys,
        )

    async def _update_routing_profile(self, user_id: str, semantic_value: str) -> None:
        """Bridge correction → routing profile so disconfirmations change future routing."""
        routing_kwargs = _ROUTING_CORRECTION_MAP.get(semantic_value)
        if routing_kwargs is None or self.db_session_factory is None:
            return
        try:
            from uuid import UUID

            from app.services.routing_profile_service import RoutingProfileService

            async with self.db_session_factory() as session:
                svc = RoutingProfileService(session, self.redis)
                await svc.record_session_outcome(UUID(user_id), **routing_kwargs)
        except Exception:
            logger.debug(
                "CorrectionFeedback: routing profile update failed semantic={}",
                semantic_value,
                exc_info=True,
            )

    async def _process_confirmation(
        self,
        *,
        user_id: str,
        semantic_value: str,
        result: CorrectionResult,
    ) -> None:
        """Apply a modest confidence boost when user confirms a hypothesis."""
        from app.signals.state_register import StateRegister

        state_keys = _SEMANTIC_TO_STATE_KEYS.get(semantic_value, [])
        register = StateRegister(self.redis)

        for sk in state_keys:
            try:
                entry = await register.get_state(user_id, sk)
                if entry is None:
                    continue
                entry.confidence = round(min(1.0, entry.confidence + self.CONFIDENCE_INCREASE), 4)
                entry.last_updated_at = _utcnow().isoformat()
                await register._save_state(user_id, entry)
                result.affected_state_keys.append(sk)
                result.new_confidence[sk] = entry.confidence
            except Exception:
                logger.debug(
                    "CorrectionFeedback: confirmation boost failed key={}",
                    sk,
                    exc_info=True,
                )

        logger.debug(
            "CorrectionFeedback: confirmation user={} semantic={} affected={}",
            user_id,
            semantic_value,
            result.affected_state_keys,
        )
