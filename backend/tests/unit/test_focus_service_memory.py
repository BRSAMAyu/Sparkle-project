from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.api.v1.plans import get_plan_progress
from app.models.focus import FocusSession, FocusStatus, FocusType
from app.models.galaxy import KnowledgeNode, UserNodeStatus
from app.models.plan import Plan, PlanType
from app.models.task import Task, TaskStatus, TaskType
from app.models.task_resources import TaskKnowledgeLink
from app.models.user import User
from app.services.focus_service import FocusService
from app.services.galaxy_service import GalaxyService


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@pytest.mark.asyncio
async def test_focus_service_writes_episodic_memory_for_completed_session(db_session, monkeypatch):
    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    db_session.add(user)
    await db_session.commit()

    publish = AsyncMock()
    collect = AsyncMock()
    create_memory = AsyncMock()

    monkeypatch.setattr("app.services.focus_service.event_bus.publish", publish)
    monkeypatch.setattr(
        "app.services.focus_service.AutoFragmentCollector.collect_from_focus_session",
        collect,
    )
    monkeypatch.setattr(
        "app.services.focus_service.MemoryService.create_episodic_memory",
        create_memory,
    )

    end_time = _utcnow()
    start_time = end_time - timedelta(minutes=30)

    result = await FocusService.log_session(
        db=db_session,
        user_id=user_id,
        task_id=None,
        start_time=start_time,
        end_time=end_time,
        duration_minutes=30,
    )

    assert result["session_id"]
    create_memory.assert_awaited_once()
    kwargs = create_memory.await_args.kwargs
    assert kwargs["user_id"] == user_id
    assert kwargs["source_type"] == "focus_session"
    assert "30 分钟专注" in kwargs["summary"]


@pytest.mark.asyncio
async def test_focus_session_boosts_linked_node_mastery(db_session, monkeypatch):
    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    node = KnowledgeNode(name="极限与连续", description="函数极限", importance_level=3)
    task = Task(
        user_id=user_id,
        title="复习极限定义",
        type=TaskType.LEARNING,
        tags=[],
        estimated_minutes=90,
        difficulty=2,
        energy_cost=2,
        status=TaskStatus.PENDING,
        priority=1,
        knowledge_node=node,
    )
    db_session.add_all([user, node, task])
    await db_session.flush()
    db_session.add(
        UserNodeStatus(
            user_id=user_id,
            node_id=node.id,
            mastery_score=42,
            bkt_mastery_prob=0.42,
            is_unlocked=True,
        )
    )
    db_session.add(
        TaskKnowledgeLink(
            task_id=task.id,
            knowledge_node_id=node.id,
            relation_type="primary",
            is_primary=True,
        )
    )
    await db_session.commit()

    async def fake_update_node_mastery(
        self,
        *,
        user_id,
        node_id,
        new_mastery,
        reason,
        version=None,
        request_id=None,
        revision=None,
    ):
        result = await self.db.execute(
            select(UserNodeStatus).where(
                UserNodeStatus.user_id == user_id,
                UserNodeStatus.node_id == node_id,
            )
        )
        status = result.scalar_one()
        old_mastery = status.mastery_score
        status.mastery_score = new_mastery
        status.bkt_mastery_prob = new_mastery / 100
        await self.db.flush()
        return {
            "success": True,
            "old_mastery": old_mastery,
            "new_mastery": new_mastery,
            "current_revision": 1,
        }

    monkeypatch.setattr(GalaxyService, "update_node_mastery", fake_update_node_mastery)
    monkeypatch.setattr("app.services.focus_service.event_bus.publish", AsyncMock())
    monkeypatch.setattr(
        "app.services.focus_service.AutoFragmentCollector.collect_from_focus_session",
        AsyncMock(),
    )
    monkeypatch.setattr(
        "app.services.focus_service.MemoryService.create_episodic_memory",
        AsyncMock(),
    )

    end_time = _utcnow()
    result = await FocusService.log_session(
        db=db_session,
        user_id=user_id,
        task_id=task.id,
        start_time=end_time - timedelta(minutes=55),
        end_time=end_time,
        duration_minutes=55,
    )

    assert result["mastery_updates"] == [
        {
            "node_id": str(node.id),
            "node_name": "极限与连续",
            "old_mastery": 42,
            "new_mastery": 48,
            "delta": 6,
            "reason": "focus_session",
        }
    ]

    refreshed = await db_session.get(UserNodeStatus, {"user_id": user_id, "node_id": node.id})
    assert refreshed.mastery_score == 48


@pytest.mark.asyncio
async def test_focus_session_without_linked_node_has_no_mastery_update(db_session, monkeypatch):
    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    task = Task(
        user_id=user_id,
        title="自由整理错题",
        type=TaskType.LEARNING,
        tags=[],
        estimated_minutes=25,
        difficulty=2,
        energy_cost=2,
        status=TaskStatus.PENDING,
        priority=1,
    )
    db_session.add_all([user, task])
    await db_session.commit()

    update_node_mastery = AsyncMock()
    monkeypatch.setattr(GalaxyService, "update_node_mastery", update_node_mastery)
    monkeypatch.setattr("app.services.focus_service.event_bus.publish", AsyncMock())
    monkeypatch.setattr(
        "app.services.focus_service.AutoFragmentCollector.collect_from_focus_session",
        AsyncMock(),
    )
    monkeypatch.setattr(
        "app.services.focus_service.MemoryService.create_episodic_memory",
        AsyncMock(),
    )

    end_time = _utcnow()
    result = await FocusService.log_session(
        db=db_session,
        user_id=user_id,
        task_id=task.id,
        start_time=end_time - timedelta(minutes=25),
        end_time=end_time,
        duration_minutes=25,
        status=FocusStatus.COMPLETED,
    )

    assert result["mastery_updates"] == []
    update_node_mastery.assert_not_awaited()


@pytest.mark.asyncio
async def test_focus_session_updates_task_progress_and_publishes_task_id(db_session, monkeypatch):
    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    plan = Plan(
        user_id=user_id,
        name="高数冲刺",
        type=PlanType.SPRINT,
        progress=0.0,
        mastery_level=0.0,
        daily_available_minutes=60,
    )
    task = Task(
        user_id=user_id,
        plan=plan,
        title="完成极限专题",
        type=TaskType.LEARNING,
        tags=[],
        estimated_minutes=50,
        difficulty=2,
        energy_cost=2,
        status=TaskStatus.PENDING,
        priority=1,
    )
    db_session.add_all([user, plan, task])
    await db_session.commit()

    publish = AsyncMock()
    monkeypatch.setattr("app.services.focus_service.event_bus.publish", publish)
    monkeypatch.setattr("app.services.task_service.event_bus_reliable.publish", AsyncMock())
    monkeypatch.setattr("app.services.task_service.publish_srl_event", AsyncMock())
    monkeypatch.setattr("app.services.task_service._sync_task_card_projection", AsyncMock())
    monkeypatch.setattr("app.services.plan_service._sync_plan_card_projection", AsyncMock())
    monkeypatch.setattr(
        "app.services.focus_service.AutoFragmentCollector.collect_from_focus_session",
        AsyncMock(),
    )
    monkeypatch.setattr(
        "app.services.focus_service.MemoryService.create_episodic_memory",
        AsyncMock(),
    )

    end_time = _utcnow()
    await FocusService.log_session(
        db=db_session,
        user_id=user_id,
        task_id=task.id,
        start_time=end_time - timedelta(minutes=25),
        end_time=end_time,
        duration_minutes=25,
    )
    await db_session.refresh(task)
    assert task.status == TaskStatus.IN_PROGRESS
    assert task.actual_minutes == 25

    end_time = _utcnow()
    await FocusService.log_session(
        db=db_session,
        user_id=user_id,
        task_id=task.id,
        start_time=end_time - timedelta(minutes=25),
        end_time=end_time,
        duration_minutes=25,
    )
    await db_session.refresh(task)
    assert task.status == TaskStatus.COMPLETED
    assert task.actual_minutes == 50
    assert task.completed_at is not None

    focus_events = [
        call.args[1] for call in publish.await_args_list if call.args and call.args[0] == "focus.session.completed"
    ]
    assert focus_events[-1]["task_id"] == str(task.id)
    assert focus_events[-1]["plan_id"] == str(plan.id)


@pytest.mark.asyncio
async def test_plan_progress_reports_completed_focus_minutes(db_session):
    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    plan = Plan(
        user_id=user_id,
        name="英语计划",
        type=PlanType.GROWTH,
        progress=0.0,
        mastery_level=0.0,
        daily_available_minutes=60,
    )
    task = Task(
        user_id=user_id,
        plan=plan,
        title="阅读训练",
        type=TaskType.LEARNING,
        tags=[],
        estimated_minutes=30,
        difficulty=2,
        energy_cost=2,
        status=TaskStatus.IN_PROGRESS,
        priority=1,
    )
    db_session.add_all([user, plan, task])
    await db_session.flush()

    end_time = _utcnow()
    db_session.add_all(
        [
            FocusSession(
                user_id=user_id,
                task_id=task.id,
                start_time=end_time - timedelta(minutes=25),
                end_time=end_time,
                duration_minutes=25,
                focus_type=FocusType.POMODORO,
                status=FocusStatus.COMPLETED,
            ),
            FocusSession(
                user_id=user_id,
                task_id=task.id,
                start_time=end_time - timedelta(minutes=5),
                end_time=end_time,
                duration_minutes=5,
                focus_type=FocusType.POMODORO,
                status=FocusStatus.INTERRUPTED,
            ),
        ]
    )
    await db_session.commit()

    progress = await get_plan_progress(plan_id=plan.id, current_user=user, db=db_session)

    assert progress["total_minutes_spent"] == 25
