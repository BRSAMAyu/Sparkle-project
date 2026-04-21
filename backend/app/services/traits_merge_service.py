from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.core.event_bus import TraitObserved, event_bus
from app.core.user_insight_state import BigFiveDimension, BigFiveTraits
from app.services.personalization.preference_service import PreferenceService
from app.services.traits_metrics import (
    TRAITS_CONFIDENCE_DISTRIBUTION,
    TRAITS_MERGED_TOTAL,
    TRAITS_NLP_OBSERVATION_TOTAL,
)


def _utcnow_iso() -> str:
    return datetime.now(UTC).replace(tzinfo=None).isoformat()


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


class TraitObservationDelta(BigFiveDimension):
    pass


class TraitObservation(BigFiveTraits):
    user_id: str
    evidence_id: str
    observed_at: str = _utcnow_iso()
    source: str = "nlp_observed"
    confidence_delta: float = 0.05
    text_window_days: int = 30


class TraitsMergeService:
    MIN_OBSERVATIONS_TO_MERGE = 3

    def __init__(self, db, redis=None) -> None:
        self.pref_service = PreferenceService(db, redis)

    async def register_observation(self, user_id: UUID, observation: TraitObservation) -> dict[str, Any]:
        prefs = await self.pref_service.get_preferences(user_id)
        state = dict(prefs.trait_observation_state or {})
        history = dict(state.get("history") or {})
        latest_evidence_ids = dict(state.get("latest_evidence_ids") or {})

        for dim, delta in observation.active_dimensions().items():
            records = list(history.get(dim) or [])
            direction = 1 if delta.value > 0 else -1 if delta.value < 0 else 0
            records.append(
                {
                    "evidence_id": observation.evidence_id,
                    "direction": direction,
                    "delta": delta.value,
                    "confidence_delta": min(0.1, float(observation.confidence_delta or delta.confidence)),
                    "observed_at": observation.observed_at,
                    "source": observation.source,
                }
            )
            history[dim] = records[-12:]
            latest_evidence_ids[dim] = observation.evidence_id

        state["history"] = history
        state["latest_evidence_ids"] = latest_evidence_ids
        state["last_nlp_observed_at"] = observation.observed_at
        await self.pref_service.update_trait_observation_state(user_id, state)
        TRAITS_NLP_OBSERVATION_TOTAL.labels(outcome="observed").inc()
        await event_bus.publish(
            "trait_observed",
            TraitObserved(user_id=str(user_id), evidence_id=observation.evidence_id, source=observation.source).to_dict(),
        )
        return state

    async def merge_observation(self, user_id: UUID, observation: TraitObservation) -> BigFiveTraits:
        prefs = await self.pref_service.get_preferences(user_id)
        current_traits = BigFiveTraits.model_validate(dict(prefs.traits_prior or {}))
        state = dict(prefs.trait_observation_state or {})
        history = dict(state.get("history") or {})
        merged_payload = current_traits.model_dump(mode="json", exclude_none=True)
        merged_any = False

        for dim in BigFiveTraits.DIMENSIONS:
            delta = getattr(observation, dim)
            if delta is None or delta.value == 0:
                continue
            records = list(history.get(dim) or [])
            direction = 1 if delta.value > 0 else -1
            aligned = [
                item for item in records
                if int(item.get("direction") or 0) == direction
            ]
            if len({str(item.get("evidence_id")) for item in aligned}) < self.MIN_OBSERVATIONS_TO_MERGE:
                continue

            recent = aligned[-self.MIN_OBSERVATIONS_TO_MERGE:]
            current = getattr(current_traits, dim) or BigFiveDimension(source="merged")
            average_delta = sum(float(item.get("delta") or 0.0) for item in recent) / len(recent)
            confidence_gain = min(
                0.1,
                sum(float(item.get("confidence_delta") or 0.0) for item in recent) / len(recent),
            )
            merged_dim = BigFiveDimension(
                value=_clamp(float(current.value or 0.0) + average_delta, -1.0, 1.0),
                confidence=_clamp(float(current.confidence or 0.0) + confidence_gain, 0.0, 0.3),
                evidence_count=max(int(current.evidence_count or 0), len(records)),
                last_observed_at=observation.observed_at,
                source="merged" if current.source != "coldstart" else "merged",
            )
            merged_payload[dim] = merged_dim.model_dump(mode="json")
            TRAITS_CONFIDENCE_DISTRIBUTION.labels(dimension=dim).observe(merged_dim.confidence)
            merged_any = True

        if merged_any:
            await self.pref_service.update_traits(
                user_id,
                traits_prior=merged_payload,
                trait_observation_state=state,
                traits_coldstart_completed_at=prefs.traits_coldstart_completed_at,
            )
            TRAITS_MERGED_TOTAL.labels(source=observation.source).inc()

        return BigFiveTraits.model_validate(merged_payload)
