from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from loguru import logger
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.aurora.runtime_v1.dashboard import DashboardReadout, DashboardReadoutBuilder, canonicalize_runtime_domain
from app.aurora.runtime_v1.models import AuroraDecisionTelemetry

if TYPE_CHECKING:
    from app.aurora.runtime_v1.decision_loop import AuroraDecision
    from app.aurora.runtime_v1.service import AuroraRuntimeTurnPlan


RETENTION_DAYS = 90
WAKE_THRESHOLD_MEDIUM = 0.45
WAKE_THRESHOLD_FULL = 0.72
DEFAULT_STRATEGY_CONFIDENCE = 0.7

STRATEGY_FIELDS = (
    "concept_first",
    "problem_first",
    "worked_example_first",
    "retrieval_practice",
    "interleaving",
    "spaced_review",
    "error_analysis_required",
    "drop_low_roi_topics",
    "new_topic_allowed",
)

_CORRECTION_MARKERS = (
    "你理解错",
    "理解错",
    "你误会",
    "误会了",
    "不是这个意思",
    "不是这个情况",
    "不是准备考试",
    "你搞错",
    "纠正一下",
    "更正一下",
    "说错了",
)
_TIMEOUT_MARKERS = (
    "没做完",
    "没完成",
    "来不及",
    "没时间",
    "时间不够",
    "超时",
    "做不完",
    "还没做",
    "卡住了",
    "推迟了",
)
_SKIP_MARKERS = (
    "跳过",
    "先不",
    "先别",
    "稍后再",
    "之后再",
    "晚点再",
    "回头再",
    "先放着",
    "暂时不",
    "不想聊",
)
_COMPLETED_MARKERS = (
    "完成了",
    "做完了",
    "搞定了",
    "补完了",
    "解决了",
    "弄完了",
    "会了",
    "明白了",
    "学完了",
    "已经做了",
    "刚做完",
)
_ACK_ONLY_MARKERS = {
    "好",
    "好的",
    "嗯",
    "嗯嗯",
    "收到",
    "知道了",
    "ok",
    "okay",
}

_EXPLICIT_OUTCOME_ALIASES = {
    "task_completed": "task_completed",
    "task_completion": "task_completed",
    "completed": "task_completed",
    "success": "task_completed",
    "timeout": "timeout",
    "timed_out": "timeout",
    "late": "timeout",
    "skipped": "skipped",
    "skip": "skipped",
    "user_corrected": "user_corrected",
    "corrected": "user_corrected",
    "correction": "user_corrected",
}


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _clamp_unit(value: Any, *, default: float = 0.0) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = float(default)
    return round(max(0.0, min(1.0, numeric)), 4)


def _strip(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _safe_days_remaining(value: Any) -> int | None:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_count(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


@dataclass(frozen=True)
class ClassifiedOutcome:
    outcome: str
    reason: str


class AuroraDecisionTelemetryService:
    """Persist Aurora turn decisions and backfill the previous turn's observed outcome."""

    def __init__(self, db: AsyncSession, *, retention_days: int = RETENTION_DAYS) -> None:
        self.db = db
        self.retention_days = max(1, int(retention_days))
        self.dashboard_builder = DashboardReadoutBuilder()

    async def record_turn(
        self,
        *,
        user_id: str,
        surface: str,
        conversation_id: str,
        request_id: str,
        user_message: str,
        request_extra_context: dict[str, Any] | None,
        readout: DashboardReadout,
        decision: AuroraDecision,
        plan: AuroraRuntimeTurnPlan,
        decided_at: datetime | None = None,
    ) -> dict[str, Any] | None:
        user_uuid = self._coerce_uuid(user_id)
        if user_uuid is None:
            return None

        now = decided_at or _utcnow()
        request_extra_context = dict(request_extra_context or {})

        try:
            await self._cleanup_expired(now=now)
            await self._backfill_previous_outcome(
                user_id=user_uuid,
                conversation_id=conversation_id,
                request_id=request_id,
                user_message=user_message,
                request_extra_context=request_extra_context,
                observed_at=now,
            )

            action_context = self._action_context_payload(readout=readout, decision=decision)
            control_signal = self._build_control_signal(
                readout=readout,
                decision=decision,
                plan=plan,
                request_extra_context=request_extra_context,
            )

            record = AuroraDecisionTelemetry(
                decision_id=str(uuid4()),
                user_id=user_uuid,
                surface=surface,
                conversation_id=str(conversation_id),
                request_id=_strip(request_id) or None,
                decided_at=now,
                wake_score=control_signal["wake_score"],
                energy_level=control_signal["energy_level"],
                strategy_payload=control_signal["strategy"],
                expression_payload=control_signal["expression"],
                context_mask=sorted(action_context.keys()),
                action=str(decision.action or "wait"),
                chat_directive_core=self._chat_directive_core(decision.chat_directive),
                standard_layer_contract=control_signal["standard_layer_contract"],
                strategy_confidence=_clamp_unit(
                    (readout.self_model or {}).get("strategy_confidence"),
                    default=DEFAULT_STRATEGY_CONFIDENCE,
                ),
            )
            self.db.add(record)
            await self.db.commit()
            await self.db.refresh(record)
            return {
                "decision_id": str(record.decision_id),
                "wake_score": float(record.wake_score or 0.0),
                "energy_level": str(record.energy_level or "light"),
            }
        except Exception as exc:
            await self.db.rollback()
            logger.warning("Aurora runtime telemetry write failed for user {}: {}", user_id, exc)
            return None

    async def build_summary(self, *, days: int = 30) -> dict[str, Any]:
        now = _utcnow()
        await self._cleanup_expired(now=now)
        await self.db.commit()

        window_days = max(1, min(int(days or 30), self.retention_days))
        since = now - timedelta(days=window_days)
        stmt = (
            select(AuroraDecisionTelemetry)
            .where(
                AuroraDecisionTelemetry.deleted_at.is_(None),
                AuroraDecisionTelemetry.decided_at >= since,
            )
            .order_by(AuroraDecisionTelemetry.decided_at.desc())
        )
        rows = list((await self.db.execute(stmt)).scalars().all())

        strategy_distribution = {
            field: {"true": 0, "false": 0, "missing": 0}
            for field in STRATEGY_FIELDS
        }
        wake_buckets = {"lt_0_45": 0, "0_45_to_0_72": 0, "gte_0_72": 0}
        by_energy_level = {"silent": 0, "light": 0, "medium": 0, "full": 0}
        by_surface: dict[str, int] = {}
        by_action: dict[str, int] = {}
        by_outcome = {"task_completed": 0, "timeout": 0, "skipped": 0, "user_corrected": 0, "pending": 0}

        wake_score_total = 0.0
        resolved_rows: list[AuroraDecisionTelemetry] = []
        escalated_rows: list[AuroraDecisionTelemetry] = []

        for row in rows:
            strategy_payload = dict(row.strategy_payload or {})
            for field in STRATEGY_FIELDS:
                if field not in strategy_payload:
                    strategy_distribution[field]["missing"] += 1
                elif bool(strategy_payload.get(field)):
                    strategy_distribution[field]["true"] += 1
                else:
                    strategy_distribution[field]["false"] += 1

            score = float(row.wake_score or 0.0)
            wake_score_total += score
            if score < WAKE_THRESHOLD_MEDIUM:
                wake_buckets["lt_0_45"] += 1
            elif score < WAKE_THRESHOLD_FULL:
                wake_buckets["0_45_to_0_72"] += 1
            else:
                wake_buckets["gte_0_72"] += 1

            level = str(row.energy_level or "light")
            by_energy_level[level] = by_energy_level.get(level, 0) + 1
            by_surface[str(row.surface or "unknown")] = by_surface.get(str(row.surface or "unknown"), 0) + 1
            by_action[str(row.action or "wait")] = by_action.get(str(row.action or "wait"), 0) + 1

            outcome = str(row.outcome or "").strip()
            if not outcome:
                by_outcome["pending"] += 1
            else:
                by_outcome[outcome] = by_outcome.get(outcome, 0) + 1
                resolved_rows.append(row)

            if level in {"medium", "full"}:
                escalated_rows.append(row)

        resolved_count = len(resolved_rows)
        escalated_resolved = [row for row in escalated_rows if row.outcome]
        successful_count = _safe_count(by_outcome.get("task_completed"))
        escalated_success = sum(1 for row in escalated_resolved if row.outcome == "task_completed")
        escalated_error = sum(1 for row in escalated_resolved if row.outcome in {"timeout", "skipped", "user_corrected"})

        return {
            "days": window_days,
            "window_start": since.isoformat(),
            "window_end": now.isoformat(),
            "total_decisions": len(rows),
            "strategy_distribution": strategy_distribution,
            "wake_frequency": {
                "average_wake_score": round(wake_score_total / max(len(rows), 1), 4),
                "wake_score_buckets": wake_buckets,
                "by_energy_level": by_energy_level,
                "by_surface": by_surface,
                "by_action": by_action,
            },
            "accuracy": {
                "resolved_count": resolved_count,
                "outcome_breakdown": by_outcome,
                "success_rate": round(successful_count / max(resolved_count, 1), 4),
                "upgrade_accuracy": round(escalated_success / max(len(escalated_resolved), 1), 4),
                "error_upgrade_rate": round(escalated_error / max(len(escalated_resolved), 1), 4),
            },
        }

    async def _backfill_previous_outcome(
        self,
        *,
        user_id: UUID,
        conversation_id: str,
        request_id: str,
        user_message: str,
        request_extra_context: dict[str, Any],
        observed_at: datetime,
    ) -> None:
        previous_stmt = (
            select(AuroraDecisionTelemetry)
            .where(
                AuroraDecisionTelemetry.deleted_at.is_(None),
                AuroraDecisionTelemetry.user_id == user_id,
                AuroraDecisionTelemetry.conversation_id == str(conversation_id),
                AuroraDecisionTelemetry.outcome.is_(None),
                AuroraDecisionTelemetry.decided_at < observed_at,
            )
            .order_by(AuroraDecisionTelemetry.decided_at.desc(), AuroraDecisionTelemetry.created_at.desc())
            .limit(1)
        )
        previous = (await self.db.execute(previous_stmt)).scalar_one_or_none()
        if previous is None:
            return

        classified = self._classify_outcome(
            previous=previous,
            user_message=user_message,
            request_extra_context=request_extra_context,
        )
        previous.outcome = classified.outcome
        previous.outcome_reason = classified.reason
        previous.outcome_filled_at = observed_at
        previous.request_id = previous.request_id or (_strip(request_id) or None)

    async def _cleanup_expired(self, *, now: datetime) -> None:
        cutoff = now - timedelta(days=self.retention_days)
        await self.db.execute(
            delete(AuroraDecisionTelemetry).where(AuroraDecisionTelemetry.decided_at < cutoff)
        )

    def _classify_outcome(
        self,
        *,
        previous: AuroraDecisionTelemetry,
        user_message: str,
        request_extra_context: dict[str, Any],
    ) -> ClassifiedOutcome:
        explicit = self._explicit_outcome(request_extra_context)
        if explicit is not None:
            return explicit

        normalized_message = _strip(user_message).lower()
        if not normalized_message:
            return ClassifiedOutcome(outcome="skipped", reason="empty_follow_up_turn")
        if any(marker in normalized_message for marker in _CORRECTION_MARKERS):
            return ClassifiedOutcome(outcome="user_corrected", reason="user_message_signaled_correction")
        if any(marker in normalized_message for marker in _TIMEOUT_MARKERS):
            return ClassifiedOutcome(outcome="timeout", reason="user_message_signaled_timeout")
        if any(marker in normalized_message for marker in _SKIP_MARKERS):
            return ClassifiedOutcome(outcome="skipped", reason="user_message_signaled_skip")
        if any(marker in normalized_message for marker in _COMPLETED_MARKERS):
            return ClassifiedOutcome(outcome="task_completed", reason="user_message_signaled_completion")

        if normalized_message in _ACK_ONLY_MARKERS:
            return ClassifiedOutcome(outcome="skipped", reason="ack_without_new_signal")

        target_domain = self._extract_target_domain(dict(previous.chat_directive_core or {}))
        inferred_domains = self.dashboard_builder._infer_domains_from_text(normalized_message)
        if target_domain and (
            target_domain in inferred_domains
            or self.dashboard_builder._source_has_domain_evidence(target_domain, request_extra_context)
        ):
            return ClassifiedOutcome(outcome="task_completed", reason=f"user_supplied_{target_domain}_signal")

        if len(normalized_message) >= 4 and str(previous.action or "") in {"emit_message", "soft_return_topic"}:
            return ClassifiedOutcome(outcome="task_completed", reason="substantive_follow_up_after_visible_prompt")

        return ClassifiedOutcome(outcome="skipped", reason="no_positive_alignment_signal")

    def _explicit_outcome(self, request_extra_context: dict[str, Any]) -> ClassifiedOutcome | None:
        candidates = (
            request_extra_context.get("aurora_telemetry_outcome"),
            request_extra_context.get("aurora_outcome"),
            request_extra_context.get("telemetry_outcome"),
        )
        for candidate in candidates:
            if isinstance(candidate, dict):
                normalized = _EXPLICIT_OUTCOME_ALIASES.get(_strip(candidate.get("outcome") or candidate.get("status")).lower())
                if normalized:
                    return ClassifiedOutcome(outcome=normalized, reason="explicit_turn_outcome")
            else:
                normalized = _EXPLICIT_OUTCOME_ALIASES.get(_strip(candidate).lower())
                if normalized:
                    return ClassifiedOutcome(outcome=normalized, reason="explicit_turn_outcome")
        return None

    def _build_control_signal(
        self,
        *,
        readout: DashboardReadout,
        decision: AuroraDecision,
        plan: AuroraRuntimeTurnPlan,
        request_extra_context: dict[str, Any],
    ) -> dict[str, Any]:
        strategy = self._strategy_payload(readout=readout, decision=decision)
        expression = self._expression_payload(readout=readout, plan=plan, decision=decision)
        wake_payload = dict(plan.wake_policy or getattr(readout, "wake_policy", {}) or {})
        wake_score = self._wake_score(
            readout=readout,
            decision=decision,
            request_extra_context=request_extra_context,
            wake_payload=wake_payload,
        )
        energy_level = self._normalize_energy_level(wake_payload.get("energy")) or self._energy_level_for_wake_score(wake_score)
        standard_layer_contract = self._standard_layer_contract(
            readout=readout,
            decision=decision,
            plan=plan,
            strategy=strategy,
            expression=expression,
            request_extra_context=request_extra_context,
        )
        return {
            "wake_score": wake_score,
            "energy_level": energy_level,
            "strategy": strategy,
            "expression": expression,
            "standard_layer_contract": standard_layer_contract,
        }

    def _wake_score(
        self,
        *,
        readout: DashboardReadout,
        decision: AuroraDecision,
        request_extra_context: dict[str, Any],
        wake_payload: dict[str, Any],
    ) -> float:
        wake_score = _safe_float(wake_payload.get("wake_score"))
        if wake_score is not None:
            return _clamp_unit(wake_score)

        sprint_summary = dict(readout.sprint_policy_summary or {})
        days_remaining = _safe_days_remaining(sprint_summary.get("days_remaining"))
        mode = _strip(sprint_summary.get("mode")).lower()
        exam_urgency = 0.25
        if days_remaining is not None:
            if days_remaining <= 1:
                exam_urgency = 1.0
            elif days_remaining <= 3:
                exam_urgency = 0.9
            elif days_remaining <= 7:
                exam_urgency = 0.8
            elif days_remaining <= 14:
                exam_urgency = 0.6
            else:
                exam_urgency = 0.35
        if mode == "seven_day_survival":
            exam_urgency = max(exam_urgency, 0.85)

        lowered_message = _strip(readout.user_message).lower()
        plan_drift = 0.2 if any(token in lowered_message for token in ("落后", "偏了", "没跟上", "来不及")) else 0.0
        if str(decision.action or "") in {"soft_return_topic", "schedule_wake"}:
            plan_drift = max(plan_drift, 0.45)
        if readout.surface == "aurora_checkpoint":
            plan_drift = max(plan_drift, 0.55)

        self_model = dict(readout.self_model or {})
        learning_failure_signal = min(
            1.0,
            max(
                float(_safe_count(self_model.get("task_failure_streak"))) / 3.0,
                1.0 - _clamp_unit(self_model.get("strategy_confidence"), default=DEFAULT_STRATEGY_CONFIDENCE),
            ),
        )

        state_conflict = min(1.0, len(readout.informational_tensions) / 4.0)
        if self_model.get("needs_recalibration"):
            state_conflict = max(state_conflict, 0.6)

        user_distress = 0.0
        if any(token in lowered_message for token in ("焦虑", "崩溃", "慌", "压力", "来不及", "烦")):
            user_distress = 0.7
        elif any(token in lowered_message for token in ("卡住", "不会", "看不懂", "没时间")):
            user_distress = 0.45

        standard_layer_uncertainty = min(
            1.0,
            max(
                len(readout.missing_domains) / 5.0,
                1.0 - _clamp_unit(self_model.get("strategy_confidence"), default=DEFAULT_STRATEGY_CONFIDENCE),
            ),
        )
        if request_extra_context.get("standard_layer_contract"):
            standard_layer_uncertainty = max(0.0, standard_layer_uncertainty - 0.1)

        wake_score = (
            0.25 * exam_urgency
            + 0.20 * plan_drift
            + 0.20 * learning_failure_signal
            + 0.15 * state_conflict
            + 0.10 * user_distress
            + 0.10 * standard_layer_uncertainty
        )
        return _clamp_unit(wake_score)

    @staticmethod
    def _energy_level_for_wake_score(wake_score: float) -> str:
        if wake_score >= WAKE_THRESHOLD_FULL:
            return "full"
        if wake_score >= WAKE_THRESHOLD_MEDIUM:
            return "medium"
        return "light"

    @staticmethod
    def _normalize_energy_level(value: Any) -> str | None:
        normalized = _strip(value).lower()
        if not normalized:
            return None
        if normalized == "moderate":
            return "medium"
        return normalized

    def _strategy_payload(self, *, readout: DashboardReadout, decision: AuroraDecision) -> dict[str, Any]:
        payload = dict((decision.harness_updates or {}).get("strategy") or {})
        if not payload:
            payload = dict((readout.activity_profile or {}).get("strategy") or {})
        return {field: bool(payload.get(field)) for field in STRATEGY_FIELDS}

    def _expression_payload(
        self,
        *,
        readout: DashboardReadout,
        plan: AuroraRuntimeTurnPlan,
        decision: AuroraDecision,
    ) -> dict[str, Any]:
        expression = dict((plan.activity_profile or {}).get("expression") or {})
        if not expression:
            expression = dict((readout.activity_profile or {}).get("expression") or {})
        override = dict((decision.harness_updates or {}).get("expression") or {})
        expression.update(override)
        return expression

    def _standard_layer_contract(
        self,
        *,
        readout: DashboardReadout,
        decision: AuroraDecision,
        plan: AuroraRuntimeTurnPlan,
        strategy: dict[str, Any],
        expression: dict[str, Any],
        request_extra_context: dict[str, Any],
    ) -> dict[str, Any]:
        explicit = request_extra_context.get("standard_layer_contract")
        if isinstance(explicit, dict) and explicit:
            return dict(explicit)

        must_include: list[str] = []
        must_not_include: list[str] = []

        if strategy.get("worked_example_first"):
            must_include.append("one_worked_example")
        if strategy.get("retrieval_practice"):
            must_include.append("retrieval_check")
        if strategy.get("error_analysis_required"):
            must_include.append("error_check")
        if plan.surface_complete:
            must_include.append("completion_check")

        if readout.surface == "aurora_modeling" and not plan.surface_complete:
            must_not_include.append("full_week_replan")
        if _clamp_unit(expression.get("brevity"), default=0.6) >= 0.75:
            must_not_include.append("long_motivational_speech")
        if decision.action == "wait":
            must_not_include.append("user_visible_message")

        response_type = "task_help"
        if decision.action == "wait":
            response_type = "silent"
        elif decision.action == "schedule_wake":
            response_type = "follow_up"
        elif decision.action == "soft_return_topic":
            response_type = "topic_recovery"
        elif readout.surface == "aurora_modeling" and not plan.surface_complete:
            response_type = "clarifying_question"
        elif readout.surface == "aurora_planning":
            response_type = "plan_guidance"

        return {
            "response_type": response_type,
            "must_include": must_include,
            "must_not_include": must_not_include,
        }

    def _action_context_payload(self, *, readout: DashboardReadout, decision: AuroraDecision) -> dict[str, Any]:
        payload = readout.to_llm_payload(action=str(decision.action or "emit_message"))
        surface_state = self._surface_state(readout)
        if surface_state:
            payload["surface_state"] = surface_state
        return payload

    @staticmethod
    def _surface_state(readout: DashboardReadout) -> dict[str, Any]:
        request_context = readout.request_extra_context if isinstance(readout.request_extra_context, dict) else {}
        surface_state: dict[str, Any] = {}

        direct_state = request_context.get("surface_state")
        if isinstance(direct_state, dict):
            surface_state.update(direct_state)

        detour_scaffold = request_context.get("planning_detour_scaffold")
        if isinstance(detour_scaffold, dict):
            scaffold_state = detour_scaffold.get("surface_state")
            if isinstance(scaffold_state, dict):
                surface_state.update(scaffold_state)
            if readout.surface == "aurora_planning" and (
                detour_scaffold.get("recent_detours") or detour_scaffold.get("top_latent_thread")
            ):
                surface_state.setdefault("in_detour", True)

        return surface_state

    @staticmethod
    def _chat_directive_core(chat_directive: dict[str, Any] | None) -> dict[str, Any]:
        directive = dict(chat_directive or {})
        keep_keys = {"intent", "target_domain", "question_domain", "domain", "thread_id", "reason"}
        return {
            key: value
            for key, value in directive.items()
            if key in keep_keys and value not in (None, "", [], {})
        }

    @staticmethod
    def _extract_target_domain(chat_directive: dict[str, Any]) -> str | None:
        for key in ("target_domain", "question_domain", "domain"):
            domain = canonicalize_runtime_domain(chat_directive.get(key))
            if domain:
                return domain
        return None

    @staticmethod
    def _coerce_uuid(value: UUID | str) -> UUID | None:
        try:
            return value if isinstance(value, UUID) else UUID(str(value))
        except (TypeError, ValueError):
            return None
