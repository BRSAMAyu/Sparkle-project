from __future__ import annotations

import uuid
from datetime import datetime

import pytest

from app.aurora.core_session import AuroraCoreSession, AuroraCoreSessionService
from app.aurora.runtime_v1.control_surface import ControlSurfaceService, HarnessUpdateRejectedError
from app.aurora.runtime_v1.persistence import AuroraPersistenceStore
from app.aurora.runtime_v1.planning import AuroraRuntimePlanningAdapter, get_tension_prompt
from app.aurora.runtime_v1.service import AuroraRuntimeV1Service
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
from app.services.aurora_stage38_kill_switch_service import AuroraStage38KillSwitchService
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


class _RecordingDecisionLoop:
    def __init__(self) -> None:
        self.readouts = []

    async def decide(self, readout):
        from app.aurora.runtime_v1.decision_loop import AuroraDecision

        self.readouts.append(readout)
        if len(self.readouts) == 1:
            return AuroraDecision(
                action="emit_message",
                state_updates={
                    "informational_tensions": [
                        {
                            "domain": "传输层",
                            "description": "传输层 checkpoint 还没补齐",
                            "priority": 0.8,
                            "status": "open",
                        }
                    ],
                    "latent_threads": [
                        {
                            "context_snapshot": "下个 checkpoint 要追回传输层",
                            "salience": 0.75,
                        }
                    ],
                },
                harness_updates={"agenda_priority": "传输层"},
                chat_directive={"intent": "checkpoint_repair", "target_domain": "传输层"},
            )
        return AuroraDecision(action="emit_message", chat_directive={"intent": "checkpoint_repair"})


class _StaticChatAdapter:
    async def render(self, decision, readout):
        return ["checkpoint runtime message"]


class _DropThreadDecisionLoop:
    async def decide(self, readout):
        from app.aurora.runtime_v1.decision_loop import AuroraDecision

        return AuroraDecision(
            action="drop_thread",
            state_updates={},
            chat_directive={"intent": "drop_thread", "target_domain": "传输层"},
        )


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


def test_activity_profile_expression_defaults_round_trip() -> None:
    profile = ActivityProfile(expression={"directness": 0.82, "brevity": 0.9})

    assert profile.expression["directness"] == pytest.approx(0.82)
    assert profile.expression["brevity"] == pytest.approx(0.9)
    assert profile.expression["tone_warmth"] == pytest.approx(0.68)
    assert profile.expression["friendliness"] == pytest.approx(0.74)
    assert profile.expression["challenge_intensity"] == pytest.approx(0.36)

    dumped = profile.model_dump(mode="python")

    assert set(dumped["expression"].keys()) == {
        "tone_warmth",
        "directness",
        "brevity",
        "friendliness",
        "challenge_intensity",
    }
    assert ActivityProfile.model_validate(dumped).expression["directness"] == pytest.approx(0.82)


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
async def test_checkpoint_surface_loads_prior_runtime_threads_across_conversations() -> None:
    redis = _FakeRedis()
    decision_loop = _RecordingDecisionLoop()
    service = AuroraRuntimeV1Service(
        redis_client=redis,
        decision_loop=decision_loop,
        chat_adapter=_StaticChatAdapter(),
    )

    await service.plan_turn(
        active_db=None,
        user_id="user-checkpoint",
        surface="aurora_checkpoint",
        conversation_id="cp:plan:2",
        request_id="req-1",
        user_message="第 2 天 checkpoint，传输层落后",
        request_extra_context={"checkpoint_state": {"checkpoint_day": 2}},
        conversation_context={"messages": []},
        user_context_payload={},
    )
    await service.plan_turn(
        active_db=None,
        user_id="user-checkpoint",
        surface="aurora_checkpoint",
        conversation_id="cp:plan:4",
        request_id="req-2",
        user_message="第 4 天 checkpoint",
        request_extra_context={"checkpoint_state": {"checkpoint_day": 4}},
        conversation_context={"messages": []},
        user_context_payload={},
    )

    second_readout = decision_loop.readouts[1]
    assert second_readout.informational_tensions
    assert second_readout.informational_tensions[0]["domain"] == "传输层"
    assert second_readout.latent_threads
    assert "传输层" in second_readout.latent_threads[0]["context_snapshot"]


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
    pref_service = PreferenceService(db_session, redis=None)
    await pref_service.update_explicit(
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

    service = ControlSurfaceService(db_session, redis=_FakeRedis(), enabled=True, preference_service=pref_service)
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

    pref_svc = PreferenceService(db_session, redis=None)
    service = ControlSurfaceService(db_session, redis=_FakeRedis(), enabled=True, preference_service=pref_svc)
    reading = await service.read_control_surface(test_user.id)

    with pytest.raises(HarnessUpdateRejectedError) as exc_info:
        service.validate_harness_update(
            {"agenda_priority": "family_conflict"},
            hard_bounds=reading.hard_bounds,
        )

    assert "privacy boundary" in str(exc_info.value)


@pytest.mark.asyncio
async def test_control_surface_expression_update_round_trips(db_session, test_user) -> None:
    service = ControlSurfaceService(db_session, redis=_FakeRedis(), enabled=True)

    reading = await service.apply_harness_update(
        test_user.id,
        {"expression": {"directness": 0.92, "brevity": 0.88}},
    )

    assert reading.adjustable.expression["directness"] == pytest.approx(0.92)
    assert reading.adjustable.expression["brevity"] == pytest.approx(0.88)
    assert reading.adjustable.expression["tone_warmth"] == pytest.approx(0.68)
    assert reading.adjustable.expression["friendliness"] == pytest.approx(0.74)


@pytest.mark.asyncio
async def test_dnd_wake_is_suppressed(db_session, test_user) -> None:
    redis = _FakeRedis()
    pref_svc = PreferenceService(db_session, redis=None)
    await pref_svc.update_explicit(
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
        control_surface_service=ControlSurfaceService(db_session, redis=redis, enabled=True, preference_service=pref_svc),
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


def test_tension_prompt_registry_supports_planning_domain_aliases() -> None:
    assert "具体考哪些范围" in get_tension_prompt("exam_scope")
    assert "具体考哪些范围" in get_tension_prompt("scope")
    assert "关键信息" in get_tension_prompt("unknown_domain")


@pytest.mark.asyncio
async def test_planning_detour_marks_surface_state_without_sidecar_prompt() -> None:
    adapter = AuroraRuntimePlanningAdapter(redis_client=_FakeRedis())
    state = await adapter.get_or_create_state(
        user_id="user-1",
        conversation_id="conv-1",
        db=None,
        planning_session_id="planning-1",
        goal_raw="7天后考计算机网络",
        collected={"goal_raw": "7天后考计算机网络"},
    )

    state = await adapter.absorb_user_turn(
        state=state,
        db=None,
        message="先帮我查一下这个任务完成没有",
        extracted_fields={},
        is_detour=True,
    )
    scaffold = adapter.build_detour_scaffold(state)

    assert scaffold["surface_state"]["in_detour"] is True
    assert scaffold["recent_detours"] == ["先帮我查一下这个任务完成没有"]
    assert adapter.build_detour_prompt(state) == ""


# ---------------------------------------------------------------------------
# V3-FIX-253 行内四缺陷回归（wt538）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_plan_turn_kill_switch_off_returns_minimal_plan(monkeypatch: pytest.MonkeyPatch) -> None:
    """kill-switch off 分支必须返回合法 AuroraRuntimeTurnPlan（零消息）。

    修前该分支以不存在的 telemetry/next_action/source 字段构造 TurnPlan
    且缺 surface/surface_complete/modeling_complete 必填字段，一触发即 TypeError。
    注：当前 AuroraStage38KillSwitchService 未注册 aurora_runtime binding，
    get_feature_mode("aurora_runtime") 恒 ValueError → 缺省 "shadow"，故本测
    直接桩掉 get_feature_mode 以到达分支（binding 接线属后续开关接入工作）。
    """

    async def _mode_off(self, feature: str) -> str:
        return "off"

    monkeypatch.setattr(AuroraStage38KillSwitchService, "get_feature_mode", _mode_off)
    decision_loop = _RecordingDecisionLoop()
    service = AuroraRuntimeV1Service(
        redis_client=_FakeRedis(),
        decision_loop=decision_loop,
        chat_adapter=_StaticChatAdapter(),
    )

    plan = await service.plan_turn(
        active_db=None,
        user_id="user-off",
        surface="aurora_modeling",
        conversation_id="conv-off",
        request_id="req-off",
        user_message="继续",
        request_extra_context=None,
        conversation_context=None,
        user_context_payload=None,
    )

    # off 分支短路：决策管线不应执行
    assert decision_loop.readouts == []
    assert plan.messages == []
    assert plan.surface == "aurora_modeling"
    assert plan.surface_complete is False
    assert plan.modeling_complete is False
    assert plan.action == "wait"


@pytest.mark.asyncio
async def test_active_core_session_payload_formats_iso_strings(monkeypatch: pytest.MonkeyPatch) -> None:
    """AuroraCoreSession.last_activity_at/.expires_at 是 ISO str（非 datetime），
    payload 必须直接透传而非调 .isoformat()（修前 AttributeError）。"""

    async def _fake_get_active_session(self, user_id: str) -> AuroraCoreSession:
        return AuroraCoreSession(
            session_id="core-1",
            user_id=user_id,
            conversation_id="conv-core",
            surface="aurora_modeling",
            status="active",
            stage="declare",
            scope="传输层校准",
            session_type="strategy_recalibration",
        )

    monkeypatch.setattr(AuroraCoreSessionService, "get_active_session", _fake_get_active_session)
    service = AuroraRuntimeV1Service(redis_client=_FakeRedis())

    payload = await service._active_core_session_payload(uuid.UUID("b9a9e0a0-2956-47de-86dc-002ee8b835ad"))

    assert payload is not None
    assert payload["session_id"] == "core-1"
    assert payload["status"] == "active"
    # 两者本就是 ISO 8601 串，透传后必须仍可解析
    datetime.fromisoformat(str(payload["last_activity_at"]))
    datetime.fromisoformat(str(payload["expires_at"]))


@pytest.mark.asyncio
async def test_plan_turn_drop_thread_decision_persists_valid_intent() -> None:
    """decision.action == "drop_thread" 时 _persist_runtime_state 构造的
    AuroraIntent.intent_type 必须是合法 AuroraIntentType（修前 ValidationError
    使整个 plan_turn 崩溃，且带 drop_thread intent 的存量状态读回即被静默丢弃）。"""

    redis = _FakeRedis()
    service = AuroraRuntimeV1Service(
        redis_client=redis,
        decision_loop=_DropThreadDecisionLoop(),
        chat_adapter=_StaticChatAdapter(),
    )

    await service.plan_turn(
        active_db=None,
        user_id="user-drop",
        surface="aurora_modeling",
        conversation_id="conv-drop",
        request_id="req-drop",
        user_message="这个线索不用再追了",
        request_extra_context=None,
        conversation_context=None,
        user_context_payload={},
    )

    state = await AuroraRuntimeStore(redis, enabled=True).load_runtime_state(
        user_id="user-drop",
        surface="aurora_modeling",
        conversation_id="conv-drop",
    )
    assert state is not None
    assert state.current_intent is not None
    assert state.current_intent.intent_type == "drop_thread"
