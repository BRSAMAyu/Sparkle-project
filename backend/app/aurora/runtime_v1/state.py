from __future__ import annotations

import inspect
import json
from datetime import UTC, datetime
from typing import Any, Literal, Mapping
from uuid import UUID

from pydantic import Field, field_validator

from app.aurora.common import AuroraSchemaBase
from app.config import settings

AuroraSurface = Literal["aurora_modeling", "aurora_planning", "aurora_checkpoint"]
TensionStatus = Literal["open", "partially_resolved", "resolved", "dropped"]
AuroraIntentType = Literal[
    "pursue_tension",
    "confirm_understanding",
    "answer_detour",
    "soft_return",
    "encourage",
    "schedule_follow_up",
    "wait",
]
ConversationStyle = Literal["warm", "structured", "exploratory"]
WakeStatus = Literal["pending", "executed", "cancelled", "suppressed"]
StreamingStatus = Literal["idle", "emitting", "waiting_user"]
ExpressionDimension = Literal[
    "tone_warmth",
    "directness",
    "brevity",
    "friendliness",
    "challenge_intensity",
]

EXPRESSION_DIMENSIONS: tuple[ExpressionDimension, ...] = (
    "tone_warmth",
    "directness",
    "brevity",
    "friendliness",
    "challenge_intensity",
)
DEFAULT_ACTIVITY_EXPRESSION: dict[ExpressionDimension, float] = {
    "tone_warmth": 0.68,
    "directness": 0.48,
    "brevity": 0.55,
    "friendliness": 0.74,
    "challenge_intensity": 0.36,
}
CORE_MODELING_DOMAINS: tuple[str, ...] = ("goal", "scope", "baseline", "time", "motivation")

# Aurora energy levels — L0 silent through L3 full core session
AuroraEnergyLevel = Literal["L0", "L1", "L2", "L3"]
AuroraBandStatus = Literal[
    "sensing",             # L0-L1: Aurora observing / light context
    "calibrated",          # All facets ready, no action needed
    "risk_found",          # Strategy or model conflict detected
    "needs_confirm",       # Aurora has a judgment needing user validation
    "calibration_available",  # User can trigger L3 deep calibration
    "cooling_down",        # L3 session recently completed, cooldown active
]


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _normalize_user_id(value: UUID | str) -> str:
    if isinstance(value, UUID):
        return str(value)
    text = _normalize_text(value)
    if not text:
        raise ValueError("user_id is required")
    return text


def default_activity_expression() -> dict[str, float]:
    return dict(DEFAULT_ACTIVITY_EXPRESSION)


def normalize_expression_update(value: Any) -> dict[str, float]:
    if value in (None, ""):
        return {}
    if not isinstance(value, Mapping):
        raise ValueError("expression must be a mapping")

    unknown = sorted(str(key) for key in value if str(key) not in EXPRESSION_DIMENSIONS)
    if unknown:
        raise ValueError(f"unsupported expression field: {unknown[0]}")

    normalized: dict[str, float] = {}
    for key in EXPRESSION_DIMENSIONS:
        if key not in value:
            continue
        try:
            numeric = float(value[key])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"expression.{key} must be numeric") from exc
        if not 0.0 <= numeric <= 1.0:
            raise ValueError(f"expression.{key} must be within [0.0, 1.0]")
        normalized[key] = numeric
    return normalized


def merge_expression_settings(
    base: Mapping[str, Any] | None = None,
    updates: Mapping[str, Any] | None = None,
) -> dict[str, float]:
    merged = default_activity_expression()
    if isinstance(base, Mapping):
        merged.update(normalize_expression_update(base))
    if isinstance(updates, Mapping):
        merged.update(normalize_expression_update(updates))
    return merged


def merge_activity_profile_payload(
    base: Mapping[str, Any] | None = None,
    updates: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    merged = dict(base or {})
    merged["expression"] = merge_expression_settings(merged.get("expression"))
    if not isinstance(updates, Mapping):
        return merged

    for key, value in updates.items():
        if key == "expression":
            if isinstance(value, Mapping):
                merged["expression"] = merge_expression_settings(merged.get("expression"), value)
            continue
        if key == "strategy":
            if isinstance(value, Mapping):
                base_strategy = (
                    dict(merged.get("strategy") or {}) if isinstance(merged.get("strategy"), Mapping) else {}
                )
                base_strategy.update(dict(value))
                merged["strategy"] = base_strategy
            continue
        if value in (None, ""):
            continue
        merged[str(key)] = value
    return merged


class InformationalTension(AuroraSchemaBase):
    tension_id: str
    domain: str
    description: str
    priority: float
    status: TensionStatus = "open"
    evidence: list[str] = Field(default_factory=list)
    importance_reasoning: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)
    last_attempted_at: datetime | None = None

    @field_validator("tension_id", "description")
    @classmethod
    def _validate_text(cls, value: str) -> str:
        text = _normalize_text(value)
        if not text:
            raise ValueError("text field is required")
        return text

    @field_validator("domain")
    @classmethod
    def _validate_domain(cls, value: str) -> str:
        text = _normalize_text(value)
        if not text:
            raise ValueError("text field is required")
        if text.lower() == "motivation":
            return "motivation"
        return text

    @field_validator("priority")
    @classmethod
    def _validate_priority(cls, value: float) -> float:
        numeric = float(value)
        if not 0.0 <= numeric <= 1.0:
            raise ValueError("priority must be within [0.0, 1.0]")
        return numeric


class AuroraIntent(AuroraSchemaBase):
    intent_type: AuroraIntentType
    target_tension_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("target_tension_id")
    @classmethod
    def _normalize_target(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = _normalize_text(value)
        return text or None


class LatentThread(AuroraSchemaBase):
    thread_id: str
    source_intent: AuroraIntent
    tension_links: list[str] = Field(default_factory=list)
    salience: float
    context_snapshot: str
    created_at: datetime = Field(default_factory=_utcnow)

    @field_validator("thread_id", "context_snapshot")
    @classmethod
    def _validate_text(cls, value: str) -> str:
        text = _normalize_text(value)
        if not text:
            raise ValueError("text field is required")
        return text

    @field_validator("salience")
    @classmethod
    def _validate_salience(cls, value: float) -> float:
        numeric = float(value)
        if not 0.0 <= numeric <= 1.0:
            raise ValueError("salience must be within [0.0, 1.0]")
        return numeric


class AuroraTeachingStrategy(AuroraSchemaBase):
    concept_first: bool = False
    problem_first: bool = False
    worked_example_first: bool = False
    retrieval_practice: bool = False
    interleaving: bool = False
    spaced_review: bool = False
    error_analysis_required: bool = False
    drop_low_roi_topics: bool = False
    new_topic_allowed: bool = True


class ActivityProfile(AuroraSchemaBase):
    proactive_intensity: float = 0.6
    next_wake_at: datetime | None = None
    conversation_style: ConversationStyle = "warm"
    expression: dict[str, float] = Field(default_factory=default_activity_expression)
    agenda_priority: str | None = None
    task_density_hint: float = 0.7
    strategy: AuroraTeachingStrategy = Field(default_factory=AuroraTeachingStrategy)

    @field_validator("proactive_intensity", "task_density_hint")
    @classmethod
    def _validate_unit_interval(cls, value: float) -> float:
        numeric = float(value)
        if not 0.0 <= numeric <= 1.0:
            raise ValueError("numeric field must be within [0.0, 1.0]")
        return numeric

    @field_validator("agenda_priority")
    @classmethod
    def _normalize_agenda_priority(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = _normalize_text(value)
        return text or None

    @field_validator("expression", mode="before")
    @classmethod
    def _normalize_expression(cls, value: Any) -> dict[str, float]:
        if value in (None, ""):
            return default_activity_expression()
        return merge_expression_settings(updates=normalize_expression_update(value))


class ScheduledWake(AuroraSchemaBase):
    wake_id: str
    scheduled_at: datetime
    reason: str
    planned_action: str
    status: WakeStatus = "pending"

    @field_validator("wake_id", "reason", "planned_action")
    @classmethod
    def _validate_text(cls, value: str) -> str:
        text = _normalize_text(value)
        if not text:
            raise ValueError("text field is required")
        return text


class AuroraRuntimeMetadata(AuroraSchemaBase):
    aurora_surface: str
    aurora_runtime_enabled: bool
    surface_complete: bool = False
    modeling_complete: bool = False

    @field_validator("aurora_surface")
    @classmethod
    def _validate_surface(cls, value: str) -> str:
        text = _normalize_text(value)
        if not text:
            raise ValueError("aurora_surface is required")
        return text


class AuroraState(AuroraSchemaBase):
    user_id: str
    surface: str
    conversation_id: str
    runtime_session_id: str
    user_model_snapshot: dict[str, Any] = Field(default_factory=dict)
    informational_tensions: list[InformationalTension] = Field(default_factory=list)
    current_intent: AuroraIntent | None = None
    latent_threads: list[LatentThread] = Field(default_factory=list)
    activity_profile: ActivityProfile = Field(default_factory=ActivityProfile)
    self_scheduled_wakes: list[ScheduledWake] = Field(default_factory=list)
    streaming_status: StreamingStatus = "idle"
    ingress_events: list[dict[str, Any]] = Field(default_factory=list)
    last_decision_at: datetime | None = None
    updated_at: datetime = Field(default_factory=_utcnow)

    @field_validator("user_id")
    @classmethod
    def _validate_user_id(cls, value: str) -> str:
        return _normalize_user_id(value)

    @field_validator("surface", "conversation_id", "runtime_session_id")
    @classmethod
    def _validate_scope_fields(cls, value: str) -> str:
        text = _normalize_text(value)
        if not text:
            raise ValueError("scope field is required")
        return text


class AuroraCognitiveSnapshot(AuroraSchemaBase):
    user_id: str
    user_model_snapshot: dict[str, Any] = Field(default_factory=dict)
    informational_tensions: list[InformationalTension] = Field(default_factory=list)
    current_intent: AuroraIntent | None = None
    latent_threads: list[LatentThread] = Field(default_factory=list)
    activity_profile: ActivityProfile = Field(default_factory=ActivityProfile)
    last_surface: str | None = None
    last_conversation_id: str | None = None
    last_runtime_session_id: str | None = None
    last_decision_at: datetime | None = None
    updated_at: datetime = Field(default_factory=_utcnow)
    snapshot_version: int = 1

    @field_validator("user_id")
    @classmethod
    def _validate_user(cls, value: str) -> str:
        return _normalize_user_id(value)


class AuroraEnergyState(AuroraSchemaBase):
    """Tracks Aurora's current energy level and wake eligibility."""
    user_id: str
    current_level: AuroraEnergyLevel = "L0"
    wake_score: float = 0.0
    last_l3_session_at: datetime | None = None
    l3_session_count_today: int = 0
    cooldown_until: datetime | None = None
    updated_at: datetime = Field(default_factory=_utcnow)

    @field_validator("wake_score")
    @classmethod
    def _validate_wake_score(cls, value: float) -> float:
        return max(0.0, min(1.0, float(value)))

    @property
    def is_cooling_down(self) -> bool:
        if self.cooldown_until is None:
            return False
        return _utcnow() < self.cooldown_until.replace(tzinfo=None)

    @property
    def can_user_wake(self) -> bool:
        return not self.is_cooling_down and self.l3_session_count_today < 3


class AuroraWakeEligibility(AuroraSchemaBase):
    """Determines if and how Aurora can be woken for a deep calibration."""
    can_user_wake: bool = False
    user_quota_remaining: int = 0
    cooldown_status: str = "available"  # available | cooling_down | exhausted
    cooldown_remaining_min: int = 0
    recommended_session_type: str = "strategy_recalibration"
    estimated_duration_sec: int = 240
    wake_reasons: list[str] = Field(default_factory=list)
    suggested_scope: str = ""
    fallback_if_unavailable: str = "quick_calibration"


def build_aurora_runtime_metadata(
    *,
    surface: str,
    surface_complete: bool = False,
    modeling_complete: bool = False,
    runtime_enabled: bool | None = None,
) -> AuroraRuntimeMetadata:
    enabled = settings.ENABLE_AURORA_RUNTIME_V1 if runtime_enabled is None else bool(runtime_enabled)
    return AuroraRuntimeMetadata(
        aurora_surface=surface,
        aurora_runtime_enabled=enabled,
        surface_complete=surface_complete,
        modeling_complete=modeling_complete,
    )


class AuroraRuntimeStore:
    RUNTIME_STATE_TTL_SECONDS = 24 * 60 * 60
    RUNTIME_KEY_TEMPLATE = "aurora:runtime:{user_id}:{surface}:{conversation_id}"
    SURFACE_INDEX_KEY_PREFIX = "aurora:surface-index:"

    def __init__(
        self,
        redis,
        *,
        ttl_seconds: int = RUNTIME_STATE_TTL_SECONDS,
        enabled: bool | None = None,
    ) -> None:
        self.redis = redis
        self.ttl_seconds = ttl_seconds
        self._enabled = enabled

    @property
    def enabled(self) -> bool:
        return settings.ENABLE_AURORA_RUNTIME_V1 if self._enabled is None else bool(self._enabled)

    def runtime_key(self, user_id: UUID | str, surface: str, conversation_id: str) -> str:
        return self.RUNTIME_KEY_TEMPLATE.format(
            user_id=_normalize_user_id(user_id),
            surface=_normalize_text(surface),
            conversation_id=_normalize_text(conversation_id),
        )

    def surface_index_key(self, user_id: UUID | str) -> str:
        return f"{self.SURFACE_INDEX_KEY_PREFIX}{_normalize_user_id(user_id)}"

    async def save_runtime_state(self, state: AuroraState) -> bool:
        if not self.enabled or self.redis is None:
            return False

        key = self.runtime_key(state.user_id, state.surface, state.conversation_id)
        await self._redis_call("setex", key, self.ttl_seconds, state.model_dump_json())
        await self._update_surface_index(state)
        return True

    async def load_runtime_state(
        self,
        *,
        user_id: UUID | str,
        surface: str,
        conversation_id: str,
    ) -> AuroraState | None:
        if not self.enabled or self.redis is None:
            return None

        raw = await self._redis_call("get", self.runtime_key(user_id, surface, conversation_id))
        if not raw:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        try:
            return AuroraState.model_validate_json(raw)
        except Exception:
            data = json.loads(raw) if isinstance(raw, str) else raw
            if not isinstance(data, dict):
                return None
            return AuroraState.model_validate(self._coerce_legacy_state_payload(data))

    async def load_latest_surface_state(
        self,
        *,
        user_id: UUID | str,
        surface: str,
    ) -> AuroraState | None:
        if not self.enabled or self.redis is None:
            return None
        index = await self.load_surface_index(user_id)
        entry = index.get(_normalize_text(surface))
        if not isinstance(entry, dict) or not entry.get("conversation_id"):
            return None
        return await self.load_runtime_state(
            user_id=user_id,
            surface=surface,
            conversation_id=str(entry["conversation_id"]),
        )

    async def delete_runtime_state(
        self,
        *,
        user_id: UUID | str,
        surface: str,
        conversation_id: str,
    ) -> bool:
        if not self.enabled or self.redis is None:
            return False

        key = self.runtime_key(user_id, surface, conversation_id)
        await self._redis_call("delete", key)
        await self._remove_surface_index(
            user_id=user_id,
            surface=surface,
            conversation_id=conversation_id,
        )
        return True

    async def load_surface_index(self, user_id: UUID | str) -> dict[str, dict[str, Any]]:
        if not self.enabled or self.redis is None:
            return {}

        raw = await self._redis_call("get", self.surface_index_key(user_id))
        if not raw:
            return {}
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}

    async def _update_surface_index(self, state: AuroraState) -> None:
        index = await self.load_surface_index(state.user_id)
        index[state.surface] = {
            "conversation_id": state.conversation_id,
            "runtime_session_id": state.runtime_session_id,
            "updated_at": state.updated_at.isoformat(),
        }
        await self._redis_call(
            "setex",
            self.surface_index_key(state.user_id),
            self.ttl_seconds,
            json.dumps(index, ensure_ascii=False),
        )

    async def _remove_surface_index(
        self,
        *,
        user_id: UUID | str,
        surface: str,
        conversation_id: str,
    ) -> None:
        index = await self.load_surface_index(user_id)
        entry = index.get(surface)
        if isinstance(entry, dict) and entry.get("conversation_id") == _normalize_text(conversation_id):
            index.pop(surface, None)
        await self._redis_call(
            "setex",
            self.surface_index_key(user_id),
            self.ttl_seconds,
            json.dumps(index, ensure_ascii=False),
        )

    async def _redis_call(self, method_name: str, *args, **kwargs):
        method = getattr(self.redis, method_name, None)
        if method is None:
            return None
        result = method(*args, **kwargs)
        if inspect.isawaitable(result):
            return await result
        return result

    def _coerce_legacy_state_payload(self, data: dict[str, Any]) -> dict[str, Any]:
        coerced = dict(data)
        surface = _normalize_text(coerced.get("surface")) or "aurora_modeling"
        conversation_id = _normalize_text(coerced.get("conversation_id")) or "unknown"
        runtime_session_id = _normalize_text(coerced.get("runtime_session_id")) or conversation_id
        coerced["surface"] = surface
        coerced["conversation_id"] = conversation_id
        coerced["runtime_session_id"] = runtime_session_id
        coerced["user_id"] = _normalize_user_id(coerced.get("user_id") or "unknown")

        normalized_tensions: list[dict[str, Any]] = []
        for index, item in enumerate(coerced.get("informational_tensions") or []):
            if not isinstance(item, Mapping):
                continue
            domain = _normalize_text(item.get("domain")) or "checkpoint_gap"
            description = _normalize_text(item.get("description")) or domain
            try:
                priority = float(item.get("priority") or 0.5)
            except (TypeError, ValueError):
                priority = 0.5
            normalized_tensions.append(
                {
                    **dict(item),
                    "tension_id": _normalize_text(item.get("tension_id"))
                    or f"{conversation_id}:tension:{domain}:{index}",
                    "domain": domain,
                    "description": description,
                    "priority": max(0.0, min(1.0, priority)),
                    "status": item.get("status") or "open",
                }
            )
        coerced["informational_tensions"] = normalized_tensions

        default_intent = coerced.get("current_intent")
        if not isinstance(default_intent, Mapping):
            default_intent = {"intent_type": "wait", "payload": {}}
        coerced["current_intent"] = dict(default_intent)

        normalized_threads: list[dict[str, Any]] = []
        for index, item in enumerate(coerced.get("latent_threads") or []):
            if not isinstance(item, Mapping):
                continue
            context_snapshot = _normalize_text(item.get("context_snapshot")) or _normalize_text(item.get("summary"))
            if not context_snapshot:
                continue
            try:
                salience = float(item.get("salience") or 0.5)
            except (TypeError, ValueError):
                salience = 0.5
            normalized_threads.append(
                {
                    **dict(item),
                    "thread_id": _normalize_text(item.get("thread_id")) or f"{conversation_id}:thread:{index}",
                    "source_intent": (
                        dict(item.get("source_intent"))
                        if isinstance(item.get("source_intent"), Mapping)
                        else default_intent
                    ),
                    "salience": max(0.0, min(1.0, salience)),
                    "context_snapshot": context_snapshot,
                }
            )
        coerced["latent_threads"] = normalized_threads

        wakes: list[dict[str, Any]] = []
        for index, item in enumerate(coerced.get("self_scheduled_wakes") or []):
            if not isinstance(item, Mapping) or not item.get("scheduled_at"):
                continue
            reason = (
                _normalize_text(item.get("reason")) or _normalize_text(item.get("planned_action")) or "scheduled wake"
            )
            wakes.append(
                {
                    **dict(item),
                    "wake_id": _normalize_text(item.get("wake_id"))
                    or _normalize_text(item.get("id"))
                    or f"{conversation_id}:wake:{index}",
                    "reason": reason,
                    "planned_action": _normalize_text(item.get("planned_action")) or "emit_message",
                    "status": item.get("status") or "pending",
                }
            )
        coerced["self_scheduled_wakes"] = wakes
        return coerced


class AuroraEnergyStore:
    """Redis-backed store for Aurora energy levels, cooldowns, and wake eligibility."""

    ENERGY_KEY = "aurora:energy:{user_id}"
    COOLDOWN_TEMPLATES: dict[str, int] = {
        "default": 360,        # 6 hours in minutes
        "sprint_14d": 240,     # 4 hours
        "sprint_7d": 120,      # 2 hours
        "sprint_48h": 90,      # 90 minutes
        "sprint_24h": 60,      # 60 minutes
    }
    DAILY_QUOTA: dict[str, int] = {
        "default": 1,
        "sprint_14d": 2,
        "sprint_7d": 2,
        "sprint_48h": 3,
        "sprint_24h": 3,
    }

    def __init__(self, redis, *, enabled: bool | None = None) -> None:
        self.redis = redis
        self._enabled = enabled

    @property
    def enabled(self) -> bool:
        return settings.ENABLE_AURORA_RUNTIME_V1 if self._enabled is None else bool(self._enabled)

    async def load_energy(self, user_id: UUID | str) -> AuroraEnergyState:
        uid = _normalize_user_id(user_id)
        if not self.enabled or self.redis is None:
            return AuroraEnergyState(user_id=uid)

        raw = await self._redis_call("get", self.ENERGY_KEY.format(user_id=uid))
        if not raw:
            return AuroraEnergyState(user_id=uid)
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        try:
            return AuroraEnergyState.model_validate_json(raw)
        except Exception:
            return AuroraEnergyState(user_id=uid)

    async def save_energy(self, state: AuroraEnergyState) -> bool:
        if not self.enabled or self.redis is None:
            return False
        key = self.ENERGY_KEY.format(user_id=state.user_id)
        ttl = 48 * 60 * 60  # 48 hours
        await self._redis_call("setex", key, ttl, state.model_dump_json())
        return True

    async def record_l3_session(self, user_id: UUID | str, *, sprint_mode: str = "default") -> AuroraEnergyState:
        energy = await self.load_energy(user_id)
        now = _utcnow()
        energy.current_level = "L3"
        energy.last_l3_session_at = now
        energy.l3_session_count_today += 1

        cooldown_min = self.COOLDOWN_TEMPLATES.get(sprint_mode, 360)
        from datetime import timedelta

        energy.cooldown_until = now + timedelta(minutes=cooldown_min)
        energy.updated_at = now
        await self.save_energy(energy)
        return energy

    async def resolve_energy_level(
        self,
        user_id: UUID | str,
        *,
        aurora_active: bool = False,
        overall_status: str = "missing",
        ready_count: int = 0,
        total_count: int = 4,
        has_risk: bool = False,
    ) -> AuroraEnergyState:
        energy = await self.load_energy(user_id)

        if energy.is_cooling_down:
            energy.current_level = "L0"
        elif not aurora_active:
            energy.current_level = "L0"
            energy.wake_score = 0.0
        elif has_risk or overall_status == "recalibrating":
            energy.current_level = "L2"
            energy.wake_score = min(1.0, 0.5 + ready_count * 0.1)
        elif overall_status == "ready" and ready_count == total_count:
            energy.current_level = "L1"
            energy.wake_score = min(1.0, 0.7 + ready_count * 0.05)
        elif overall_status in ("partial", "missing"):
            energy.current_level = "L1"
            energy.wake_score = min(1.0, 0.3 + ready_count * 0.1)
        else:
            energy.current_level = "L1"
            energy.wake_score = 0.5

        energy.updated_at = _utcnow()
        await self.save_energy(energy)
        return energy

    def compute_wake_eligibility(
        self,
        energy: AuroraEnergyState,
        *,
        sprint_mode: str = "default",
        wake_reasons: list[str] | None = None,
    ) -> AuroraWakeEligibility:
        if energy.is_cooling_down:
            remaining = int((energy.cooldown_until.replace(tzinfo=None) - _utcnow()).total_seconds() / 60)
            return AuroraWakeEligibility(
                can_user_wake=False,
                user_quota_remaining=max(0, self.DAILY_QUOTA.get(sprint_mode, 1) - energy.l3_session_count_today),
                cooldown_status="cooling_down",
                cooldown_remaining_min=max(0, remaining),
                wake_reasons=wake_reasons or [],
                suggested_scope="",
                fallback_if_unavailable="quick_calibration",
            )

        quota = self.DAILY_QUOTA.get(sprint_mode, 1)
        remaining = max(0, quota - energy.l3_session_count_today)
        if remaining <= 0:
            return AuroraWakeEligibility(
                can_user_wake=False,
                user_quota_remaining=0,
                cooldown_status="exhausted",
                fallback_if_unavailable="quick_calibration",
                wake_reasons=wake_reasons or [],
            )

        return AuroraWakeEligibility(
            can_user_wake=True,
            user_quota_remaining=remaining,
            cooldown_status="available",
            wake_reasons=wake_reasons or [],
            recommended_session_type="strategy_recalibration",
            estimated_duration_sec=240,
        )

    async def _redis_call(self, method_name: str, *args, **kwargs):
        method = getattr(self.redis, method_name, None)
        if method is None:
            return None
        result = method(*args, **kwargs)
        if inspect.isawaitable(result):
            return await result
        return result
