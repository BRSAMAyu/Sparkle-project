#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "backend"
BACKEND_VENV_PYTHON = BACKEND_ROOT / ".venv" / "bin" / "python"

if (
    BACKEND_VENV_PYTHON.exists()
    and Path(sys.executable).resolve() != BACKEND_VENV_PYTHON.resolve()
):
    os.execv(
        str(BACKEND_VENV_PYTHON),
        [str(BACKEND_VENV_PYTHON), str(Path(__file__).resolve()), *sys.argv[1:]],
    )

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

logging.basicConfig(level=logging.ERROR)

from loguru import logger

logger.remove()
logger.add(sys.stderr, level="ERROR")

from app.aurora.runtime_v1 import (
    AURORA_CHECKPOINT_SURFACE,
    AURORA_RUNTIME_STATE_KEY_TEMPLATE,
    AURORA_SURFACE_MODELING,
    AuroraCheckpointRuntimeService,
    AuroraDecisionLoop,
    AuroraRuntimeV1Service,
    ChatLayerAdapter,
    build_aurora_surface_metadata,
)
from app.aurora.runtime_v1.models import AuroraScheduledWake, AuroraStateSnapshot
from app.models.base import Base
from app.models.chat import ChatMessage, MessageRole
from app.models.plan import Plan, PlanType
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import PushPreference, User
from app.models.user_preferences import UserPreferencesCenter
from app.orchestration.adaptive_replanner import AdaptiveReplanner
from app.services.checkpoint_nudge_service import CheckpointDebriefService

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


async def _acceptance_adjust_for_checkpoint(self, *, user_id, plan_id, debrief_result):
    return {
        "user_id": str(user_id),
        "plan_id": str(plan_id),
        "mode": "acceptance_stub",
        "debrief_result": dict(debrief_result or {}),
    }


AdaptiveReplanner.adjust_for_checkpoint = _acceptance_adjust_for_checkpoint


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, object] = {}

    async def get(self, key: str):
        return self.values.get(key)

    async def setex(self, key: str, ttl: int, value: object) -> None:
        self.values[key] = value

    async def delete(self, key: str) -> None:
        self.values.pop(key, None)


@dataclass
class ScenarioResult:
    name: str
    details: str


class SequenceJsonLLM:
    def __init__(self, payloads: list[object]) -> None:
        self.payloads = list(payloads)
        self.calls: list[list[dict[str, str]]] = []

    async def chat_json(self, messages, **kwargs):
        self.calls.append(messages)
        if not self.payloads:
            raise RuntimeError("acceptance sequence exhausted")
        payload = self.payloads.pop(0)
        if isinstance(payload, Exception):
            raise payload
        return payload


def utc(year: int, month: int, day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=UTC).replace(tzinfo=None)


def _runtime_state_key(*, user_id: str, conversation_id: str) -> str:
    return AURORA_RUNTIME_STATE_KEY_TEMPLATE.format(
        user_id=user_id,
        surface=AURORA_SURFACE_MODELING,
        conversation_id=conversation_id,
    )


def _load_runtime_state(redis: FakeRedis, *, user_id: str, conversation_id: str) -> dict:
    raw = redis.values[_runtime_state_key(user_id=user_id, conversation_id=conversation_id)]
    return json.loads(str(raw))


def _infer_asked_domains(messages: list[str]) -> list[str]:
    domains: list[str] = []
    for message in messages:
        text = str(message or "")
        if not any(marker in text for marker in ("？", "?", "哪些", "哪几", "多久", "多少", "哪块", "什么")):
            continue
        if any(token in text for token in ("章节", "题型", "范围", "考哪些")) and "scope" not in domains:
            domains.append("scope")
        if any(token in text for token in ("最熟", "最虚", "基础", "掌握")) and "baseline" not in domains:
            domains.append("baseline")
        if any(token in text for token in ("每天", "多少时间", "多久", "几小时")) and "time" not in domains:
            domains.append("time")
        if any(token in text for token in ("目标", "结果", "想达到")) and "goal" not in domains:
            domains.append("goal")
    return domains


def _is_fragment(message: str) -> bool:
    text = str(message or "").strip()
    return bool(text) and text[-1] in {"，", ",", "：", ":", "；", ";"}


def _semantic_similarity(left: str, right: str) -> float:
    normalized_left = re.sub(r"[^\w\u4e00-\u9fff]+", "", left.lower())
    normalized_right = re.sub(r"[^\w\u4e00-\u9fff]+", "", right.lower())
    if not normalized_left or not normalized_right:
        return 0.0
    if normalized_left == normalized_right:
        return 1.0
    grams_left = {normalized_left[i : i + 2] for i in range(max(len(normalized_left) - 1, 1))}
    grams_right = {normalized_right[i : i + 2] for i in range(max(len(normalized_right) - 1, 1))}
    if not grams_left or not grams_right:
        return 0.0
    overlap = len(grams_left.intersection(grams_right))
    return overlap / max(min(len(grams_left), len(grams_right)), 1)


async def create_session() -> (
    tuple[AsyncSession, async_sessionmaker[AsyncSession], object]
):
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    session = session_factory()
    return session, session_factory, engine


async def create_user(
    session: AsyncSession,
    *,
    username: str,
    timezone_name: str = "Asia/Shanghai",
    aurora_preferences: dict | None = None,
) -> User:
    user = User(
        username=username,
        email=f"{username}@example.com",
        hashed_password="hashed",
        photon_balance=0,
    )
    session.add(user)
    await session.flush()
    session.add(PushPreference(user_id=user.id, timezone=timezone_name))
    if aurora_preferences is not None:
        session.add(
            UserPreferencesCenter(
                user_id=user.id, explicit={"aurora_preferences": aurora_preferences}
            )
        )
    await session.commit()
    await session.refresh(user)
    return user


async def seed_plan(
    session: AsyncSession,
    *,
    user_id,
    name: str,
    task_title: str,
) -> tuple[Plan, Task]:
    plan = Plan(
        id=uuid4(), user_id=user_id, name=name, type=PlanType.SPRINT, is_active=True
    )
    task = Task(
        user_id=user_id,
        plan_id=plan.id,
        title=task_title,
        type=TaskType.LEARNING,
        tags=[],
        estimated_minutes=75,
        difficulty=3,
        energy_cost=2,
        status=TaskStatus.PENDING,
        order_index=1000,
        phase_index=2,
    )
    session.add_all([plan, task])
    await session.commit()
    return plan, task


async def run_blocked_debrief(
    session: AsyncSession,
    *,
    user_id,
    redis: FakeRedis,
    plan: Plan,
    checkpoint_description: str = "Day 2 晚：做20题自测",
) -> tuple[dict, str, str]:
    session_id = uuid4()
    conversation_id = f"cp:{plan.id}:2"
    service = CheckpointDebriefService(session, redis)
    await service.process_turn(
        user_id=user_id,
        chat_session_id=session_id,
        user_message="我来复盘一下",
        context={
            "debrief_context": {
                "nudge_id": conversation_id,
                "plan_id": str(plan.id),
                "checkpoint_day": 2,
                "checkpoint_description": checkpoint_description,
            }
        },
    )
    await service.process_turn(
        user_id=user_id,
        chat_session_id=session_id,
        user_message="落后了，没完成",
        context={},
    )
    final = await service.process_turn(
        user_id=user_id,
        chat_session_id=session_id,
        user_message="主要是没时间，传输层也没搞定",
        context={},
    )
    return final, str(session_id), conversation_id


async def scenario_multi_message_and_detour(session: AsyncSession) -> ScenarioResult:
    redis = FakeRedis()
    user = await create_user(session, username="blocked_user")
    plan, _ = await seed_plan(
        session, user_id=user.id, name="7天计网冲刺", task_title="Day 4 · 传输层补强"
    )
    final, _, conversation_id = await run_blocked_debrief(
        session, user_id=user.id, redis=redis, plan=plan
    )

    wake_info = final["aurora_runtime"]["wake"]
    assert wake_info["status"] == "scheduled"
    wake = await session.get(AuroraScheduledWake, wake_info["wake_id"])
    wake.created_at = utc(2026, 4, 24, 9, 0)
    wake.scheduled_at = utc(2026, 4, 24, 10, 0)
    session.add(
        ChatMessage(
            user_id=user.id,
            session_id=wake.session_id,
            role=MessageRole.USER,
            content="顺便问下英语作文怎么收尾？",
            created_at=utc(2026, 4, 24, 9, 20),
        )
    )
    await session.commit()

    summary = await AuroraCheckpointRuntimeService(session, redis).process_due_wakes(
        now=utc(2026, 4, 24, 10, 5)
    )
    assert summary["executed"] == 1

    rows = await session.execute(
        select(ChatMessage)
        .where(
            ChatMessage.user_id == user.id,
            ChatMessage.session_id == wake.session_id,
            ChatMessage.role == MessageRole.ASSISTANT,
        )
        .order_by(ChatMessage.created_at.asc())
    )
    messages = list(rows.scalars().all())
    assert len(messages) == 2
    assert any("传输层" in message.content for message in messages)
    assert messages[0].actions[0]["data"]["surface_complete"] is False
    assert messages[1].actions[0]["data"]["surface_complete"] is True
    assert messages[1].actions[0]["data"]["conversation_id"] == conversation_id

    snapshot = await session.scalar(
        select(AuroraStateSnapshot).where(
            AuroraStateSnapshot.user_id == user.id,
            AuroraStateSnapshot.conversation_id == conversation_id,
        )
    )
    assert snapshot is not None
    runtime_key = (
        f"aurora:runtime:{user.id}:{AURORA_CHECKPOINT_SURFACE}:{conversation_id}"
    )
    assert runtime_key in redis.values
    return ScenarioResult(
        name="multi_message_and_detour",
        details="wake 在 DND 外执行，连续发 2 条，并且插话后仍然追原始卡点。",
    )


async def scenario_gap_closed_no_repeat(session: AsyncSession) -> ScenarioResult:
    redis = FakeRedis()
    user = await create_user(session, username="gap_closed_user")
    plan, _ = await seed_plan(
        session, user_id=user.id, name="7天计网冲刺", task_title="Day 4 · 传输层补强"
    )
    final, _, _ = await run_blocked_debrief(
        session, user_id=user.id, redis=redis, plan=plan
    )
    wake = await session.get(
        AuroraScheduledWake, final["aurora_runtime"]["wake"]["wake_id"]
    )
    wake.created_at = utc(2026, 4, 24, 9, 0)
    wake.scheduled_at = utc(2026, 4, 24, 10, 0)
    session.add(
        ChatMessage(
            user_id=user.id,
            session_id=wake.session_id,
            role=MessageRole.USER,
            content="我把传输层的滑动窗口补完了，现在已经搞明白了。",
            created_at=utc(2026, 4, 24, 9, 20),
        )
    )
    await session.commit()

    summary = await AuroraCheckpointRuntimeService(session, redis).process_due_wakes(
        now=utc(2026, 4, 24, 10, 5)
    )
    assert summary["cancelled"] == 1

    refreshed = await session.get(AuroraScheduledWake, wake.id)
    assert refreshed.status == "cancelled"
    rows = await session.execute(
        select(ChatMessage).where(
            ChatMessage.user_id == user.id,
            ChatMessage.session_id == wake.session_id,
            ChatMessage.role == MessageRole.ASSISTANT,
        )
    )
    assert list(rows.scalars().all()) == []
    return ScenarioResult(
        name="gap_closed_no_repeat",
        details="用户补上缺口后，wake 被取消，不会重复追问同一个卡点。",
    )


async def scenario_smooth_vs_blocked(session: AsyncSession) -> ScenarioResult:
    blocked_redis = FakeRedis()
    smooth_redis = FakeRedis()

    blocked_user = await create_user(session, username="blocked_vs_smooth_a")
    blocked_plan, _ = await seed_plan(
        session,
        user_id=blocked_user.id,
        name="7天计网冲刺",
        task_title="Day 4 · 传输层补强",
    )
    blocked_final, _, _ = await run_blocked_debrief(
        session, user_id=blocked_user.id, redis=blocked_redis, plan=blocked_plan
    )
    assert blocked_final["aurora_runtime"]["wake"]["status"] == "scheduled"

    smooth_user = await create_user(session, username="blocked_vs_smooth_b")
    smooth_plan, _ = await seed_plan(
        session,
        user_id=smooth_user.id,
        name="7天计网冲刺",
        task_title="Day 4 · 核心攻克",
    )
    service = CheckpointDebriefService(session, smooth_redis)
    session_id = uuid4()
    await service.process_turn(
        user_id=smooth_user.id,
        chat_session_id=session_id,
        user_message="我来复盘一下",
        context={
            "debrief_context": {
                "nudge_id": f"cp:{smooth_plan.id}:2",
                "plan_id": str(smooth_plan.id),
                "checkpoint_day": 2,
                "checkpoint_description": "Day 2 晚：做20题自测",
            }
        },
    )
    await service.process_turn(
        user_id=smooth_user.id,
        chat_session_id=session_id,
        user_message="进展不错",
        context={},
    )
    smooth_final = await service.process_turn(
        user_id=smooth_user.id,
        chat_session_id=session_id,
        user_message="框架部分最踏实，20题也刷完了。",
        context={},
    )

    assert smooth_final["aurora_runtime"]["wake"]["status"] == "not_scheduled"
    return ScenarioResult(
        name="smooth_vs_blocked",
        details="卡住用户会安排 follow-up，顺利用户不会被额外追着问。",
    )


async def scenario_dnd_suppression(session: AsyncSession) -> ScenarioResult:
    user = await create_user(
        session,
        username="dnd_user",
        aurora_preferences={"dnd_windows": [{"start": "22:30", "end": "07:30"}]},
    )
    wake = AuroraScheduledWake(
        user_id=user.id,
        surface=AURORA_CHECKPOINT_SURFACE,
        conversation_id="cp:dnd:2",
        session_id=uuid4(),
        scheduled_at=utc(2026, 4, 24, 15, 30),
        status="pending",
        reason="晚一点再看一眼自测结果",
        planned_action="checkpoint_follow_up",
        urgency_score=0.35,
        payload={"blocker_summary": "自测结果还没确认"},
        runtime_metadata=build_aurora_surface_metadata(
            surface=AURORA_CHECKPOINT_SURFACE,
            surface_complete=True,
            modeling_complete=False,
        ),
    )
    session.add(wake)
    await session.commit()

    summary = await AuroraCheckpointRuntimeService(
        session, FakeRedis()
    ).process_due_wakes(now=utc(2026, 4, 24, 15, 35))
    assert summary["suppressed"] == 1
    refreshed = await session.get(AuroraScheduledWake, wake.id)
    assert refreshed.status == "suppressed"
    return ScenarioResult(
        name="dnd_suppression",
        details="低紧急度 wake 落入 DND 时会 suppress，不绕开用户硬边界。",
    )


async def scenario_modeling_core_deepening() -> ScenarioResult:
    redis = FakeRedis()
    decision_llm = SequenceJsonLLM(
        [
            {
                "action": "emit_message",
                "modeling_complete": False,
                "chat_directive": {"intent": "ask_scope", "target_domain": "scope"},
            },
            {
                "action": "emit_message",
                "modeling_complete": False,
                "chat_directive": {"intent": "ask_scope", "target_domain": "scope"},
            },
            {
                "action": "emit_message",
                "modeling_complete": False,
                "chat_directive": {"intent": "ask_baseline", "target_domain": "baseline"},
            },
            {
                "action": "emit_message",
                "modeling_complete": False,
                "chat_directive": {"intent": "ask_time", "target_domain": "time"},
            },
        ]
    )
    chat_llm = SequenceJsonLLM(
        [
            {
                "messages": [
                    "我先接住你的目标，",
                    "这样我就能更稳地往下规划。",
                    "这样我就能更稳地往下规划。",
                    "这次主要考哪些章节？",
                ]
            },
            RuntimeError("force adapter fallback"),
            RuntimeError("force adapter fallback"),
            RuntimeError("force adapter fallback"),
        ]
    )
    service = AuroraRuntimeV1Service(
        redis_client=redis,
        decision_loop=AuroraDecisionLoop(llm_factory=lambda: decision_llm),
        chat_adapter=ChatLayerAdapter(llm_factory=lambda: chat_llm),
    )

    conversation_id = "acceptance:modeling"
    conversation_context: dict[str, list[dict[str, str]]] = {"messages": []}
    user_id = "acceptance-user"
    turns = [
        {
            "user_message": "我想在 7 天后通过计算机网络考试。",
            "request_extra_context": {
                "task_state": {
                    "goal_raw": "7 天后通过计算机网络考试",
                },
                "informational_tensions": [
                    {"domain": "goal", "status": "resolved"},
                    {"domain": "scope", "status": "open"},
                    {"domain": "baseline", "status": "open"},
                    {"domain": "time", "status": "open"},
                ],
                "exam_sprint_policy": {
                    "mode": "seven_day_survival",
                    "days_remaining": 7,
                    "summary": "先保过线，优先高频必考内容。",
                },
            },
        },
        {
            "user_message": "范围主要是传输层、网络层和应用层，老师说题型以选择和简答为主。",
            "request_extra_context": {
                "task_state": {
                    "goal_raw": "7 天后通过计算机网络考试",
                    "exam_scope": "传输层、网络层、应用层；选择 + 简答",
                },
                "informational_tensions": [
                    {"domain": "goal", "status": "resolved"},
                    {"domain": "exam_scope", "status": "resolved"},
                    {"domain": "knowledge_baseline", "status": "open"},
                    {"domain": "time_available", "status": "open"},
                ],
                "exam_sprint_policy": {
                    "mode": "seven_day_survival",
                    "days_remaining": 6,
                    "summary": "继续优先高频必考内容。",
                },
            },
        },
        {
            "user_message": "基础很一般，传输层最虚，网络层只记得一点点概念。",
            "request_extra_context": {
                "task_state": {
                    "goal_raw": "7 天后通过计算机网络考试",
                    "exam_scope": "传输层、网络层、应用层；选择 + 简答",
                    "knowledge_baseline": "传输层最虚，网络层只有零散概念",
                },
                "informational_tensions": [
                    {"domain": "goal", "status": "resolved"},
                    {"domain": "exam_scope", "status": "resolved"},
                    {"domain": "knowledge_baseline", "status": "resolved"},
                    {"domain": "time_available", "status": "open"},
                ],
                "exam_sprint_policy": {
                    "mode": "seven_day_survival",
                    "days_remaining": 5,
                    "summary": "再补时间约束就能进入有效规划。",
                },
            },
        },
        {
            "user_message": "这几天每天大概能学 3 小时，周末能多挤一点。",
            "request_extra_context": {
                "task_state": {
                    "goal_raw": "7 天后通过计算机网络考试",
                    "exam_scope": "传输层、网络层、应用层；选择 + 简答",
                    "knowledge_baseline": "传输层最虚，网络层只有零散概念",
                    "daily_available_hours": 3,
                },
                "informational_tensions": [
                    {"domain": "goal", "status": "resolved"},
                    {"domain": "exam_scope", "status": "resolved"},
                    {"domain": "knowledge_baseline", "status": "resolved"},
                    {"domain": "time_available", "status": "resolved"},
                ],
                "exam_sprint_policy": {
                    "mode": "seven_day_survival",
                    "days_remaining": 4,
                    "summary": "信息闭环，可进入规划。",
                },
            },
        },
    ]

    asked_domains: list[str] = []
    repeated_asks = 0
    turns_to_planning: int | None = None
    final_runtime_state: dict = {}

    for index, turn in enumerate(turns, start=1):
        conversation_context["messages"].append({"role": "user", "content": turn["user_message"]})
        plan = await service.plan_turn(
            active_db=None,
            user_id=user_id,
            surface=AURORA_SURFACE_MODELING,
            conversation_id=conversation_id,
            request_id=f"acceptance-{index}",
            user_message=turn["user_message"],
            request_extra_context=turn["request_extra_context"],
            conversation_context=conversation_context,
            user_context_payload={},
        )
        assert len(plan.messages) <= 3
        assert all(not _is_fragment(message) for message in plan.messages)
        for left_index, left in enumerate(plan.messages):
            for right in plan.messages[left_index + 1 :]:
                assert _semantic_similarity(left, right) < 0.82

        current_asked = _infer_asked_domains(plan.messages)
        repeated_asks += sum(1 for domain in current_asked if domain in asked_domains)
        asked_domains.extend(domain for domain in current_asked if domain not in asked_domains)

        for message in plan.messages:
            conversation_context["messages"].append({"role": "assistant", "content": message})

        if plan.modeling_complete and turns_to_planning is None:
            turns_to_planning = index
        final_runtime_state = _load_runtime_state(redis, user_id=user_id, conversation_id=conversation_id)

    assert turns_to_planning is not None and turns_to_planning <= 5
    assert repeated_asks == 0
    assert asked_domains == ["scope", "baseline", "time"]
    final_decision = final_runtime_state["decision"]
    assert set(final_decision["metadata"]["covered_domains"]) >= {"goal", "scope", "baseline", "time"}
    assert final_decision["modeling_complete"] is True
    return ScenarioResult(
        name="modeling_core_deepening",
        details=(
            "4 轮内补齐 目标/范围/基础/时间，0 次重复追问，并验证连续消息不会拆句或语义重叠。"
        ),
    )


async def scenario_modeling_metadata_contract() -> ScenarioResult:
    metadata = build_aurora_surface_metadata(
        surface="aurora_modeling",
        surface_complete=True,
        modeling_complete=True,
    )
    assert metadata["aurora_surface"] == "aurora_modeling"
    assert metadata["aurora_runtime_enabled"] is True
    assert metadata["surface_complete"] is True
    assert metadata["modeling_complete"] is True
    return ScenarioResult(
        name="modeling_metadata_contract",
        details="统一 metadata 合同包含 modeling_complete=true。",
    )


async def main() -> None:
    results: list[ScenarioResult] = []
    for scenario in (
        scenario_multi_message_and_detour,
        scenario_gap_closed_no_repeat,
        scenario_smooth_vs_blocked,
        scenario_dnd_suppression,
    ):
        session, _, engine = await create_session()
        try:
            results.append(await scenario(session))
        finally:
            await session.close()
            await engine.dispose()

    results.append(await scenario_modeling_core_deepening())
    results.append(await scenario_modeling_metadata_contract())
    print("Aurora Runtime v1 acceptance passed.")
    for item in results:
        print(f"- {item.name}: {item.details}")


if __name__ == "__main__":
    asyncio.run(main())
