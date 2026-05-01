from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from app.services.struggle_signal_aggregator import StruggleSignalAggregator

WAKE_COOLDOWN_KEY_TEMPLATE = "aurora:wake_cooldown:{user_id}"
WAKE_COOLDOWN_TTL_SECONDS = 3 * 24 * 60 * 60
SILENT_THRESHOLD = 0.45
FULL_THRESHOLD = 0.72
DEFAULT_EXPECTED_COMPLETION_RATE = 0.75
ACTIVE_FULL_WAKE_PHRASES = (
    "重新理解我",
    "你理解错我了",
    "你理解错了我",
    "重新校准",
    "进入深度模式",
)


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _clamp_unit(value: Any, default: float = 0.0) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = float(default)
    return round(max(0.0, min(1.0, numeric)), 4)


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any) -> int | None:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _normalize_message(value: Any) -> str:
    text = _normalize_text(value).lower()
    return re.sub(r"[\s\W_]+", "", text, flags=re.UNICODE)


@dataclass(slots=True, frozen=True)
class WakeScoreComponents:
    exam_urgency: float = 0.0
    plan_drift: float = 0.0
    learning_failure: float = 0.0
    state_conflict: float = 0.0
    user_distress: float = 0.0
    standard_layer_uncertainty: float = 0.0

    @property
    def wake_score(self) -> float:
        return round(
            (0.25 * self.exam_urgency)
            + (0.20 * self.plan_drift)
            + (0.20 * self.learning_failure)
            + (0.15 * self.state_conflict)
            + (0.10 * self.user_distress)
            + (0.10 * self.standard_layer_uncertainty),
            4,
        )

    def to_dict(self) -> dict[str, float]:
        return {
            "exam_urgency": self.exam_urgency,
            "plan_drift": self.plan_drift,
            "learning_failure": self.learning_failure,
            "state_conflict": self.state_conflict,
            "user_distress": self.user_distress,
            "standard_layer_uncertainty": self.standard_layer_uncertainty,
            "wake_score": self.wake_score,
        }


@dataclass(slots=True, frozen=True)
class WakeCooldownPolicy:
    cooldown_minutes: int
    daily_limit: int
    policy_name: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "cooldown_minutes": self.cooldown_minutes,
            "daily_limit": self.daily_limit,
            "policy_name": self.policy_name,
        }


@dataclass(slots=True, frozen=True)
class WakeCooldownStatus:
    allowed: bool
    remaining_seconds: int = 0
    day_count: int = 0
    day_limit: int = 0
    last_full_wake_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "remaining_seconds": self.remaining_seconds,
            "day_count": self.day_count,
            "day_limit": self.day_limit,
            "last_full_wake_at": self.last_full_wake_at,
        }


@dataclass(slots=True, frozen=True)
class ModerateDiagnosticSignal:
    triggered: bool = False
    same_cause_error_streak: int = 0
    quiz_accuracy_declining: bool = False
    quiz_accuracy_drop: float = 0.0
    reminder_topic: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "triggered": self.triggered,
            "same_cause_error_streak": self.same_cause_error_streak,
            "quiz_accuracy_declining": self.quiz_accuracy_declining,
            "quiz_accuracy_drop": self.quiz_accuracy_drop,
            "reminder_topic": self.reminder_topic,
        }


@dataclass(slots=True, frozen=True)
class WakeDecision:
    energy: str
    wake_score: float
    components: WakeScoreComponents
    cooldown_policy: WakeCooldownPolicy
    cooldown_status: WakeCooldownStatus
    multimessage_allowed: bool = False
    context_budget: str = "compact"
    user_requested_full_wake: bool = False
    full_candidate: bool = False
    full_allowed: bool = False
    light_adjustment_triggered: bool = False
    risk_override_triggered: bool = False
    diagnostic_signal: ModerateDiagnosticSignal = field(default_factory=ModerateDiagnosticSignal)
    pass_probability: float | None = None
    plan_completion_rate: float | None = None
    days_left: int | None = None

    def prompt_instruction(self) -> str:
        if self.full_allowed:
            return (
                "Wake energy is FULL. Aurora may step into explicit calibration mode. "
                "A multi-message recalibration dialogue is allowed. Use the extended context budget. "
                "If plan completion is weak or pass probability is low, prioritize strategy reset over another generic nudge."
            )
        if self.full_candidate and not self.full_allowed:
            return (
                "Wake energy reached FULL-candidate, but full escalation is blocked by cooldown. "
                "Do not initiate a full calibration dialogue this turn. Keep the intervention lighter and focused."
            )
        if self.energy == "moderate":
            topic = self.diagnostic_signal.reminder_topic or "当前反复卡住的概念"
            return (
                "Wake energy is MODERATE. Prefer a short diagnostic reminder instead of a full intervention. "
                "Keep it lightweight, easy to ignore, and focused on one stuck topic. "
                f"If helpful, name the recurring bottleneck as {topic} and suggest trying a different approach."
            )
        if self.energy == "light":
            return (
                "Wake energy is LIGHT. Bias toward invisible harness adjustment: reduce task density, simplify the next step, "
                "and avoid turning this turn into a proactive calibration conversation unless the user explicitly asks for it."
            )
        return "Wake energy is SILENT. Keep Aurora in the background and avoid extra proactive escalation."

    def apply_activity_profile(self, activity_profile: dict[str, Any]) -> dict[str, Any]:
        adjusted = dict(activity_profile or {})
        current_density = _clamp_unit(adjusted.get("task_density_hint"), default=0.5)
        proactive = _clamp_unit(adjusted.get("proactive_intensity"), default=0.5)
        expression = dict(adjusted.get("expression") or {})

        if self.energy == "light":
            adjusted["task_density_hint"] = round(max(0.15, current_density - 0.12), 4)
            adjusted["proactive_intensity"] = round(min(proactive, 0.4), 4)
        elif self.energy == "moderate":
            adjusted["task_density_hint"] = round(max(0.15, current_density - 0.08), 4)
            adjusted["proactive_intensity"] = round(max(proactive, 0.58), 4)
            if expression:
                expression["challenge_intensity"] = round(
                    min(0.62, max(float(expression.get("challenge_intensity", 0.0)), 0.38)), 4
                )
                adjusted["expression"] = expression
        elif self.energy == "full":
            adjusted["task_density_hint"] = round(max(0.12, current_density - 0.15), 4)
            adjusted["proactive_intensity"] = round(max(proactive, 0.82), 4)
            if expression:
                expression["directness"] = round(max(float(expression.get("directness", 0.0)), 0.62), 4)
                expression["challenge_intensity"] = round(
                    max(float(expression.get("challenge_intensity", 0.0)), 0.58), 4
                )
                adjusted["expression"] = expression
        return adjusted

    def to_payload(self) -> dict[str, Any]:
        return {
            "energy": self.energy,
            "wake_score": self.wake_score,
            "components": self.components.to_dict(),
            "cooldown_policy": self.cooldown_policy.to_dict(),
            "cooldown_status": self.cooldown_status.to_dict(),
            "multimessage_allowed": self.multimessage_allowed,
            "context_budget": self.context_budget,
            "user_requested_full_wake": self.user_requested_full_wake,
            "full_candidate": self.full_candidate,
            "full_allowed": self.full_allowed,
            "light_adjustment_triggered": self.light_adjustment_triggered,
            "risk_override_triggered": self.risk_override_triggered,
            "diagnostic_signal": self.diagnostic_signal.to_dict(),
            "diagnostic_prompt": self.prompt_instruction(),
            "pass_probability": self.pass_probability,
            "plan_completion_rate": self.plan_completion_rate,
            "days_left": self.days_left,
        }


class AuroraWakePolicyService:
    def __init__(
        self,
        redis_client=None,
        *,
        struggle_signal_aggregator: StruggleSignalAggregator | None = None,
    ) -> None:
        self.redis = redis_client
        self.struggle_signal_aggregator = struggle_signal_aggregator or StruggleSignalAggregator()

    async def evaluate(
        self,
        *,
        active_db,
        user_id: str,
        user_message: str,
        request_extra_context: dict[str, Any] | None,
        user_context_payload: dict[str, Any] | None,
        self_model: dict[str, Any] | None,
        now: datetime | None = None,
    ) -> WakeDecision:
        request_extra_context = _as_dict(request_extra_context)
        user_context_payload = _as_dict(user_context_payload)
        self_model = _as_dict(self_model)
        now = now or _utcnow()

        days_left = self._extract_days_left(request_extra_context, user_context_payload)
        actual_completion_rate, expected_completion_rate = self._extract_completion_rates(
            request_extra_context,
            user_context_payload,
            self_model,
        )
        pass_probability = self._extract_pass_probability(request_extra_context, user_context_payload)
        same_cause_error_streak = self._extract_same_cause_error_streak(request_extra_context, user_context_payload)
        quiz_accuracy_declining, quiz_accuracy_drop = self._extract_quiz_accuracy_decline(
            request_extra_context,
            user_context_payload,
        )
        reminder_topic = self._extract_reminder_topic(request_extra_context, user_context_payload)
        failure_streak = self._extract_failure_streak(request_extra_context, user_context_payload, self_model)
        timeout_streak = self._extract_timeout_streak(request_extra_context, user_context_payload, self_model)
        light_adjustment_triggered = max(timeout_streak, failure_streak) >= 2
        diagnostic_signal = ModerateDiagnosticSignal(
            triggered=same_cause_error_streak >= 3 and quiz_accuracy_declining,
            same_cause_error_streak=same_cause_error_streak,
            quiz_accuracy_declining=quiz_accuracy_declining,
            quiz_accuracy_drop=quiz_accuracy_drop,
            reminder_topic=reminder_topic,
        )

        strategy_confidence = self._extract_strategy_confidence(self_model, request_extra_context, user_context_payload)
        user_distress = await self._resolve_user_distress(
            active_db=active_db,
            user_id=user_id,
            request_extra_context=request_extra_context,
            user_context_payload=user_context_payload,
        )
        standard_layer_uncertainty = self._extract_standard_layer_uncertainty(
            request_extra_context, user_context_payload
        )
        learning_failure = self._build_learning_failure_score(
            same_cause_error_streak=same_cause_error_streak,
            quiz_accuracy_drop=quiz_accuracy_drop,
            failure_streak=failure_streak,
            timeout_streak=timeout_streak,
        )

        components = WakeScoreComponents(
            exam_urgency=self._build_exam_urgency(days_left),
            plan_drift=self._build_plan_drift(actual_completion_rate, expected_completion_rate),
            learning_failure=learning_failure,
            state_conflict=round(1.0 - strategy_confidence, 4),
            user_distress=user_distress,
            standard_layer_uncertainty=standard_layer_uncertainty,
        )

        user_requested_full_wake = self._contains_active_full_wake_phrase(user_message)
        # Suppress risk override on exam day itself (days_left == 0):
        # The user needs stabilisation and confidence, not aggressive calibration.
        # Risk override is meaningful only in the 1–3 days-left window.
        risk_override_triggered = bool(
            days_left is not None
            and 1 <= days_left <= 3
            and pass_probability is not None
            and pass_probability < 0.45
            and actual_completion_rate is not None
            and actual_completion_rate < 0.5
        )
        full_candidate = bool(
            user_requested_full_wake or risk_override_triggered or components.wake_score >= FULL_THRESHOLD
        )
        cooldown_policy = self._select_cooldown_policy(days_left)
        cooldown_status = await self._cooldown_status(user_id=user_id, policy=cooldown_policy, now=now)
        full_allowed = bool(full_candidate and cooldown_status.allowed)

        if full_allowed:
            energy = "full"
        elif full_candidate or components.wake_score >= SILENT_THRESHOLD:
            energy = "moderate"
        elif light_adjustment_triggered:
            energy = "light"
        else:
            energy = "silent"

        return WakeDecision(
            energy=energy,
            wake_score=components.wake_score,
            components=components,
            cooldown_policy=cooldown_policy,
            cooldown_status=cooldown_status,
            multimessage_allowed=energy == "full",
            context_budget="extended" if energy == "full" else "compact",
            user_requested_full_wake=user_requested_full_wake,
            full_candidate=full_candidate,
            full_allowed=full_allowed,
            light_adjustment_triggered=light_adjustment_triggered,
            risk_override_triggered=risk_override_triggered,
            diagnostic_signal=diagnostic_signal,
            pass_probability=pass_probability,
            plan_completion_rate=actual_completion_rate,
            days_left=days_left,
        )

    async def record_full_wake(
        self,
        *,
        user_id: str,
        policy: WakeCooldownPolicy,
        now: datetime | None = None,
    ) -> None:
        if self.redis is None:
            return
        now = now or _utcnow()
        payload = await self._load_cooldown_payload(user_id)
        today = now.date().isoformat()
        if payload.get("day") != today:
            payload["day"] = today
            payload["day_count"] = 0
        payload["day_count"] = int(payload.get("day_count") or 0) + 1
        payload["last_full_wake_at"] = now.isoformat()
        payload["policy_name"] = policy.policy_name
        await self._store_cooldown_payload(user_id, payload)

    def cooldown_key(self, user_id: str) -> str:
        return WAKE_COOLDOWN_KEY_TEMPLATE.format(user_id=str(user_id))

    async def _cooldown_status(
        self,
        *,
        user_id: str,
        policy: WakeCooldownPolicy,
        now: datetime,
    ) -> WakeCooldownStatus:
        payload = await self._load_cooldown_payload(user_id)
        today = now.date().isoformat()
        day_count = int(payload.get("day_count") or 0) if payload.get("day") == today else 0

        last_full_wake_at = self._parse_datetime(payload.get("last_full_wake_at"))
        remaining_seconds = 0
        if last_full_wake_at is not None:
            next_allowed_at = last_full_wake_at + timedelta(minutes=policy.cooldown_minutes)
            remaining_seconds = max(0, int((next_allowed_at - now).total_seconds()))

        allowed = day_count < policy.daily_limit and remaining_seconds == 0
        return WakeCooldownStatus(
            allowed=allowed,
            remaining_seconds=remaining_seconds,
            day_count=day_count,
            day_limit=policy.daily_limit,
            last_full_wake_at=payload.get("last_full_wake_at"),
        )

    async def _load_cooldown_payload(self, user_id: str) -> dict[str, Any]:
        if self.redis is None:
            return {}
        raw = await self._redis_call("get", self.cooldown_key(user_id))
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
        except (TypeError, ValueError, json.JSONDecodeError):
            return {}
        return parsed if isinstance(parsed, dict) else {}

    async def _store_cooldown_payload(self, user_id: str, payload: dict[str, Any]) -> None:
        if self.redis is None:
            return
        await self._redis_call(
            "setex",
            self.cooldown_key(user_id),
            WAKE_COOLDOWN_TTL_SECONDS,
            json.dumps(payload, ensure_ascii=False, default=str),
        )

    async def _redis_call(self, method: str, *args: Any) -> Any:
        if self.redis is None or not hasattr(self.redis, method):
            return None
        fn = getattr(self.redis, method)
        return await fn(*args)

    async def _resolve_user_distress(
        self,
        *,
        active_db,
        user_id: str,
        request_extra_context: dict[str, Any],
        user_context_payload: dict[str, Any],
    ) -> float:
        explicit = self._first_numeric(
            request_extra_context.get("struggle_score"),
            _as_dict(request_extra_context.get("struggle_context")).get("struggle_score"),
            user_context_payload.get("struggle_score"),
            _as_dict(user_context_payload.get("struggle_context")).get("struggle_score"),
        )
        if explicit is not None:
            return _clamp_unit(explicit)

        cached = await self.struggle_signal_aggregator.get_cached_score(self.redis, user_id=str(user_id))
        if cached is not None:
            return _clamp_unit(cached)

        plan_id = self._extract_plan_id(request_extra_context, user_context_payload)
        if active_db is None or not plan_id:
            return 0.0

        try:
            score = await self.struggle_signal_aggregator.compute_struggle_score(
                active_db,
                self.redis,
                user_id=str(user_id),
                plan_id=str(plan_id),
            )
            return _clamp_unit(score)
        except Exception:
            return 0.0

    def _contains_active_full_wake_phrase(self, user_message: str) -> bool:
        normalized = _normalize_message(user_message)
        return any(_normalize_message(phrase) in normalized for phrase in ACTIVE_FULL_WAKE_PHRASES)

    def _build_exam_urgency(self, days_left: int | None) -> float:
        if days_left is None:
            return 0.0
        return _clamp_unit(1.0 - (float(days_left) / 14.0))

    def _build_plan_drift(self, actual_rate: float | None, expected_rate: float | None) -> float:
        if actual_rate is None and expected_rate is None:
            return 0.0
        expected = expected_rate if expected_rate is not None else DEFAULT_EXPECTED_COMPLETION_RATE
        actual = actual_rate if actual_rate is not None else 0.0
        if expected <= 0:
            return _clamp_unit(1.0 - actual)
        return _clamp_unit(max(0.0, expected - actual) / max(expected, 0.01))

    def _build_learning_failure_score(
        self,
        *,
        same_cause_error_streak: int,
        quiz_accuracy_drop: float,
        failure_streak: int,
        timeout_streak: int,
    ) -> float:
        signals = [
            min(1.0, same_cause_error_streak / 4.0) if same_cause_error_streak > 0 else 0.0,
            min(1.0, max(quiz_accuracy_drop, 0.0) / 0.25) if quiz_accuracy_drop > 0 else 0.0,
            min(1.0, failure_streak / 4.0) if failure_streak > 0 else 0.0,
            min(1.0, timeout_streak / 3.0) if timeout_streak > 0 else 0.0,
        ]
        return round(max(signals), 4)

    def _select_cooldown_policy(self, days_left: int | None) -> WakeCooldownPolicy:
        if days_left is not None and days_left <= 2:
            return WakeCooldownPolicy(cooldown_minutes=90, daily_limit=4, policy_name="exam_48h")
        if days_left is not None and days_left <= 7:
            return WakeCooldownPolicy(cooldown_minutes=120, daily_limit=3, policy_name="exam_7d")
        return WakeCooldownPolicy(cooldown_minutes=240, daily_limit=2, policy_name="default")

    def _extract_days_left(
        self, request_extra_context: dict[str, Any], user_context_payload: dict[str, Any]
    ) -> int | None:
        for candidate in (
            request_extra_context.get("days_left"),
            request_extra_context.get("time_constraint_days"),
            _as_dict(request_extra_context.get("exam_sprint_policy")).get("days_left"),
            _as_dict(request_extra_context.get("exam_sprint_policy")).get("days_remaining"),
            _as_dict(request_extra_context.get("exam_urgency")).get("days_left"),
            _as_dict(user_context_payload.get("exam_sprint_policy")).get("days_left"),
            _as_dict(user_context_payload.get("exam_sprint_policy")).get("days_remaining"),
            _as_dict(user_context_payload.get("exam_urgency")).get("days_left"),
            _as_dict(user_context_payload.get("cold_start_context")).get("time_constraint_days"),
            _as_dict(user_context_payload.get("cold_start_context")).get("days_left"),
            _as_dict(_as_dict(user_context_payload.get("profile_context")).get("cold_start_context")).get(
                "time_constraint_days"
            ),
            _as_dict(_as_dict(user_context_payload.get("profile_context")).get("cold_start_context")).get("days_left"),
        ):
            parsed = _safe_int(candidate)
            if parsed is not None and parsed >= 0:
                return parsed
        return None

    def _extract_completion_rates(
        self,
        request_extra_context: dict[str, Any],
        user_context_payload: dict[str, Any],
        self_model: dict[str, Any],
    ) -> tuple[float | None, float | None]:
        task_state = _as_dict(request_extra_context.get("task_state") or user_context_payload.get("task_state"))
        achievement_signals = _as_dict(
            request_extra_context.get("achievement_signals") or user_context_payload.get("achievement_signals")
        )
        harness_effectiveness = _as_dict(self_model.get("harness_effectiveness"))

        actual = self._first_numeric(
            request_extra_context.get("plan_completion_rate"),
            request_extra_context.get("completion_rate"),
            achievement_signals.get("plan_completion_rate"),
            task_state.get("plan_completion_rate"),
            task_state.get("avg_completion_rate"),
            user_context_payload.get("plan_completion_rate"),
            harness_effectiveness.get("task_completion_rate"),
        )
        expected = self._first_numeric(
            request_extra_context.get("expected_plan_completion_rate"),
            request_extra_context.get("expected_completion_rate"),
            request_extra_context.get("target_completion_rate"),
            task_state.get("expected_completion_rate"),
            task_state.get("target_completion_rate"),
            user_context_payload.get("expected_plan_completion_rate"),
        )
        return (
            _clamp_unit(actual) if actual is not None else None,
            _clamp_unit(expected, default=DEFAULT_EXPECTED_COMPLETION_RATE) if expected is not None else None,
        )

    def _extract_pass_probability(
        self, request_extra_context: dict[str, Any], user_context_payload: dict[str, Any]
    ) -> float | None:
        task_state = _as_dict(request_extra_context.get("task_state") or user_context_payload.get("task_state"))
        exam_sprint_policy = _as_dict(
            request_extra_context.get("exam_sprint_policy") or user_context_payload.get("exam_sprint_policy")
        )
        cold_start_context = _as_dict(user_context_payload.get("cold_start_context"))
        profile_cold_start = _as_dict(_as_dict(user_context_payload.get("profile_context")).get("cold_start_context"))
        value = self._first_numeric(
            request_extra_context.get("pass_probability"),
            exam_sprint_policy.get("pass_probability"),
            task_state.get("pass_probability"),
            task_state.get("diagnostic_pass_probability"),
            cold_start_context.get("diagnostic_pass_probability"),
            profile_cold_start.get("diagnostic_pass_probability"),
        )
        return _clamp_unit(value) if value is not None else None

    def _extract_same_cause_error_streak(
        self,
        request_extra_context: dict[str, Any],
        user_context_payload: dict[str, Any],
    ) -> int:
        error_bridge = self._extract_error_bridge_payload(request_extra_context, user_context_payload)
        for candidate in (
            request_extra_context.get("same_cause_error_streak"),
            request_extra_context.get("same_error_cause_streak"),
            _as_dict(request_extra_context.get("learning_failure")).get("same_cause_error_streak"),
            user_context_payload.get("same_cause_error_streak"),
            _as_dict(user_context_payload.get("learning_failure")).get("same_cause_error_streak"),
            error_bridge.get("recent_error_count"),
        ):
            parsed = _safe_int(candidate)
            if parsed is not None and parsed >= 0:
                return parsed
        return 0

    def _extract_quiz_accuracy_decline(
        self,
        request_extra_context: dict[str, Any],
        user_context_payload: dict[str, Any],
    ) -> tuple[bool, float]:
        for history_candidate in (
            request_extra_context.get("quiz_accuracy_history"),
            _as_dict(request_extra_context.get("learning_failure")).get("quiz_accuracy_history"),
            user_context_payload.get("quiz_accuracy_history"),
            _as_dict(user_context_payload.get("learning_failure")).get("quiz_accuracy_history"),
        ):
            history = [_clamp_unit(item) for item in _as_list(history_candidate) if _safe_float(item) is not None]
            if len(history) >= 2:
                drop = round(max(0.0, history[-2] - history[-1]), 4)
                return drop > 0.0, drop

        previous = self._first_numeric(
            request_extra_context.get("quiz_accuracy_prev"),
            request_extra_context.get("previous_quiz_accuracy"),
            user_context_payload.get("quiz_accuracy_prev"),
            user_context_payload.get("previous_quiz_accuracy"),
        )
        current = self._first_numeric(
            request_extra_context.get("quiz_accuracy"),
            request_extra_context.get("current_quiz_accuracy"),
            user_context_payload.get("quiz_accuracy"),
            user_context_payload.get("current_quiz_accuracy"),
        )
        if previous is not None and current is not None:
            drop = round(max(0.0, previous - current), 4)
            return drop > 0.0, drop

        explicit_drop = self._first_numeric(
            request_extra_context.get("quiz_accuracy_drop"),
            user_context_payload.get("quiz_accuracy_drop"),
        )
        drop = round(max(0.0, float(explicit_drop or 0.0)), 4)
        return drop > 0.0, drop

    def _extract_reminder_topic(
        self, request_extra_context: dict[str, Any], user_context_payload: dict[str, Any]
    ) -> str | None:
        for candidate in (
            request_extra_context.get("wake_reminder_topic"),
            request_extra_context.get("stuck_topic"),
            _as_dict(request_extra_context.get("checkpoint_state")).get("blocker"),
            _as_dict(request_extra_context.get("error_replan_bridge")).get("node_name"),
            user_context_payload.get("wake_reminder_topic"),
            _as_dict(user_context_payload.get("checkpoint_state")).get("blocker"),
        ):
            text = _normalize_text(candidate)
            if text:
                return text

        for collection in (
            request_extra_context.get("stuck_concepts"),
            _as_dict(request_extra_context.get("task_state")).get("diagnostic_top_bottlenecks"),
            user_context_payload.get("stuck_concepts"),
        ):
            for item in _as_list(collection):
                text = _normalize_text(item)
                if text:
                    return text
        return None

    def _extract_strategy_confidence(
        self,
        self_model: dict[str, Any],
        request_extra_context: dict[str, Any],
        user_context_payload: dict[str, Any],
    ) -> float:
        value = self._first_numeric(
            self_model.get("strategy_confidence"),
            request_extra_context.get("strategy_confidence"),
            user_context_payload.get("strategy_confidence"),
        )
        return _clamp_unit(value, default=0.7)

    def _extract_standard_layer_uncertainty(
        self,
        request_extra_context: dict[str, Any],
        user_context_payload: dict[str, Any],
    ) -> float:
        error_bridge = self._extract_error_bridge_payload(request_extra_context, user_context_payload)
        explicit = self._first_numeric(
            request_extra_context.get("standard_layer_uncertainty"),
            user_context_payload.get("standard_layer_uncertainty"),
            error_bridge.get("standard_layer_uncertainty"),
            error_bridge.get("uncertainty"),
            error_bridge.get("uncertainty_score"),
        )
        if explicit is not None:
            return _clamp_unit(explicit)

        confidence = self._first_numeric(error_bridge.get("confidence"))
        if confidence is not None:
            return _clamp_unit(1.0 - confidence)

        reason = _normalize_text(error_bridge.get("reason")).lower()
        if "error" in reason or "failed" in reason:
            return 0.65
        if reason:
            return 0.35
        return 0.0

    def _extract_failure_streak(
        self,
        request_extra_context: dict[str, Any],
        user_context_payload: dict[str, Any],
        self_model: dict[str, Any],
    ) -> int:
        for candidate in (
            request_extra_context.get("failure_streak"),
            request_extra_context.get("task_failure_streak"),
            user_context_payload.get("failure_streak"),
            self_model.get("task_failure_streak"),
        ):
            parsed = _safe_int(candidate)
            if parsed is not None and parsed >= 0:
                return parsed
        return 0

    def _extract_timeout_streak(
        self,
        request_extra_context: dict[str, Any],
        user_context_payload: dict[str, Any],
        self_model: dict[str, Any],
    ) -> int:
        for candidate in (
            request_extra_context.get("timeout_streak"),
            request_extra_context.get("consecutive_task_timeouts"),
            _as_dict(request_extra_context.get("learning_failure")).get("timeout_streak"),
            user_context_payload.get("timeout_streak"),
            _as_dict(user_context_payload.get("learning_failure")).get("timeout_streak"),
            self_model.get("timeout_count"),
        ):
            parsed = _safe_int(candidate)
            if parsed is not None and parsed >= 0:
                return parsed
        return 0

    def _extract_error_bridge_payload(
        self,
        request_extra_context: dict[str, Any],
        user_context_payload: dict[str, Any],
    ) -> dict[str, Any]:
        for candidate in (
            request_extra_context.get("error_replan_bridge"),
            request_extra_context.get("standard_layer"),
            user_context_payload.get("error_replan_bridge"),
            user_context_payload.get("standard_layer"),
        ):
            payload = _as_dict(candidate)
            if payload:
                return payload
        return {}

    def _extract_plan_id(
        self, request_extra_context: dict[str, Any], user_context_payload: dict[str, Any]
    ) -> str | None:
        task_state = _as_dict(request_extra_context.get("task_state") or user_context_payload.get("task_state"))
        for candidate in (
            request_extra_context.get("plan_id"),
            request_extra_context.get("active_plan_id"),
            task_state.get("plan_id"),
            user_context_payload.get("plan_id"),
            user_context_payload.get("active_plan_id"),
            _as_dict(user_context_payload.get("plan_context")).get("plan_id"),
        ):
            text = _normalize_text(candidate)
            if text:
                return text
        return None

    def _first_numeric(self, *candidates: Any) -> float | None:
        for candidate in candidates:
            parsed = _safe_float(candidate)
            if parsed is not None:
                return parsed
        return None

    def _parse_datetime(self, value: Any) -> datetime | None:
        if not value:
            return None
        if isinstance(value, datetime):
            return value.replace(tzinfo=None) if value.tzinfo is None else value.astimezone(UTC).replace(tzinfo=None)
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is not None:
            return parsed.astimezone(UTC).replace(tzinfo=None)
        return parsed
