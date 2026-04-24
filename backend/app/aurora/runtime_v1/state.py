from __future__ import annotations

import inspect
import json
from datetime import datetime, timezone
from typing import Any, Literal
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


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _normalize_user_id(value: UUID | str) -> str:
    if isinstance(value, UUID):
        return str(value)
    text = _normalize_text(value)
    if not text:
        raise ValueError("user_id is required")
    return text


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

    @field_validator("tension_id", "domain", "description")
    @classmethod
    def _validate_text(cls, value: str) -> str:
        text = _normalize_text(value)
        if not text:
            raise ValueError("text field is required")
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


class ActivityProfile(AuroraSchemaBase):
    proactive_intensity: float = 0.6
    next_wake_at: datetime | None = None
    conversation_style: ConversationStyle = "warm"
    agenda_priority: str | None = None
    task_density_hint: float = 0.7

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
        return AuroraState.model_validate_json(raw)

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
