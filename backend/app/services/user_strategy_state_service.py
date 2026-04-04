from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import timezone, datetime, timedelta
from typing import Any
from uuid import UUID

from loguru import logger

from app.services.personalization.preference_service import PreferenceService
from app.services.plan_state_service import PlanStateService


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _parse_dt(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    raw = str(value or "").strip()
    if not raw:
        return None
    normalized = raw.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        dumped = value.model_dump(mode="json")
        return dumped if isinstance(dumped, dict) else {}
    return {}


def _as_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _clean_text(value: Any, *, limit: int = 240) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return f"{text[: max(0, limit - 1)].rstrip()}…"


@dataclass(frozen=True)
class StrategyFieldSpec:
    default: Any
    allowed_layers: set[str]
    value_type: str
    min_value: float | None = None
    max_value: float | None = None
    allowed_values: set[str] | None = None
    max_length: int | None = None


class UserStrategyStateService:
    SESSION_LAYER = "session"
    EPISODE_LAYER = "episode"
    PROFILE_LAYER = "profile"
    LAYER_PRECEDENCE = (SESSION_LAYER, EPISODE_LAYER, PROFILE_LAYER)

    SESSION_KEY_PREFIX = "session:strategy:"
    SESSION_HISTORY_KEY_PREFIX = "session:strategy_history:"
    SESSION_DEFAULT_TTL_SECONDS = 6 * 60 * 60
    SESSION_MAX_TTL_SECONDS = 7 * 24 * 60 * 60

    EPISODE_DEFAULT_TTL_SECONDS = 14 * 24 * 60 * 60
    EPISODE_MAX_TTL_SECONDS = 30 * 24 * 60 * 60

    PROFILE_STATE_KEY = "user_strategy_state"
    PROFILE_META_KEY = "user_strategy_meta"
    PROFILE_HISTORY_KEY = "user_strategy_history"

    EPISODE_STATE_KEY = "user_strategy_state"
    EPISODE_META_KEY = "user_strategy_meta"
    EPISODE_HISTORY_KEY = "user_strategy_history"

    HISTORY_LIMIT = 50

    FIELD_SPECS: dict[str, StrategyFieldSpec] = {
        "difficulty_level": StrategyFieldSpec(
            default=3,
            allowed_layers={SESSION_LAYER, EPISODE_LAYER, PROFILE_LAYER},
            value_type="int",
            min_value=1,
            max_value=5,
        ),
        "push_vs_support": StrategyFieldSpec(
            default=0.5,
            allowed_layers={SESSION_LAYER, EPISODE_LAYER, PROFILE_LAYER},
            value_type="float",
            min_value=0.0,
            max_value=1.0,
        ),
        "session_mode": StrategyFieldSpec(
            default="guided",
            allowed_layers={SESSION_LAYER, EPISODE_LAYER, PROFILE_LAYER},
            value_type="enum",
            allowed_values={"guided", "exploratory", "review", "recovery"},
        ),
        "intervention_intensity": StrategyFieldSpec(
            default="medium",
            allowed_layers={SESSION_LAYER, EPISODE_LAYER, PROFILE_LAYER},
            value_type="enum",
            allowed_values={"low", "medium", "high"},
        ),
        "explanation_style": StrategyFieldSpec(
            default="conceptual",
            allowed_layers={SESSION_LAYER, EPISODE_LAYER, PROFILE_LAYER},
            value_type="enum",
            allowed_values={"conceptual", "example_based", "step_by_step"},
        ),
        "retrieval_emphasis": StrategyFieldSpec(
            default="balanced",
            allowed_layers={SESSION_LAYER, EPISODE_LAYER, PROFILE_LAYER},
            value_type="enum",
            allowed_values={"user_materials", "balanced", "general_knowledge"},
        ),
        "current_episode_note": StrategyFieldSpec(
            default="",
            allowed_layers={SESSION_LAYER, EPISODE_LAYER},
            value_type="str",
            max_length=240,
        ),
    }

    def __init__(self, db, redis=None):
        self.db = db
        self.redis = redis
        self.preference_service = PreferenceService(db, redis)
        self.plan_state_service = PlanStateService(db, redis)

    async def get_effective_state(
        self,
        user_id: UUID,
        *,
        plan_id: UUID | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        profile_layer = await self._load_profile_layer(user_id)
        episode_layer = await self._load_episode_layer(user_id, plan_id)
        session_layer = await self._load_session_layer(session_id)

        values = {field: spec.default for field, spec in self.FIELD_SPECS.items()}
        sources = {field: "default" for field in self.FIELD_SPECS}
        expirations: dict[str, str | None] = {}

        for layer_name, layer_payload in (
            (self.PROFILE_LAYER, profile_layer),
            (self.EPISODE_LAYER, episode_layer),
            (self.SESSION_LAYER, session_layer),
        ):
            for field, value in dict(layer_payload.get("state") or {}).items():
                if field not in self.FIELD_SPECS:
                    continue
                values[field] = value
                sources[field] = layer_name
                expirations[field] = self._layer_expiration_for_field(layer_payload, field)

        adaptive_view = episode_layer.get("adaptive_view") if isinstance(episode_layer, dict) else {}
        if isinstance(adaptive_view, dict):
            difficulty_shift = adaptive_view.get("difficulty_shift")
            if (
                isinstance(difficulty_shift, (int, float))
                and sources.get("difficulty_level") in {"default", self.PROFILE_LAYER}
            ):
                values["difficulty_level"] = self._normalize_field_value(
                    "difficulty_level",
                    values["difficulty_level"] + round(float(difficulty_shift) * 2),
                )
                sources["difficulty_level"] = "episode_adaptive"
            adaptive_summary = str(adaptive_view.get("summary") or "").strip()
            if adaptive_summary and not str(values.get("current_episode_note") or "").strip():
                values["current_episode_note"] = adaptive_summary
                sources["current_episode_note"] = "episode_adaptive"

        meta = {
            "sources": sources,
            "field_expirations": {key: value for key, value in expirations.items() if value},
            "session_layer_active": bool(session_layer.get("state")),
            "episode_layer_active": bool(episode_layer.get("state")),
            "profile_layer_active": bool(profile_layer.get("state")),
            "adaptive_adjustments": dict(adaptive_view.get("adaptive_adjustments") or {}) if isinstance(adaptive_view, dict) else {},
            "adaptive_summary": str(adaptive_view.get("summary") or "").strip() if isinstance(adaptive_view, dict) else "",
        }

        return {**values, "meta": meta}

    async def get_recent_changes(
        self,
        user_id: UUID,
        *,
        plan_id: UUID | None = None,
        session_id: str | None = None,
        limit: int = 12,
    ) -> list[dict[str, Any]]:
        profile_layer = await self._load_profile_layer(user_id)
        episode_layer = await self._load_episode_layer(user_id, plan_id)
        session_layer = await self._load_session_layer(session_id)

        combined = [
            *[item for item in _as_list(session_layer.get("history")) if isinstance(item, dict)],
            *[item for item in _as_list(episode_layer.get("history")) if isinstance(item, dict)],
            *[item for item in _as_list(profile_layer.get("history")) if isinstance(item, dict)],
        ]
        combined.sort(
            key=lambda item: _parse_dt(item.get("timestamp")) or datetime.min,
            reverse=True,
        )
        return combined[: max(1, limit)]

    async def apply_adjustment(
        self,
        user_id: UUID,
        changes: dict[str, Any],
        *,
        layer: str,
        reason: str,
        evidence: dict[str, Any],
        confidence: float,
        session_id: str | None = None,
        plan_id: UUID | None = None,
        ttl_seconds: int | None = None,
    ) -> dict[str, Any]:
        normalized_layer = str(layer or "").strip().lower()
        if normalized_layer not in self.LAYER_PRECEDENCE:
            raise ValueError(f"Unsupported strategy layer: {layer}")
        if normalized_layer == self.SESSION_LAYER and not str(session_id or "").strip():
            raise ValueError("session_id is required for session-layer strategy writes")
        if normalized_layer == self.EPISODE_LAYER and plan_id is None:
            raise ValueError("plan_id is required for episode-layer strategy writes")
        if not isinstance(changes, dict) or not changes:
            return {
                "applied": [],
                "effective_state": await self.get_effective_state(user_id, plan_id=plan_id, session_id=session_id),
            }

        valid_changes = self._normalize_changes(changes, layer=normalized_layer)
        timestamp = _utcnow()
        expires_at = self._calculate_expiration(normalized_layer, ttl_seconds, timestamp)
        bounded_confidence = round(min(1.0, max(0.0, float(confidence))), 2)

        if normalized_layer == self.SESSION_LAYER:
            current_layer = await self._load_session_layer(session_id)
        elif normalized_layer == self.EPISODE_LAYER:
            current_layer = await self._load_episode_layer(user_id, plan_id)
        else:
            current_layer = await self._load_profile_layer(user_id)

        current_state = dict(current_layer.get("state") or {})
        current_meta = dict(current_layer.get("meta") or {})
        history = [item for item in _as_list(current_layer.get("history")) if isinstance(item, dict)]
        field_expirations = dict(current_meta.get("field_expirations") or {})
        audit_entries: list[dict[str, Any]] = []

        for field, new_value in valid_changes.items():
            old_value = current_state.get(field, self.FIELD_SPECS[field].default)
            current_state[field] = new_value
            if expires_at is not None:
                field_expirations[field] = expires_at.isoformat()
            else:
                field_expirations.pop(field, None)
            audit_entries.append(
                {
                    "field": field,
                    "layer": normalized_layer,
                    "old_value": old_value,
                    "new_value": new_value,
                    "reason": _clean_text(reason, limit=180),
                    "evidence": _as_dict(evidence),
                    "confidence": bounded_confidence,
                    "timestamp": timestamp.isoformat(),
                    "expires_at": expires_at.isoformat() if expires_at is not None else None,
                }
            )

        current_meta.update(
            {
                "updated_at": timestamp.isoformat(),
                "last_reason": _clean_text(reason, limit=180),
                "field_expirations": field_expirations,
            }
        )
        history = (audit_entries + history)[: self.HISTORY_LIMIT]

        if normalized_layer == self.SESSION_LAYER:
            await self._persist_session_layer(
                session_id=session_id,
                state=current_state,
                meta=current_meta,
                history=history,
                ttl_seconds=self._session_cache_ttl(current_meta),
            )
        elif normalized_layer == self.EPISODE_LAYER:
            await self._persist_episode_layer(
                user_id=user_id,
                plan_id=plan_id,
                state=current_state,
                meta=current_meta,
                history=history,
            )
        else:
            await self._persist_profile_layer(
                user_id=user_id,
                state=current_state,
                meta=current_meta,
                history=history,
            )

        return {
            "applied": audit_entries,
            "effective_state": await self.get_effective_state(user_id, plan_id=plan_id, session_id=session_id),
        }

    def _normalize_changes(self, changes: dict[str, Any], *, layer: str) -> dict[str, Any]:
        normalized: dict[str, Any] = {}
        for field, value in changes.items():
            if field not in self.FIELD_SPECS:
                raise ValueError(f"Unsupported strategy field: {field}")
            spec = self.FIELD_SPECS[field]
            if layer not in spec.allowed_layers:
                raise ValueError(f"Field {field} cannot be written to {layer} layer")
            normalized[field] = self._normalize_field_value(field, value)
        return normalized

    def _normalize_field_value(self, field: str, value: Any) -> Any:
        spec = self.FIELD_SPECS[field]
        if spec.value_type == "int":
            numeric = int(round(float(value)))
            numeric = int(max(spec.min_value or numeric, min(spec.max_value or numeric, numeric)))
            return numeric
        if spec.value_type == "float":
            numeric = round(float(value), 3)
            if spec.min_value is not None:
                numeric = max(spec.min_value, numeric)
            if spec.max_value is not None:
                numeric = min(spec.max_value, numeric)
            return numeric
        if spec.value_type == "enum":
            text = str(value or "").strip()
            if text not in (spec.allowed_values or set()):
                raise ValueError(f"Invalid value for {field}: {value}")
            return text
        text = _clean_text(value, limit=spec.max_length or 240)
        return text

    def _calculate_expiration(
        self,
        layer: str,
        ttl_seconds: int | None,
        timestamp: datetime,
    ) -> datetime | None:
        if layer == self.PROFILE_LAYER:
            return None
        if ttl_seconds is None:
            ttl = self.SESSION_DEFAULT_TTL_SECONDS if layer == self.SESSION_LAYER else self.EPISODE_DEFAULT_TTL_SECONDS
        else:
            ttl = int(ttl_seconds)
        max_ttl = self.SESSION_MAX_TTL_SECONDS if layer == self.SESSION_LAYER else self.EPISODE_MAX_TTL_SECONDS
        ttl = max(60, min(max_ttl, ttl))
        return timestamp + timedelta(seconds=ttl)

    def _session_cache_ttl(self, meta: dict[str, Any]) -> int:
        expirations = []
        for raw in dict(meta.get("field_expirations") or {}).values():
            parsed = _parse_dt(raw)
            if parsed is not None:
                expirations.append(parsed)
        if not expirations:
            return self.SESSION_DEFAULT_TTL_SECONDS
        remaining = max(int((max(expirations) - _utcnow()).total_seconds()), 60)
        return min(self.SESSION_MAX_TTL_SECONDS, remaining)

    async def _load_session_layer(self, session_id: str | None) -> dict[str, Any]:
        if not self.redis or not str(session_id or "").strip():
            return {"state": {}, "meta": {}, "history": []}
        try:
            raw_state = await self.redis.get(f"{self.SESSION_KEY_PREFIX}{session_id}")
            raw_history = await self.redis.get(f"{self.SESSION_HISTORY_KEY_PREFIX}{session_id}")
        except Exception as exc:
            logger.warning(f"Failed to read session strategy layer: {exc}")
            return {"state": {}, "meta": {}, "history": []}
        payload = self._decode_layer_payload(raw_state)
        payload["history"] = self._decode_history(raw_history)
        return self._prune_expired_layer(payload)

    async def _load_episode_layer(self, user_id: UUID, plan_id: UUID | None) -> dict[str, Any]:
        if plan_id is None:
            return {"state": {}, "meta": {}, "history": [], "adaptive_view": {}}
        state = await self.plan_state_service.get_plan_state(user_id, plan_id)
        facts = dict((state.facts or {})) if state is not None else {}
        payload = {
            "state": dict(facts.get(self.EPISODE_STATE_KEY) or {}),
            "meta": dict(facts.get(self.EPISODE_META_KEY) or {}),
            "history": [item for item in _as_list(facts.get(self.EPISODE_HISTORY_KEY)) if isinstance(item, dict)],
        }
        payload = self._prune_expired_layer(payload)
        payload["adaptive_view"] = self._build_adaptive_view(facts)
        return payload

    async def _load_profile_layer(self, user_id: UUID) -> dict[str, Any]:
        prefs = await self.preference_service.get_preferences(user_id)
        inferred = dict(prefs.inferred or {})
        payload = {
            "state": dict(inferred.get(self.PROFILE_STATE_KEY) or {}),
            "meta": dict(inferred.get(self.PROFILE_META_KEY) or {}),
            "history": [item for item in _as_list(inferred.get(self.PROFILE_HISTORY_KEY)) if isinstance(item, dict)],
        }
        return self._prune_expired_layer(payload)

    async def _persist_session_layer(
        self,
        *,
        session_id: str,
        state: dict[str, Any],
        meta: dict[str, Any],
        history: list[dict[str, Any]],
        ttl_seconds: int,
    ) -> None:
        if not self.redis:
            return
        await self.redis.setex(
            f"{self.SESSION_KEY_PREFIX}{session_id}",
            ttl_seconds,
            json.dumps({"state": state, "meta": meta}, ensure_ascii=False),
        )
        await self.redis.setex(
            f"{self.SESSION_HISTORY_KEY_PREFIX}{session_id}",
            ttl_seconds,
            json.dumps(history, ensure_ascii=False),
        )

    async def _persist_episode_layer(
        self,
        *,
        user_id: UUID,
        plan_id: UUID,
        state: dict[str, Any],
        meta: dict[str, Any],
        history: list[dict[str, Any]],
    ) -> None:
        await self.plan_state_service.upsert_plan_state(
            user_id=user_id,
            plan_id=plan_id,
            patch={
                "facts": {
                    self.EPISODE_STATE_KEY: state,
                    self.EPISODE_META_KEY: meta,
                    self.EPISODE_HISTORY_KEY: history,
                }
            },
        )

    async def _persist_profile_layer(
        self,
        *,
        user_id: UUID,
        state: dict[str, Any],
        meta: dict[str, Any],
        history: list[dict[str, Any]],
    ) -> None:
        await self.preference_service.update_inferred(
            user_id,
            {
                self.PROFILE_STATE_KEY: state,
                self.PROFILE_META_KEY: meta,
                self.PROFILE_HISTORY_KEY: history,
            },
        )

    def _decode_layer_payload(self, raw_payload: Any) -> dict[str, Any]:
        if not raw_payload:
            return {"state": {}, "meta": {}}
        try:
            decoded = json.loads(raw_payload)
        except Exception:
            return {"state": {}, "meta": {}}
        if not isinstance(decoded, dict):
            return {"state": {}, "meta": {}}
        return {
            "state": dict(decoded.get("state") or {}),
            "meta": dict(decoded.get("meta") or {}),
        }

    def _decode_history(self, raw_payload: Any) -> list[dict[str, Any]]:
        if not raw_payload:
            return []
        try:
            decoded = json.loads(raw_payload)
        except Exception:
            return []
        return [item for item in _as_list(decoded) if isinstance(item, dict)]

    def _prune_expired_layer(self, payload: dict[str, Any]) -> dict[str, Any]:
        state = dict(payload.get("state") or {})
        meta = dict(payload.get("meta") or {})
        history = [item for item in _as_list(payload.get("history")) if isinstance(item, dict)]
        field_expirations = dict(meta.get("field_expirations") or {})
        now = _utcnow()
        for field, raw_expiry in list(field_expirations.items()):
            parsed = _parse_dt(raw_expiry)
            if parsed is None:
                continue
            if parsed <= now:
                state.pop(field, None)
                field_expirations.pop(field, None)
        meta["field_expirations"] = field_expirations
        return {"state": state, "meta": meta, "history": history}

    def _layer_expiration_for_field(self, payload: dict[str, Any], field: str) -> str | None:
        expirations = dict((payload.get("meta") or {}).get("field_expirations") or {})
        raw = expirations.get(field)
        parsed = _parse_dt(raw)
        if parsed is None or parsed <= _utcnow():
            return None
        return parsed.isoformat()

    def _build_adaptive_view(self, facts: dict[str, Any]) -> dict[str, Any]:
        adaptive = dict(facts.get("adaptive_adjustments") or {})
        if not adaptive:
            return {}
        parts: list[str] = []
        time_multiplier = adaptive.get("time_multiplier")
        if isinstance(time_multiplier, (int, float)) and abs(float(time_multiplier) - 1.0) >= 0.05:
            if float(time_multiplier) > 1.0:
                parts.append(f"当前回合的任务时长预算已放宽到 {float(time_multiplier):.2f} 倍")
            else:
                parts.append(f"当前回合的任务时长预算收紧到 {float(time_multiplier):.2f} 倍")
        difficulty_shift = adaptive.get("difficulty_shift")
        if isinstance(difficulty_shift, (int, float)) and abs(float(difficulty_shift)) >= 0.05:
            if float(difficulty_shift) > 0:
                parts.append("当前任务难度被临时上调")
            else:
                parts.append("当前任务难度被临时下调")
        if adaptive.get("insert_prerequisite_review"):
            parts.append("需要先补前置知识再继续推进")
        if adaptive.get("max_concurrent_tasks"):
            parts.append(f"并发任务数被限制为 {adaptive.get('max_concurrent_tasks')}")
        return {
            "adaptive_adjustments": adaptive,
            "difficulty_shift": difficulty_shift,
            "time_multiplier": time_multiplier,
            "summary": "；".join(parts[:3]),
        }
