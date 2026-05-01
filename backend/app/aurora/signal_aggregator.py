from __future__ import annotations

import hashlib
import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from app.aurora.schemas import RetentionTier, SignalSnapshot, SignalTier
from app.orchestration.signal_samplers.achievement_sampler import sample_achievement_growth_signal


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _safe_dump(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if hasattr(value, "__dict__"):
        return {str(key): _safe_dump(item) for key, item in vars(value).items() if not str(key).startswith("_")}
    if isinstance(value, dict):
        return {str(key): _safe_dump(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_safe_dump(item) for item in value]
    if isinstance(value, tuple):
        return [_safe_dump(item) for item in value]
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _estimate_tokens(value: Any) -> int:
    text = json.dumps(_safe_dump(value), ensure_ascii=False, sort_keys=True)
    return max(1, int(len(text) / 4) + 1)


def _canonical_hash(value: Any) -> str:
    text = json.dumps(_safe_dump(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _trim_text(text: str, limit: int = 240) -> str:
    clean = " ".join(str(text or "").split())
    if len(clean) <= limit:
        return clean
    return f"{clean[: max(0, limit - 1)].rstrip()}…"


def _compact_payload(value: Any, *, max_depth: int = 2, max_items: int = 6, max_text: int = 180) -> Any:
    if max_depth <= 0:
        return _trim_text(str(value), max_text)
    if isinstance(value, dict):
        compacted: dict[str, Any] = {}
        for idx, (key, item) in enumerate(value.items()):
            if idx >= max_items:
                compacted["__truncated__"] = True
                break
            compacted[str(key)] = _compact_payload(item, max_depth=max_depth - 1, max_items=max_items, max_text=max_text)
        return compacted
    if isinstance(value, list):
        compacted_list = [
            _compact_payload(item, max_depth=max_depth - 1, max_items=max_items, max_text=max_text)
            for item in value[:max_items]
        ]
        if len(value) > max_items:
            compacted_list.append({"__truncated__": True, "remaining_items": len(value) - max_items})
        return compacted_list
    if isinstance(value, tuple):
        return _compact_payload(list(value), max_depth=max_depth, max_items=max_items, max_text=max_text)
    if isinstance(value, str):
        return _trim_text(value, max_text)
    return value


@dataclass(frozen=True)
class SignalSourceSpec:
    name: str
    tier: SignalTier
    service_key: str
    collector: Callable[[Any, UUID, dict[str, Any]], Awaitable[dict[str, Any]]]


@dataclass(frozen=True)
class SignalSourceReading:
    name: str
    tier: SignalTier
    payload: dict[str, Any]
    collected_at: datetime
    freshness: datetime
    estimated_tokens: int


async def _collect_memory(service: Any, user_id: UUID, context: dict[str, Any]) -> dict[str, Any]:
    if service is None:
        return {}
    payload: dict[str, Any] = {}
    if hasattr(service, "list_active_goals"):
        goals = await service.list_active_goals(user_id)
        payload["active_goals"] = [_safe_dump(goal) for goal in goals[:5]]
    if hasattr(service, "list_preferences"):
        payload["preferences"] = _safe_dump(await service.list_preferences(user_id))
    if hasattr(service, "list_recent_episodic"):
        payload["recent_episodic"] = [_safe_dump(item) for item in (await service.list_recent_episodic(user_id, limit=5))]
    return payload


async def _collect_focus(service: Any, user_id: UUID, context: dict[str, Any]) -> dict[str, Any]:
    if service is None or not hasattr(service, "get_today_stats"):
        return {}
    return {"today_stats": _safe_dump(await service.get_today_stats(user_id))}


async def _collect_companion(service: Any, user_id: UUID, context: dict[str, Any]) -> dict[str, Any]:
    if service is None or not hasattr(service, "get_effective_state"):
        return {}
    plan_id = context.get("plan_id")
    session_id = context.get("session_id")
    return {
        "effective_state": _safe_dump(await service.get_effective_state(user_id, plan_id=plan_id, session_id=session_id)),
        "recent_revisions": _safe_dump(await service.get_recent_revisions(user_id, plan_id=plan_id, session_id=session_id)),
    }


async def _collect_strategy(service: Any, user_id: UUID, context: dict[str, Any]) -> dict[str, Any]:
    if service is None or not hasattr(service, "get_effective_state"):
        return {}
    plan_id = context.get("plan_id")
    session_id = context.get("session_id")
    payload = {"effective_state": _safe_dump(await service.get_effective_state(user_id, plan_id=plan_id, session_id=session_id))}
    if hasattr(service, "get_recent_changes"):
        payload["recent_changes"] = _safe_dump(await service.get_recent_changes(user_id, plan_id=plan_id, session_id=session_id))
    return payload


async def _collect_persona(service: Any, user_id: UUID, context: dict[str, Any]) -> dict[str, Any]:
    if service is None or not hasattr(service, "get_snapshot"):
        return {}
    purpose = str(context.get("purpose") or "aurora_signal_snapshot")
    return {"snapshot": _safe_dump(await service.get_snapshot(user_id, purpose))}


async def _collect_error_book(service: Any, user_id: UUID, context: dict[str, Any]) -> dict[str, Any]:
    if service is None:
        return {}
    payload: dict[str, Any] = {}
    if hasattr(service, "get_review_stats"):
        payload["review_stats"] = _safe_dump(await service.get_review_stats(user_id))
    if hasattr(service, "list_errors"):
        params = context.get("error_query_params")
        if params is not None:
            errors, total = await service.list_errors(user_id, params)
            payload["recent_errors"] = {"total": total, "items": [_safe_dump(item) for item in errors[:5]]}
    return payload


async def _collect_plan_state(service: Any, user_id: UUID, context: dict[str, Any]) -> dict[str, Any]:
    if service is None:
        return {}
    payload: dict[str, Any] = {}
    plan_id = context.get("plan_id")
    if plan_id is not None and hasattr(service, "get_plan_state"):
        payload["plan_state"] = _safe_dump(await service.get_plan_state(user_id, plan_id))
    if hasattr(service, "get_active_plan_states"):
        payload["active_plans"] = _safe_dump(await service.get_active_plan_states(user_id, limit=5))
    return payload


async def _collect_achievement(service: Any, user_id: UUID, context: dict[str, Any]) -> dict[str, Any]:
    contract = await sample_achievement_growth_signal(service, user_id, context=context)
    return {
        "growth_signal_contract": contract.to_payload(),
        "growth_signal_summary": contract.summary_payload(),
    }


async def _collect_predictive(service: Any, user_id: UUID, context: dict[str, Any]) -> dict[str, Any]:
    if service is None:
        return {}
    payload: dict[str, Any] = {}
    if hasattr(service, "predict_engagement"):
        payload["engagement_forecast"] = _safe_dump(await service.predict_engagement(user_id))
    if hasattr(service, "get_next_intent_forecast"):
        payload["next_intent_forecast"] = _safe_dump(await service.get_next_intent_forecast(user_id))
    return payload


async def _collect_analytics(service: Any, user_id: UUID, context: dict[str, Any]) -> dict[str, Any]:
    if service is None:
        return {}
    payload: dict[str, Any] = {}
    if hasattr(service, "get_user_profile_summary"):
        payload["profile_summary"] = await service.get_user_profile_summary(user_id)
    return payload


DEFAULT_SIGNAL_SOURCES: tuple[SignalSourceSpec, ...] = (
    SignalSourceSpec("memory_service", SignalTier.CORE, "memory_service", _collect_memory),
    SignalSourceSpec("focus_service", SignalTier.CORE, "focus_service", _collect_focus),
    SignalSourceSpec("companion_state_service", SignalTier.ENHANCED, "companion_state_service", _collect_companion),
    SignalSourceSpec("user_strategy_state_service", SignalTier.ENHANCED, "user_strategy_state_service", _collect_strategy),
    SignalSourceSpec("persona_service", SignalTier.ENHANCED, "persona_service", _collect_persona),
    SignalSourceSpec("error_book_service", SignalTier.CORE, "error_book_service", _collect_error_book),
    SignalSourceSpec("plan_state_service", SignalTier.ENHANCED, "plan_state_service", _collect_plan_state),
    SignalSourceSpec("achievement_engine", SignalTier.OPTIONAL, "achievement_engine", _collect_achievement),
    SignalSourceSpec("predictive_service", SignalTier.OPTIONAL, "predictive_service", _collect_predictive),
    SignalSourceSpec("analytics_service", SignalTier.OPTIONAL, "analytics_service", _collect_analytics),
)


class SignalAggregator:
    """Build tiered SignalSnapshot objects from read-only service inputs."""

    def __init__(
        self,
        *,
        service_map: dict[str, Any] | None = None,
        sources: tuple[SignalSourceSpec, ...] = DEFAULT_SIGNAL_SOURCES,
    ) -> None:
        self.service_map = dict(service_map or {})
        self.sources = sources

    async def assemble_snapshot(
        self,
        user_id: UUID,
        *,
        scenario_pack_id: str,
        policy_version: str,
        budget_limit: int = 4000,
        collected_at: datetime | None = None,
        services: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> SignalSnapshot:
        context = dict(context or {})
        service_map = {**self.service_map, **(services or {})}
        now = collected_at or _utcnow()

        readings = await self._collect_readings(user_id, service_map, context, now)
        tiered_payload = self._build_tiered_payload(readings)
        tiered_payload = self._enforce_budget(tiered_payload, budget_limit)
        core_signals = tiered_payload[SignalTier.CORE.value]
        enhanced_signals = tiered_payload[SignalTier.ENHANCED.value]
        optional_signals = tiered_payload[SignalTier.OPTIONAL.value]

        signal_freshness = {name: reading.freshness for name, reading in readings.items()}
        stale_signals = self._find_stale_signals(readings, now)
        snapshot_payload = {
            "user_id": str(user_id),
            "scenario_pack_id": scenario_pack_id,
            "policy_version": policy_version,
            "core_signals": core_signals,
            "enhanced_signals": enhanced_signals,
            "optional_signals": optional_signals,
            "signal_freshness": {key: value.isoformat() for key, value in signal_freshness.items()},
            "stale_signals": stale_signals,
            "budget_limit": budget_limit,
            "retention_tier": self._choose_retention_tier(stale_signals, core_signals, enhanced_signals, optional_signals),
        }
        snapshot_hash = _canonical_hash(snapshot_payload)
        total_tokens = sum(reading.estimated_tokens for reading in readings.values())
        total_tokens = min(total_tokens, budget_limit)
        summary_digest = _canonical_hash(
            {
                "snapshot_hash": snapshot_hash,
                "core": core_signals,
                "enhanced": enhanced_signals,
                "optional": optional_signals,
            }
        )
        return SignalSnapshot(
            snapshot_hash=snapshot_hash,
            user_id=user_id,
            collected_at=now,
            scenario_pack_id=scenario_pack_id,
            policy_version=policy_version,
            core_signals=core_signals,
            enhanced_signals=enhanced_signals,
            optional_signals=optional_signals,
            signal_freshness=signal_freshness,
            stale_signals=stale_signals,
            total_tokens=total_tokens,
            budget_limit=budget_limit,
            retention_tier=self._choose_retention_tier(stale_signals, core_signals, enhanced_signals, optional_signals),
            summary_digest=summary_digest,
        )

    async def build_snapshot(self, *args: Any, **kwargs: Any) -> SignalSnapshot:
        return await self.assemble_snapshot(*args, **kwargs)

    async def assemble(self, *args: Any, **kwargs: Any) -> SignalSnapshot:
        return await self.assemble_snapshot(*args, **kwargs)

    async def collect_snapshot(self, *args: Any, **kwargs: Any) -> SignalSnapshot:
        return await self.assemble_snapshot(*args, **kwargs)

    async def _collect_readings(
        self,
        user_id: UUID,
        service_map: dict[str, Any],
        context: dict[str, Any],
        collected_at: datetime,
    ) -> dict[str, SignalSourceReading]:
        readings: dict[str, SignalSourceReading] = {}
        tasks = []
        for spec in self.sources:
            service = service_map.get(spec.service_key)
            tasks.append((spec, service, spec.collector(service, user_id, context)))
        for spec, _service, coro in tasks:
            try:
                payload = await coro
            except Exception:
                payload = {}
            compacted = payload if spec.name == "achievement_engine" else _compact_payload(payload)
            freshness = self._infer_freshness(compacted, collected_at, spec.tier)
            reading = SignalSourceReading(
                name=spec.name,
                tier=spec.tier,
                payload=compacted if isinstance(compacted, dict) else {"value": compacted},
                collected_at=collected_at,
                freshness=freshness,
                estimated_tokens=_estimate_tokens(compacted),
            )
            if reading.payload:
                readings[spec.name] = reading
        return readings

    def _build_tiered_payload(self, readings: dict[str, SignalSourceReading]) -> dict[str, dict[str, Any]]:
        tiered: dict[str, dict[str, Any]] = {
            SignalTier.CORE.value: {},
            SignalTier.ENHANCED.value: {},
            SignalTier.OPTIONAL.value: {},
        }
        for name, reading in readings.items():
            tiered[reading.tier.value][name] = reading.payload
        return tiered

    def _enforce_budget(self, tiered_payload: dict[str, dict[str, Any]], budget_limit: int) -> dict[str, dict[str, Any]]:
        current = self._estimate_tiered_tokens(tiered_payload)
        if current <= budget_limit:
            return tiered_payload

        adjusted = {tier: dict(payload) for tier, payload in tiered_payload.items()}
        for tier_name in (SignalTier.OPTIONAL.value, SignalTier.ENHANCED.value):
            adjusted[tier_name] = self._trim_tier(
                adjusted[tier_name],
                budget_limit,
                adjusted,
                tier_name=tier_name,
                protected_tier=SignalTier.CORE.value,
            )
            if self._estimate_tiered_tokens(adjusted) <= budget_limit:
                return adjusted

        if self._estimate_tiered_tokens(adjusted) > budget_limit:
            adjusted[SignalTier.CORE.value] = self._trim_tier(
                adjusted[SignalTier.CORE.value],
                budget_limit,
                adjusted,
                tier_name=SignalTier.CORE.value,
                protected_tier=None,
            )
        return adjusted

    def _trim_tier(
        self,
        payload: dict[str, Any],
        budget_limit: int,
        tiered_payload: dict[str, dict[str, Any]],
        *,
        tier_name: str,
        protected_tier: str | None,
    ) -> dict[str, Any]:
        working = dict(payload)
        while self._estimate_tiered_tokens(tiered_payload) > budget_limit and working:
            removable = [
                (name, _estimate_tokens(item))
                for name, item in working.items()
                if protected_tier is None or name not in tiered_payload.get(protected_tier, {})
            ]
            if not removable:
                break
            removable.sort(key=lambda item: item[1], reverse=True)
            name, _ = removable[0]
            item = working[name]
            compacted = _compact_payload(item, max_depth=1, max_items=3, max_text=96)
            if _estimate_tokens(compacted) < _estimate_tokens(item):
                working[name] = compacted
            else:
                working.pop(name)
            tiered_payload[tier_name] = working
        return working

    def _estimate_tiered_tokens(self, tiered_payload: dict[str, dict[str, Any]]) -> int:
        return _estimate_tokens(tiered_payload)

    def _infer_freshness(self, payload: Any, collected_at: datetime, tier: SignalTier) -> datetime:
        if isinstance(payload, dict):
            for key in ("collected_at", "updated_at", "last_updated_at", "timestamp"):
                candidate = payload.get(key)
                if isinstance(candidate, datetime):
                    return candidate.replace(tzinfo=None)
                if isinstance(candidate, str) and candidate.strip():
                    try:
                        parsed = datetime.fromisoformat(candidate.replace("Z", "+00:00"))
                    except ValueError:
                        continue
                    return parsed.astimezone(UTC).replace(tzinfo=None) if parsed.tzinfo else parsed
        return collected_at

    def _find_stale_signals(self, readings: dict[str, SignalSourceReading], now: datetime) -> list[str]:
        stale: list[str] = []
        for name, reading in readings.items():
            age = now - reading.freshness
            threshold = {
                SignalTier.CORE: timedelta(days=1),
                SignalTier.ENHANCED: timedelta(days=3),
                SignalTier.OPTIONAL: timedelta(days=7),
            }[reading.tier]
            if age > threshold:
                stale.append(name)
        return stale

    def _choose_retention_tier(
        self,
        stale_signals: list[str],
        core_signals: dict[str, Any],
        enhanced_signals: dict[str, Any],
        optional_signals: dict[str, Any],
    ) -> RetentionTier:
        if not (core_signals or enhanced_signals or optional_signals):
            return RetentionTier.RECONSTRUCTABLE
        if stale_signals:
            return RetentionTier.COLD_ARCHIVE
        return RetentionTier.HOT
