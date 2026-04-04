from __future__ import annotations

import json
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.orchestration.soul_compiler import DEFAULT_COMPANION_STATE
from app.services.companion_state_service import CompanionStateService


class _AsyncRedisStub:
    def __init__(self, payload: dict[str, str] | None = None) -> None:
        self.payload = payload or {}
        self.ttl: dict[str, int] = {}

    async def get(self, key: str) -> str | None:
        return self.payload.get(key)

    async def setex(self, key: str, ttl_seconds: int, value: str) -> None:
        self.payload[key] = value
        self.ttl[key] = ttl_seconds

    async def set(self, key: str, value: str) -> None:
        self.payload[key] = value

    async def expire(self, key: str, ttl_seconds: int) -> None:
        self.ttl[key] = ttl_seconds


class _PreferenceServiceStub:
    def __init__(self, inferred: dict | None = None) -> None:
        self.live_inferred = dict(inferred or {})
        self.snapshot_inferred = dict(self.live_inferred)
        self.prefs = SimpleNamespace(inferred=self.live_inferred, version=1)

    async def get_preferences(self, user_id):
        return SimpleNamespace(inferred=dict(self.snapshot_inferred), version=self.prefs.version)

    async def update_inferred(self, user_id, updates: dict):
        self.live_inferred.update(dict(updates or {}))
        self.snapshot_inferred = dict(self.live_inferred)
        self.prefs = SimpleNamespace(inferred=dict(self.live_inferred), version=(self.prefs.version or 0) + 1)
        return self.prefs

    async def update_inferred_raw(self, user_id, inferred: dict):
        self.live_inferred = dict(inferred)
        self.snapshot_inferred = dict(self.live_inferred)
        self.prefs = SimpleNamespace(inferred=inferred, version=(self.prefs.version or 0) + 1)
        return self.prefs


class _PlanStateServiceStub:
    def __init__(self) -> None:
        self.states: dict[tuple[str, str], SimpleNamespace] = {}

    async def get_plan_state(self, user_id, plan_id, refresh: bool = False):
        return self.states.get((str(user_id), str(plan_id)))

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


def _wire_service(
    service: CompanionStateService, *, pref_stub: _PreferenceServiceStub, plan_stub: _PlanStateServiceStub
) -> None:
    service.preference_service = pref_stub
    service.plan_state_service = plan_stub
    service.self_revision_service.preference_service = pref_stub
    service.self_revision_service.plan_state_service = plan_stub
    service.relationship_profile_service.self_revision_service.preference_service = pref_stub
    service.relationship_profile_service.self_revision_service.plan_state_service = plan_stub


@pytest.mark.asyncio
async def test_companion_state_service_defaults_when_no_data() -> None:
    service = CompanionStateService(db=object(), redis=None)
    pref_stub = _PreferenceServiceStub()
    plan_stub = _PlanStateServiceStub()
    _wire_service(service, pref_stub=pref_stub, plan_stub=plan_stub)

    state = await service.get_effective_state(uuid4())
    relationship = await service.get_relationship_profile(uuid4())
    revisions = await service.get_recent_revisions(uuid4())

    assert state == DEFAULT_COMPANION_STATE.to_dict()
    assert relationship == {}
    assert revisions == []


@pytest.mark.asyncio
async def test_companion_state_service_merges_profile_episode_and_session_layers() -> None:
    user_id = uuid4()
    plan_id = uuid4()
    session_id = "session-123"
    redis = _AsyncRedisStub(
        {
            "session:companion:session-123": json.dumps(
                {
                    "companion_state": {
                        "warmth_calibration": 0.9,
                        "challenge_style": "firm",
                    },
                    "companion_revision_history": [{"field": "warmth_calibration", "layer": "session"}],
                },
                ensure_ascii=False,
            )
        }
    )
    service = CompanionStateService(db=object(), redis=redis)
    pref_stub = _PreferenceServiceStub(
        inferred={
            "companion_state": {
                "warmth_calibration": 0.4,
                "candor_calibration": 0.5,
                "preferred_truth_style": "gentle_reflective",
            },
            "relationship_profile": {
                "trust_level": 0.66,
                "candor_tolerance": 0.72,
                "shared_milestones": [{"kind": "recovery", "summary": "一起熬过了第一次大崩盘"}],
            },
            "companion_revision_history": [{"field": "preferred_truth_style", "layer": "profile"}],
        }
    )
    plan_stub = _PlanStateServiceStub()
    await plan_stub.upsert_plan_state(
        user_id,
        plan_id,
        {
            "facts": {
                "companion_state": {
                    "candor_calibration": 0.8,
                    "relationship_stage": "trusted",
                },
                "companion_revision_history": [{"field": "candor_calibration", "layer": "episode"}],
            }
        },
    )
    _wire_service(service, pref_stub=pref_stub, plan_stub=plan_stub)

    state = await service.get_effective_state(user_id, plan_id=plan_id, session_id=session_id)
    relationship = await service.get_relationship_profile(user_id)
    revisions = await service.get_recent_revisions(user_id, plan_id=plan_id, session_id=session_id)

    assert state["warmth_calibration"] == 0.9
    assert state["candor_calibration"] == 0.8
    assert state["challenge_style"] == "firm"
    assert state["relationship_stage"] == "trusted"
    assert state["preferred_truth_style"] == "gentle_reflective"
    assert relationship["trust_level"] == 0.66
    assert relationship["candor_tolerance"] == 0.72
    assert revisions[0]["layer"] == "session"
    assert revisions[1]["layer"] == "episode"
    assert revisions[2]["layer"] == "profile"


@pytest.mark.asyncio
async def test_write_session_state_records_ledger_and_is_readable_next_turn() -> None:
    user_id = uuid4()
    redis = _AsyncRedisStub()
    service = CompanionStateService(db=object(), redis=redis)
    pref_stub = _PreferenceServiceStub()
    plan_stub = _PlanStateServiceStub()
    _wire_service(service, pref_stub=pref_stub, plan_stub=plan_stub)

    result = await service.write_session_state(
        user_id=user_id,
        session_id="session-1",
        field="candor_calibration",
        value=0.82,
        reason="User responded better to direct corrections in this conversation.",
        evidence={
            "source": "conversation",
            "snippet": "直接说重点更有帮助",
            "message_id": "msg-1",
            "measurable_effect": True,
        },
        confidence=0.84,
    )

    effective_state = await service.get_effective_state(user_id, session_id="session-1")
    history = await service.get_self_revision_history(user_id, session_id="session-1")

    assert result["updated"] is True
    assert result["session_write"]["revision"]["old_value"] is None
    assert result["session_write"]["revision"]["new_value"] == 0.82
    assert effective_state["candor_calibration"] == 0.82
    assert history[0]["reason"].startswith("User responded better")
    assert history[0]["evidence"]["snippet"] == "直接说重点更有帮助"
    assert "session:companion:session-1" in redis.payload
    assert "session:companion:revisions:session-1" in redis.payload


@pytest.mark.asyncio
async def test_write_session_state_promotes_to_episode_after_repeated_evidence() -> None:
    user_id = uuid4()
    plan_id = uuid4()
    redis = _AsyncRedisStub()
    service = CompanionStateService(db=object(), redis=redis)
    pref_stub = _PreferenceServiceStub()
    plan_stub = _PlanStateServiceStub()
    _wire_service(service, pref_stub=pref_stub, plan_stub=plan_stub)

    await service.write_session_state(
        user_id=user_id,
        session_id="session-2",
        field="challenge_style",
        value="firm",
        reason="Direct challenge helped the user re-engage.",
        evidence={"source": "conversation", "snippet": "继续推我一下", "measurable_effect": True},
        confidence=0.78,
        plan_id=plan_id,
    )
    result = await service.write_session_state(
        user_id=user_id,
        session_id="session-2",
        field="challenge_style",
        value="firm",
        reason="The firmer stance kept working across the plan episode.",
        evidence={"source": "conversation", "snippet": "这样更有劲", "measurable_effect": True},
        confidence=0.81,
        plan_id=plan_id,
    )

    episode_state = await service.get_effective_state(user_id, plan_id=plan_id, session_id=None)

    assert result["promotions"]
    assert result["promotions"][0]["layer"] == "episode"
    assert episode_state["challenge_style"] == "firm"


@pytest.mark.asyncio
async def test_write_relationship_note_promotes_profile_only_after_repeated_evidence() -> None:
    user_id = uuid4()
    redis = _AsyncRedisStub()
    service = CompanionStateService(db=object(), redis=redis)
    pref_stub = _PreferenceServiceStub()
    plan_stub = _PlanStateServiceStub()
    _wire_service(service, pref_stub=pref_stub, plan_stub=plan_stub)

    first = await service.write_relationship_note(
        user_id=user_id,
        session_id="session-3",
        note="User trusts direct boundary-setting when it is paired with warmth.",
        note_kind="boundary",
        reason="Boundary-setting reduced confusion in the chat.",
        evidence={"source": "conversation", "snippet": "你这样说我更安心", "measurable_effect": True},
        confidence=0.82,
    )
    second = await service.write_relationship_note(
        user_id=user_id,
        session_id="session-3",
        note="User trusts direct boundary-setting when it is paired with warmth.",
        note_kind="boundary",
        reason="The same boundary style kept improving trust.",
        evidence={"source": "conversation", "snippet": "你这样说我更安心", "measurable_effect": True},
        confidence=0.86,
    )

    relationship = await service.get_relationship_profile(user_id)

    assert first["promotions"] == []
    assert second["promotions"][-1]["layer"] == "profile"
    assert relationship["boundary_notes"][0]["kind"] == "boundary"


@pytest.mark.asyncio
async def test_profile_promotion_requires_repeated_evidence_and_effect() -> None:
    user_id = uuid4()
    redis = _AsyncRedisStub()
    service = CompanionStateService(db=object(), redis=redis)
    pref_stub = _PreferenceServiceStub()
    plan_stub = _PlanStateServiceStub()
    _wire_service(service, pref_stub=pref_stub, plan_stub=plan_stub)

    result = await service.write_relationship_note(
        user_id=user_id,
        session_id="session-4",
        note="User likes firmer reminders.",
        note_kind="boundary",
        reason="This might be true, but it has not been validated enough.",
        evidence={"source": "conversation", "snippet": "maybe", "measurable_effect": False},
        confidence=0.88,
    )

    relationship = await service.get_relationship_profile(user_id)

    assert result["promotions"] == []
    assert relationship == {}


@pytest.mark.asyncio
async def test_profile_revision_merge_preserves_unrelated_inferred_preferences() -> None:
    user_id = uuid4()
    service = CompanionStateService(db=object(), redis=_AsyncRedisStub())
    pref_stub = _PreferenceServiceStub(
        inferred={
            "existing_signal": {"value": "keep-me"},
            "companion_state": {"warmth_calibration": 0.4},
        }
    )
    pref_stub.snapshot_inferred = {
        "companion_state": {"warmth_calibration": 0.4},
    }
    plan_stub = _PlanStateServiceStub()
    _wire_service(service, pref_stub=pref_stub, plan_stub=plan_stub)

    await service.self_revision_service.append_profile_revision(
        user_id=user_id,
        revision=service.self_revision_service.build_revision(
            field="warmth_calibration",
            layer="profile",
            old_value=0.4,
            new_value=0.7,
            reason="Repeated effect justified promotion.",
            evidence={"source": "conversation", "snippet": "worked", "measurable_effect": True},
            confidence=0.83,
        ),
        state_patch={"warmth_calibration": 0.7},
    )

    assert pref_stub.prefs.inferred["existing_signal"] == {"value": "keep-me"}
    assert pref_stub.prefs.inferred["companion_state"]["warmth_calibration"] == 0.7


@pytest.mark.asyncio
async def test_relationship_profile_promotion_dedupes_and_caps_semantic_entries() -> None:
    user_id = uuid4()
    redis = _AsyncRedisStub()
    service = CompanionStateService(db=object(), redis=redis)
    pref_stub = _PreferenceServiceStub()
    plan_stub = _PlanStateServiceStub()
    _wire_service(service, pref_stub=pref_stub, plan_stub=plan_stub)

    for idx in range(3):
        await service.write_relationship_note(
            user_id=user_id,
            session_id="session-dedupe",
            note="User trusts direct boundary-setting when it is paired with warmth.",
            note_kind="boundary",
            reason=f"Promotion evidence {idx}",
            evidence={
                "source": "conversation",
                "snippet": f"evidence-{idx}",
                "message_id": f"msg-{idx}",
                "measurable_effect": True,
            },
            confidence=0.8 + (idx * 0.02),
        )

    relationship = await service.get_relationship_profile(user_id)
    boundary_notes = relationship["boundary_notes"]

    assert len(boundary_notes) == 1
    assert boundary_notes[0]["kind"] == "boundary"
    assert len(boundary_notes[0]["evidence_refs"]) <= 4


@pytest.mark.asyncio
async def test_recent_revisions_are_sorted_by_timestamp_descending() -> None:
    user_id = uuid4()
    plan_id = uuid4()
    redis = _AsyncRedisStub(
        {
            "session:companion:revisions:session-sort": json.dumps(
                [
                    {"field": "candor_calibration", "layer": "session", "timestamp": "2026-04-04T09:00:00+00:00"},
                ]
            )
        }
    )
    service = CompanionStateService(db=object(), redis=redis)
    pref_stub = _PreferenceServiceStub(
        inferred={
            "companion_revision_history": [
                {"field": "warmth_calibration", "layer": "profile", "timestamp": "2026-04-04T10:00:00+00:00"},
            ]
        }
    )
    plan_stub = _PlanStateServiceStub()
    await plan_stub.upsert_plan_state(
        user_id,
        plan_id,
        {
            "facts": {
                "companion_revision_history": [
                    {"field": "challenge_style", "layer": "episode", "timestamp": "2026-04-04T08:00:00+00:00"},
                ]
            }
        },
    )
    _wire_service(service, pref_stub=pref_stub, plan_stub=plan_stub)

    revisions = await service.get_recent_revisions(user_id, plan_id=plan_id, session_id="session-sort")

    assert [item["layer"] for item in revisions[:3]] == ["profile", "session", "episode"]
