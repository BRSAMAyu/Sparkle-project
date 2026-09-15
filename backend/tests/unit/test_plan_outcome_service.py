from __future__ import annotations

import json
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core.business_metrics import OUTCOME_RECORDS_TOTAL, snapshot_metric
from app.services.plan_outcome_service import PlanOutcomeService


class _AsyncRedisStub:
    def __init__(self) -> None:
        self.payload: dict[str, str] = {}
        self.ttl: dict[str, int] = {}

    async def get(self, key: str) -> str | None:
        return self.payload.get(key)

    async def setex(self, key: str, ttl_seconds: int, value: str) -> None:
        self.payload[key] = value
        self.ttl[key] = ttl_seconds


class _PreferenceServiceStub:
    def __init__(self) -> None:
        self.prefs = SimpleNamespace(inferred={}, version=1)

    async def get_preferences(self, user_id):
        return self.prefs

    async def update_inferred(self, user_id, updates: dict):
        self.prefs.inferred.update(dict(updates or {}))
        return self.prefs


class _PlanStateServiceStub:
    def __init__(self) -> None:
        self.states: dict[tuple[str, str], SimpleNamespace] = {}

    async def get_or_create_plan_state(self, user_id, plan_id, *args, **kwargs):
        key = (str(user_id), str(plan_id))
        state = self.states.get(key)
        if state is None:
            state = SimpleNamespace(facts={})
            self.states[key] = state
        return state

    async def upsert_plan_state(self, user_id, plan_id, patch: dict, bump_version: bool = True):
        state = await self.get_or_create_plan_state(user_id, plan_id)
        state.facts = dict(patch.get("facts") or {})
        self.states[(str(user_id), str(plan_id))] = state
        return state

    async def get_plan_state(self, user_id, plan_id, refresh: bool = False):
        return self.states.get((str(user_id), str(plan_id)))


def _metric_value(snapshot: dict[str, float], needle: str) -> float:
    for label, value in snapshot.items():
        if needle in label:
            return value
    return 0.0


@pytest.mark.asyncio
async def test_plan_outcome_service_persists_session_and_episode_records() -> None:
    user_id = uuid4()
    plan_id = uuid4()
    redis = _AsyncRedisStub()
    service = PlanOutcomeService(db=object(), redis=redis)
    service.preference_service = _PreferenceServiceStub()
    service.plan_state_service = _PlanStateServiceStub()

    result = await service.record_outcome(
        user_id,
        source_family="task_feedback",
        source_id="fb-1",
        evidence_level="Behavioral Signal",
        target_type="plan",
        target_layer="episode",
        target_object=str(plan_id),
        target_hypothesis="dense_first_step_overloads_user",
        observed_outcome="too_difficult",
        outcome_signal={"category": "too_difficult"},
        confidence=0.79,
        evidence_strength="strong",
        plan_id=plan_id,
        session_id="session-1",
    )

    assert result["persisted_layers"] == ["session", "episode"]
    session_entries = json.loads(redis.payload["session:plan_outcomes:session-1"])
    assert session_entries[0]["target_hypothesis"] == "dense_first_step_overloads_user"
    assert session_entries[0]["planning_implications"]["lighter_first_step"] is True

    stored = await service.list_records(user_id, session_id="session-1", plan_id=plan_id)
    assert len(stored) == 1
    assert stored[0]["observed_outcome"] == "too_difficult"


@pytest.mark.asyncio
async def test_plan_outcome_service_tracks_outcome_record_metrics() -> None:
    user_id = uuid4()
    redis = _AsyncRedisStub()
    service = PlanOutcomeService(db=object(), redis=redis)
    service.preference_service = _PreferenceServiceStub()
    service.plan_state_service = _PlanStateServiceStub()

    before = snapshot_metric(OUTCOME_RECORDS_TOTAL)
    await service.record_outcome(
        user_id,
        source_family="behavioral_outcome",
        source_id="bo-1",
        evidence_level="Behavioral Signal",
        target_type="intervention",
        target_layer="session",
        target_object="iv-1",
        target_hypothesis="lighter_first_step_helps_starting",
        observed_outcome="success",
        confidence=0.74,
        evidence_strength="strong",
        session_id="session-1",
        persist_profile_ledger=True,
    )
    after = snapshot_metric(OUTCOME_RECORDS_TOTAL)

    session_delta = _metric_value(after, "evidence_level=Behavioral Signal,layer=session,source_family=behavioral_outcome") - _metric_value(
        before,
        "evidence_level=Behavioral Signal,layer=session,source_family=behavioral_outcome",
    )
    profile_delta = _metric_value(
        after,
        "evidence_level=Behavioral Signal,layer=profile_ledger,source_family=behavioral_outcome",
    ) - _metric_value(
        before,
        "evidence_level=Behavioral Signal,layer=profile_ledger,source_family=behavioral_outcome",
    )

    assert session_delta == 1.0
    assert profile_delta == 1.0


def test_plan_outcome_service_build_record_derives_planning_implications() -> None:
    service = PlanOutcomeService(db=object(), redis=None)

    record = service.build_record(
        source_family="human_eval",
        source_id="seg-1",
        evidence_level="Human Truth",
        target_type="insight",
        target_layer="episode",
        target_object="scenario-1",
        target_hypothesis="grounding_missing_hurts_plan_quality",
        observed_outcome="grounding_weak",
        outcome_signal={},
        confidence=0.88,
        evidence_strength="strong",
        learning_domain="insight",
    ).to_dict()

    assert record["promotion_recommendation"] == "episode_candidate"
    assert record["planning_implications"]["grounding_mode"] == "mandatory"
    assert record["metadata"] == {}
