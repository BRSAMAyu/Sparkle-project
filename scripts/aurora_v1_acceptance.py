#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import logging
import os
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
    AuroraCheckpointRuntimeService,
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


def utc(year: int, month: int, day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=UTC).replace(tzinfo=None)


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
    wake.scheduled_at = utc(2026, 4, 24, 10, 0)
    session.add(
        ChatMessage(
            user_id=user.id,
            session_id=wake.session_id,
            role=MessageRole.USER,
            content="顺便问下英语作文怎么收尾？",
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
    wake.scheduled_at = utc(2026, 4, 24, 10, 0)
    session.add(
        ChatMessage(
            user_id=user.id,
            session_id=wake.session_id,
            role=MessageRole.USER,
            content="我把传输层的滑动窗口补完了，现在已经搞明白了。",
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

    results.append(await scenario_modeling_metadata_contract())
    print("Aurora Runtime v1 acceptance passed.")
    for item in results:
        print(f"- {item.name}: {item.details}")


if __name__ == "__main__":
    asyncio.run(main())
