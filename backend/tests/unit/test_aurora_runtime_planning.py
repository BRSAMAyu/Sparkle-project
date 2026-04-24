from __future__ import annotations

import json
from uuid import uuid4

import pytest

from app.aurora.runtime_v1 import AuroraRuntimePlanningAdapter
from app.orchestration.planning_workflow import PlanningSession, PlanningWorkflowManager


class FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self.store.get(key)

    async def setex(self, key: str, _ttl: int, value: str) -> None:
        self.store[key] = value

    async def delete(self, key: str) -> None:
        self.store.pop(key, None)


@pytest.mark.asyncio
async def test_detour_keeps_latent_thread_for_planning_surface() -> None:
    redis = FakeRedis()
    manager = PlanningWorkflowManager(redis_client=redis)
    user_id = uuid4()
    conversation_id = "aurora-planning-detour"

    first_turn = await manager.process_planning_turn(
        db=None,  # type: ignore[arg-type]
        user_id=user_id,
        chat_session_id=conversation_id,
        message="7天后考计算机网络，帮我规划一下",
        context={},
    )

    detour_turn = await manager.process_planning_turn(
        db=None,  # type: ignore[arg-type]
        user_id=user_id,
        chat_session_id=conversation_id,
        message="先帮我查一下这个任务完成没有",
        context={},
    )

    state = await manager.runtime_adapter.load_state(user_id=str(user_id), conversation_id=conversation_id)

    assert first_turn is not None
    assert detour_turn is not None and detour_turn["bypass_planning"] is True
    assert state is not None
    assert "Aurora planning sidecar is active" in manager.runtime_adapter.build_detour_prompt(state)
    assert state.surface == "aurora_planning"
    assert any(thread.status == "active" for thread in state.latent_threads)
    assert state.activity_profile.agenda_priority in {"exam_scope", "knowledge_baseline", "time_available"}


@pytest.mark.asyncio
async def test_user_supplied_info_resolves_tension_without_reasking_same_domain() -> None:
    redis = FakeRedis()
    manager = PlanningWorkflowManager(redis_client=redis)
    user_id = uuid4()
    conversation_id = "aurora-planning-fill-gap"

    await manager.process_planning_turn(
        db=None,  # type: ignore[arg-type]
        user_id=user_id,
        chat_session_id=conversation_id,
        message="7天后考计算机网络，帮我规划一下",
        context={},
    )

    await manager.process_planning_turn(
        db=None,  # type: ignore[arg-type]
        user_id=user_id,
        chat_session_id=conversation_id,
        message="考传输层、网络层和应用层",
        context={},
    )

    reply = await manager.process_planning_turn(
        db=None,  # type: ignore[arg-type]
        user_id=user_id,
        chat_session_id=conversation_id,
        message="我是零基础",
        context={},
    )

    state = await manager.runtime_adapter.load_state(user_id=str(user_id), conversation_id=conversation_id)

    assert reply is not None
    assert "每天大概能投入多少时间" in reply["message"]
    assert "基础大概在哪个位置" not in reply["message"]
    assert state is not None
    baseline_tension = next(item for item in state.informational_tensions if item.domain == "knowledge_baseline")
    time_tension = next(item for item in state.informational_tensions if item.domain == "time_available")
    assert baseline_tension.status == "resolved"
    assert time_tension.status == "open"


@pytest.mark.asyncio
async def test_strategy_and_task_prompt_consume_richer_aurora_runtime_state() -> None:
    redis = FakeRedis()
    manager = PlanningWorkflowManager(redis_client=redis)
    session = PlanningSession(
        planning_session_id="planning-runtime-rich",
        chat_session_id="planning-runtime-rich-chat",
        user_id=str(uuid4()),
        state="CLARIFYING",
        goal_raw="7天后考计算机网络，帮我规划",
        collected={
            "time_constraint_days": 7,
            "daily_available_hours": 2,
            "subject": "计算机网络",
            "exam_scope": "考传输层、网络层、应用层",
            "knowledge_baseline": "完全没学过",
            "time_available": "每天约 2 小时",
            "available_materials": ["真题", "课件"],
            "blocked_days": ["周三下午有实验"],
        },
    )

    state = await manager.runtime_adapter.get_or_create_state(
        user_id=session.user_id,
        conversation_id=session.chat_session_id,
        planning_session_id=session.planning_session_id,
        goal_raw=session.goal_raw,
        profile_context={},
        collected=session.collected,
    )

    strategy = manager._build_strategy(session, aurora_state=state)
    guide_json = manager._build_task_guide_json(
        session=session,
        phase=strategy["phases"][0],
        phase_index=1,
        default_daily_hours=2,
        day_number=1,
        day_focus=strategy["phases"][0]["focus"],
        aurora_state=state,
    )
    task_prompt = manager._build_task_ai_prompt(
        session=session,
        phase=strategy["phases"][0],
        guide_json=guide_json,
        aurora_state=state,
    )

    assert strategy["user_context_digest"]["available_materials"] == ["真题", "课件"]
    assert "周三下午有实验" in strategy["checkpoints"][0]["description"]
    assert "真题" in strategy["phases"][0]["method"]
    assert "手头资料包括：真题、课件" in task_prompt
    assert "已知忙碌时段：周三下午有实验" in task_prompt


@pytest.mark.asyncio
async def test_planning_runtime_state_isolated_from_other_surfaces() -> None:
    redis = FakeRedis()
    adapter = AuroraRuntimePlanningAdapter(redis_client=redis)

    planning_state = await adapter.get_or_create_state(
        user_id="user-1",
        conversation_id="shared-conv",
        planning_session_id="planning-session",
        goal_raw="帮我做规划",
        profile_context={},
        collected={"knowledge_baseline": "完全没学过"},
    )

    modeling_key = adapter.runtime_key(user_id="user-1", conversation_id="shared-conv", surface="aurora_modeling")
    checkpoint_key = adapter.runtime_key(user_id="user-1", conversation_id="shared-conv", surface="aurora_checkpoint")
    await redis.setex(
        modeling_key,
        60,
        json.dumps(
            {
                **planning_state.to_dict(),
                "surface": "aurora_modeling",
                "user_model_snapshot": {"knowledge_baseline": "建模面里的值"},
            },
            ensure_ascii=False,
        ),
    )
    await redis.setex(
        checkpoint_key,
        60,
        json.dumps(
            {
                **planning_state.to_dict(),
                "surface": "aurora_checkpoint",
                "user_model_snapshot": {"knowledge_baseline": "checkpoint 面里的值"},
            },
            ensure_ascii=False,
        ),
    )

    reloaded = await adapter.load_state(user_id="user-1", conversation_id="shared-conv")

    assert modeling_key != adapter.runtime_key(user_id="user-1", conversation_id="shared-conv")
    assert checkpoint_key != adapter.runtime_key(user_id="user-1", conversation_id="shared-conv")
    assert reloaded is not None
    assert reloaded.surface == "aurora_planning"
    assert reloaded.user_model_snapshot["knowledge_baseline"] == "完全没学过"
