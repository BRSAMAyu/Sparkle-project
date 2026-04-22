from __future__ import annotations

import json
from datetime import date
from uuid import uuid4

import pytest

from app.models.plan import Plan, PlanStage, PlanType
from app.orchestration.prompts import build_system_prompt
from app.services.user_strategy_state_service import UserStrategyStateService


class _FakeRedis:
    def __init__(self) -> None:
        self._kv: dict[str, str] = {}
        self._ttl: dict[str, int] = {}

    async def get(self, key: str) -> str | None:
        return self._kv.get(key)

    async def setex(self, key: str, ttl: int, value: str) -> None:
        self._kv[key] = value
        self._ttl[key] = ttl

    async def delete(self, *keys: str) -> None:
        for key in keys:
            self._kv.pop(key, None)


@pytest.fixture
async def test_plan(db_session, test_user) -> Plan:
    plan = Plan(
        user_id=test_user.id,
        name="热力学冲刺计划",
        type=PlanType.SPRINT,
        description="掌握热力学第二章",
        plan_stage=PlanStage.SPRINT,
        target_date=date(2026, 4, 20),
        daily_available_minutes=90,
        progress=0.35,
        is_active=True,
        is_primary=True,
    )
    db_session.add(plan)
    await db_session.commit()
    await db_session.refresh(plan)
    return plan


@pytest.mark.asyncio
async def test_user_strategy_state_merges_profile_episode_session_with_precedence(db_session, test_user, test_plan) -> None:
    redis = _FakeRedis()
    service = UserStrategyStateService(db_session, redis=redis)

    await service.apply_adjustment(
        test_user.id,
        {"difficulty_level": 4, "session_mode": "exploratory"},
        layer="profile",
        reason="long-term tendency",
        evidence={"source": "history", "snippet": "user often wants breadth"},
        confidence=0.72,
    )
    await service.apply_adjustment(
        test_user.id,
        {"difficulty_level": 2, "retrieval_emphasis": "user_materials"},
        layer="episode",
        plan_id=test_plan.id,
        reason="exam week needs tighter grounding",
        evidence={"source": "plan", "snippet": "focus on current materials"},
        confidence=0.81,
    )
    await service.apply_adjustment(
        test_user.id,
        {"session_mode": "recovery", "push_vs_support": 0.2},
        layer="session",
        session_id="session-1",
        reason="user said they are overwhelmed",
        evidence={"source": "conversation", "snippet": "this is overwhelming"},
        confidence=0.9,
    )

    effective = await service.get_effective_state(
        test_user.id,
        plan_id=test_plan.id,
        session_id="session-1",
    )

    assert effective["difficulty_level"] == 2
    assert effective["session_mode"] == "recovery"
    assert effective["retrieval_emphasis"] == "user_materials"
    assert effective["push_vs_support"] == 0.2
    assert effective["meta"]["sources"]["difficulty_level"] == "episode"
    assert effective["meta"]["sources"]["session_mode"] == "session"


@pytest.mark.asyncio
async def test_user_strategy_state_profile_write_invalidates_context_cache(db_session, test_user) -> None:
    redis = _FakeRedis()
    redis._kv[f"user:context:{test_user.id}"] = "stale"

    service = UserStrategyStateService(db_session, redis=redis)
    await service.apply_adjustment(
        test_user.id,
        {"explanation_style": "step_by_step"},
        layer="profile",
        reason="user repeatedly asks for more structured explanations",
        evidence={"source": "conversation", "snippet": "step by step please"},
        confidence=0.84,
    )

    assert f"user:context:{test_user.id}" not in redis._kv


@pytest.mark.asyncio
async def test_user_strategy_state_episode_write_persists_history_and_adaptive_view(db_session, test_user, test_plan) -> None:
    service = UserStrategyStateService(db_session)

    await service.plan_state_service.upsert_plan_state(
        user_id=test_user.id,
        plan_id=test_plan.id,
        patch={"facts": {"adaptive_adjustments": {"time_multiplier": 1.25, "difficulty_shift": -0.5}}},
    )
    await service.apply_adjustment(
        test_user.id,
        {"current_episode_note": "这周先降载，优先稳住连续性"},
        layer="episode",
        plan_id=test_plan.id,
        reason="exam week overload",
        evidence={"source": "conversation", "snippet": "最近压力很大"},
        confidence=0.88,
    )

    effective = await service.get_effective_state(test_user.id, plan_id=test_plan.id)
    recent = await service.get_recent_changes(test_user.id, plan_id=test_plan.id)
    state = await service.plan_state_service.get_plan_state(test_user.id, test_plan.id)

    assert effective["current_episode_note"] == "这周先降载，优先稳住连续性"
    assert effective["meta"]["adaptive_adjustments"]["time_multiplier"] == 1.25
    assert recent[0]["field"] == "current_episode_note"
    assert isinstance((state.facts or {}).get("user_strategy_history"), list)


@pytest.mark.asyncio
async def test_user_strategy_state_write_changes_subsequent_prompt_context(db_session, test_user, test_plan) -> None:
    redis = _FakeRedis()
    service = UserStrategyStateService(db_session, redis=redis)

    await service.apply_adjustment(
        test_user.id,
        {
            "session_mode": "recovery",
            "explanation_style": "step_by_step",
            "retrieval_emphasis": "user_materials",
            "current_episode_note": "这轮先降载，不要一下子塞太多任务",
        },
        layer="session",
        session_id="session-bridge-2",
        reason="user said current tasks feel overwhelming",
        evidence={"source": "conversation", "snippet": "this feels overwhelming"},
        confidence=0.93,
    )

    strategy_state = await service.get_effective_state(
        test_user.id,
        plan_id=test_plan.id,
        session_id="session-bridge-2",
    )
    prompt = build_system_prompt(
        user_context={
            "preferences": {"depth_preference": 0.5, "curiosity_preference": 0.5},
            "user_strategy_state": strategy_state,
        },
        conversation_history={"messages": []},
    )

    # drift-fix: prompt rendering now exposes the adaptive strategy section
    # through the user-facing interaction strategy copy instead of the old
    # raw state dump header.
    assert "【当前交互策略】" in prompt
    assert "优先保护可重启性并降低负担" in prompt  # drift-fix
    assert "按步骤解释，把推理链条拆开，不要跳步" in prompt  # drift-fix
    assert "优先依赖用户自己的材料和当前计划来校准内容" in prompt  # drift-fix
