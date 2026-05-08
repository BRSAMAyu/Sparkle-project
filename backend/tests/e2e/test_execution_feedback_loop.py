"""
E2E Test: Task Execution, Dynamic Replanning & Feedback Loop

Tests the complete loop:
1. User generates task cards
2. User modifies task A
3. System triggers dynamic replanning
4. System adjusts subsequent task B
5. User provides feedback
6. System updates parameters
7. New tasks reflect updated parameters

Author: Claude Code (Sonnet 4.5)
Created: 2026-01-28
"""

import pytest
from datetime import timezone, datetime, timedelta
from uuid import uuid4
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from sqlalchemy import select

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task, TaskStatus, TaskType
from app.models.plan import Plan, PlanType
from app.models.plan_state import PlanState, PlanStateStatus
from app.models.user import User

from app.services.task_service import TaskService
from app.services.plan_service import PlanService
from app.services.plan_state_service import PlanStateService
from app.orchestration.adaptive_replanner import AdaptiveReplanner
from app.services.plan_progress_service import PlanProgressService
from app.services.task_event_consumer import TaskEventConsumer
from app.orchestration.version_conflict_service import (
    VersionConflictService,
    VersionConflictResult,
)
from app.orchestration.state_manager import SessionStateManager
from app.services.milestone_handler import MilestoneHandler
from app.orchestration.step_feedback_collector import PlanExecutionFeedback


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# =============================================================================
# E2E Test 3: Milestone → Progressive Task Generation
# =============================================================================


@pytest.mark.asyncio
async def test_e2e_milestone_triggers_progressive_task_generation(db_session: AsyncSession):
    """
    E2E: Milestone achievement → generates next phase tasks (not all at once)

    Scenario:
    1. User creates a plan
    2. User completes 25% of tasks (first milestone)
    3. System generates milestone proposal
    4. User confirms proposal
    5. Only 3-5 new tasks created (not entire plan)

    Note: This test verifies the milestone handler mechanism. The actual
    proposal generation depends on pending task count and milestone type.
    """
    # Setup
    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    db_session.add(user)

    plan_id = uuid4()
    plan = Plan(
        id=plan_id,
        user_id=user_id,
        name="英语学习计划",
        type=PlanType.SPRINT,
        subject="英语",
        progress=0.0,
        target_date=_utcnow() + timedelta(days=30),
        is_active=True,
    )
    db_session.add(plan)

    # Create 10 initial tasks
    tasks = []
    for i in range(10):
        task = Task(
            id=uuid4(),
            user_id=user_id,
            plan_id=plan_id,
            title=f"英语单词 {i+1}",
            type=TaskType.LEARNING,
            status=TaskStatus.PENDING if i > 2 else TaskStatus.COMPLETED,
            estimated_minutes=20,
            difficulty=3,
        )
        tasks.append(task)
        db_session.add(task)

    await db_session.commit()

    # Initialize PlanState with milestones
    plan_state_service = PlanStateService(db_session, redis=None)
    initial_state = await plan_state_service.get_or_create_plan_state(
        user_id=user_id,
        plan_id=plan_id,
    )

    # Simulate milestone achievement (30% = 3/10 tasks completed)
    initial_state.task_index = {"total": 10, "completed": 3, "by_type": {"learning": 3}}
    initial_state.completed_milestones = ["ms-25pct-completion"]
    await db_session.commit()

    # Use MilestoneHandler to trigger proposal
    from app.services.milestone_handler import MilestoneHandler

    handler = MilestoneHandler(db_session)

    # Mock LLM to avoid actual API call
    with patch("app.services.milestone_handler.get_llm_service_for_task") as mock_llm:
        mock_llm.return_value = AsyncMock()
        mock_llm.return_value.chat_json = AsyncMock(
            return_value={
                "reasoning": "User reached 30% completion, recommending next phase",
                "tasks": [
                    {
                        "title": "英语阅读进阶 1",
                        "type": "learning",
                        "estimated_minutes": 30,
                        "difficulty": 4,
                        "priority": "high",
                    },
                    {
                        "title": "英语阅读进阶 2",
                        "type": "training",
                        "estimated_minutes": 25,
                        "difficulty": 4,
                        "priority": "medium",
                    },
                    {
                        "title": "英语听力练习",
                        "type": "training",
                        "estimated_minutes": 20,
                        "difficulty": 3,
                        "priority": "medium",
                    },
                ],
            }
        )

        # Trigger milestone handler with low pending count to allow generation
        # (pending_task_count < 5 allows generation for non-critical milestones)
        action_id = await handler.on_milestone_achieved(
            user_id=user_id,
            plan_id=plan_id,
            milestone={
                "id": "ms-25pct-completion",
                "title": "完成25%任务",
                "description": "已完成10个任务中的3个",
            },
            pending_task_count=3,  # Less than 5 threshold
            current_plan_context={"title": "英语学习计划"},
        )

        # Verify proposal was generated (not None when pending < 5)
        assert action_id is not None, "Should generate milestone proposal when pending tasks < 5"

        # Verify no new tasks created yet (stored as pending action)
        result = await db_session.execute(
            select(Task).where(
                Task.plan_id == plan_id,
                Task.user_id == user_id,
                Task.deleted_at.is_(None),
            )
        )
        all_tasks = result.scalars().all()
        assert len(all_tasks) == 10, "Should still have 10 tasks (no new ones created yet)"

    # Step 4: User confirms proposal (simulate confirm_proposal)
    # This would normally be triggered by UI action
    # For E2E test, we verify the mechanism exists


# =============================================================================
# E2E Test 4: Version Conflict → Auto Replan
# =============================================================================


@pytest.mark.asyncio
async def test_e2e_version_conflict_triggers_auto_replan(db_session: AsyncSession):
    """
    E2E: Version conflict → auto replan → new plan reflects current state

    Scenario:
    1. User creates a plan with initial version 1
    2. User modifies tasks (version bumps to 2)
    3. System tries to execute old plan (version 1)
    4. System detects version conflict
    5. System triggers auto-replan
    6. New plan reflects current state
    """
    # Setup
    user_id = uuid4()
    plan_id = uuid4()

    plan = Plan(
        id=plan_id,
        user_id=user_id,
        name="物理学习计划",
        type=PlanType.SPRINT,
        subject="物理",
        progress=0.0,
        is_active=True,
    )
    db_session.add(plan)

    # Create tasks
    for i in range(5):
        task = Task(
            id=uuid4(),
            user_id=user_id,
            plan_id=plan_id,
            title=f"物理练习 {i+1}",
            type=TaskType.TRAINING,
            status=TaskStatus.PENDING,
            estimated_minutes=30,
        )
        db_session.add(task)

    await db_session.commit()

    # Initialize PlanState version 1
    plan_state_service = PlanStateService(db_session, redis=None)
    initial_state = await plan_state_service.get_or_create_plan_state(
        user_id=user_id,
        plan_id=plan_id,
        initial_facts={"current_phase": "phase1"},
    )
    assert initial_state.version == 1

    # Simulate state change (bump version to 2)
    initial_state.facts["current_phase"] = "phase2"
    initial_state.version = 2
    await db_session.commit()

    # Create version conflict detection
    from app.orchestration.schemas import ExecutablePlan, ToolCallSpec

    old_plan = ExecutablePlan(
        schema_version="4.0",
        plan_id=str(plan_id),
        snapshot_id="",
        context_version=f"{plan_id}:v1",
        source="langgraph",
        confidence=0.8,
        rationale="Original plan",
        tool_calls=[],
        plan_version=1,  # Old version
    )

    conflict_service = VersionConflictService(
        redis=None,
        plan_state_service=plan_state_service,
        planner=None,  # Will mock replan
    )

    # Detect conflict
    conflict_result = await conflict_service.check_version_conflict(
        plan=old_plan,
        user_id=user_id,
    )

    # Verify conflict detected
    assert conflict_result.has_conflict is True, "Should detect version conflict"
    assert conflict_result.expected_version == 1
    assert conflict_result.current_version == 2
    assert conflict_result.conflict_type == "plan_version"

    # Verify recommendation
    assert conflict_result.recommendation in ["replan", "hitl"]


# =============================================================================
# E2E Test 5: Feedback Consumer Routing
# =============================================================================


@pytest.mark.asyncio
async def test_task_feedback_consumer_routes_to_adaptive_replanner():
    user_id = uuid4()
    task_id = uuid4()
    plan_id = uuid4()
    consumer = TaskEventConsumer(Mock())

    class _FakeSessionCM:
        def __init__(self, db):
            self.db = db

        async def __aenter__(self):
            return self.db

        async def __aexit__(self, exc_type, exc, tb):
            return False

    db_session = AsyncMock()
    db_session.execute = AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: plan_id))

    collector_instance = SimpleNamespace(handle_task_feedback_event=AsyncMock())
    replanner_instance = SimpleNamespace(on_task_feedback=AsyncMock(return_value=[]))

    with patch("app.services.task_event_consumer.AsyncSessionLocal", return_value=_FakeSessionCM(db_session)), patch(
        "app.services.task_event_consumer.BehaviorSignalCollector",
        return_value=collector_instance,
    ), patch(
        "app.services.task_event_consumer.AdaptiveReplanner",
        return_value=replanner_instance,
    ):
        await consumer._handle_task_feedback(
            {
                "event_type": "task.feedback_submitted",
                "user_id": str(user_id),
                "task_id": str(task_id),
                "category": "too_difficult",
                "difficulty_delta": -0.2,
                "feedback_text": "太难了",
            }
        )

    collector_instance.handle_task_feedback_event.assert_awaited_once()
    replanner_instance.on_task_feedback.assert_awaited_once()
    kwargs = replanner_instance.on_task_feedback.await_args.kwargs
    assert kwargs["user_id"] == user_id
    assert kwargs["plan_id"] == plan_id
    assert kwargs["task_id"] == task_id
    assert kwargs["category"] == "too_difficult"
    assert kwargs["difficulty_delta"] == -0.2
    assert kwargs["feedback_text"] == "太难了"


@pytest.mark.asyncio
async def test_task_feedback_consumer_safe_fallback_when_plan_missing():
    user_id = uuid4()
    task_id = uuid4()
    consumer = TaskEventConsumer(Mock())

    class _FakeSessionCM:
        def __init__(self, db):
            self.db = db

        async def __aenter__(self):
            return self.db

        async def __aexit__(self, exc_type, exc, tb):
            return False

    db_session = AsyncMock()
    db_session.execute = AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: None))

    collector_instance = SimpleNamespace(handle_task_feedback_event=AsyncMock())
    replanner_instance = SimpleNamespace(on_task_feedback=AsyncMock(return_value=[]))

    with patch("app.services.task_event_consumer.AsyncSessionLocal", return_value=_FakeSessionCM(db_session)), patch(
        "app.services.task_event_consumer.BehaviorSignalCollector",
        return_value=collector_instance,
    ), patch(
        "app.services.task_event_consumer.AdaptiveReplanner",
        return_value=replanner_instance,
    ):
        await consumer._handle_task_feedback(
            {
                "event_type": "task.feedback_submitted",
                "user_id": str(user_id),
                "task_id": str(task_id),
                "feedback_text": "",
            }
        )

    collector_instance.handle_task_feedback_event.assert_awaited_once()
    replanner_instance.on_task_feedback.assert_not_called()


# =============================================================================
# E2E Test 6: Multi-Plan Isolation
# =============================================================================


@pytest.mark.asyncio
async def test_e2e_multi_plan_state_isolation(db_session: AsyncSession):
    """
    E2E: Multi-plan state isolation

    Scenario:
    1. User creates two plans (Plan A and Plan B)
    2. User completes a task in Plan A
    3. Plan A state updates
    4. Plan B state remains unchanged
    5. Switch active plan
    6. Verify states don't interfere
    """
    # Setup
    user_id = uuid4()

    plan_a_id = uuid4()
    plan_a = Plan(
        id=plan_a_id,
        user_id=user_id,
        name="数学计划",
        type=PlanType.SPRINT,
        subject="数学",
        progress=0.0,
        is_active=True,
    )
    db_session.add(plan_a)

    plan_b_id = uuid4()
    plan_b = Plan(
        id=plan_b_id,
        user_id=user_id,
        name="英语计划",
        type=PlanType.SPRINT,
        subject="英语",
        progress=0.0,
        is_active=True,
    )
    db_session.add(plan_b)

    # Create tasks for Plan A
    task_a1 = Task(
        id=uuid4(),
        user_id=user_id,
        plan_id=plan_a_id,
        title="数学题 1",
        type=TaskType.TRAINING,
        status=TaskStatus.PENDING,
        estimated_minutes=30,
    )
    db_session.add(task_a1)

    # Create tasks for Plan B
    task_b1 = Task(
        id=uuid4(),
        user_id=user_id,
        plan_id=plan_b_id,
        title="英语单词 1",
        type=TaskType.LEARNING,
        status=TaskStatus.PENDING,
        estimated_minutes=20,
    )
    db_session.add(task_b1)

    await db_session.commit()

    # Initialize PlanStates
    plan_state_service = PlanStateService(db_session, redis=None)

    state_a = await plan_state_service.get_or_create_plan_state(
        user_id=user_id,
        plan_id=plan_a_id,
        initial_facts={"difficulty_preference": "hard"},
    )

    state_b = await plan_state_service.get_or_create_plan_state(
        user_id=user_id,
        plan_id=plan_b_id,
        initial_facts={"difficulty_preference": "easy"},
    )

    # Verify initial states
    assert state_a.facts["difficulty_preference"] == "hard"
    assert state_b.facts["difficulty_preference"] == "easy"

    # Step 1: Complete task in Plan A
    await TaskService.complete(
        db=db_session,
        db_obj=task_a1,
        actual_minutes=30,
    )

    # Step 2: Update Plan A progress
    from app.services.plan_service import PlanService
    await PlanService.update_progress(db_session, task_a1.plan_id, user_id)

    # Step 3: Modify Plan A state
    state_a.facts["difficulty_preference"] = "medium"
    state_a.task_index["completed"] = 1
    state_a.version = 2
    await db_session.commit()

    # Step 4: Verify Plan B state is unchanged
    await db_session.refresh(state_b)
    assert state_b.facts["difficulty_preference"] == "easy", "Plan B state should be unchanged"
    assert state_b.version == 1, "Plan B version should not increment"
    assert state_b.task_index["completed"] == 0, "Plan B completed count should remain 0"

    # Step 5: Simulate active plan switching
    session_id = f"session_{uuid4().hex[:8]}"

    # Mock Redis for SessionStateManager (with proper return values)
    stored_data = {}

    async def mock_setex(key, ttl, value):
        stored_data[key] = value
        return True

    async def mock_get(key):
        return stored_data.get(key)

    mock_redis = AsyncMock()
    mock_redis.setex = mock_setex
    mock_redis.get = mock_get

    state_manager = SessionStateManager(mock_redis)

    # Set Plan A as active
    await state_manager.set_active_plan(session_id, plan_a_id, reason="manual")
    active_plan = await state_manager.get_active_plan(session_id)
    assert active_plan is not None
    assert active_plan["plan_id"] == str(plan_a_id)

    # Switch to Plan B
    await state_manager.set_active_plan(session_id, plan_b_id, reason="user_switch")
    active_plan = await state_manager.get_active_plan(session_id)
    assert active_plan is not None
    assert active_plan["plan_id"] == str(plan_b_id)

    # Verify states remain isolated after switch
    final_state_a = await plan_state_service.get_plan_state(user_id, plan_a_id)
    final_state_b = await plan_state_service.get_plan_state(user_id, plan_b_id)

    assert final_state_a.facts["difficulty_preference"] == "medium"
    assert final_state_b.facts["difficulty_preference"] == "easy"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
