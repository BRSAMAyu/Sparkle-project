from __future__ import annotations

import json
from datetime import timezone, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.chat import ChatMessage, ChatSession, MessageRole
from app.models.plan import Plan, PlanType
from app.models.task import Task, TaskStatus, TaskType
from app.services.checkpoint_nudge_service import (
    CheckpointDebriefService,
    scan_and_send_checkpoint_nudges,
)


class _FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, object] = {}

    async def get(self, key: str):
        return self.values.get(key)

    async def setex(self, key: str, ttl: int, value: object) -> None:
        self.values[key] = value

    async def delete(self, key: str) -> None:
        self.values.pop(key, None)


@pytest.mark.asyncio
async def test_checkpoint_scan_writes_nudge_once(db_session, test_user) -> None:
    user_id = test_user.id
    session = ChatSession(id=uuid4(), user_id=user_id, is_active=True, last_message_at=datetime.utcnow())
    created_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1)
    plan = Plan(
        id=uuid4(),
        user_id=user_id,
        name="7天计网冲刺",
        type=PlanType.SPRINT,
        description=json.dumps(
            {"strategy": {"checkpoints": [{"day": 2, "description": "Day 2 晚：做20题自测"}]}},
            ensure_ascii=False,
        ),
        subject="计算机网络",
        is_active=True,
        created_at=created_at,
    )
    db_session.add_all([session, plan])
    await db_session.commit()

    redis = _FakeRedis()
    today = (created_at.replace(tzinfo=timezone.utc) + timedelta(hours=8)).date() + timedelta(days=1)
    first = await scan_and_send_checkpoint_nudges(db=db_session, redis=redis, today=today)
    second = await scan_and_send_checkpoint_nudges(db=db_session, redis=redis, today=today)

    assert first["triggered"] == 1
    assert second["triggered"] == 0
    assert second["skipped_duplicate"] == 1
    key = f"checkpoint:triggered:{plan.id}:2"
    assert redis.values[key] == "1"

    rows = await db_session.execute(
        select(ChatMessage).where(ChatMessage.session_id == session.id, ChatMessage.role == MessageRole.ASSISTANT)
    )
    messages = list(rows.scalars().all())
    assert len(messages) == 1
    assert "第 2 天" in messages[0].content
    assert messages[0].actions[0]["type"] == "aurora_nudge_entry"


@pytest.mark.asyncio
async def test_checkpoint_debrief_inserts_remedial_when_behind(db_session, test_user) -> None:
    user_id = test_user.id
    session_id = uuid4()
    plan_id = uuid4()
    plan = Plan(id=plan_id, user_id=user_id, name="7天计网冲刺", type=PlanType.SPRINT, is_active=True)
    next_task = Task(
        user_id=user_id,
        plan_id=plan_id,
        title="Day 4 · 核心攻克",
        type=TaskType.LEARNING,
        tags=[],
        estimated_minutes=60,
        difficulty=3,
        energy_cost=2,
        status=TaskStatus.PENDING,
        order_index=1000,
        phase_index=2,
    )
    db_session.add_all([plan, next_task])
    await db_session.commit()

    redis = _FakeRedis()
    service = CheckpointDebriefService(db_session, redis)
    start = await service.process_turn(
        user_id=user_id,
        chat_session_id=session_id,
        user_message="我来复盘一下",
        context={
            "debrief_context": {
                "nudge_id": f"cp:{plan_id}:2",
                "plan_id": str(plan_id),
                "checkpoint_day": 2,
                "checkpoint_description": "Day 2 晚：做20题自测",
            }
        },
    )
    second = await service.process_turn(
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

    assert start["message"] == "这个检查点的情况怎么样？"
    assert second["message"] == "卡在哪里了，是理解问题还是时间问题？"
    assert final["finished"] is True
    rows = await db_session.execute(select(Task).where(Task.user_id == user_id, Task.plan_id == plan_id))
    tasks = list(rows.scalars().all())
    remedials = [task for task in tasks if task.title.startswith("[复盘补强]")]
    assert len(remedials) == 1
    assert remedials[0].estimated_minutes == 25
    assert remedials[0].order_index == 1000
    assert "reduced_density" in (remedials[0].tags or [])
    assert "time_boxed" in (remedials[0].tags or [])
    assert remedials[0].guide_json["sprint_fail_safe"] is True
    assert remedials[0].guide_json["density_adjustment"] == "minimum_viable"
    assert remedials[0].guide_json["scaffolding_mode"] == "checkpoint_time_boxed_recovery"


@pytest.mark.asyncio
async def test_checkpoint_debrief_does_not_adjust_when_progress_good(db_session, test_user) -> None:
    user_id = test_user.id
    session_id = uuid4()
    plan_id = uuid4()
    plan = Plan(id=plan_id, user_id=user_id, name="7天计网冲刺", type=PlanType.SPRINT, is_active=True)
    db_session.add(plan)
    await db_session.commit()

    service = CheckpointDebriefService(db_session, _FakeRedis())
    await service.process_turn(
        user_id=user_id,
        chat_session_id=session_id,
        user_message="我来复盘一下",
        context={"debrief_context": {"nudge_id": f"cp:{plan_id}:2", "plan_id": str(plan_id), "checkpoint_day": 2}},
    )
    await service.process_turn(user_id=user_id, chat_session_id=session_id, user_message="进展不错", context={})
    final = await service.process_turn(
        user_id=user_id, chat_session_id=session_id, user_message="框架部分最踏实", context={}
    )

    assert final["goal_met"] is True
    rows = await db_session.execute(select(Task).where(Task.user_id == user_id, Task.plan_id == plan_id))
    assert [task for task in rows.scalars().all() if task.title.startswith("[复盘补强]")] == []
