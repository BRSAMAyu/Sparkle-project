from __future__ import annotations

import inspect
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from datetime import date as date_type
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from loguru import logger
from pydantic import BaseModel, Field
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
RECENT_TELEMETRY_TTL_SECONDS = 7 * 24 * 60 * 60
RECENT_TELEMETRY_LIMIT = 50
RECENT_TELEMETRY_KEY_TEMPLATE = "aurora:runtime_v1:telemetry:{user_id}:{conversation_id}:recent"

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


class AuroraCompletionRateBucket(BaseModel):
    turns: int = 0
    completed: int = 0
    completion_rate: float = 0.0


class AuroraWakeRetentionReport(BaseModel):
    high_wake_score_sessions: int = 0
    high_wake_score_returned_next_day: int = 0
    high_wake_score_return_rate: float = 0.0
    baseline_sessions: int = 0
    baseline_returned_next_day: int = 0
    baseline_return_rate: float = 0.0
    next_day_return_rate_lift_percentage: float = 0.0
    next_day_return_rate_lift_pp: float = 0.0


class AuroraStrategyEffectivenessInsight(BaseModel):
    strategy: str
    resolved_turns: int
    completion_rate: float
    baseline_completion_rate: float
    lift_percentage: float
    correlation_score: float


class AuroraEffectivenessReport(BaseModel):
    days: int
    total_turns: int = 0
    resolved_turns: int = 0
    has_enough_data: bool = False
    strategy_adjusted_turns: int = 0
    strategy_adjusted_completed_turns: int = 0
    strategy_adjusted_completion_rate: float = 0.0
    non_adjusted_turns: int = 0
    baseline_completed_turns: int = 0
    baseline_completion_rate: float = 0.0
    lift_percentage: float = 0.0
    high_wake_score_sessions: int = 0
    high_wake_score_next_day_return_rate: float = 0.0
    baseline_next_day_return_rate: float = 0.0
    next_day_return_rate_lift_percentage: float = 0.0
    top_effective_strategy: str | None = None
    top_effective_strategy_completion_rate: float = 0.0
    top_effective_strategy_baseline_completion_rate: float = 0.0
    top_effective_strategy_lift_percentage: float = 0.0
    top_effective_strategy_correlation: float = 0.0
    strategy_adjusted: AuroraCompletionRateBucket = Field(default_factory=AuroraCompletionRateBucket)
    baseline: AuroraCompletionRateBucket = Field(default_factory=AuroraCompletionRateBucket)
    wake_retention: AuroraWakeRetentionReport = Field(default_factory=AuroraWakeRetentionReport)
    top_effective_strategy_insight: AuroraStrategyEffectivenessInsight | None = None


class AuroraDecisionTelemetryService:
    """Persist Aurora turn decisions and backfill the previous turn's observed outcome."""

    def __init__(
        self,
        db: AsyncSession | None,
        *,
        redis_client=None,
        retention_days: int = RETENTION_DAYS,
    ) -> None:
        self.db = db
        self.redis = redis_client
        self.retention_days = max(1, int(retention_days))
        self.dashboard_builder = DashboardReadoutBuilder()

    @classmethod
    def recent_telemetry_key(cls, *, user_id: str, conversation_id: str) -> str:
        return RECENT_TELEMETRY_KEY_TEMPLATE.format(
            user_id=_strip(user_id),
            conversation_id=_strip(conversation_id),
        )

    async def detect_stale_strategy(
        self,
        *,
        user_id: str,
        conversation_id: str,
        window: int = 5,
    ) -> dict[str, Any] | None:
        """Return a recalibration signal when the latest turns repeat without coverage gain."""

        if self.redis is None:
            return None

        try:
            safe_window = max(3, int(window or 5))
        except (TypeError, ValueError):
            safe_window = 5

        raw_items = await self._redis_call(
            "lrange",
            self.recent_telemetry_key(user_id=user_id, conversation_id=conversation_id),
            0,
            safe_window - 1,
        )
        records = [record for record in (self._normalize_recent_record(item) for item in raw_items or []) if record]
        if len(records) < 3:
            return None

        latest_three = records[:3]
        response_type = latest_three[0]["response_type"]
        target_domain = latest_three[0]["target_domain"]
        if not response_type or not target_domain:
            return None
        if any(
            record["response_type"] != response_type or record["target_domain"] != target_domain
            for record in latest_three
        ):
            return None
        if self._has_new_covered_domain(latest_three):
            return None
        return {
            "stale": True,
            "stuck_on": target_domain,
            "suggestion": "switch_to_concept_first",
        }

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
        if self.db is None:
            return None

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
            try:
                await self._cache_recent_strategy_record(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    request_id=request_id,
                    readout=readout,
                    record=record,
                    decided_at=now,
                )
            except Exception as exc:
                logger.warning("Aurora runtime telemetry Redis cache failed for user {}: {}", user_id, exc)
            return {
                "decision_id": str(record.decision_id),
                "wake_score": float(record.wake_score or 0.0),
                "energy_level": str(record.energy_level or "light"),
            }
        except Exception as exc:
            await self.db.rollback()
            logger.warning("Aurora runtime telemetry write failed for user {}: {}", user_id, exc)
            return None

    async def _cache_recent_strategy_record(
        self,
        *,
        user_id: str,
        conversation_id: str,
        request_id: str,
        readout: DashboardReadout,
        record: AuroraDecisionTelemetry,
        decided_at: datetime,
    ) -> None:
        if self.redis is None:
            return

        standard_layer_contract = dict(record.standard_layer_contract or {})
        chat_directive_core = dict(record.chat_directive_core or {})
        payload = {
            "decision_id": str(record.decision_id),
            "request_id": _strip(request_id) or None,
            "decided_at": decided_at.isoformat(),
            "response_type": _strip(standard_layer_contract.get("response_type")).lower(),
            "target_domain": self._extract_target_domain(chat_directive_core),
            "covered_domains": [
                domain
                for domain in (canonicalize_runtime_domain(item) for item in list(readout.covered_domains or []))
                if domain
            ],
            "strategy_payload": dict(record.strategy_payload or {}),
        }
        key = self.recent_telemetry_key(user_id=user_id, conversation_id=conversation_id)
        await self._redis_call("lpush", key, json.dumps(payload, ensure_ascii=False, default=str))
        await self._redis_call("ltrim", key, 0, RECENT_TELEMETRY_LIMIT - 1)
        await self._redis_call("expire", key, RECENT_TELEMETRY_TTL_SECONDS)

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

        strategy_distribution = {field: {"true": 0, "false": 0, "missing": 0} for field in STRATEGY_FIELDS}
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
        escalated_error = sum(
            1 for row in escalated_resolved if row.outcome in {"timeout", "skipped", "user_corrected"}
        )

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

    async def get_effectiveness_report(
        self,
        *,
        user_id: UUID | str | None = None,
        days: int = 30,
    ) -> AuroraEffectivenessReport:
        """Compute Aurora A/B effectiveness: strategy-adjusted vs baseline completion and wake-score retention."""
        if self.db is None:
            return self._empty_effectiveness_report(days=days)

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
            .order_by(AuroraDecisionTelemetry.decided_at.asc())
        )
        user_uuid = self._coerce_uuid(user_id) if user_id is not None else None
        if user_uuid is not None:
            stmt = stmt.where(AuroraDecisionTelemetry.user_id == user_uuid)

        rows = list((await self.db.execute(stmt)).scalars().all())
        if len(rows) < 10:
            return self._empty_effectiveness_report(days=window_days, total_turns=len(rows))

        adjusted_completed = 0
        adjusted_resolved = 0
        baseline_completed = 0
        baseline_resolved = 0
        resolved_rows: list[AuroraDecisionTelemetry] = []
        strategy_outcome_counts: dict[str, dict[str, int]] = defaultdict(
            lambda: {
                "with_completed": 0,
                "with_resolved": 0,
                "without_completed": 0,
                "without_resolved": 0,
            }
        )

        for row in rows:
            outcome = str(row.outcome or "").strip()
            if not outcome:
                continue

            has_strategy = self._row_has_active_strategy(row)
            is_completed = outcome == "task_completed"
            resolved_rows.append(row)

            if has_strategy:
                adjusted_resolved += 1
                if is_completed:
                    adjusted_completed += 1
            else:
                baseline_resolved += 1
                if is_completed:
                    baseline_completed += 1

            strategy_payload = dict(row.strategy_payload or {})
            for field in STRATEGY_FIELDS:
                if strategy_payload.get(field):
                    strategy_outcome_counts[field]["with_resolved"] += 1
                    if is_completed:
                        strategy_outcome_counts[field]["with_completed"] += 1
                else:
                    strategy_outcome_counts[field]["without_resolved"] += 1
                    if is_completed:
                        strategy_outcome_counts[field]["without_completed"] += 1

        adjusted_rate = self._safe_rate(adjusted_completed, adjusted_resolved)
        baseline_rate = self._safe_rate(baseline_completed, baseline_resolved)
        lift = self._lift_percentage(adjusted_rate, baseline_rate)

        best_strategy: AuroraStrategyEffectivenessInsight | None = None
        for field, counts in strategy_outcome_counts.items():
            if counts["with_resolved"] < 3:
                continue

            with_rate = self._safe_rate(counts["with_completed"], counts["with_resolved"])
            without_rate = self._safe_rate(counts["without_completed"], counts["without_resolved"])
            correlation = round(with_rate - without_rate, 4)
            candidate = AuroraStrategyEffectivenessInsight(
                strategy=field,
                resolved_turns=counts["with_resolved"],
                completion_rate=with_rate,
                baseline_completion_rate=without_rate,
                lift_percentage=self._lift_percentage(with_rate, without_rate),
                correlation_score=correlation,
            )
            if best_strategy is None or self._strategy_insight_sort_key(candidate) > self._strategy_insight_sort_key(
                best_strategy
            ):
                best_strategy = candidate

        sessions_by_key: dict[tuple[str, str, date_type], list[float]] = defaultdict(list)
        for row in resolved_rows:
            session_day = row.decided_at.date()
            sessions_by_key[(str(row.user_id), str(row.conversation_id), session_day)].append(float(row.wake_score or 0.0))

        all_user_days: set[tuple[str, date_type]] = {(uid, session_day) for uid, _, session_day in sessions_by_key}
        high_wake_sessions = 0
        high_wake_returned = 0
        baseline_sessions = 0
        baseline_returned = 0
        observation_cutoff_day = now.date()

        for (uid, _conversation_id, session_day), scores in sessions_by_key.items():
            if session_day >= observation_cutoff_day:
                continue

            session_wake_score = max(scores) if scores else 0.0
            returned_next_day = (uid, session_day + timedelta(days=1)) in all_user_days

            if session_wake_score > 0.6:
                high_wake_sessions += 1
                if returned_next_day:
                    high_wake_returned += 1
            else:
                baseline_sessions += 1
                if returned_next_day:
                    baseline_returned += 1

        high_wake_return_rate = self._safe_rate(high_wake_returned, high_wake_sessions)
        baseline_return_rate = self._safe_rate(baseline_returned, baseline_sessions)
        return_lift_percentage = self._lift_percentage(high_wake_return_rate, baseline_return_rate)
        return_lift_pp = round((high_wake_return_rate - baseline_return_rate) * 100, 2)

        wake_retention = AuroraWakeRetentionReport(
            high_wake_score_sessions=high_wake_sessions,
            high_wake_score_returned_next_day=high_wake_returned,
            high_wake_score_return_rate=high_wake_return_rate,
            baseline_sessions=baseline_sessions,
            baseline_returned_next_day=baseline_returned,
            baseline_return_rate=baseline_return_rate,
            next_day_return_rate_lift_percentage=return_lift_percentage,
            next_day_return_rate_lift_pp=return_lift_pp,
        )
        strategy_adjusted_bucket = AuroraCompletionRateBucket(
            turns=adjusted_resolved,
            completed=adjusted_completed,
            completion_rate=adjusted_rate,
        )
        baseline_bucket = AuroraCompletionRateBucket(
            turns=baseline_resolved,
            completed=baseline_completed,
            completion_rate=baseline_rate,
        )

        return AuroraEffectivenessReport(
            days=window_days,
            total_turns=len(rows),
            resolved_turns=len(resolved_rows),
            has_enough_data=True,
            strategy_adjusted_turns=adjusted_resolved,
            strategy_adjusted_completed_turns=adjusted_completed,
            strategy_adjusted_completion_rate=adjusted_rate,
            non_adjusted_turns=baseline_resolved,
            baseline_completed_turns=baseline_completed,
            baseline_completion_rate=baseline_rate,
            lift_percentage=lift,
            high_wake_score_sessions=high_wake_sessions,
            high_wake_score_next_day_return_rate=high_wake_return_rate,
            baseline_next_day_return_rate=baseline_return_rate,
            next_day_return_rate_lift_percentage=return_lift_percentage,
            top_effective_strategy=best_strategy.strategy if best_strategy else None,
            top_effective_strategy_completion_rate=best_strategy.completion_rate if best_strategy else 0.0,
            top_effective_strategy_baseline_completion_rate=(
                best_strategy.baseline_completion_rate if best_strategy else 0.0
            ),
            top_effective_strategy_lift_percentage=best_strategy.lift_percentage if best_strategy else 0.0,
            top_effective_strategy_correlation=best_strategy.correlation_score if best_strategy else 0.0,
            strategy_adjusted=strategy_adjusted_bucket,
            baseline=baseline_bucket,
            wake_retention=wake_retention,
            top_effective_strategy_insight=best_strategy,
        )

    @staticmethod
    def _empty_effectiveness_report(*, days: int, total_turns: int = 0) -> AuroraEffectivenessReport:
        return AuroraEffectivenessReport(
            days=days,
            total_turns=total_turns,
            has_enough_data=total_turns >= 10,
        )

    @staticmethod
    def _row_has_active_strategy(row: AuroraDecisionTelemetry) -> bool:
        payload = dict(row.strategy_payload or {})
        return any(payload.get(field) for field in STRATEGY_FIELDS)

    @staticmethod
    def _safe_rate(numerator: int, denominator: int) -> float:
        return round(numerator / denominator, 4) if denominator > 0 else 0.0

    @staticmethod
    def _lift_percentage(rate: float, baseline_rate: float) -> float:
        if baseline_rate <= 0:
            if rate <= 0:
                return 0.0
            return 100.0
        return round(((rate - baseline_rate) / baseline_rate) * 100, 2)

    @staticmethod
    def _strategy_insight_sort_key(insight: AuroraStrategyEffectivenessInsight) -> tuple[float, int, float]:
        return (
            insight.correlation_score,
            insight.resolved_turns,
            insight.completion_rate,
        )

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
        await self._update_bayesian_policy_from_outcome(previous=previous, outcome=classified.outcome)

    async def _update_bayesian_policy_from_outcome(
        self,
        *,
        previous: AuroraDecisionTelemetry,
        outcome: str,
    ) -> None:
        if self.redis is None:
            return
        try:
            from app.aurora.bayesian import AuroraBayesianLearner

            await AuroraBayesianLearner(self.redis).record_outcome(
                user_id=str(previous.user_id),
                action=str(previous.action or ""),
                outcome=outcome,
            )
        except Exception as exc:
            logger.warning(
                "Aurora Bayesian policy update failed for user {} decision {}: {}",
                previous.user_id,
                previous.decision_id,
                exc,
            )

    async def _cleanup_expired(self, *, now: datetime) -> None:
        cutoff = now - timedelta(days=self.retention_days)
        await self.db.execute(delete(AuroraDecisionTelemetry).where(AuroraDecisionTelemetry.decided_at < cutoff))

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
                normalized = _EXPLICIT_OUTCOME_ALIASES.get(
                    _strip(candidate.get("outcome") or candidate.get("status")).lower()
                )
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
        energy_level = self._normalize_energy_level(wake_payload.get("energy")) or self._energy_level_for_wake_score(
            wake_score
        )
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
        return {key: value for key, value in directive.items() if key in keep_keys and value not in (None, "", [], {})}

    @staticmethod
    def _extract_target_domain(chat_directive: dict[str, Any]) -> str | None:
        for key in ("target_domain", "question_domain", "domain"):
            domain = canonicalize_runtime_domain(chat_directive.get(key))
            if domain:
                return domain
        return None

    def _normalize_recent_record(self, raw: Any) -> dict[str, Any] | None:
        payload = self._parse_recent_record(raw)
        if not isinstance(payload, dict):
            return None
        standard_layer_contract = payload.get("standard_layer_contract")
        standard_layer_contract = dict(standard_layer_contract) if isinstance(standard_layer_contract, dict) else {}
        chat_directive = payload.get("chat_directive_core") or payload.get("chat_directive")
        chat_directive = dict(chat_directive) if isinstance(chat_directive, dict) else {}
        if payload.get("target_domain"):
            chat_directive.setdefault("target_domain", payload.get("target_domain"))

        response_type = _strip(payload.get("response_type") or standard_layer_contract.get("response_type")).lower()
        target_domain = self._extract_target_domain(chat_directive)
        covered_domains = [
            domain
            for domain in (canonicalize_runtime_domain(item) for item in list(payload.get("covered_domains") or []))
            if domain
        ]
        return {
            "response_type": response_type,
            "target_domain": target_domain,
            "covered_domains": covered_domains,
        }

    @staticmethod
    def _parse_recent_record(raw: Any) -> dict[str, Any] | None:
        if isinstance(raw, dict):
            return raw
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        try:
            parsed = json.loads(str(raw))
        except (TypeError, ValueError, json.JSONDecodeError):
            return None
        return parsed if isinstance(parsed, dict) else None

    @staticmethod
    def _has_new_covered_domain(records_newest_first: list[dict[str, Any]]) -> bool:
        records_oldest_first = list(reversed(records_newest_first))
        seen = set(records_oldest_first[0].get("covered_domains") or [])
        for record in records_oldest_first[1:]:
            covered = set(record.get("covered_domains") or [])
            if covered - seen:
                return True
            seen.update(covered)
        return False

    async def _redis_call(self, method: str, *args: Any) -> Any:
        if self.redis is None or not hasattr(self.redis, method):
            return None
        fn = getattr(self.redis, method)
        result = fn(*args)
        if inspect.isawaitable(result):
            return await result
        return result

    @staticmethod
    def _coerce_uuid(value: UUID | str) -> UUID | None:
        try:
            return value if isinstance(value, UUID) else UUID(str(value))
        except (TypeError, ValueError):
            return None
