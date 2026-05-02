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
from uuid import UUID

from loguru import logger

from app.aurora.correction_types import AuroraCorrectionPayload
from app.core.metrics import AURORA_CORRECTION_TO_STATE_CHANGE_TOTAL
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
    routing_feedback_recorded: bool = False
    user_visible_effect: dict[str, Any] = field(default_factory=dict)
    calibration_receipt: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "correction_id": self.correction_id,
            "telemetry_id": self.telemetry_id,
            "action": self.action,
            "affected_state_keys": self.affected_state_keys,
            "new_confidence": self.new_confidence,
            "self_model_updated": self.self_model_updated,
            "correction_recorded": self.correction_recorded,
            "routing_feedback_recorded": self.routing_feedback_recorded,
            "user_visible_effect": self.user_visible_effect,
            "calibration_receipt": self.calibration_receipt,
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


_STATE_LABELS_ZH: dict[str, str] = {
    "affective_pressure": "你当前压力或焦虑程度",
    "aurora_wake_intent": "是否需要 Aurora 主动提醒",
    "execution_consistency": "执行风险和稳定性",
    "goal_mode": "当前目标模式",
    "growth_momentum": "推进状态",
    "knowledge_bottleneck": "知识卡点",
    "material_utilization": "材料使用判断",
    "strategy_confidence": "下一步策略判断",
    "task_granularity_fit": "任务颗粒度是否合适",
    "transfer_failure": "迁移理解是否卡住",
}

_STATE_LABELS_EN: dict[str, str] = {
    "affective_pressure": "your current stress or anxiety level",
    "aurora_wake_intent": "whether Aurora should proactively remind you",
    "execution_consistency": "execution risk and consistency",
    "goal_mode": "the current goal mode",
    "growth_momentum": "your forward momentum",
    "knowledge_bottleneck": "the knowledge blocker",
    "material_utilization": "how useful the current materials are",
    "strategy_confidence": "the next-step strategy judgment",
    "task_granularity_fit": "whether the task size fits",
    "transfer_failure": "whether transfer of understanding is stuck",
}


def _state_label(state_key: str, *, locale: str) -> str:
    labels = _STATE_LABELS_EN if locale == "en" else _STATE_LABELS_ZH
    return labels.get(state_key, state_key.replace("_", " "))


def _format_confidence_change(
    *,
    state_key: str,
    new_confidence: float | None,
    confidence_delta: float,
    locale: str,
) -> str:
    label = _state_label(state_key, locale=locale)
    if new_confidence is None:
        if locale == "en":
            return f"I updated my judgment about {label}."
        return f"我更新了对「{label}」的判断。"

    previous = max(0.0, min(1.0, float(new_confidence) - confidence_delta))
    if locale == "en":
        direction = "lowered" if confidence_delta < 0 else "raised"
        return f"I {direction} my confidence about {label} from {previous:.2f} to {float(new_confidence):.2f}."
    direction = "下调" if confidence_delta < 0 else "上调"
    return f"我把「{label}」的判断置信度从 {previous:.2f} {direction}到 {float(new_confidence):.2f}。"


def _receipt_reason(*, freeform_text: str, chip_label: str, locale: str) -> str:
    reason = freeform_text.strip() or chip_label.strip()
    if reason:
        if locale == "en":
            return f'Because you corrected me with: "{reason}".'
        return f"因为你纠正了我：「{reason}」。"
    if locale == "en":
        return "Because you marked that Aurora's earlier read was not quite right."
    return "因为你标记了 Aurora 刚才的判断不够准确。"


def _receipt_next_time(*, action: str, locale: str) -> str:
    if action == "freeform_correction":
        if locale == "en":
            return "Next time a similar situation appears, I will check this interpretation before acting on it."
        return "下次遇到类似情境，我会先确认这个理解，再决定是否提醒或推进。"
    if action == "disconfirmed":
        if locale == "en":
            return (
                "Next time a similar signal appears, I will treat this judgment as less certain and ask before nudging."
            )
        return "下次出现类似信号时，我会把这个判断当作不那么确定，并先确认再提醒。"
    if locale == "en":
        return "Next time I see a similar signal, I can use this confirmation with slightly more confidence."
    return "下次看到类似信号时，我会稍微更有把握地使用这个判断。"


def generate_calibration_receipt(
    correction_result: CorrectionResult,
    *,
    semantic_value: str = "",
    freeform_text: str = "",
    chip_label: str = "",
    surface: str = "",
    timestamp: datetime | None = None,
) -> dict[str, Any]:
    """Generate a user-visible calibration receipt from the applied correction."""
    occurred_at = timestamp or _utcnow()
    action = correction_result.action
    if action == "confirmed":
        confidence_delta = CorrectionFeedbackProcessor.CONFIDENCE_INCREASE
    elif correction_result.affected_state_keys:
        confidence_delta = -CorrectionFeedbackProcessor.CONFIDENCE_DECREASE
    else:
        confidence_delta = 0.0

    affected_states = list(correction_result.affected_state_keys or [])
    first_state = affected_states[0] if affected_states else ""
    new_confidence = correction_result.new_confidence.get(first_state) if first_state else None

    if first_state:
        what_zh = _format_confidence_change(
            state_key=first_state,
            new_confidence=new_confidence,
            confidence_delta=confidence_delta,
            locale="zh",
        )
        what_en = _format_confidence_change(
            state_key=first_state,
            new_confidence=new_confidence,
            confidence_delta=confidence_delta,
            locale="en",
        )
        if len(affected_states) > 1:
            extra_zh = "、".join(_state_label(state, locale="zh") for state in affected_states[1:3])
            extra_en = ", ".join(_state_label(state, locale="en") for state in affected_states[1:3])
            what_zh = f"{what_zh} 同时也更新了「{extra_zh}」。"
            what_en = f"{what_en} I also updated {extra_en}."
    else:
        what_zh = "我记录了一条新的校准：这次判断需要按你的说明重新理解。"
        what_en = "I recorded a new calibration: this judgment should be reinterpreted using your correction."

    why_zh = _receipt_reason(freeform_text=freeform_text, chip_label=chip_label, locale="zh")
    why_en = _receipt_reason(freeform_text=freeform_text, chip_label=chip_label, locale="en")
    next_zh = _receipt_next_time(action=action, locale="zh")
    next_en = _receipt_next_time(action=action, locale="en")

    return {
        "correction_id": correction_result.correction_id,
        "what_changed": what_zh,
        "why_changed": why_zh,
        "next_time": next_zh,
        "affected_states": affected_states,
        "confidence_delta": round(confidence_delta, 4),
        "surface": surface or "unknown",
        "timestamp": occurred_at.isoformat(),
        "i18n": {
            "zh": {
                "what_changed": what_zh,
                "why_changed": why_zh,
                "next_time": next_zh,
            },
            "en": {
                "what_changed": what_en,
                "why_changed": why_en,
                "next_time": next_en,
            },
        },
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
        semantic_value: str = "",
        is_disconfirming: bool = False,
        is_freeform: bool = False,
        freeform_text: str = "",
        telemetry_id: str = "",
        context_source: str = "",
        correction_payload: AuroraCorrectionPayload | dict[str, Any] | None = None,
    ) -> CorrectionResult:
        """Process a user option selection.

        Disconfirming selections trigger the full correction feedback loop.
        Confirming selections receive a modest confidence boost.
        Freeform corrections create an open-ended correction entry.
        """
        if isinstance(correction_payload, AuroraCorrectionPayload):
            payload = correction_payload
        elif isinstance(correction_payload, dict):
            payload = AuroraCorrectionPayload.normalize(correction_payload)
        else:
            payload = AuroraCorrectionPayload.normalize(
                semantic_value=semantic_value,
                is_disconfirming=is_disconfirming,
                is_freeform=is_freeform,
                freeform_text=freeform_text,
                telemetry_id=telemetry_id,
                context_source=context_source or None,
            )
        semantic_value = payload.semantic_value
        is_disconfirming = payload.is_disconfirming
        is_freeform = payload.is_freeform
        freeform_text = payload.freeform_text
        telemetry_id = payload.telemetry_id

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
                context_source=payload.source or context_source,
                correction_payload=payload,
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
            payload=payload,
            result=result,
        )
        result.calibration_receipt = generate_calibration_receipt(
            result,
            semantic_value=payload.semantic_value,
            freeform_text=payload.freeform_text,
            chip_label=payload.label,
            surface=payload.surface,
        )
        await self._persist_calibration_receipt(
            user_id=user_id,
            receipt=result.calibration_receipt,
            session_id=payload.conversation_id,
        )
        AURORA_CORRECTION_TO_STATE_CHANGE_TOTAL.labels(
            surface=payload.surface or "unknown",
            action=result.action,
            changed=(
                "true"
                if result.affected_state_keys or result.self_model_updated or result.correction_recorded
                else "false"
            ),
        ).inc()
        return result

    async def _persist_calibration_receipt(
        self,
        *,
        user_id: str,
        receipt: dict[str, Any],
        session_id: str = "",
    ) -> None:
        if not receipt:
            return
        try:
            from app.services.memory_service import MemoryService

            await MemoryService(None, self.redis).record_calibration_receipt(
                user_id=user_id,
                receipt=receipt,
            )
        except Exception:
            logger.debug("CorrectionFeedback: recent correction receipt persist failed", exc_info=True)

        if self.redis is None or not session_id:
            return
        try:
            from app.working_memory.service import WorkingMemoryService

            text = " ".join(
                part
                for part in (
                    str(receipt.get("what_changed") or "").strip(),
                    str(receipt.get("next_time") or "").strip(),
                )
                if part
            )
            if not text:
                return
            await WorkingMemoryService(self.redis).upsert_entry(
                user_id=user_id,
                session_id=session_id,
                text=text,
                semantic_key=f"calibration_receipt:{receipt.get('correction_id') or _uid('corr')}",
                salience_score=0.82,
                subject_type="aurora_correction",
                confidence=0.9,
                evidence_token=str(receipt.get("correction_id") or ""),
                occurred_at=_utcnow(),
                source_turn_id=str(receipt.get("correction_id") or ""),
                source_lane="aurora_calibration_receipt",
            )
        except Exception:
            logger.debug("CorrectionFeedback: working memory receipt write failed", exc_info=True)

    def _build_user_visible_effect(
        self,
        *,
        payload: AuroraCorrectionPayload,
        result: CorrectionResult,
    ) -> dict[str, Any]:
        """Small product-facing receipt for status surfaces."""
        return {
            "visible": result.action in {"disconfirmed", "freeform_correction"},
            "semantic_value": payload.semantic_value,
            "action": result.action,
            "surface": payload.surface,
            "source": payload.source,
            "conversation_id": payload.conversation_id,
            "message_id": payload.message_id,
            "affected_state_keys": result.affected_state_keys,
            "routing_feedback_recorded": result.routing_feedback_recorded,
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
        correction_payload: AuroraCorrectionPayload,
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
                **correction_payload.to_dict(),
                "context_source": context_source,
            }
            await self_model.record_user_correction(
                user_id=user_id,
                correction_text=json.dumps(correction_context, ensure_ascii=False),
                user_context_payload={
                    "source": correction_payload.source,
                    "surface": correction_payload.surface,
                    "conversation_id": correction_payload.conversation_id,
                    "message_id": correction_payload.message_id,
                },
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
        await self._record_routing_correction_outcome(
            user_id=user_id,
            correction_payload=correction_payload,
            result=result,
        )

        logger.info(
            "CorrectionFeedback: disconfirmation user={} semantic={} affected_states={}",
            user_id,
            semantic_value,
            result.affected_state_keys,
        )

    async def _record_routing_correction_outcome(
        self,
        *,
        user_id: str,
        correction_payload: AuroraCorrectionPayload,
        result: CorrectionResult,
    ) -> None:
        """Mark the related DualCore route as failed when a correction carries trace ids."""
        if self.db_session_factory is None:
            return
        decision_id = str(correction_payload.route_history_decision_id or "").strip()
        signal_id = str(correction_payload.routing_outcome_signal_id or "").strip()
        if not decision_id and not signal_id:
            return
        outcome_signal_id = (
            correction_payload.telemetry_id or result.telemetry_id or result.correction_id or "aurora_correction"
        )
        try:
            from sqlalchemy import select
            from sqlalchemy.orm.attributes import flag_modified

            from app.models.intervention_adaptive import PassiveSignal
            from app.scaffolding.scaffolding_fsm import ScaffoldingFSM
            from app.services.route_history_service import RouteHistoryService

            async with self.db_session_factory() as session:
                parsed_user_id = UUID(user_id)
                recorded = False
                if decision_id:
                    updated = await RouteHistoryService(session).record_user_correction(
                        decision_id=UUID(decision_id),
                        outcome_signal_id=outcome_signal_id,
                    )
                    recorded = updated is not None
                if signal_id:
                    signal = (
                        await session.execute(
                            select(PassiveSignal).where(
                                PassiveSignal.id == UUID(signal_id),
                                PassiveSignal.user_id == parsed_user_id,
                                PassiveSignal.signal_type == "routing_decision",
                            )
                        )
                    ).scalar_one_or_none()
                    if signal is not None:
                        context = dict(signal.context or {})
                        context["outcome_recorded"] = True
                        context["outcome_success"] = False
                        context["outcome_reason"] = "explicit_user_correction_after_routing"
                        context["outcome_signal_id"] = outcome_signal_id
                        context["corrected_at"] = _utcnow().isoformat()
                        signal.context = context
                        flag_modified(signal, "context")
                        await ScaffoldingFSM(session).apply_feedback(
                            parsed_user_id,
                            success=False,
                            feedback="explicit_user_correction_after_routing",
                            weight=1.25,
                        )
                        await session.commit()
                        recorded = True
                result.routing_feedback_recorded = recorded
        except Exception:
            logger.debug("CorrectionFeedback: route outcome backfill failed", exc_info=True)

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
