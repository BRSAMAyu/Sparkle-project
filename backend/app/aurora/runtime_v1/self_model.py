from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from loguru import logger

SPARKLE_SELF_MODEL_KEY_TEMPLATE = "aurora:self_model:{user_id}"
SPARKLE_SELF_MODEL_TTL_SECONDS = 30 * 24 * 60 * 60
SPARKLE_SELF_MODEL_DAILY_RECAP_TTL_SECONDS = 24 * 60 * 60
DEFAULT_STRATEGY_CONFIDENCE = 0.7
DEFAULT_EFFECTIVENESS_RATE = 0.7
_DAILY_RECAP_WORKING_THRESHOLD = 0.8
_DAILY_RECAP_STRUGGLING_THRESHOLD = 0.4
_TASK_SHAPE_WORKING = "working"
_TASK_SHAPE_PARTIAL = "partial"
_TASK_SHAPE_STRUGGLING = "struggling"

_DAILY_TIME_ASSUMPTION = "daily_available_time"
_DURATION_ASSUMPTION = "task_duration_fit"
_DIFFICULTY_ASSUMPTION = "task_difficulty_fit"
_DEFAULT_ASSUMPTION_IDS = (
    _DAILY_TIME_ASSUMPTION,
    _DURATION_ASSUMPTION,
    _DIFFICULTY_ASSUMPTION,
)
_ASSUMPTION_DEFAULTS = {
    _DAILY_TIME_ASSUMPTION: "用户每天可稳定投入当前计划预估的学习时长",
    _DURATION_ASSUMPTION: "当前推荐的任务时长与用户实际节奏匹配",
    _DIFFICULTY_ASSUMPTION: "当前推荐的任务难度与用户当前基础匹配",
}
_TIME_KEYWORDS = ("时间", "分钟", "小时", "daily", "time", "schedule", "90")
_DIFFICULTY_KEYWORDS = ("难", "太难", "简单", "太简单", "基础", "难度", "difficulty", "baseline")
_MAX_EVIDENCE_ITEMS = 5
_MAX_SIGNAL_IDS = 100
_LOW_CONFIDENCE_THRESHOLD = 0.45
_SMOOTHING_PRIOR_WEIGHT = 2


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _strip(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _clamp_unit(value: Any, *, default: float = DEFAULT_EFFECTIVENESS_RATE) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = float(default)
    return round(max(0.0, min(1.0, numeric)), 4)


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _as_list_of_dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)]


class SparkleSelfModelService:
    """Redis-backed self-model for Aurora strategy calibration."""

    def __init__(
        self,
        redis_client=None,
        *,
        ttl_seconds: int = SPARKLE_SELF_MODEL_TTL_SECONDS,
    ) -> None:
        self.redis = redis_client
        self.ttl_seconds = int(ttl_seconds)

    def redis_key(self, user_id: str) -> str:
        return SPARKLE_SELF_MODEL_KEY_TEMPLATE.format(user_id=str(user_id))

    async def get_readout_summary(
        self,
        *,
        user_id: str,
        request_extra_context: dict[str, Any] | None = None,
        user_context_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        state = await self._load_or_initialize(user_id)
        changed = self._hydrate_assumptions_from_context(
            state,
            request_extra_context=_as_dict(request_extra_context),
            user_context_payload=_as_dict(user_context_payload),
        )
        self._recompute_recalibration(state)
        if changed:
            await self._persist(user_id=user_id, state=state)
        else:
            await self._refresh_ttl(user_id)
        return self._to_readout_summary(state)

    async def record_task_outcome(
        self,
        *,
        user_id: str,
        signal_id: str | None = None,
        completed: bool,
        timed_out: bool | None = None,
        estimated_minutes: int | None = None,
        actual_minutes: int | None = None,
        difficulty: int | None = None,
        source: str = "task",
        reason: str | None = None,
    ) -> dict[str, Any]:
        state = await self._load_or_initialize(user_id)
        if signal_id and not self._remember_signal(state, signal_id):
            await self._refresh_ttl(user_id)
            return state

        estimated = _safe_int(estimated_minutes)
        actual = _safe_int(actual_minutes)
        timeout_detected = bool(timed_out)
        if timed_out is None and estimated > 0 and actual > estimated:
            timeout_detected = True
        success = bool(completed) and not timeout_detected

        state["task_signal_count"] = _safe_int(state.get("task_signal_count")) + 1
        if success:
            state["task_success_count"] = _safe_int(state.get("task_success_count")) + 1
            state["failure_streak"] = 0
            state["strategy_confidence"] = _clamp_unit(
                float(state.get("strategy_confidence") or DEFAULT_STRATEGY_CONFIDENCE) + 0.02,
                default=DEFAULT_STRATEGY_CONFIDENCE,
            )
            self._adjust_assumption(
                state,
                assumption_id=_DURATION_ASSUMPTION,
                delta=0.02,
                evidence_detail=self._task_evidence_detail(
                    completed=completed,
                    timed_out=timeout_detected,
                    estimated_minutes=estimated,
                    actual_minutes=actual,
                    difficulty=difficulty,
                    reason=reason,
                ),
                source=source,
            )
            self._adjust_assumption(
                state,
                assumption_id=_DIFFICULTY_ASSUMPTION,
                delta=0.01,
                evidence_detail=f"任务按预估节奏完成，当前难度暂时匹配。{reason or ''}".strip(),
                source=source,
            )
        else:
            state["failure_streak"] = _safe_int(state.get("failure_streak")) + 1
            if timeout_detected:
                state["timeout_count"] = _safe_int(state.get("timeout_count")) + 1
            confidence_delta = -0.04 if timeout_detected else -0.03
            if _safe_int(state.get("failure_streak")) >= 3:
                confidence_delta -= 0.05
            state["strategy_confidence"] = _clamp_unit(
                float(state.get("strategy_confidence") or DEFAULT_STRATEGY_CONFIDENCE) + confidence_delta,
                default=DEFAULT_STRATEGY_CONFIDENCE,
            )
            self._adjust_assumption(
                state,
                assumption_id=_DURATION_ASSUMPTION,
                delta=-0.12 if timeout_detected else -0.08,
                evidence_detail=self._task_evidence_detail(
                    completed=completed,
                    timed_out=timeout_detected,
                    estimated_minutes=estimated,
                    actual_minutes=actual,
                    difficulty=difficulty,
                    reason=reason,
                ),
                source=source,
            )
            self._adjust_assumption(
                state,
                assumption_id=_DAILY_TIME_ASSUMPTION,
                delta=-0.08 if timeout_detected else -0.04,
                evidence_detail="任务实际推进慢于系统假设，日可用时长或节奏假设可能偏乐观。",
                source=source,
            )
            self._adjust_assumption(
                state,
                assumption_id=_DIFFICULTY_ASSUMPTION,
                delta=-0.08 if (difficulty or 0) >= 4 else -0.05,
                evidence_detail="任务未按预期完成，当前难度假设需要重新校准。",
                source=source,
            )

        self._recompute_harness_effectiveness(state)
        self._recompute_recalibration(state)
        await self._persist(user_id=user_id, state=state)
        return state

    async def record_user_correction(
        self,
        *,
        user_id: str,
        signal_id: str | None = None,
        reason: str | None = None,
        source: str = "user_correction",
    ) -> dict[str, Any]:
        state = await self._load_or_initialize(user_id)
        if signal_id and not self._remember_signal(state, signal_id):
            await self._refresh_ttl(user_id)
            return state

        harness = _as_dict(state.get("harness_effectiveness"))
        harness["user_corrections_count"] = _safe_int(harness.get("user_corrections_count")) + 1
        state["harness_effectiveness"] = harness
        state["strategy_confidence"] = _clamp_unit(
            float(state.get("strategy_confidence") or DEFAULT_STRATEGY_CONFIDENCE) - 0.05,
            default=DEFAULT_STRATEGY_CONFIDENCE,
        )

        correction_reason = _strip(reason) or "用户明确指出系统原有判断不准确。"
        lowered = correction_reason.lower()
        targeted: list[str] = []
        if any(token in lowered for token in _TIME_KEYWORDS):
            targeted.append(_DAILY_TIME_ASSUMPTION)
        if any(token in lowered for token in _DIFFICULTY_KEYWORDS):
            targeted.append(_DIFFICULTY_ASSUMPTION)
        if not targeted:
            targeted = [_DAILY_TIME_ASSUMPTION, _DURATION_ASSUMPTION]

        for assumption_id in targeted:
            self._adjust_assumption(
                state,
                assumption_id=assumption_id,
                delta=-0.08 if assumption_id == _DAILY_TIME_ASSUMPTION else -0.06,
                evidence_detail=correction_reason,
                source=source,
            )

        self._recompute_harness_effectiveness(state)
        self._recompute_recalibration(state)
        await self._persist(user_id=user_id, state=state)
        return state

    async def update_daily_recap(
        self,
        *,
        user_id: str,
        completion_rate: float,
    ) -> dict[str, Any]:
        """Update self-model at end of Sprint day based on completion rate.

        Tiers:
            completion_rate >= 0.8  → "working",   failure_streak reset to 0
            0.4 <= rate  < 0.8      → "partial",   failure_streak unchanged
            completion_rate < 0.4   → "struggling", failure_streak += 1
        """
        state = await self._load_or_initialize(user_id)
        rate = _clamp_unit(completion_rate, default=0.5)

        if rate >= _DAILY_RECAP_WORKING_THRESHOLD:
            task_shape = _TASK_SHAPE_WORKING
            state["failure_streak"] = 0
        elif rate < _DAILY_RECAP_STRUGGLING_THRESHOLD:
            task_shape = _TASK_SHAPE_STRUGGLING
            state["failure_streak"] = max(0, _safe_int(state.get("failure_streak"))) + 1
        else:
            task_shape = _TASK_SHAPE_PARTIAL

        harness = _as_dict(state.get("harness_effectiveness"))
        harness["task_shape"] = task_shape
        harness["task_completion_rate"] = rate
        state["harness_effectiveness"] = harness

        self._recompute_recalibration(state)
        await self._persist(user_id=user_id, state=state)
        return state

    async def _load_or_initialize(self, user_id: str) -> dict[str, Any]:
        if self.redis is None:
            return self._default_state(user_id)

        try:
            raw = await self.redis.get(self.redis_key(user_id))
        except Exception as exc:
            logger.warning("Sparkle self model read failed for {}: {}", user_id, exc)
            return self._default_state(user_id)

        if not raw:
            state = self._default_state(user_id)
            await self._persist(user_id=user_id, state=state)
            return state

        try:
            payload = json.loads(raw)
        except Exception as exc:
            logger.warning("Sparkle self model decode failed for {}: {}", user_id, exc)
            payload = {}

        state = self._normalize_state(user_id=user_id, payload=payload)
        return state

    def _default_state(self, user_id: str) -> dict[str, Any]:
        return {
            "version": 1,
            "user_id": str(user_id),
            "strategy_confidence": DEFAULT_STRATEGY_CONFIDENCE,
            "known_assumptions": [
                {
                    "assumption_id": assumption_id,
                    "statement": statement,
                    "confidence": DEFAULT_STRATEGY_CONFIDENCE,
                    "evidence": [],
                }
                for assumption_id, statement in _ASSUMPTION_DEFAULTS.items()
            ],
            "harness_effectiveness": {
                "context_hit_rate": DEFAULT_EFFECTIVENESS_RATE,
                "task_completion_rate": DEFAULT_EFFECTIVENESS_RATE,
                "user_corrections_count": 0,
                "task_shape": _TASK_SHAPE_PARTIAL,
            },
            "needs_recalibration": False,
            "recalibration_reasons": [],
            "task_signal_count": 0,
            "task_success_count": 0,
            "timeout_count": 0,
            "failure_streak": 0,
            "processed_signal_ids": [],
            "updated_at": _utcnow().isoformat(),
        }

    def _normalize_state(self, *, user_id: str, payload: Any) -> dict[str, Any]:
        state = self._default_state(user_id)
        if not isinstance(payload, Mapping):
            return state

        state["strategy_confidence"] = _clamp_unit(
            payload.get("strategy_confidence"),
            default=DEFAULT_STRATEGY_CONFIDENCE,
        )
        state["needs_recalibration"] = bool(payload.get("needs_recalibration"))
        state["recalibration_reasons"] = [
            _strip(item)
            for item in list(payload.get("recalibration_reasons") or [])
            if _strip(item)
        ][:4]
        state["task_signal_count"] = max(0, _safe_int(payload.get("task_signal_count")))
        state["task_success_count"] = max(0, _safe_int(payload.get("task_success_count")))
        state["timeout_count"] = max(0, _safe_int(payload.get("timeout_count")))
        state["failure_streak"] = max(0, _safe_int(payload.get("failure_streak")))
        state["updated_at"] = _strip(payload.get("updated_at")) or state["updated_at"]
        state["processed_signal_ids"] = [
            _strip(item)
            for item in list(payload.get("processed_signal_ids") or [])
            if _strip(item)
        ][-_MAX_SIGNAL_IDS:]

        harness = _as_dict(payload.get("harness_effectiveness"))
        task_shape_raw = str(harness.get("task_shape") or "").strip()
        task_shape = task_shape_raw if task_shape_raw in (_TASK_SHAPE_WORKING, _TASK_SHAPE_PARTIAL, _TASK_SHAPE_STRUGGLING) else _TASK_SHAPE_PARTIAL
        state["harness_effectiveness"] = {
            "context_hit_rate": _clamp_unit(
                harness.get("context_hit_rate"),
                default=DEFAULT_EFFECTIVENESS_RATE,
            ),
            "task_completion_rate": _clamp_unit(
                harness.get("task_completion_rate"),
                default=DEFAULT_EFFECTIVENESS_RATE,
            ),
            "user_corrections_count": max(0, _safe_int(harness.get("user_corrections_count"))),
            "task_shape": task_shape,
        }

        assumptions_by_id = {
            item["assumption_id"]: item
            for item in _as_list_of_dicts(payload.get("known_assumptions"))
            if _strip(item.get("assumption_id"))
        }
        state["known_assumptions"] = []
        for assumption_id in _DEFAULT_ASSUMPTION_IDS:
            stored = assumptions_by_id.get(assumption_id, {})
            state["known_assumptions"].append(
                {
                    "assumption_id": assumption_id,
                    "statement": _strip(stored.get("statement")) or _ASSUMPTION_DEFAULTS[assumption_id],
                    "confidence": _clamp_unit(
                        stored.get("confidence"),
                        default=DEFAULT_STRATEGY_CONFIDENCE,
                    ),
                    "evidence": [
                        {
                            "source": _strip(item.get("source")),
                            "detail": _strip(item.get("detail")),
                            "observed_at": _strip(item.get("observed_at")),
                        }
                        for item in _as_list_of_dicts(stored.get("evidence"))
                        if _strip(item.get("detail"))
                    ][-_MAX_EVIDENCE_ITEMS:],
                }
            )
        self._recompute_harness_effectiveness(state)
        self._recompute_recalibration(state)
        return state

    async def _persist(self, *, user_id: str, state: dict[str, Any]) -> None:
        if self.redis is None:
            return
        state["updated_at"] = _utcnow().isoformat()
        try:
            await self.redis.setex(
                self.redis_key(user_id),
                self.ttl_seconds,
                json.dumps(state, ensure_ascii=False, default=str),
            )
        except Exception as exc:
            logger.warning("Sparkle self model persist failed for {}: {}", user_id, exc)

    async def _refresh_ttl(self, user_id: str) -> None:
        if self.redis is None or not hasattr(self.redis, "expire"):
            return
        try:
            await self.redis.expire(self.redis_key(user_id), self.ttl_seconds)
        except Exception:
            return

    def _remember_signal(self, state: dict[str, Any], signal_id: str) -> bool:
        normalized = _strip(signal_id)
        if not normalized:
            return True
        seen = list(state.get("processed_signal_ids") or [])
        if normalized in seen:
            return False
        seen.append(normalized)
        state["processed_signal_ids"] = seen[-_MAX_SIGNAL_IDS:]
        return True

    def _assumptions_by_id(self, state: dict[str, Any]) -> dict[str, dict[str, Any]]:
        assumptions = _as_list_of_dicts(state.get("known_assumptions"))
        indexed = {
            _strip(item.get("assumption_id")): item
            for item in assumptions
            if _strip(item.get("assumption_id"))
        }
        for assumption_id in _DEFAULT_ASSUMPTION_IDS:
            indexed.setdefault(
                assumption_id,
                {
                    "assumption_id": assumption_id,
                    "statement": _ASSUMPTION_DEFAULTS[assumption_id],
                    "confidence": DEFAULT_STRATEGY_CONFIDENCE,
                    "evidence": [],
                },
            )
        state["known_assumptions"] = [indexed[assumption_id] for assumption_id in _DEFAULT_ASSUMPTION_IDS]
        return indexed

    def _adjust_assumption(
        self,
        state: dict[str, Any],
        *,
        assumption_id: str,
        delta: float,
        evidence_detail: str,
        source: str,
    ) -> None:
        assumptions = self._assumptions_by_id(state)
        assumption = assumptions[assumption_id]
        assumption["confidence"] = _clamp_unit(
            float(assumption.get("confidence") or DEFAULT_STRATEGY_CONFIDENCE) + delta,
            default=DEFAULT_STRATEGY_CONFIDENCE,
        )
        evidence = [
            item
            for item in _as_list_of_dicts(assumption.get("evidence"))
            if _strip(item.get("detail"))
        ]
        evidence.append(
            {
                "source": _strip(source) or "self_model",
                "detail": _strip(evidence_detail),
                "observed_at": _utcnow().isoformat(),
            }
        )
        assumption["evidence"] = evidence[-_MAX_EVIDENCE_ITEMS:]

    def _recompute_harness_effectiveness(self, state: dict[str, Any]) -> None:
        task_signal_count = max(0, _safe_int(state.get("task_signal_count")))
        task_success_count = max(0, _safe_int(state.get("task_success_count")))
        harness = _as_dict(state.get("harness_effectiveness"))
        user_corrections_count = max(0, _safe_int(harness.get("user_corrections_count")))
        task_shape = str(harness.get("task_shape") or "").strip()
        if task_shape not in (_TASK_SHAPE_WORKING, _TASK_SHAPE_PARTIAL, _TASK_SHAPE_STRUGGLING):
            task_shape = _TASK_SHAPE_PARTIAL

        if task_signal_count > 0:
            task_completion_rate = (
                DEFAULT_EFFECTIVENESS_RATE * _SMOOTHING_PRIOR_WEIGHT + float(task_success_count)
            ) / (_SMOOTHING_PRIOR_WEIGHT + float(task_signal_count))
        else:
            task_completion_rate = DEFAULT_EFFECTIVENESS_RATE

        total_context_signals = task_signal_count + user_corrections_count
        if total_context_signals > 0:
            context_hit_rate = (
                DEFAULT_EFFECTIVENESS_RATE * _SMOOTHING_PRIOR_WEIGHT + float(task_success_count)
            ) / (_SMOOTHING_PRIOR_WEIGHT + float(total_context_signals))
        else:
            context_hit_rate = DEFAULT_EFFECTIVENESS_RATE

        state["harness_effectiveness"] = {
            "context_hit_rate": round(context_hit_rate, 4),
            "task_completion_rate": round(task_completion_rate, 4),
            "user_corrections_count": user_corrections_count,
            "task_shape": task_shape,
        }

    def _recompute_recalibration(self, state: dict[str, Any]) -> None:
        assumptions = self._assumptions_by_id(state)
        low_confidence_assumptions = [
            item
            for item in assumptions.values()
            if _clamp_unit(item.get("confidence"), default=DEFAULT_STRATEGY_CONFIDENCE) < _LOW_CONFIDENCE_THRESHOLD
        ]
        harness = _as_dict(state.get("harness_effectiveness"))
        task_completion_rate = _clamp_unit(harness.get("task_completion_rate"))
        user_corrections_count = max(0, _safe_int(harness.get("user_corrections_count")))
        failure_streak = max(0, _safe_int(state.get("failure_streak")))
        task_signal_count = max(0, _safe_int(state.get("task_signal_count")))

        reasons: list[str] = []
        if failure_streak >= 3:
            reasons.append(f"连续 {failure_streak} 次任务超时或未完成。")
        if task_signal_count >= 3 and task_completion_rate < 0.55:
            reasons.append(f"最近任务完成率仅约 {task_completion_rate:.0%}。")
        if user_corrections_count >= 2:
            reasons.append(f"用户近期已纠正系统 {user_corrections_count} 次。")
        if len(low_confidence_assumptions) >= 2:
            labels = "、".join(item["assumption_id"] for item in low_confidence_assumptions[:3])
            reasons.append(f"多个关键假设置信度偏低：{labels}。")

        state["needs_recalibration"] = bool(
            reasons and (
                len(low_confidence_assumptions) >= 2
                or failure_streak >= 3
                or user_corrections_count >= 2
            )
        )
        state["recalibration_reasons"] = reasons[:4]

    def _hydrate_assumptions_from_context(
        self,
        state: dict[str, Any],
        *,
        request_extra_context: dict[str, Any],
        user_context_payload: dict[str, Any],
    ) -> bool:
        changed = False
        task_state = _as_dict(request_extra_context.get("task_state") or user_context_payload.get("task_state"))
        profile_context = _as_dict(user_context_payload.get("profile_context"))
        preferences = _as_dict(profile_context.get("preferences"))
        cold_start_context = _as_dict(preferences.get("cold_start_context"))
        assumptions = self._assumptions_by_id(state)

        daily_minutes = self._extract_daily_minutes(task_state, cold_start_context)
        if daily_minutes is not None:
            statement = f"用户每天可稳定投入约 {daily_minutes} 分钟学习"
            daily_assumption = assumptions[_DAILY_TIME_ASSUMPTION]
            if _strip(daily_assumption.get("statement")) != statement:
                daily_assumption["statement"] = statement
                changed = True
            if self._append_context_evidence(
                daily_assumption,
                source="turn_context",
                detail=f"当前上下文显示用户可投入约 {daily_minutes} 分钟/天。",
            ):
                changed = True

        baseline_text = _strip(
            task_state.get("knowledge_baseline")
            or task_state.get("baseline")
            or cold_start_context.get("knowledge_baseline")
        )
        if baseline_text:
            difficulty_assumption = assumptions[_DIFFICULTY_ASSUMPTION]
            statement = f"当前推荐难度需要匹配用户基础：{baseline_text}"
            if _strip(difficulty_assumption.get("statement")) != statement:
                difficulty_assumption["statement"] = statement
                changed = True
            if self._append_context_evidence(
                difficulty_assumption,
                source="turn_context",
                detail=f"当前建模上下文提供的基础线索：{baseline_text}",
            ):
                changed = True

        return changed

    def _append_context_evidence(self, assumption: dict[str, Any], *, source: str, detail: str) -> bool:
        normalized_detail = _strip(detail)
        if not normalized_detail:
            return False
        evidence = _as_list_of_dicts(assumption.get("evidence"))
        if any(_strip(item.get("detail")) == normalized_detail for item in evidence):
            return False
        evidence.append(
            {
                "source": _strip(source),
                "detail": normalized_detail,
                "observed_at": _utcnow().isoformat(),
            }
        )
        assumption["evidence"] = evidence[-_MAX_EVIDENCE_ITEMS:]
        return True

    def _extract_daily_minutes(self, *sources: dict[str, Any]) -> int | None:
        for source in sources:
            if not source:
                continue
            hours = _safe_float(source.get("daily_available_hours"))
            if hours is not None and hours > 0:
                return max(5, int(round(hours * 60)))
            minutes = _safe_float(source.get("daily_available_minutes"))
            if minutes is not None and minutes > 0:
                return max(5, int(round(minutes)))
            time_text = _strip(source.get("time_available"))
            parsed = self._parse_minutes_from_text(time_text)
            if parsed is not None:
                return parsed
        return None

    def _parse_minutes_from_text(self, value: str) -> int | None:
        text = _strip(value).lower()
        if not text:
            return None
        if "小时" in text or "hour" in text:
            digits = "".join(ch for ch in text if ch.isdigit() or ch == ".")
            hours = _safe_float(digits)
            if hours is not None and hours > 0:
                return max(5, int(round(hours * 60)))
        if "分钟" in text or "min" in text:
            digits = "".join(ch for ch in text if ch.isdigit() or ch == ".")
            minutes = _safe_float(digits)
            if minutes is not None and minutes > 0:
                return max(5, int(round(minutes)))
        return None

    def _task_evidence_detail(
        self,
        *,
        completed: bool,
        timed_out: bool,
        estimated_minutes: int,
        actual_minutes: int,
        difficulty: int | None,
        reason: str | None,
    ) -> str:
        status = "按预期完成" if completed and not timed_out else "超时或未按预期完成"
        difficulty_text = f"，难度 {difficulty}" if difficulty is not None else ""
        reason_text = f"，原因：{_strip(reason)}" if _strip(reason) else ""
        if estimated_minutes > 0 and actual_minutes > 0:
            return (
                f"任务{status}，预计 {estimated_minutes} 分钟，实际 {actual_minutes} 分钟"
                f"{difficulty_text}{reason_text}。"
            )
        if estimated_minutes > 0:
            return f"任务{status}，预计 {estimated_minutes} 分钟{difficulty_text}{reason_text}。"
        return f"任务{status}{difficulty_text}{reason_text}。"

    def _to_readout_summary(self, state: dict[str, Any]) -> dict[str, Any]:
        assumptions = self._assumptions_by_id(state)
        return {
            "strategy_confidence": _clamp_unit(
                state.get("strategy_confidence"),
                default=DEFAULT_STRATEGY_CONFIDENCE,
            ),
            "known_assumptions": [
                {
                    "assumption_id": item["assumption_id"],
                    "statement": item["statement"],
                    "confidence": _clamp_unit(
                        item.get("confidence"),
                        default=DEFAULT_STRATEGY_CONFIDENCE,
                    ),
                    "evidence": _as_list_of_dicts(item.get("evidence"))[-2:],
                }
                for item in assumptions.values()
            ],
            "harness_effectiveness": _as_dict(state.get("harness_effectiveness")),
            "needs_recalibration": bool(state.get("needs_recalibration")),
            "recalibration_reasons": list(state.get("recalibration_reasons") or []),
            "task_failure_streak": max(0, _safe_int(state.get("failure_streak"))),
        }
