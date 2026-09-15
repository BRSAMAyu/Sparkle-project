from __future__ import annotations

import json
from datetime import timezone, datetime
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from app.models.task import Task, TaskStatus, TaskType
from app.services.personalization.preference_service import PreferenceService
from app.services.task_feedback_service import TaskFeedbackService


class _FakeRedis:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    async def get(self, key: str) -> str | None:
        return json.dumps(self.payload, ensure_ascii=False)


@pytest.mark.asyncio
async def test_task_feedback_service_updates_routing_profile_after_execution_first_struggle(
    db_session,
    test_user,
    monkeypatch,
) -> None:
    user_id = test_user.id
    task = Task(
        user_id=user_id,
        plan_id=uuid4(),
        title="热力学练习",
        type=TaskType.LEARNING,
        tags=[],
        estimated_minutes=30,
        difficulty=3,
        energy_cost=2,
        status=TaskStatus.COMPLETED,
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    task_id = task.id

    replanner_calls = AsyncMock(return_value=[])
    reflection_calls = AsyncMock(return_value=None)
    routing_calls = AsyncMock(
        return_value={
            "procrastination_threshold": 0.57,
            "emotional_sensitivity": 0.5,
            "directness_preference": 0.5,
        }
    )
    event_publish = AsyncMock(return_value=None)

    class _FakeAdaptiveReplanner:
        def __init__(self, db, redis):
            self.on_task_feedback = replanner_calls

        @staticmethod
        def is_strong_cognitive_struggle_feedback(*, category, feedback_text) -> bool:
            return category in {"unclear", "too_difficult"} or "不懂" in str(feedback_text or "")

        @staticmethod
        def is_strong_cognitive_struggle_feedback(*, category, feedback_text) -> bool:
            return category == "unclear" or "不理解" in str(feedback_text or "")

    monkeypatch.setattr(
        "app.services.task_feedback_service.AdaptiveReplanner",
        _FakeAdaptiveReplanner,
    )
    monkeypatch.setattr(
        "app.services.task_feedback_service.TaskReflectionService",
        lambda db, redis: SimpleNamespace(maybe_enqueue_reflection_prompt=reflection_calls),
    )
    monkeypatch.setattr(
        "app.services.task_feedback_service.RoutingProfileService",
        lambda db, redis: SimpleNamespace(record_session_outcome=routing_calls),
    )
    monkeypatch.setattr("app.services.task_feedback_service.event_bus.publish", event_publish)

    service = TaskFeedbackService(
        db_session,
        redis=_FakeRedis(
            {
                "mode": "execution_first",
                "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            }
        ),
    )

    feedback, reflection_prompt = await service.submit_feedback(
        user_id=user_id,
        task_id=task_id,
        feedback_text="我还是不理解这部分概念",
        category="unclear",
    )

    assert reflection_prompt is None
    assert feedback.category == "unclear"
    assert feedback.feedback_text == "我还是不理解这部分概念"
    replanner_kwargs = replanner_calls.await_args.kwargs
    assert replanner_kwargs["feedback_text"] == "我还是不理解这部分概念"
    assert replanner_kwargs["category"] == "unclear"
    routing_kwargs = routing_calls.await_args.kwargs
    assert routing_kwargs["route_mode"] == "execution_first"
    assert routing_kwargs["execution_suggestion_ignored"] is True


@pytest.mark.asyncio
async def test_task_feedback_inserts_remedial_task_and_records_knowledge_gap(
    db_session,
    test_user,
    monkeypatch,
) -> None:
    user_id = test_user.id
    plan_id = uuid4()
    task = Task(
        user_id=user_id,
        plan_id=plan_id,
        title="Day 3 · 核心攻克",
        type=TaskType.LEARNING,
        tags=["规划生成", "phase:2"],
        estimated_minutes=60,
        difficulty=3,
        energy_cost=2,
        status=TaskStatus.COMPLETED,
        order_index=1000,
        guide_json={"objective": "理解 TCP 三次握手"},
        source_planning_session_id="planning-session-1",
        phase_index=2,
    )
    next_task = Task(
        user_id=user_id,
        plan_id=plan_id,
        title="Day 4 · 核心攻克",
        type=TaskType.LEARNING,
        tags=["规划生成", "phase:2"],
        estimated_minutes=60,
        difficulty=3,
        energy_cost=2,
        status=TaskStatus.PENDING,
        order_index=2000,
    )
    db_session.add_all([task, next_task])
    await db_session.commit()
    await db_session.refresh(task)
    await db_session.refresh(next_task)
    task_id = task.id
    task_phase_index = task.phase_index

    replanner_calls = AsyncMock(return_value=[])
    reflection_calls = AsyncMock(return_value=None)
    routing_calls = AsyncMock(return_value={})
    event_publish = AsyncMock(return_value=None)

    class _FakeAdaptiveReplanner:
        def __init__(self, db, redis):
            self.on_task_feedback = replanner_calls

        @staticmethod
        def is_strong_cognitive_struggle_feedback(*, category, feedback_text) -> bool:
            return category in {"unclear", "too_difficult"} or "不懂" in str(feedback_text or "")

    monkeypatch.setattr("app.services.task_feedback_service.AdaptiveReplanner", _FakeAdaptiveReplanner)
    monkeypatch.setattr(
        "app.services.task_feedback_service.TaskReflectionService",
        lambda db, redis: SimpleNamespace(maybe_enqueue_reflection_prompt=reflection_calls),
    )
    monkeypatch.setattr(
        "app.services.task_feedback_service.RoutingProfileService",
        lambda db, redis: SimpleNamespace(record_session_outcome=routing_calls),
    )
    monkeypatch.setattr("app.services.task_feedback_service.event_bus.publish", event_publish)

    service = TaskFeedbackService(db_session, redis=None)
    feedback, _ = await service.submit_feedback(
        user_id=user_id,
        task_id=task_id,
        feedback_text="TCP 三次握手这里我还是看不懂",
        category="too_difficult",
    )

    prefs = await PreferenceService(db_session).get_preferences(user_id)
    gaps = prefs.explicit.get("knowledge_gaps")
    assert feedback.category == "too_difficult"
    assert isinstance(gaps, list)
    assert gaps[-1]["task_id"] == str(task_id)
    assert "TCP 三次握手" in gaps[-1]["description"]

    rows = await db_session.execute(
        select(Task).where(Task.user_id == user_id, Task.plan_id == plan_id).order_by(Task.order_index.asc())
    )
    tasks = list(rows.scalars().all())
    remedial = [item for item in tasks if item.title.startswith("[补强]")]
    assert len(remedial) == 1
    assert remedial[0].estimated_minutes <= 30
    assert remedial[0].guide_json is not None
    assert remedial[0].ai_prompt
    assert "reduced_density" in (remedial[0].tags or [])
    assert remedial[0].guide_json["sprint_fail_safe"] is True
    assert remedial[0].guide_json["density_adjustment"] == "reduced"
    assert remedial[0].guide_json["output_action"] == "补清 1 个卡点，并完成 1 个最小检查题。"
    assert "只处理 1 个卡点" in remedial[0].guide_json["micro_contract"]
    current_task_index = next(index for index, item in enumerate(tasks) if item.id == task_id)
    assert tasks.index(remedial[0]) == current_task_index + 1
    assert remedial[0].phase_index == task_phase_index


@pytest.mark.asyncio
async def test_task_feedback_time_pressure_inserts_time_boxed_fail_safe_task(
    db_session,
    test_user,
    monkeypatch,
) -> None:
    user_id = test_user.id
    plan_id = uuid4()
    task = Task(
        user_id=user_id,
        plan_id=plan_id,
        title="Day 5 · 阶段练习",
        type=TaskType.LEARNING,
        tags=["规划生成", "phase:2"],
        estimated_minutes=60,
        difficulty=3,
        energy_cost=2,
        status=TaskStatus.COMPLETED,
        order_index=1000,
    )
    next_task = Task(
        user_id=user_id,
        plan_id=plan_id,
        title="Day 6 · 阶段练习",
        type=TaskType.LEARNING,
        tags=["规划生成", "phase:2"],
        estimated_minutes=60,
        difficulty=3,
        energy_cost=2,
        status=TaskStatus.PENDING,
        order_index=2000,
    )
    db_session.add_all([task, next_task])
    await db_session.commit()
    await db_session.refresh(task)

    class _FakeAdaptiveReplanner:
        def __init__(self, db, redis):
            self.on_task_feedback = AsyncMock(return_value=[])

        @staticmethod
        def is_strong_cognitive_struggle_feedback(*, category, feedback_text) -> bool:
            return category in {"unclear", "too_difficult"} or "不懂" in str(feedback_text or "")

    monkeypatch.setattr("app.services.task_feedback_service.AdaptiveReplanner", _FakeAdaptiveReplanner)
    monkeypatch.setattr(
        "app.services.task_feedback_service.TaskReflectionService",
        lambda db, redis: SimpleNamespace(maybe_enqueue_reflection_prompt=AsyncMock(return_value=None)),
    )
    monkeypatch.setattr(
        "app.services.task_feedback_service.RoutingProfileService",
        lambda db, redis: SimpleNamespace(record_session_outcome=AsyncMock(return_value={})),
    )
    monkeypatch.setattr("app.services.task_feedback_service.event_bus.publish", AsyncMock(return_value=None))

    service = TaskFeedbackService(db_session, redis=None)
    await service.submit_feedback(
        user_id=user_id,
        task_id=task.id,
        feedback_text="今天没时间，这个任务太长了，根本做不完",
        category="too_long",
    )

    rows = await db_session.execute(
        select(Task).where(Task.user_id == user_id, Task.plan_id == plan_id).order_by(Task.order_index.asc())
    )
    tasks = list(rows.scalars().all())
    remedial = next(item for item in tasks if item.title.startswith("[补强]"))
    assert remedial.estimated_minutes <= 25
    assert "time_boxed" in (remedial.tags or [])
    assert remedial.guide_json["density_adjustment"] == "minimum_viable"
    assert remedial.guide_json["scaffolding_mode"] == "time_boxed_minimum_viable"
    assert "最小保底产出" in remedial.guide_json["output_action"]
    assert "时间压缩版保底任务" in remedial.ai_prompt


@pytest.mark.asyncio
async def test_task_feedback_caps_consecutive_remedial_tasks(
    db_session,
    test_user,
    monkeypatch,
) -> None:
    user_id = test_user.id
    plan_id = uuid4()
    task = Task(
        user_id=user_id,
        plan_id=plan_id,
        title="Day 3 · 核心攻克",
        type=TaskType.LEARNING,
        tags=["规划生成", "phase:2"],
        estimated_minutes=60,
        difficulty=3,
        energy_cost=2,
        status=TaskStatus.COMPLETED,
        order_index=1000,
    )
    remedial_one = Task(
        user_id=user_id,
        plan_id=plan_id,
        title="[补强] 第一次补强",
        type=TaskType.LEARNING,
        tags=["remedial"],
        estimated_minutes=20,
        difficulty=2,
        energy_cost=1,
        status=TaskStatus.PENDING,
        order_index=1001,
    )
    remedial_two = Task(
        user_id=user_id,
        plan_id=plan_id,
        title="[补强] 第二次补强",
        type=TaskType.LEARNING,
        tags=["remedial"],
        estimated_minutes=20,
        difficulty=2,
        energy_cost=1,
        status=TaskStatus.PENDING,
        order_index=1002,
    )
    db_session.add_all([task, remedial_one, remedial_two])
    await db_session.commit()
    await db_session.refresh(task)
    task_id = task.id

    class _FakeAdaptiveReplanner:
        def __init__(self, db, redis):
            self.on_task_feedback = AsyncMock(return_value=[])

        @staticmethod
        def is_strong_cognitive_struggle_feedback(*, category, feedback_text) -> bool:
            return category in {"unclear", "too_difficult"} or "不懂" in str(feedback_text or "")

    monkeypatch.setattr("app.services.task_feedback_service.AdaptiveReplanner", _FakeAdaptiveReplanner)
    monkeypatch.setattr(
        "app.services.task_feedback_service.TaskReflectionService",
        lambda db, redis: SimpleNamespace(maybe_enqueue_reflection_prompt=AsyncMock(return_value=None)),
    )
    monkeypatch.setattr(
        "app.services.task_feedback_service.RoutingProfileService",
        lambda db, redis: SimpleNamespace(record_session_outcome=AsyncMock(return_value={})),
    )
    monkeypatch.setattr("app.services.task_feedback_service.event_bus.publish", AsyncMock(return_value=None))

    service = TaskFeedbackService(db_session, redis=None)
    await service.submit_feedback(
        user_id=user_id,
        task_id=task_id,
        feedback_text="这里不会",
        category="unclear",
    )

    rows = await db_session.execute(select(Task).where(Task.user_id == user_id, Task.plan_id == plan_id))
    remedials = [item for item in rows.scalars().all() if item.title.startswith("[补强]")]
    assert len(remedials) == 2
