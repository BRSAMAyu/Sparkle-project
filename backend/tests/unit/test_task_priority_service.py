from __future__ import annotations

from datetime import date, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core.cache import cache_service
from app.models.galaxy import KnowledgeNode, UserNodeStatus
from app.models.plan import Plan, PlanPriority, PlanStage, PlanType
from app.models.plan_state import PlanState, PlanStateStatus
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import User
from app.services.task_priority_service import TaskPriorityService


@pytest.fixture(autouse=True)
def _clear_priority_cache():
    cache_service._local_cache.clear()
    yield
    cache_service._local_cache.clear()


@pytest.fixture
def low_energy_aurora(monkeypatch):
    class _FakeAuroraStore:
        def __init__(self, redis):
            pass

        async def load_energy(self, user_id):
            return SimpleNamespace(
                current_level="L2",
                wake_score=0.82,
                is_cooling_down=False,
            )

    monkeypatch.setattr(
        "app.services.daily_task_selection_service.AuroraRuntimeStore",
        _FakeAuroraStore,
    )


async def _create_user(db_session) -> User:
    token = uuid4().hex[:8]
    user = User(
        username=f"priority_reasoning_{token}",
        email=f"priority_reasoning_{token}@example.com",
        hashed_password="hashed",
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def _create_plan(db_session, user: User) -> Plan:
    plan = Plan(
        user_id=user.id,
        name="Linear Algebra Sprint",
        type=PlanType.SPRINT,
        plan_stage=PlanStage.SPRINT,
        target_date=date.today() + timedelta(days=3),
        progress=0.6,
        priority=PlanPriority.HIGH,
        is_primary=True,
    )
    db_session.add(plan)
    await db_session.flush()
    state = PlanState(
        plan_id=plan.id,
        user_id=user.id,
        status=PlanStateStatus.ACTIVE.value,
        is_focus=True,
        parallel_priority=3,
    )
    db_session.add(state)
    await db_session.flush()
    return plan


async def _create_node(db_session, user: User) -> KnowledgeNode:
    node = KnowledgeNode(
        name="Matrix inverse",
        importance_level=4,
        source_type="seed",
    )
    db_session.add(node)
    await db_session.flush()
    status = UserNodeStatus(
        user_id=user.id,
        node_id=node.id,
        mastery_score=42,
        is_unlocked=True,
        next_review_at=datetime.utcnow() - timedelta(hours=2),
    )
    db_session.add(status)
    await db_session.flush()
    return node


async def _create_task(
    db_session,
    user: User,
    *,
    title: str = "Review inverse matrix mistakes",
    plan: Plan | None = None,
    node: KnowledgeNode | None = None,
    priority: int = 3,
    energy_cost: int = 2,
    difficulty: int = 2,
    due_date_value: date | None = None,
    task_type: TaskType = TaskType.LEARNING,
    tags: list[str] | None = None,
) -> Task:
    task = Task(
        user_id=user.id,
        plan_id=plan.id if plan else None,
        knowledge_node_id=node.id if node else None,
        title=title,
        type=task_type,
        tags=tags or ["priority-reasoning"],
        estimated_minutes=25,
        difficulty=difficulty,
        energy_cost=energy_cost,
        status=TaskStatus.PENDING,
        priority=priority,
        due_date=due_date_value or date.today(),
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    return task


@pytest.mark.asyncio
async def test_reasoning_contains_four_normalized_signal_types(db_session, low_energy_aurora):
    user = await _create_user(db_session)
    plan = await _create_plan(db_session, user)
    node = await _create_node(db_session, user)
    task = await _create_task(db_session, user, plan=plan, node=node)

    reasoning = await TaskPriorityService(db_session).generate_priority_reasoning(
        user_id=user.id,
        task_id=task.id,
    )

    assert {signal.type for signal in reasoning.supporting_signals} == {
        "spaced_repetition",
        "goal_progress",
        "energy_match",
        "social_context",
    }
    assert sum(signal.weight for signal in reasoning.supporting_signals) == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_due_knowledge_node_becomes_primary_reason(db_session, low_energy_aurora):
    user = await _create_user(db_session)
    node = await _create_node(db_session, user)
    task = await _create_task(db_session, user, node=node)

    reasoning = await TaskPriorityService(db_session).generate_priority_reasoning(
        user_id=user.id,
        task_id=task.id,
    )

    assert reasoning.primary_reason == "Matrix inverse is due for spaced repetition today."
    spaced_signal = next(signal for signal in reasoning.supporting_signals if signal.type == "spaced_repetition")
    assert "42%" in spaced_signal.detail


@pytest.mark.asyncio
async def test_goal_progress_detail_includes_plan_progress(db_session, low_energy_aurora):
    user = await _create_user(db_session)
    plan = await _create_plan(db_session, user)
    task = await _create_task(db_session, user, plan=plan)

    reasoning = await TaskPriorityService(db_session).generate_priority_reasoning(
        user_id=user.id,
        task_id=task.id,
    )

    goal_signal = next(signal for signal in reasoning.supporting_signals if signal.type == "goal_progress")
    assert "Linear Algebra Sprint is 60% complete" in goal_signal.detail
    assert "current focus plan" in goal_signal.detail


@pytest.mark.asyncio
async def test_energy_signal_uses_aurora_target_and_task_cost(db_session, low_energy_aurora):
    user = await _create_user(db_session)
    task = await _create_task(db_session, user, energy_cost=2, difficulty=2)

    reasoning = await TaskPriorityService(db_session).generate_priority_reasoning(
        user_id=user.id,
        task_id=task.id,
    )

    energy_signal = next(signal for signal in reasoning.supporting_signals if signal.type == "energy_match")
    assert "target effort 2/5" in energy_signal.detail
    assert "costs 2/5" in energy_signal.detail


@pytest.mark.asyncio
async def test_alternative_options_include_lower_ranked_tasks(db_session, low_energy_aurora):
    user = await _create_user(db_session)
    selected = await _create_task(db_session, user, priority=5, title="Selected task")
    alternative = await _create_task(
        db_session,
        user,
        priority=1,
        title="Lower ranked task",
        due_date_value=date.today() + timedelta(days=5),
    )

    reasoning = await TaskPriorityService(db_session).generate_priority_reasoning(
        user_id=user.id,
        task_id=selected.id,
    )

    assert reasoning.alternative_options_skipped
    assert reasoning.alternative_options_skipped[0].task_id == str(alternative.id)
    assert "lower than this task" in reasoning.alternative_options_skipped[0].reason


@pytest.mark.asyncio
async def test_cached_reasoning_is_invalidated_when_task_updated_at_changes(db_session, low_energy_aurora):
    user = await _create_user(db_session)
    task = await _create_task(db_session, user)
    service = TaskPriorityService(db_session)

    reasoning = await service.generate_and_cache(user_id=user.id, task_id=task.id)
    cached = await service.get_cached_reasoning(user_id=user.id, task=task)
    assert cached is not None
    assert cached["task_id"] == reasoning.task_id

    task.updated_at = datetime.utcnow() + timedelta(minutes=5)
    stale = await service.get_cached_reasoning(user_id=user.id, task=task)
    assert stale is None
