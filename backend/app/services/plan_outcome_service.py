from __future__ import annotations

import inspect
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from app.core.business_metrics import OUTCOME_RECORDS_TOTAL
from app.services.personalization.preference_service import PreferenceService
from app.services.plan_state_service import PlanStateService

SESSION_PLAN_OUTCOMES_KEY_PREFIX = "session:plan_outcomes:"
SESSION_PLAN_OUTCOMES_TTL_SECONDS = 14 * 24 * 60 * 60
MAX_OUTCOME_RECORDS_PER_LAYER = 200
EPISODE_PLAN_OUTCOME_KEY = "plan_outcome_records"
PROFILE_OUTCOME_LEDGER_KEY = "plan_outcome_records"

EVIDENCE_LEVEL_TURN_REACTION = "Turn Reaction"
EVIDENCE_LEVEL_BEHAVIORAL_SIGNAL = "Behavioral Signal"
EVIDENCE_LEVEL_PLAN_OUTCOME = "Plan Outcome"
EVIDENCE_LEVEL_HUMAN_TRUTH = "Human Truth"


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _utcnow_iso() -> str:
    return _utcnow().isoformat()


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    if hasattr(value, "model_dump"):
        dumped = value.model_dump(mode="json")
        return dumped if isinstance(dumped, dict) else {}
    if hasattr(value, "to_dict"):
        dumped = value.to_dict()
        return dumped if isinstance(dumped, dict) else {}
    return {}


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return list(value)
    if isinstance(value, tuple):
        return list(value)
    return []


def _strip(value: Any) -> str:
    return str(value or "").strip()


def _bounded_confidence(value: Any, *, fallback: float = 0.6) -> float:
    try:
        return round(max(0.0, min(1.0, float(value))), 2)
    except (TypeError, ValueError):
        return fallback


def _normalize_evidence_strength(value: Any) -> str:
    normalized = _strip(value).lower()
    if normalized in {"weak", "medium", "strong"}:
        return normalized
    return "medium"


def _normalize_evidence_level(value: Any) -> str:
    normalized = _strip(value)
    if normalized in {
        EVIDENCE_LEVEL_TURN_REACTION,
        EVIDENCE_LEVEL_BEHAVIORAL_SIGNAL,
        EVIDENCE_LEVEL_PLAN_OUTCOME,
        EVIDENCE_LEVEL_HUMAN_TRUTH,
    }:
        return normalized
    return EVIDENCE_LEVEL_BEHAVIORAL_SIGNAL


def _normalize_learning_domain(value: Any) -> str:
    normalized = _strip(value).lower()
    if normalized in {"plan", "insight"}:
        return normalized
    return "plan"


def _default_promotion_recommendation(*, evidence_level: str, evidence_strength: str, confidence: float) -> str:
    if evidence_level == EVIDENCE_LEVEL_TURN_REACTION:
        return "session_only"
    if evidence_level == EVIDENCE_LEVEL_HUMAN_TRUTH and confidence >= 0.7:
        return "episode_candidate"
    if evidence_strength == "strong" and confidence >= 0.75:
        return "episode_candidate"
    return "session_candidate"


def _default_planning_implications(
    *,
    source_family: str,
    observed_outcome: str,
    outcome_signal: dict[str, Any],
) -> dict[str, Any]:
    signal = {key: value for key, value in dict(outcome_signal).items() if value not in (None, "", [], {})}
    observed = _strip(observed_outcome).lower()
    family = _strip(source_family).lower()
    if any(token in observed for token in ("overload", "too_difficult", "too_long", "stalled", "failed")):
        signal.setdefault("scaffold_level", "high")
        signal.setdefault("lighter_first_step", True)
        signal.setdefault("checkpoint_cadence", "short")
    if "grounding" in observed or "grounding" in family:
        signal.setdefault("grounding_mode", "mandatory")
    if "timing_wrong" in observed:
        signal.setdefault("checkpoint_cadence", "short")
    if "success" in observed or "effective" in observed or "helped" in observed:
        signal.setdefault("preserve_success_pattern", True)
    return signal


@dataclass(frozen=True)
class PlanOutcomeRecord:
    record_id: str
    recorded_at: str
    source_family: str
    source_id: str
    evidence_level: str
    evidence_strength: str
    target_type: str
    target_layer: str
    target_object: str
    target_hypothesis: str
    learning_domain: str
    observed_outcome: str
    outcome_signal: dict[str, Any]
    outcome_window: str
    time_horizon: str
    confidence: float
    evidence_sources: tuple[str, ...] = field(default_factory=tuple)
    planning_implications: dict[str, Any] = field(default_factory=dict)
    promotion_recommendation: str = "session_candidate"
    reversal_candidate: bool = False
    session_id: str | None = None
    plan_id: str | None = None
    intervention_id: str | None = None
    freshness_deadline: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "recorded_at": self.recorded_at,
            "source_family": self.source_family,
            "source_id": self.source_id,
            "evidence_level": self.evidence_level,
            "evidence_strength": self.evidence_strength,
            "target_type": self.target_type,
            "target_layer": self.target_layer,
            "target_object": self.target_object,
            "target_hypothesis": self.target_hypothesis,
            "learning_domain": self.learning_domain,
            "observed_outcome": self.observed_outcome,
            "outcome_signal": dict(self.outcome_signal),
            "outcome_window": self.outcome_window,
            "time_horizon": self.time_horizon,
            "confidence": self.confidence,
            "evidence_sources": list(self.evidence_sources),
            "planning_implications": dict(self.planning_implications),
            "promotion_recommendation": self.promotion_recommendation,
            "reversal_candidate": self.reversal_candidate,
            "session_id": self.session_id,
            "plan_id": self.plan_id,
            "intervention_id": self.intervention_id,
            "freshness_deadline": self.freshness_deadline,
            "metadata": dict(self.metadata),
        }


class PlanOutcomeService:
    """Append-only outcome record ledger backed by existing session, episode, and preference state."""

    def __init__(self, db, redis=None) -> None:
        self.db = db
        self.redis = redis
        self.plan_state_service = PlanStateService(db, redis)
        self.preference_service = PreferenceService(db, redis)

    def build_record(
        self,
        *,
        source_family: str,
        source_id: str,
        evidence_level: str,
        target_type: str,
        target_layer: str,
        target_object: str,
        target_hypothesis: str,
        observed_outcome: str,
        outcome_signal: dict[str, Any] | None = None,
        outcome_window: str = "",
        time_horizon: str = "",
        confidence: float = 0.6,
        evidence_strength: str = "medium",
        evidence_sources: list[str] | tuple[str, ...] | None = None,
        planning_implications: dict[str, Any] | None = None,
        promotion_recommendation: str | None = None,
        reversal_candidate: bool = False,
        learning_domain: str = "plan",
        session_id: str | None = None,
        plan_id: UUID | str | None = None,
        intervention_id: UUID | str | None = None,
        freshness_window_days: int | None = 30,
        metadata: dict[str, Any] | None = None,
    ) -> PlanOutcomeRecord:
        normalized_signal = _as_dict(outcome_signal)
        bounded_confidence = _bounded_confidence(confidence)
        normalized_strength = _normalize_evidence_strength(evidence_strength)
        normalized_level = _normalize_evidence_level(evidence_level)
        normalized_domain = _normalize_learning_domain(learning_domain)
        normalized_implications = _default_planning_implications(
            source_family=source_family,
            observed_outcome=observed_outcome,
            outcome_signal=planning_implications or normalized_signal,
        )
        promotion = promotion_recommendation or _default_promotion_recommendation(
            evidence_level=normalized_level,
            evidence_strength=normalized_strength,
            confidence=bounded_confidence,
        )
        freshness_deadline = None
        if freshness_window_days and freshness_window_days > 0:
            freshness_deadline = (_utcnow() + timedelta(days=freshness_window_days)).isoformat()
        return PlanOutcomeRecord(
            record_id=str(uuid4()),
            recorded_at=_utcnow_iso(),
            source_family=_strip(source_family),
            source_id=_strip(source_id) or str(uuid4()),
            evidence_level=normalized_level,
            evidence_strength=normalized_strength,
            target_type=_strip(target_type),
            target_layer=_strip(target_layer) or "session",
            target_object=_strip(target_object),
            target_hypothesis=_strip(target_hypothesis),
            learning_domain=normalized_domain,
            observed_outcome=_strip(observed_outcome),
            outcome_signal=normalized_signal,
            outcome_window=_strip(outcome_window),
            time_horizon=_strip(time_horizon),
            confidence=bounded_confidence,
            evidence_sources=tuple(_strip(item) for item in (evidence_sources or []) if _strip(item)),
            planning_implications=normalized_implications,
            promotion_recommendation=_strip(promotion) or "session_candidate",
            reversal_candidate=bool(reversal_candidate),
            session_id=_strip(session_id) or None,
            plan_id=_strip(plan_id) or None,
            intervention_id=_strip(intervention_id) or None,
            freshness_deadline=freshness_deadline,
            metadata=_as_dict(metadata),
        )

    async def record_outcome(
        self,
        user_id: UUID,
        *,
        source_family: str,
        source_id: str,
        evidence_level: str,
        target_type: str,
        target_layer: str,
        target_object: str,
        target_hypothesis: str,
        observed_outcome: str,
        outcome_signal: dict[str, Any] | None = None,
        outcome_window: str = "",
        time_horizon: str = "",
        confidence: float = 0.6,
        evidence_strength: str = "medium",
        evidence_sources: list[str] | tuple[str, ...] | None = None,
        planning_implications: dict[str, Any] | None = None,
        promotion_recommendation: str | None = None,
        reversal_candidate: bool = False,
        learning_domain: str = "plan",
        session_id: str | None = None,
        plan_id: UUID | str | None = None,
        intervention_id: UUID | str | None = None,
        freshness_window_days: int | None = 30,
        metadata: dict[str, Any] | None = None,
        persist_profile_ledger: bool = False,
    ) -> dict[str, Any]:
        metadata = _as_dict(metadata)
        if persist_profile_ledger:
            metadata["persist_profile_ledger"] = True
        record = self.build_record(
            source_family=source_family,
            source_id=source_id,
            evidence_level=evidence_level,
            target_type=target_type,
            target_layer=target_layer,
            target_object=target_object,
            target_hypothesis=target_hypothesis,
            observed_outcome=observed_outcome,
            outcome_signal=outcome_signal,
            outcome_window=outcome_window,
            time_horizon=time_horizon,
            confidence=confidence,
            evidence_strength=evidence_strength,
            evidence_sources=evidence_sources,
            planning_implications=planning_implications,
            promotion_recommendation=promotion_recommendation,
            reversal_candidate=reversal_candidate,
            learning_domain=learning_domain,
            session_id=session_id,
            plan_id=plan_id,
            intervention_id=intervention_id,
            freshness_window_days=freshness_window_days,
            metadata=metadata,
        )
        persisted_layers = await self.append_record(
            user_id=user_id,
            record=record.to_dict(),
            session_id=session_id,
            plan_id=plan_id,
            persist_profile_ledger=persist_profile_ledger,
        )
        return {
            "record": record.to_dict(),
            "persisted_layers": persisted_layers,
        }

    async def append_record(
        self,
        *,
        user_id: UUID,
        record: dict[str, Any],
        session_id: str | None = None,
        plan_id: UUID | str | None = None,
        persist_profile_ledger: bool = False,
    ) -> list[str]:
        persisted_layers: list[str] = []
        normalized = self._normalize_record(record)
        normalized_session_id = _strip(session_id or normalized.get("session_id"))
        normalized_plan_id = _strip(plan_id or normalized.get("plan_id"))

        if normalized_session_id:
            entries = await self._read_session_records(normalized_session_id)
            entries.append(normalized)
            await self._write_session_records(normalized_session_id, entries[-MAX_OUTCOME_RECORDS_PER_LAYER :])
            persisted_layers.append("session")
            self._record_metrics(normalized, layer="session")

        if normalized_plan_id:
            plan_uuid = UUID(normalized_plan_id)
            state = await self.plan_state_service.get_or_create_plan_state(user_id, plan_uuid)
            facts = dict(state.facts or {})
            current = [dict(item) for item in list(facts.get(EPISODE_PLAN_OUTCOME_KEY) or []) if isinstance(item, dict)]
            current.append(normalized)
            facts[EPISODE_PLAN_OUTCOME_KEY] = current[-MAX_OUTCOME_RECORDS_PER_LAYER :]
            await self.plan_state_service.upsert_plan_state(
                user_id,
                plan_uuid,
                {"facts": facts},
                bump_version=True,
            )
            persisted_layers.append("episode")
            self._record_metrics(normalized, layer="episode")
        elif persist_profile_ledger:
            prefs = await self.preference_service.get_preferences(user_id)
            inferred = dict(prefs.inferred or {})
            current = [dict(item) for item in list(inferred.get(PROFILE_OUTCOME_LEDGER_KEY) or []) if isinstance(item, dict)]
            current.append(normalized)
            await self.preference_service.update_inferred(
                user_id,
                {PROFILE_OUTCOME_LEDGER_KEY: current[-MAX_OUTCOME_RECORDS_PER_LAYER :]},
            )
            persisted_layers.append("profile_ledger")
            self._record_metrics(normalized, layer="profile_ledger")

        return persisted_layers

    async def list_records(
        self,
        user_id: UUID,
        *,
        session_id: str | None = None,
        plan_id: UUID | str | None = None,
        include_profile_ledger: bool = False,
        limit: int = MAX_OUTCOME_RECORDS_PER_LAYER,
    ) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        normalized_plan_id = _strip(plan_id)
        normalized_session_id = _strip(session_id)

        if normalized_session_id:
            records.extend(await self._read_session_records(normalized_session_id))
        if normalized_plan_id:
            state = await self.plan_state_service.get_plan_state(user_id, UUID(normalized_plan_id))
            if state and isinstance(state.facts, dict):
                records.extend(
                    dict(item)
                    for item in list(state.facts.get(EPISODE_PLAN_OUTCOME_KEY) or [])
                    if isinstance(item, dict)
                )
        if include_profile_ledger:
            prefs = await self.preference_service.get_preferences(user_id)
            records.extend(
                dict(item)
                for item in list((prefs.inferred or {}).get(PROFILE_OUTCOME_LEDGER_KEY) or [])
                if isinstance(item, dict)
            )

        deduped: dict[str, dict[str, Any]] = {}
        for item in records:
            deduped[_strip(item.get("record_id")) or str(uuid4())] = self._normalize_record(item)
        ordered = sorted(
            deduped.values(),
            key=lambda item: _strip(item.get("recorded_at")),
            reverse=True,
        )
        return ordered[: max(1, limit)]

    def _normalize_record(self, record: dict[str, Any]) -> dict[str, Any]:
        normalized = {
            "record_id": _strip(record.get("record_id")) or str(uuid4()),
            "recorded_at": _strip(record.get("recorded_at")) or _utcnow_iso(),
            "source_family": _strip(record.get("source_family")),
            "source_id": _strip(record.get("source_id")),
            "evidence_level": _normalize_evidence_level(record.get("evidence_level")),
            "evidence_strength": _normalize_evidence_strength(record.get("evidence_strength")),
            "target_type": _strip(record.get("target_type")),
            "target_layer": _strip(record.get("target_layer")) or "session",
            "target_object": _strip(record.get("target_object")),
            "target_hypothesis": _strip(record.get("target_hypothesis")),
            "learning_domain": _normalize_learning_domain(record.get("learning_domain")),
            "observed_outcome": _strip(record.get("observed_outcome")),
            "outcome_signal": _as_dict(record.get("outcome_signal")),
            "outcome_window": _strip(record.get("outcome_window")),
            "time_horizon": _strip(record.get("time_horizon")),
            "confidence": _bounded_confidence(record.get("confidence")),
            "evidence_sources": [_strip(item) for item in _as_list(record.get("evidence_sources")) if _strip(item)],
            "planning_implications": _as_dict(record.get("planning_implications")),
            "promotion_recommendation": _strip(record.get("promotion_recommendation")) or "session_candidate",
            "reversal_candidate": bool(record.get("reversal_candidate")),
            "session_id": _strip(record.get("session_id")) or None,
            "plan_id": _strip(record.get("plan_id")) or None,
            "intervention_id": _strip(record.get("intervention_id")) or None,
            "freshness_deadline": _strip(record.get("freshness_deadline")) or None,
            "metadata": _as_dict(record.get("metadata")),
        }
        if not normalized["planning_implications"]:
            normalized["planning_implications"] = _default_planning_implications(
                source_family=normalized["source_family"],
                observed_outcome=normalized["observed_outcome"],
                outcome_signal=normalized["outcome_signal"],
            )
        return normalized

    @staticmethod
    def _record_metrics(record: dict[str, Any], *, layer: str) -> None:
        OUTCOME_RECORDS_TOTAL.labels(
            evidence_level=_normalize_evidence_level(record.get("evidence_level")),
            layer=_strip(layer) or "unknown",
            source_family=_strip(record.get("source_family")) or "unknown",
        ).inc()

    async def _read_session_records(self, session_id: str) -> list[dict[str, Any]]:
        if not self.redis or not session_id:
            return []
        payload = await self._read_json_key(f"{SESSION_PLAN_OUTCOMES_KEY_PREFIX}{session_id}")
        if not isinstance(payload, list):
            return []
        return [self._normalize_record(item) for item in payload if isinstance(item, dict)]

    async def _write_session_records(self, session_id: str, records: list[dict[str, Any]]) -> None:
        if not self.redis or not session_id:
            return
        dumped = json.dumps(records, ensure_ascii=False)
        if hasattr(self.redis, "setex"):
            result = self.redis.setex(
                f"{SESSION_PLAN_OUTCOMES_KEY_PREFIX}{session_id}",
                SESSION_PLAN_OUTCOMES_TTL_SECONDS,
                dumped,
            )
            if inspect.isawaitable(result):
                await result
            return
        result = self.redis.set(f"{SESSION_PLAN_OUTCOMES_KEY_PREFIX}{session_id}", dumped)
        if inspect.isawaitable(result):
            await result
        if hasattr(self.redis, "expire"):
            expire_result = self.redis.expire(
                f"{SESSION_PLAN_OUTCOMES_KEY_PREFIX}{session_id}",
                SESSION_PLAN_OUTCOMES_TTL_SECONDS,
            )
            if inspect.isawaitable(expire_result):
                await expire_result

    async def _read_json_key(self, key: str) -> dict[str, Any] | list[Any] | None:
        try:
            raw = self.redis.get(key)
            if inspect.isawaitable(raw):
                raw = await raw
            if not raw:
                return None
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            if isinstance(raw, (dict, list)):
                return raw
            if isinstance(raw, str):
                parsed = json.loads(raw)
                if isinstance(parsed, (dict, list)):
                    return parsed
        except Exception:
            return None
        return None
