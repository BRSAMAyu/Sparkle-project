from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.aurora.runtime_v1 import (
    AURORA_CHECKPOINT_SURFACE,
    AuroraCheckpointRuntimeService,
    build_aurora_surface_metadata,
)
from app.aurora.runtime_v1.models import AuroraScheduledWake, AuroraStateSnapshot
from app.models.chat import ChatMessage, MessageRole
from app.models.plan import Plan, PlanType
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import PushPreference
from app.models.user_preferences import UserPreferencesCenter
from app.services.checkpoint_nudge_service import CheckpointDebriefService


class _FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, object] = {}

    async def get(self, key: str):
        return self.values.get(key)

    async def setex(self, key: str, ttl: int, value: object) -> None:
        self.values[key] = value

    async def delete(self, key: str) -> None:
        self.values.pop(key, None)


def _utc(year: int, month: int, day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=UTC).replace(tzinfo=None)


async def _run_blocked_debrief(
    db_session, user_id, redis: _FakeRedis
) -> tuple[dict, str, str]:
    session_id = uuid4()
    plan_id = uuid4()
    plan = Plan(
        id=plan_id,
        user_id=user_id,
        name="7天计网冲刺",
        type=PlanType.SPRINT,
        is_active=True,
    )
    next_task = Task(
        user_id=user_id,
        plan_id=plan_id,
        title="Day 4 · 传输层补强",
        type=TaskType.LEARNING,
        tags=[],
        estimated_minutes=80,
        difficulty=3,
        energy_cost=2,
        status=TaskStatus.PENDING,
        order_index=1000,
        phase_index=2,
    )
    db_session.add_all([plan, next_task])
    await db_session.commit()

    service = CheckpointDebriefService(db_session, redis)
    conversation_id = f"cp:{plan_id}:2"
    await service.process_turn(
        user_id=user_id,
        chat_session_id=session_id,
        user_message="我来复盘一下",
        context={
            "debrief_context": {
                "nudge_id": conversation_id,
                "plan_id": str(plan_id),
                "checkpoint_day": 2,
                "checkpoint_description": "Day 2 晚：做20题自测",
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


@pytest.mark.asyncio
async def test_checkpoint_runtime_schedules_specific_follow_up_and_snapshot(
    db_session, test_user
) -> None:
    redis = _FakeRedis()
    final, session_id, conversation_id = await _run_blocked_debrief(
        db_session, test_user.id, redis
    )

    wake_info = final["aurora_runtime"]["wake"]
    assert wake_info["status"] == "scheduled"
    assert wake_info["wake_id"] != "None"

    wake = await db_session.scalar(
        select(AuroraScheduledWake).where(
            AuroraScheduledWake.conversation_id == conversation_id
        )
    )
    assert wake is not None
    assert wake.surface == AURORA_CHECKPOINT_SURFACE
    assert "传输层" in wake.reason
    assert wake.payload["next_task_title"]

    snapshot = await db_session.scalar(
        select(AuroraStateSnapshot).where(
            AuroraStateSnapshot.conversation_id == conversation_id
        )
    )
    assert snapshot is not None
    assert snapshot.activity_profile["agenda_priority"] == "knowledge_gap"
    assert snapshot.runtime_metadata["aurora_surface"] == AURORA_CHECKPOINT_SURFACE
    assert snapshot.runtime_metadata["surface_complete"] is True
    assert snapshot.runtime_metadata["modeling_complete"] is False

    runtime_key = (
        f"aurora:runtime:{test_user.id}:{AURORA_CHECKPOINT_SURFACE}:{conversation_id}"
    )
    assert runtime_key in redis.values
    assert session_id in str(redis.values[runtime_key])


@pytest.mark.asyncio
async def test_checkpoint_runtime_keeps_smooth_user_unscheduled(
    db_session, test_user
) -> None:
    session_id = uuid4()
    plan_id = uuid4()
    db_session.add(
        Plan(
            id=plan_id,
            user_id=test_user.id,
            name="7天计网冲刺",
            type=PlanType.SPRINT,
            is_active=True,
        )
    )
    await db_session.commit()

    service = CheckpointDebriefService(db_session, _FakeRedis())
    await service.process_turn(
        user_id=test_user.id,
        chat_session_id=session_id,
        user_message="我来复盘一下",
        context={
            "debrief_context": {
                "nudge_id": f"cp:{plan_id}:2",
                "plan_id": str(plan_id),
                "checkpoint_day": 2,
            }
        },
    )
    await service.process_turn(
        user_id=test_user.id,
        chat_session_id=session_id,
        user_message="进展不错",
        context={},
    )
    final = await service.process_turn(
        user_id=test_user.id,
        chat_session_id=session_id,
        user_message="框架部分最踏实，20题也刷完了",
        context={},
    )

    assert final["goal_met"] is True
    assert final["aurora_runtime"]["wake"]["status"] == "not_scheduled"
    wakes = await db_session.execute(
        select(AuroraScheduledWake).where(AuroraScheduledWake.user_id == test_user.id)
    )
    assert list(wakes.scalars().all()) == []


@pytest.mark.asyncio
async def test_due_wake_emits_two_messages_and_keeps_original_blocker_after_detour(
    db_session, test_user
) -> None:
    redis = _FakeRedis()
    final, _, conversation_id = await _run_blocked_debrief(
        db_session, test_user.id, redis
    )
    wake_id = final["aurora_runtime"]["wake"]["wake_id"]
    wake = await db_session.get(AuroraScheduledWake, wake_id)
    wake.scheduled_at = _utc(2026, 4, 24, 10, 0)
    db_session.add(
        ChatMessage(
            user_id=test_user.id,
            session_id=wake.session_id,
            role=MessageRole.USER,
            content="顺便问下英语作文怎么收尾？",
        )
    )
    await db_session.commit()

    summary = await AuroraCheckpointRuntimeService(db_session, redis).process_due_wakes(
        now=_utc(2026, 4, 24, 10, 5)
    )

    assert summary["executed"] == 1
    rows = await db_session.execute(
        select(ChatMessage)
        .where(
            ChatMessage.user_id == test_user.id,
            ChatMessage.session_id == wake.session_id,
            ChatMessage.role == MessageRole.ASSISTANT,
        )
        .order_by(ChatMessage.created_at.asc())
    )
    messages = list(rows.scalars().all())
    assert len(messages) == 2
    assert "传输层" in messages[0].content or "传输层" in messages[1].content
    assert messages[0].actions[0]["data"]["surface_complete"] is False
    assert messages[1].actions[0]["data"]["surface_complete"] is True
    assert messages[1].actions[0]["data"]["modeling_complete"] is False
    assert messages[1].actions[0]["data"]["conversation_id"] == conversation_id


@pytest.mark.asyncio
async def test_due_wake_cancels_when_user_already_filled_gap(
    db_session, test_user
) -> None:
    redis = _FakeRedis()
    final, _, conversation_id = await _run_blocked_debrief(
        db_session, test_user.id, redis
    )
    wake = await db_session.get(
        AuroraScheduledWake, final["aurora_runtime"]["wake"]["wake_id"]
    )
    wake.scheduled_at = _utc(2026, 4, 24, 10, 0)
    db_session.add(
        ChatMessage(
            user_id=test_user.id,
            session_id=wake.session_id,
            role=MessageRole.USER,
            content="我把传输层的滑动窗口补完了，现在已经搞明白了。",
        )
    )
    await db_session.commit()

    summary = await AuroraCheckpointRuntimeService(db_session, redis).process_due_wakes(
        now=_utc(2026, 4, 24, 10, 5)
    )

    assert summary["cancelled"] == 1
    refreshed = await db_session.get(AuroraScheduledWake, wake.id)
    assert refreshed.status == "cancelled"
    messages = await db_session.execute(
        select(ChatMessage).where(
            ChatMessage.user_id == test_user.id,
            ChatMessage.session_id == wake.session_id,
            ChatMessage.role == MessageRole.ASSISTANT,
        )
    )
    assert list(messages.scalars().all()) == []
    assert refreshed.conversation_id == conversation_id


@pytest.mark.asyncio
async def test_due_wake_suppresses_when_inside_dnd(db_session, test_user) -> None:
    db_session.add(PushPreference(user_id=test_user.id, timezone="Asia/Shanghai"))
    db_session.add(
        UserPreferencesCenter(
            user_id=test_user.id,
            explicit={
                "aurora_preferences": {
                    "dnd_windows": [{"start": "22:30", "end": "07:30"}]
                }
            },
        )
    )
    wake = AuroraScheduledWake(
        user_id=test_user.id,
        surface=AURORA_CHECKPOINT_SURFACE,
        conversation_id="cp:test:2",
        session_id=uuid4(),
        scheduled_at=_utc(2026, 4, 24, 15, 30),
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
    db_session.add(wake)
    await db_session.commit()

    summary = await AuroraCheckpointRuntimeService(
        db_session, _FakeRedis()
    ).process_due_wakes(now=_utc(2026, 4, 24, 15, 35))

    assert summary["suppressed"] == 1
    refreshed = await db_session.get(AuroraScheduledWake, wake.id)
    assert refreshed.status == "suppressed"
    assert refreshed.suppression_reason == "dnd_window"


def test_build_aurora_surface_metadata_supports_modeling_complete_contract() -> None:
    metadata = build_aurora_surface_metadata(
        surface="aurora_modeling",
        surface_complete=True,
        modeling_complete=True,
    )

    assert metadata == {
        "aurora_surface": "aurora_modeling",
        "aurora_runtime_enabled": True,
        "surface_complete": True,
        "modeling_complete": True,
    }
