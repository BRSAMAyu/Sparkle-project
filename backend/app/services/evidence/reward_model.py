from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _clamp(value: float, lower: float = -1.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, float(value)))


def _positive_float(value: Any, *, default: float = 0.0) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default
    return max(0.0, parsed)


def _difficulty_from_event(event: dict[str, Any]) -> float:
    metadata = event.get("metadata") if isinstance(event.get("metadata"), dict) else {}
    source_metadata = event.get("source_metadata") if isinstance(event.get("source_metadata"), dict) else {}
    for source in (event, metadata, source_metadata):
        for key in ("intrinsic_difficulty", "difficulty_normalized", "difficulty_score"):
            raw_value = source.get(key)
            if raw_value is not None:
                try:
                    return _clamp(float(raw_value), 0.0, 1.0)
                except (TypeError, ValueError):
                    pass
    task_kind = str(
        event.get("task_kind") or metadata.get("task_kind") or source_metadata.get("task_kind") or ""
    ).lower()
    title = str(event.get("title") or event.get("task_title") or metadata.get("title") or "").lower()
    estimated_minutes = _positive_float(event.get("estimated_minutes") or metadata.get("estimated_minutes"))
    if any(marker in task_kind or marker in title for marker in ("breath", "reflection", "micro", "深呼吸", "复盘")):
        return 0.15
    if estimated_minutes and estimated_minutes <= 5:
        return 0.20
    if estimated_minutes and estimated_minutes >= 90:
        return 0.78
    if estimated_minutes and estimated_minutes >= 45:
        return 0.62
    return 0.50


def _event_timestamp(event: dict[str, Any]) -> datetime:
    raw = event.get("timestamp") or event.get("triggered_at")
    if raw:
        try:
            parsed = datetime.fromisoformat(str(raw))
            if parsed.tzinfo is not None:
                return parsed.astimezone(UTC).replace(tzinfo=None)
            return parsed
        except ValueError:
            pass
    return _utcnow()


class RewardSignalType(StrEnum):
    TASK_COMPLETED = "task.completed"
    TASK_ABANDONED = "task.abandoned"
    USER_CORRECTION_FILED = "user_correction.filed"
    USER_CORRECTION_RESOLVED = "user_correction.resolved"
    SESSION_TIMEOUT = "session.timeout"
    EXPLICIT_GRATITUDE = "explicit.gratitude"
    EXPLICIT_COMPLAINT = "explicit.complaint"
    NEXT_DAY_RETURN = "retention.next_day_return"
    TASK_FEEDBACK_POSITIVE = "task_feedback.positive"
    TASK_FEEDBACK_NEGATIVE = "task_feedback.negative"
    UNKNOWN = "unknown"


class RewardHorizon(StrEnum):
    IMMEDIATE = "immediate"
    SHORT = "short"
    LONG = "long"
    CENSORED = "censored"


class RewardCategory(StrEnum):
    TASK_OUTCOME = "task_outcome"
    TASK_FEEDBACK = "task_feedback"
    CHAT_FEEDBACK = "chat_feedback"
    RETENTION = "retention"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class RewardBreakdown:
    """Canonical V1 reward label for RL-ready traces.

    Components are intentionally preserved separately. The total is useful for
    coarse analysis, but future policy learning should prefer the decomposed
    objective/constraint fields.
    """

    signal_type: RewardSignalType
    outcome_label: str
    total_reward: float
    reward_category: RewardCategory = RewardCategory.UNKNOWN
    immediate_interaction_reward: float = 0.0
    task_progress_reward: float = 0.0
    sustainability_cost: float = 0.0
    long_horizon_reward: float = 0.0
    information_gain_reward: float = 0.0
    confidence: float = 0.5
    evidence_strength: str = "weak"
    horizon: RewardHorizon = RewardHorizon.IMMEDIATE
    time_decay: float = 1.0
    is_censored: bool = False
    observed_at: str = ""
    metadata: dict[str, Any] | None = None
    schema_version: str = "routing_reward.v1"

    def to_trace_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["signal_type"] = self.signal_type.value
        payload["reward_category"] = self.reward_category.value
        payload["horizon"] = self.horizon.value
        payload["total_reward"] = round(float(self.total_reward), 4)
        payload["normalized_reward"] = round(_clamp(float(self.total_reward)), 4)
        payload["reward_scale"] = "category_local_v1"
        payload["immediate_interaction_reward"] = round(float(self.immediate_interaction_reward), 4)
        payload["task_progress_reward"] = round(float(self.task_progress_reward), 4)
        payload["sustainability_cost"] = round(float(self.sustainability_cost), 4)
        payload["long_horizon_reward"] = round(float(self.long_horizon_reward), 4)
        payload["information_gain_reward"] = round(float(self.information_gain_reward), 4)
        payload["confidence"] = round(float(self.confidence), 4)
        payload["time_decay"] = round(float(self.time_decay), 4)
        metadata = dict(self.metadata or {})
        payload["metadata"] = metadata
        payload["raw_reward"] = round(float(metadata.get("raw_reward", self.total_reward)), 4)
        payload["difficulty_weighted_reward"] = round(
            float(metadata.get("difficulty_weighted_reward", self.total_reward)),
            4,
        )
        return payload


class RoutingRewardModel:
    """Expert-defined V1 reward model for routing traces."""

    @staticmethod
    def time_decay(seconds: float | int | None, *, half_life_hours: float = 12.0) -> float:
        if seconds is None:
            return 1.0
        elapsed = max(0.0, float(seconds))
        half_life = max(1.0, half_life_hours * 3600.0)
        return math.pow(0.5, elapsed / half_life)

    @classmethod
    def from_task_outcome(cls, event: dict[str, Any], *, completed: bool) -> RewardBreakdown:
        raw_completion = event.get("completion_rate") if completed else 0.0
        completion_rate = _clamp(float(raw_completion) if raw_completion is not None else 0.0, 0.0, 1.0)
        actual_minutes = _positive_float(event.get("actual_minutes") or event.get("time_spent"))
        estimated_minutes = _positive_float(event.get("estimated_minutes"))
        duration_ratio = actual_minutes / estimated_minutes if actual_minutes > 0 and estimated_minutes > 0 else None
        observed_at = _event_timestamp(event).isoformat()
        intrinsic_difficulty = _difficulty_from_event(event)

        if completed:
            base_progress = max(0.25, completion_rate)
            difficulty_multiplier = 0.20 + 1.80 * intrinsic_difficulty
            task_reward = base_progress * difficulty_multiplier
            sustainability_cost = 0.0
            if duration_ratio is not None and duration_ratio > 1.5:
                sustainability_cost = -min(0.35, (duration_ratio - 1.5) * 0.20)
            total = _clamp(task_reward + sustainability_cost, lower=-2.0, upper=5.0)
            return RewardBreakdown(
                signal_type=RewardSignalType.TASK_COMPLETED,
                outcome_label="task_completion",
                total_reward=total,
                reward_category=RewardCategory.TASK_OUTCOME,
                task_progress_reward=task_reward,
                sustainability_cost=sustainability_cost,
                confidence=0.92,
                evidence_strength="strong",
                horizon=RewardHorizon.SHORT,
                observed_at=observed_at,
                metadata={
                    "task_id": event.get("task_id"),
                    "plan_id": event.get("plan_id"),
                    "intrinsic_difficulty": round(intrinsic_difficulty, 4),
                    "difficulty_multiplier": round(difficulty_multiplier, 4),
                    "raw_reward": round(base_progress, 4),
                    "difficulty_weighted_reward": round(task_reward, 4),
                    "completion_rate": completion_rate,
                    "duration_ratio": round(duration_ratio, 4) if duration_ratio is not None else None,
                },
            )
        abandonment_penalty = -(1.20 - 0.50 * intrinsic_difficulty)
        return RewardBreakdown(
            signal_type=RewardSignalType.TASK_ABANDONED,
            outcome_label="task_abandonment",
            total_reward=_clamp(abandonment_penalty - 0.05, lower=-2.0, upper=0.0),
            reward_category=RewardCategory.TASK_OUTCOME,
            task_progress_reward=abandonment_penalty,
            sustainability_cost=-0.05,
            confidence=0.90,
            evidence_strength="strong",
            horizon=RewardHorizon.SHORT,
            observed_at=observed_at,
            metadata={
                "task_id": event.get("task_id"),
                "plan_id": event.get("plan_id"),
                "intrinsic_difficulty": round(intrinsic_difficulty, 4),
                "raw_reward": -1.0,
                "difficulty_weighted_reward": round(abandonment_penalty, 4),
                "reason": event.get("reason") or event.get("feedback"),
            },
        )

    @classmethod
    def from_task_feedback(cls, event: dict[str, Any]) -> RewardBreakdown | None:
        category = str(event.get("category") or event.get("feedback_category") or "").strip().lower()
        text = str(event.get("feedback_text") or event.get("feedback") or "").strip().lower()
        observed_at = _event_timestamp(event).isoformat()
        negative = category in {"too_difficult", "too_long", "boring", "confusing"} or any(
            marker in text for marker in ("太难", "太长", "无聊", "不懂", "卡住", "boring", "too hard")
        )
        positive = category in {"too_easy", "good", "helpful", "completed"} or any(
            marker in text for marker in ("轻松", "有用", "很好", "helpful", "good")
        )
        if not negative and not positive:
            return None
        if negative:
            return RewardBreakdown(
                signal_type=RewardSignalType.TASK_FEEDBACK_NEGATIVE,
                outcome_label="task_feedback_negative",
                total_reward=-0.25,
                reward_category=RewardCategory.TASK_FEEDBACK,
                immediate_interaction_reward=-0.15,
                sustainability_cost=-0.20,
                confidence=0.70,
                evidence_strength="medium",
                horizon=RewardHorizon.IMMEDIATE,
                observed_at=observed_at,
                metadata={"task_id": event.get("task_id"), "feedback_category": category},
            )
        return RewardBreakdown(
            signal_type=RewardSignalType.TASK_FEEDBACK_POSITIVE,
            outcome_label="task_feedback_positive",
            total_reward=0.20,
            reward_category=RewardCategory.TASK_FEEDBACK,
            immediate_interaction_reward=0.20,
            confidence=0.62,
            evidence_strength="weak",
            horizon=RewardHorizon.IMMEDIATE,
            observed_at=observed_at,
            metadata={"task_id": event.get("task_id"), "feedback_category": category},
        )

    @staticmethod
    def from_chat_turn(
        *,
        gratitude: bool,
        dissatisfaction: bool,
        observed_at: datetime | None = None,
    ) -> RewardBreakdown | None:
        timestamp = (observed_at or _utcnow()).isoformat()
        if dissatisfaction:
            return RewardBreakdown(
                signal_type=RewardSignalType.EXPLICIT_COMPLAINT,
                outcome_label="explicit_complaint",
                total_reward=-0.20,
                reward_category=RewardCategory.CHAT_FEEDBACK,
                immediate_interaction_reward=-0.20,
                confidence=0.66,
                evidence_strength="weak",
                horizon=RewardHorizon.IMMEDIATE,
                observed_at=timestamp,
            )
        if gratitude:
            return RewardBreakdown(
                signal_type=RewardSignalType.EXPLICIT_GRATITUDE,
                outcome_label="explicit_gratitude",
                total_reward=0.20,
                reward_category=RewardCategory.CHAT_FEEDBACK,
                immediate_interaction_reward=0.20,
                confidence=0.58,
                evidence_strength="weak",
                horizon=RewardHorizon.IMMEDIATE,
                observed_at=timestamp,
            )
        return None

    @staticmethod
    def unknown(*, observed_at: datetime | None = None) -> RewardBreakdown:
        return RewardBreakdown(
            signal_type=RewardSignalType.UNKNOWN,
            outcome_label="unknown",
            total_reward=0.0,
            reward_category=RewardCategory.UNKNOWN,
            confidence=0.0,
            evidence_strength="none",
            horizon=RewardHorizon.CENSORED,
            is_censored=True,
            observed_at=(observed_at or _utcnow()).isoformat(),
        )
