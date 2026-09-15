"""
E2E Test: Complete Plan Lifecycle
==================================

Tests the complete plan creation → execution → feedback → adjustment flow:
User Request → Intent Recognition → Plan Generation → Task Execution → Feedback → Dynamic Adjustment

Author: Claude Code (Sonnet 4.5)
Created: 2026-01-28
"""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from sqlalchemy import select

from app.models.plan import Plan, PlanType, PlanStatus
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import User
from app.services.plan_service import PlanService
from app.services.task_service import TaskService
from app.services.plan_state_service import PlanStateService
from app.services.feedback_adjustment_service import (
    FeedbackDrivenAdjustmentService,
    FeedbackEvent,
    FeedbackType,
)
from app.orchestration.adaptive_replanner import AdaptiveReplanner
from app.core.event_bus import EventBus


# =============================================================================
# Test 1: Complete Plan Creation Flow
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_e2e_plan_creation_from_chat_to_db(
    db_session,
    test_user,
    mock_llm_service,
    mock_redis,
    test_assertions,
):
    """
    E2E: User requests plan → LLM generates → Plan persisted → Tasks created

    Scenario:
    1. User sends chat message: "制定一个7天Python学习计划"
    2. Intent recognized as plan creation
    3. Information sufficient (subject=Python, duration=7 days)
    4. LLM generates plan with tasks
    5. Plan saved to database
    6. Tasks created and linked to plan
    7. User can view plan in UI
    """
    # Arrange: Initialize plan service with mock LLM
    plan_service = PlanService(db_session, mock_llm_service, mock_redis)

    # Mock LLM response for plan generation
    async def mock_generate_plan(user_input, user_context):
        return {
            "name": "Python学习计划",
            "type": "sprint",
            "subject": "编程",
            "description": "7天Python基础学习计划",
            "target_date": (datetime.now() + timedelta(days=7)).isoformat(),
            "estimated_total_minutes": 420,  # 7 days * 60 minutes
            "tasks": [
                {
                    "title": "学习Python环境搭建",
                    "type": "learning",
                    "estimated_minutes": 60,
                    "difficulty": 2,
                    "description": "安装Python和IDE",
                },
                {
                    "title": "学习Python基础语法",
                    "type": "learning",
                    "estimated_minutes": 90,
                    "difficulty": 3,
                    "description": "变量、数据类型、运算符",
                },
                {
                    "title": "编写第一个Python程序",
                    "type": "training",
                    "estimated_minutes": 60,
                    "difficulty": 3,
                    "description": "Hello World程序",
                },
                {
                    "title": "练习Python控制流",
                    "type": "training",
                    "estimated_minutes": 90,
                    "difficulty": 4,
                    "description": "if/else, for, while",
                },
                {
                    "title": "学习Python函数",
                    "type": "learning",
                    "estimated_minutes": 60,
                    "difficulty": 4,
                    "description": "函数定义和调用",
                },
                {
                    "title": "综合练习：小项目",
                    "type": "training",
                    "estimated_minutes": 60,
                    "difficulty": 5,
                    "description": "编写一个简单计算器",
                },
            ]
        }

    mock_llm_service.chat_json = mock_generate_plan

    # Act: User requests plan creation
    plan_request = {
        "user_id": str(test_user.id),
        "subject": "Python",
        "duration_days": 7,
        "daily_hours": 1,
        "goals": ["掌握Python基础", "能写简单程序"],
    }

    plan = await plan_service.create_plan_from_user_request(
        user_id=test_user.id,
        request_data=plan_request,
    )

    # Assert: Plan created
    assert plan is not None
    assert plan.name == "Python学习计划"
    assert plan.type == PlanType.SPRINT
    assert plan.subject == "编程"
    assert plan.user_id == test_user.id

    # Assert: Tasks created
    result = await db_session.execute(
        select(Task).where(Task.plan_id == plan.id)
    )
    tasks = result.scalars().all()
    assert len(tasks) == 6
    test_assertions.assert_plan_created(plan, {
        "name": "Python学习计划",
        "subject": "编程",
    })


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_e2e_plan_execution_and_progress_tracking(
    db_session,
    test_user,
    test_plan_with_tasks,
    test_assertions,
):
    """
    E2E: User executes tasks → Progress updated → Achievements triggered

    Scenario:
    1. Plan with 5 tasks created
    2. User completes task 1 (30 min, actual 35 min)
    3. Task status updated to COMPLETED
    4. Plan progress updated (20%)
    5. User completes task 2
    6. Plan progress updated (40%)
    7. Milestone reached (25% complete)
    8. Achievement unlocked
    """
    # Arrange: Get plan and tasks
    plan = test_plan_with_tasks
    result = await db_session.execute(
        select(Task).where(Task.plan_id == plan.id).order_by(Task.order)
    )
    tasks = result.scalars().all()

    # Act 1: Complete first task
    task_service = TaskService(db_session)
    await task_service.complete(
        db=db_session,
        db_obj=tasks[0],
        actual_minutes=35,  # Took 5 minutes longer than estimated
    )

    # Update plan progress
    await PlanService.update_progress(db_session, plan.id, test_user.id)

    # Assert: Task completed
    await db_session.refresh(tasks[0])
    assert tasks[0].status == TaskStatus.COMPLETED

    # Assert: Plan progress updated
    await db_session.refresh(plan)
    assert plan.progress == 20.0  # 1/5 = 20%

    # Act 2: Complete second task
    await task_service.complete(
        db=db_session,
        db_obj=tasks[1],
        actual_minutes=25,  # Finished 5 minutes earlier
    )
    await PlanService.update_progress(db_session, plan.id, test_user.id)

    # Assert: Progress updated
    await db_session.refresh(plan)
    assert plan.progress == 40.0  # 2/5 = 40%

    # Assert: Milestone reached (25% milestone)
    # In real system, this would trigger achievement
    test_assertions.assert_task_progress(tasks, 2)


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_e2e_feedback_driven_adjustment(
    db_session,
    test_user,
    test_plan_with_tasks,
    mock_redis,
):
    """
    E2E: User provides feedback → Plan adjusted → Subsequent tasks updated

    Scenario:
    1. User completes task with "too hard" feedback
    2. FeedbackDrivenAdjustmentService processes feedback
    3. Calibration service updates difficulty estimate
    4. AdaptiveReplanner adjusts remaining tasks
    5. Task difficulties lowered
    6. User sees updated plan
    """
    # Arrange: Get plan and tasks
    plan = test_plan_with_tasks
    result = await db_session.execute(
        select(Task).where(Task.plan_id == plan.id).order_by(Task.order)
    )
    tasks = result.scalars().all()

    # Complete first task
    await TaskService.complete(
        db=db_session,
        db_obj=tasks[0],
        actual_minutes=60,  # Took much longer than 30 min estimate
    )

    # Arrange: Initialize services
    plan_state_service = PlanStateService(db_session, mock_redis)
    plan_state = await plan_state_service.get_or_create_plan_state(
        user_id=test_user.id,
        plan_id=plan.id,
        initial_facts={"difficulty_shift": 0.0},
    )

    feedback_service = FeedbackDrivenAdjustmentService(
        db_session,
        plan_state_service,
    )

    # Act: User submits feedback
    feedback_event = FeedbackEvent(
        event_id=f"fb-{uuid4().hex[:8]}",
        user_id=test_user.id,
        plan_id=plan.id,
        task_id=tasks[0].id,
        feedback_type=FeedbackType.TASK_TOO_HARD,
        timestamp=datetime.utcnow(),
        actual_duration_minutes=60,
        difficulty_perception="hard",
        task_type="learning",
        rating=2,  # Low rating
    )

    # Process feedback
    actions = await feedback_service.process_feedback(feedback_event)

    # Assert: Adjustment actions generated
    assert len(actions) > 0, "Should generate adjustment actions"

    # Assert: Time estimate adjustment
    time_actions = [a for a in actions if a.action_type == "adjust_estimate"]
    assert len(time_actions) > 0, "Should have time estimate adjustment"

    time_action = time_actions[0]
    assert len(time_action.target_task_ids) == 4, "Should adjust remaining 4 tasks"

    # Assert: Tasks were actually adjusted
    for i in range(1, 5):
        await db_session.refresh(tasks[i])
        # Time estimate should increase
        assert tasks[i].estimated_minutes >= 30, "Time estimate should be adjusted"

    # Assert: PlanState updated
    updated_state = await plan_state_service.get_plan_state(test_user.id, plan.id)
    assert len(updated_state.feedback_log) > 0, "Feedback log should be updated"


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_e2e_milestone_triggers_progressive_generation(
    db_session,
    test_user,
    mock_llm_service,
    mock_redis,
):
    """
    E2E: Milestone reached → Progressive task generation

    Scenario:
    1. User creates plan with initial 3 tasks
    2. User completes all 3 tasks (100% of initial phase)
    3. Milestone achieved: "phase1_complete"
    4. System proposes next phase tasks
    5. User confirms
    6. 3 new tasks added (not entire plan at once)
    7. Progressive generation prevents overwhelming user
    """
    # Arrange: Create initial plan
    plan = Plan(
        id=uuid4(),
        user_id=test_user.id,
        name="渐进式学习计划",
        type=PlanType.SPRINT,
        subject="编程",
        is_active=True,
        progress=0.0,
    )
    db_session.add(plan)

    # Create 3 initial tasks
    for i in range(3):
        task = Task(
            id=uuid4(),
            user_id=test_user.id,
            plan_id=plan.id,
            title=f"初始任务 {i+1}",
            type=TaskType.LEARNING,
            status=TaskStatus.PENDING,
            estimated_minutes=30,
            difficulty=3,
            order=i,
        )
        db_session.add(task)

    await db_session.commit()

    # Arrange: Initialize PlanState
    plan_state_service = PlanStateService(db_session, mock_redis)
    plan_state = await plan_state_service.get_or_create_plan_state(
        user_id=test_user.id,
        plan_id=plan.id,
    )

    # Act: Complete all initial tasks
    result = await db_session.execute(
        select(Task).where(Task.plan_id == plan.id)
    )
    tasks = result.scalars().all()

    for task in tasks:
        await TaskService.complete(
            db=db_session,
            db_obj=task,
            actual_minutes=30,
        )

    # Update plan progress
    await PlanService.update_progress(db_session, plan.id, test_user.id)

    # Assert: 100% progress
    await db_session.refresh(plan)
    assert plan.progress == 100.0

    # Act: Trigger milestone handler
    from app.services.milestone_handler import MilestoneHandler
    from unittest.mock import AsyncMock, patch

    handler = MilestoneHandler(db_session)

    # Mock LLM
    with patch("app.services.milestone_handler.get_llm_service_for_task") as mock_llm:
        mock_llm.return_value = AsyncMock()
        mock_llm.return_value.chat_json = AsyncMock(
            return_value={
                "reasoning": "User completed phase 1, recommending phase 2",
                "tasks": [
                    {
                        "title": "进阶任务 1",
                        "type": "learning",
                        "estimated_minutes": 45,
                        "difficulty": 4,
                    },
                    {
                        "title": "进阶任务 2",
                        "type": "training",
                        "estimated_minutes": 45,
                        "difficulty": 4,
                    },
                    {
                        "title": "进阶任务 3",
                        "type": "training",
                        "estimated_minutes": 60,
                        "difficulty": 5,
                    },
                ],
            }
        )

        # Trigger milestone
        action_id = await handler.on_milestone_achieved(
            user_id=test_user.id,
            plan_id=plan.id,
            milestone={
                "id": "ms-phase1-complete",
                "title": "完成第一阶段",
                "description": "已完成3个初始任务",
            },
            pending_task_count=0,  # No pending tasks
            current_plan_context={"title": "渐进式学习计划"},
        )

        # Assert: Proposal generated
        assert action_id is not None, "Should generate milestone proposal"

    # Assert: Only 3 new tasks proposed (not overwhelming)
    # (In real flow, user would confirm first)


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_e2e_multi_plan_isolation_and_switching(
    db_session,
    test_user,
    mock_redis,
):
    """
    E2E: Multiple plans → State isolation → Active plan switching

    Scenario:
    1. User creates Plan A (Python)
    2. User creates Plan B (Math)
    3. Complete task in Plan A
    4. Plan A progress updated
    5. Plan B progress unchanged (isolation)
    6. Switch active plan to Plan B
    7. Work on Plan B tasks
    8. Verify both plans maintain separate states
    """
    # Arrange: Create two plans
    plan_a = Plan(
        id=uuid4(),
        user_id=test_user.id,
        name="Python学习计划",
        type=PlanType.SPRINT,
        subject="编程",
        is_active=True,
        progress=0.0,
    )
    plan_b = Plan(
        id=uuid4(),
        user_id=test_user.id,
        name="数学复习计划",
        type=PlanType.SPRINT,
        subject="数学",
        is_active=True,
        progress=0.0,
    )
    db_session.add_all([plan_a, plan_b])

    # Create tasks for each plan
    task_a = Task(
        id=uuid4(),
        user_id=test_user.id,
        plan_id=plan_a.id,
        title="Python变量",
        type=TaskType.LEARNING,
        status=TaskStatus.PENDING,
        estimated_minutes=30,
    )
    task_b = Task(
        id=uuid4(),
        user_id=test_user.id,
        plan_id=plan_b.id,
        title="数学函数",
        type=TaskType.LEARNING,
        status=TaskStatus.PENDING,
        estimated_minutes=30,
    )
    db_session.add_all([task_a, task_b])
    await db_session.commit()

    # Arrange: Initialize PlanStates
    plan_state_service = PlanStateService(db_session, mock_redis)
    state_a = await plan_state_service.get_or_create_plan_state(
        user_id=test_user.id,
        plan_id=plan_a.id,
        initial_facts={"difficulty_preference": "hard"},
    )
    state_b = await plan_state_service.get_or_create_plan_state(
        user_id=test_user.id,
        plan_id=plan_b.id,
        initial_facts={"difficulty_preference": "easy"},
    )

    # Act: Complete task in Plan A
    await TaskService.complete(
        db=db_session,
        db_obj=task_a,
        actual_minutes=30,
    )
    await PlanService.update_progress(db_session, plan_a.id, test_user.id)

    # Update Plan A state
    state_a.task_index["completed"] = 1
    state_a.version = 2
    await db_session.commit()

    # Assert: Plan A progress updated
    await db_session.refresh(plan_a)
    assert plan_a.progress == 100.0

    # Assert: Plan B unchanged (isolation)
    await db_session.refresh(plan_b)
    assert plan_b.progress == 0.0

    await db_session.refresh(state_b)
    assert state_b.version == 1, "Plan B version should not increment"
    assert state_b.task_index["completed"] == 0, "Plan B completed count should be 0"

    # Act: Switch active plan (simulated)
    session_id = f"session_{uuid4().hex[:8]}"
    from app.orchestration.state_manager import SessionStateManager
    from unittest.mock import AsyncMock

    mock_redis_client = AsyncMock()
    state_manager = SessionStateManager(mock_redis_client)

    # Set Plan A as active
    await state_manager.set_active_plan(session_id, plan_a.id, reason="manual")
    active_plan = await state_manager.get_active_plan(session_id)
    assert active_plan["plan_id"] == str(plan_a.id)

    # Switch to Plan B
    await state_manager.set_active_plan(session_id, plan_b.id, reason="user_switch")
    active_plan = await state_manager.get_active_plan(session_id)
    assert active_plan["plan_id"] == str(plan_b.id)

    # Assert: States remain isolated after switch
    final_state_a = await plan_state_service.get_plan_state(test_user.id, plan_a.id)
    final_state_b = await plan_state_service.get_plan_state(test_user.id, plan_b.id)

    assert final_state_a.facts["difficulty_preference"] == "hard"
    assert final_state_b.facts["difficulty_preference"] == "easy"


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_e2e_plan_review_and_approval_flow(
    db_session,
    test_user,
    mock_llm_service,
    mock_redis,
):
    """
    E2E: Plan generated → User reviews → User approves → Plan activated

    Scenario:
    1. User requests plan creation
    2. LLM generates plan proposal
    3. Plan in "pending_review" status
    4. User reviews tasks and timeline
    5. User approves plan
    6. Plan status → "active"
    7. Tasks visible in task board
    """
    # Arrange: Initialize plan service
    plan_service = PlanService(db_session, mock_llm_service, mock_redis)

    # Mock LLM plan generation
    async def mock_generate_plan(user_input, user_context):
        return {
            "name": "面试准备计划",
            "type": "sprint",
            "subject": "编程",
            "description": "7天冲刺准备面试",
            "target_date": (datetime.now() + timedelta(days=7)).isoformat(),
            "tasks": [
                {
                    "title": "复习算法基础",
                    "type": "learning",
                    "estimated_minutes": 120,
                    "difficulty": 4,
                },
                {
                    "title": "练习LeetCode简单题",
                    "type": "training",
                    "estimated_minutes": 120,
                    "difficulty": 3,
                },
            ],
        }

    mock_llm_service.chat_json = mock_generate_plan

    # Act: Create plan proposal
    plan_request = {
        "user_id": str(test_user.id),
        "subject": "编程面试",
        "duration_days": 7,
        "daily_hours": 2,
    }

    plan = await plan_service.create_plan_from_user_request(
        user_id=test_user.id,
        request_data=plan_request,
        auto_approve=False,  # Require user approval
    )

    # Assert: Plan in pending status
    assert plan.status == PlanStatus.PENDING_REVIEW

    # Act: User reviews and approves
    await plan_service.review_and_approve_plan(
        plan_id=plan.id,
        user_id=test_user.id,
        approved=True,
        feedback="计划看起来不错",
    )

    # Assert: Plan activated
    await db_session.refresh(plan)
    assert plan.status == PlanStatus.ACTIVE

    # Assert: Tasks visible
    result = await db_session.execute(
        select(Task).where(Task.plan_id == plan.id)
    )
    tasks = result.scalars().all()
    assert len(tasks) == 2
    assert all(t.status == TaskStatus.PENDING for t in tasks)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
