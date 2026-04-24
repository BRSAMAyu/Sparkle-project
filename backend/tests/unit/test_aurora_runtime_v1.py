from __future__ import annotations

from datetime import datetime

import pytest

from app.aurora.runtime_v1.control_surface import ControlSurfaceService, HarnessUpdateRejectedError
from app.aurora.runtime_v1.persistence import AuroraPersistenceStore
from app.aurora.runtime_v1.skills import AuroraSkillRegistry
from app.aurora.runtime_v1.state import (
    ActivityProfile,
    AuroraIntent,
    AuroraRuntimeStore,
    AuroraState,
    InformationalTension,
    LatentThread,
    ScheduledWake,
)
from app.aurora.runtime_v1.wake_scheduler import AuroraWakeScheduler
from app.services.personalization.preference_service import PreferenceService


class _FakeRedis:
    def __init__(self) -> None:
        self.kv: dict[str, str] = {}
        self.hashes: dict[str, dict[str, str]] = {}
        self.sorted_sets: dict[str, dict[str, float]] = {}
        self.ttl: dict[str, int] = {}

    async def get(self, key: str) -> str | None:
        return self.kv.get(key)

    async def setex(self, key: str, ttl_seconds: int, value: str) -> None:
        self.kv[key] = value
        self.ttl[key] = ttl_seconds

    async def delete(self, key: str) -> None:
        self.kv.pop(key, None)
        self.hashes.pop(key, None)

    async def hgetall(self, key: str) -> dict[str, str]:
        return dict(self.hashes.get(key, {}))

    async def hset(self, key: str, *, mapping: dict[str, str]) -> None:
        bucket = self.hashes.setdefault(key, {})
        bucket.update(mapping)

    async def expire(self, key: str, ttl_seconds: int) -> None:
        self.ttl[key] = ttl_seconds

    async def zadd(self, key: str, mapping: dict[str, float]) -> None:
        bucket = self.sorted_sets.setdefault(key, {})
        bucket.update(mapping)

    async def zrem(self, key: str, member: str) -> None:
        bucket = self.sorted_sets.setdefault(key, {})
        bucket.pop(member, None)


def _make_state(*, user_id, surface: str, conversation_id: str, session_suffix: str) -> AuroraState:
    intent = AuroraIntent(
        intent_type="pursue_tension",
        target_tension_id=f"tension-{session_suffix}",
        payload={"session_suffix": session_suffix},
    )
    return AuroraState(
        user_id=str(user_id),
        surface=surface,
        conversation_id=conversation_id,
        runtime_session_id=f"runtime-{session_suffix}",
        user_model_snapshot={"stage": session_suffix},
        informational_tensions=[
            InformationalTension(
                tension_id=f"tension-{session_suffix}",
                domain=f"domain-{session_suffix}",
                description=f"Need to resolve {session_suffix}",
                priority=0.8,
                evidence=[f"evidence-{session_suffix}"],
            )
        ],
        current_intent=intent,
        latent_threads=[
            LatentThread(
                thread_id=f"thread-{session_suffix}",
                source_intent=intent,
                tension_links=[f"tension-{session_suffix}"],
                salience=0.7,
                context_snapshot=f"Context {session_suffix}",
            )
        ],
        activity_profile=ActivityProfile(
            proactive_intensity=0.55,
            conversation_style="warm",
            agenda_priority=f"domain-{session_suffix}",
            task_density_hint=0.65,
        ),
        streaming_status="waiting_user",
    )


@pytest.mark.asyncio
async def test_runtime_state_isolated_by_surface_and_conversation_id(test_user) -> None:
    redis = _FakeRedis()
    store = AuroraRuntimeStore(redis, enabled=True)

    state_a = _make_state(user_id=test_user.id, surface="aurora_modeling", conversation_id="conv-a", session_suffix="a")
    state_b = _make_state(user_id=test_user.id, surface="aurora_modeling", conversation_id="conv-b", session_suffix="b")
    state_c = _make_state(user_id=test_user.id, surface="aurora_planning", conversation_id="conv-a", session_suffix="c")

    await store.save_runtime_state(state_a)
    await store.save_runtime_state(state_b)
    await store.save_runtime_state(state_c)

    loaded_a = await store.load_runtime_state(user_id=test_user.id, surface="aurora_modeling", conversation_id="conv-a")
    loaded_b = await store.load_runtime_state(user_id=test_user.id, surface="aurora_modeling", conversation_id="conv-b")
    loaded_c = await store.load_runtime_state(user_id=test_user.id, surface="aurora_planning", conversation_id="conv-a")

    assert loaded_a is not None and loaded_a.runtime_session_id == "runtime-a"
    assert loaded_b is not None and loaded_b.runtime_session_id == "runtime-b"
    assert loaded_c is not None and loaded_c.runtime_session_id == "runtime-c"
    assert loaded_a.conversation_id != loaded_b.conversation_id
    assert loaded_a.surface != loaded_c.surface


@pytest.mark.asyncio
async def test_cognitive_snapshot_persists_round_trip(db_session, test_user) -> None:
    persistence = AuroraPersistenceStore(db_session, enabled=True)
    state = _make_state(
        user_id=test_user.id,
        surface="aurora_modeling",
        conversation_id="conv-snapshot",
        session_suffix="snapshot",
    )

    saved = await persistence.save_cognitive_snapshot(state, metadata={"aurora_surface": state.surface})
    loaded = await persistence.load_cognitive_snapshot(test_user.id)

    assert saved is not None
    assert loaded is not None
    assert loaded.user_id == str(test_user.id)
    assert loaded.last_surface == "aurora_modeling"
    assert loaded.activity_profile.agenda_priority == "domain-snapshot"
    assert loaded.informational_tensions[0].tension_id == "tension-snapshot"


@pytest.mark.asyncio
async def test_scheduled_wake_persists_and_lists_pending(db_session, test_user) -> None:
    persistence = AuroraPersistenceStore(db_session, enabled=True)
    wake = ScheduledWake(
        wake_id="wake-pending",
        scheduled_at=datetime(2026, 4, 24, 12, 0, 0),
        reason="checkpoint follow-up",
        planned_action="emit_message",
        status="pending",
    )

    saved = await persistence.save_scheduled_wake(
        user_id=test_user.id,
        surface="aurora_checkpoint",
        conversation_id="conv-wake",
        runtime_session_id="runtime-wake",
        wake=wake,
        metadata={"source": "test"},
    )
    pending = await persistence.list_pending_wakes(due_before=datetime(2026, 4, 24, 13, 0, 0), user_id=test_user.id)

    assert saved is not None
    assert pending
    assert pending[0].wake.wake_id == "wake-pending"
    assert pending[0].surface == "aurora_checkpoint"


@pytest.mark.asyncio
async def test_control_surface_reads_hard_bounds_from_explicit_json(db_session, test_user) -> None:
    await PreferenceService(db_session, redis=None).update_explicit(
        test_user.id,
        {
            "timezone": "Asia/Shanghai",
            "aurora_preferences": {
                "dnd_windows": [{"start": "22:30", "end": "07:30"}],
                "privacy_boundaries": ["family_conflict"],
                "disabled_actions": ["proactive_follow_up"],
            },
        },
    )

    service = ControlSurfaceService(db_session, redis=_FakeRedis(), enabled=True)
    reading = await service.read_control_surface(test_user.id)

    assert reading.hard_bounds.timezone_name == "Asia/Shanghai"
    assert reading.hard_bounds.dnd_windows[0].start == "22:30"
    assert reading.hard_bounds.privacy_boundaries == ["family_conflict"]
    assert reading.hard_bounds.disabled_actions == ["proactive_follow_up"]


@pytest.mark.asyncio
async def test_illegal_harness_update_is_rejected(db_session, test_user) -> None:
    await PreferenceService(db_session, redis=None).update_explicit(
        test_user.id,
        {
            "aurora_preferences": {
                "privacy_boundaries": ["family_conflict"],
            },
        },
    )

    service = ControlSurfaceService(db_session, redis=_FakeRedis(), enabled=True)
    reading = await service.read_control_surface(test_user.id)

    with pytest.raises(HarnessUpdateRejectedError) as exc_info:
        service.validate_harness_update(
            {"agenda_priority": "family_conflict"},
            hard_bounds=reading.hard_bounds,
        )

    assert "privacy boundary" in str(exc_info.value)


@pytest.mark.asyncio
async def test_dnd_wake_is_suppressed(db_session, test_user) -> None:
    redis = _FakeRedis()
    await PreferenceService(db_session, redis=None).update_explicit(
        test_user.id,
        {
            "timezone": "UTC",
            "aurora_preferences": {
                "dnd_windows": [{"start": "22:00", "end": "07:00"}],
            },
        },
    )

    scheduler = AuroraWakeScheduler(
        db_session,
        redis=redis,
        persistence_store=AuroraPersistenceStore(db_session, enabled=True),
        control_surface_service=ControlSurfaceService(db_session, redis=redis, enabled=True),
        enabled=True,
    )
    suppressed = await scheduler.schedule_wake(
        test_user.id,
        surface="aurora_checkpoint",
        conversation_id="conv-dnd",
        runtime_session_id="runtime-dnd",
        wake=ScheduledWake(
            wake_id="wake-dnd",
            scheduled_at=datetime(2026, 4, 24, 23, 30, 0),
            reason="night follow-up",
            planned_action="emit_message",
        ),
    )

    assert suppressed is not None
    assert suppressed.wake.status == "suppressed"
    assert suppressed.suppressed_reason == "dnd_window"
    assert await scheduler.list_due_wakes(due_before=datetime(2026, 4, 25, 1, 0, 0), user_id=test_user.id) == []


def test_skill_registry_only_filters_candidates_without_fixed_sorting() -> None:
    registry = AuroraSkillRegistry()

    candidates = registry.load_candidate_affordances(
        "aurora_modeling",
        candidate_ids=[
            "aurora.agenda_priority",
            "aurora.wake_scheduling",
            "aurora.conversation_style",
        ],
    )

    assert [item.skill_id for item in candidates] == [
        "aurora.agenda_priority",
        "aurora.conversation_style",
    ]
