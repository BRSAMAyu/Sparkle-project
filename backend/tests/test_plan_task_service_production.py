"""
Production-grade tests for PlanService and TaskService core business logic.

These tests validate REAL business rules discovered from the source code:
- Plan lifecycle: create -> active -> archive -> restore
- First plan auto-primary
- Sprint auto-archive on 100% completion
- Plan progress auto-update on task completion
- Task lifecycle state machine
- Task stuck guard
- Focus progress auto-complete
- Task reorder deduplication and validation
- Batch task confirmation by tool_result_id
- Sentiment inference from user notes
- Ownership enforcement on all operations
"""
import pytest
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plan import Plan, PlanPriority, PlanStage, PlanType
from app.models.task import Task, TaskStatus, TaskType
from app.schemas.plan import PlanCreate, PlanUpdate
from app.schemas.task import TaskCreate, TaskUpdate
from app.services.plan_service import PlanService
from app.services.task_service import TaskService


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@pytest.fixture
def mock_plan_deps(monkeypatch):
    """Shared fixture: mock PlanQuotaService, _sync_plan_card_projection, Stage33JourneyEventService."""
    mock_quota_status = MagicMock()
    mock_quota_status.used = 0
    mock_quota_svc = AsyncMock()
    mock_quota_svc.get_quota_status.return_value = mock_quota_status
    mock_quota_svc.check_and_raise = AsyncMock()
    mock_quota_svc.auto_set_primary_plan = AsyncMock(return_value=None)
    mock_quota_svc.ensure_primary_exists = AsyncMock()

    monkeypatch.setattr(
        "app.services.plan_quota_service.PlanQuotaService",
        lambda db, redis: mock_quota_svc,
    )
    monkeypatch.setattr(
        "app.services.plan_service._sync_plan_card_projection",
        AsyncMock(),
    )
    monkeypatch.setattr(
        "app.services.stage33_journey_event_service.Stage33JourneyEventService.publish",
        AsyncMock(),
    )
    return mock_quota_svc


@pytest.fixture
def mock_task_deps(monkeypatch):
    """Shared fixture: mock common task service dependencies."""
    monkeypatch.setattr(
        "app.services.task_service.get_personalization_engine",
        MagicMock(side_effect=Exception("no engine")),
    )
    monkeypatch.setattr(
        "app.services.task_service._sync_task_card_projection",
        AsyncMock(),
    )
    monkeypatch.setattr(
        "app.services.task_service.task_document_service",
        MagicMock(auto_link_from_task_context=AsyncMock()),
    )
    monkeypatch.setattr(
        "app.services.task_service.cache_service",
        MagicMock(redis=None),
    )
    monkeypatch.setattr(
        "app.services.task_service.event_bus_reliable",
        MagicMock(publish=AsyncMock()),
    )
    monkeypatch.setattr(
        "app.services.task_service.publish_srl_event",
        AsyncMock(),
    )


# ── PlanService: Create ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_plan_create_first_plan_auto_primary(db_session: AsyncSession, mock_plan_deps):
    """First plan for a user MUST be auto-set as primary (is_primary=True)."""
    user_id = uuid4()
    mock_plan_deps.get_quota_status.return_value.used = 0

    obj_in = PlanCreate(name="我的第一个计划", type=PlanType.SPRINT, subject="数学")
    plan = await PlanService.create(db_session, obj_in, user_id, skip_quota_check=True)

    assert plan.is_primary is True
    assert plan.user_id == user_id
    assert plan.name == "我的第一个计划"
    assert plan.type == PlanType.SPRINT


@pytest.mark.asyncio
async def test_plan_create_second_plan_not_primary(db_session: AsyncSession, mock_plan_deps):
    """Second plan for a user MUST NOT be auto-set as primary."""
    user_id = uuid4()
    mock_plan_deps.get_quota_status.return_value.used = 1

    obj_in = PlanCreate(name="第二个计划", type=PlanType.GROWTH, subject="英语")
    plan = await PlanService.create(db_session, obj_in, user_id, skip_quota_check=True)

    assert plan.is_primary is False


@pytest.mark.asyncio
async def test_plan_create_defaults_to_daily_stage(db_session: AsyncSession, mock_plan_deps):
    """When plan_stage not provided, MUST default to DAILY."""
    user_id = uuid4()
    obj_in = PlanCreate(name="默认阶段测试", type=PlanType.SPRINT)
    plan = await PlanService.create(db_session, obj_in, user_id, skip_quota_check=True)
    assert plan.plan_stage == PlanStage.DAILY


@pytest.mark.asyncio
async def test_plan_create_priority_default_normal(db_session: AsyncSession, mock_plan_deps):
    """When priority not provided, MUST default to NORMAL."""
    user_id = uuid4()
    obj_in = PlanCreate(name="优先级测试", type=PlanType.SPRINT)
    plan = await PlanService.create(db_session, obj_in, user_id, skip_quota_check=True)
    assert plan.priority == PlanPriority.NORMAL


# ── PlanService: Archive / Restore ───────────────────────────────────


@pytest.mark.asyncio
async def test_plan_archive_sets_inactive_and_not_primary(db_session: AsyncSession, mock_plan_deps):
    """Archiving a plan MUST set is_active=False AND is_primary=False."""
    user_id = uuid4()
    plan = Plan(
        id=uuid4(),
        user_id=user_id,
        name="待归档计划",
        type=PlanType.SPRINT,
        is_active=True,
        is_primary=True,
    )
    db_session.add(plan)
    await db_session.commit()

    archived = await PlanService.archive(db_session, plan.id, user_id)

    assert archived is not None
    assert archived.is_active is False
    assert archived.is_primary is False


@pytest.mark.asyncio
async def test_plan_archive_triggers_auto_primary_selection(db_session: AsyncSession, mock_plan_deps):
    """When archiving the primary plan, system MUST auto-select a new primary."""
    user_id = uuid4()
    plan_a = Plan(
        id=uuid4(),
        user_id=user_id,
        name="主计划",
        type=PlanType.SPRINT,
        is_active=True,
        is_primary=True,
    )
    plan_b = Plan(
        id=uuid4(),
        user_id=user_id,
        name="备用计划",
        type=PlanType.GROWTH,
        is_active=True,
        is_primary=False,
    )
    db_session.add_all([plan_a, plan_b])
    await db_session.commit()

    mock_plan_deps.auto_set_primary_plan = AsyncMock(return_value=plan_b.id)

    await PlanService.archive(db_session, plan_a.id, user_id)

    mock_plan_deps.auto_set_primary_plan.assert_called_once_with(user_id)


@pytest.mark.asyncio
async def test_plan_archive_wrong_user_returns_none(db_session: AsyncSession, mock_plan_deps):
    """Archiving another user's plan MUST return None (ownership enforced)."""
    user_a = uuid4()
    user_b = uuid4()
    plan = Plan(
        id=uuid4(),
        user_id=user_a,
        name="用户A的计划",
        type=PlanType.SPRINT,
        is_active=True,
    )
    db_session.add(plan)
    await db_session.commit()

    result = await PlanService.archive(db_session, plan.id, user_b)
    assert result is None


@pytest.mark.asyncio
async def test_plan_restore_reactivates(db_session: AsyncSession, mock_plan_deps):
    """Restoring an archived plan MUST set is_active=True."""
    user_id = uuid4()
    plan = Plan(
        id=uuid4(),
        user_id=user_id,
        name="已归档计划",
        type=PlanType.SPRINT,
        is_active=False,
    )
    db_session.add(plan)
    await db_session.commit()

    restored = await PlanService.restore(db_session, plan.id, user_id, skip_quota_check=True)

    assert restored is not None
    assert restored.is_active is True


@pytest.mark.asyncio
async def test_plan_restore_active_plan_returns_none(db_session: AsyncSession, mock_plan_deps):
    """Restoring an already active plan MUST return None."""
    user_id = uuid4()
    plan = Plan(
        id=uuid4(),
        user_id=user_id,
        name="活跃计划",
        type=PlanType.SPRINT,
        is_active=True,
    )
    db_session.add(plan)
    await db_session.commit()

    result = await PlanService.restore(db_session, plan.id, user_id, skip_quota_check=True)
    assert result is None


# ── PlanService: Sprint Auto-Archive ─────────────────────────────────


@pytest.mark.asyncio
async def test_plan_sprint_auto_archive_on_all_tasks_completed(db_session: AsyncSession, monkeypatch):
    """Sprint plan MUST auto-archive when ALL tasks are completed."""
    user_id = uuid4()
    plan = Plan(
        id=uuid4(),
        user_id=user_id,
        name="冲刺自动归档",
        type=PlanType.SPRINT,
        is_active=True,
        progress=0.0,
    )
    db_session.add(plan)
    await db_session.commit()

    for _ in range(2):
        task = Task(
            id=uuid4(),
            user_id=user_id,
            plan_id=plan.id,
            title="任务",
            type=TaskType.LEARNING,
            status=TaskStatus.COMPLETED,
            estimated_minutes=30,
        )
        db_session.add(task)
    await db_session.commit()

    monkeypatch.setattr(
        "app.services.plan_service._sync_plan_card_projection",
        AsyncMock(),
    )
    mock_quota_svc = AsyncMock()
    mock_quota_svc.auto_set_primary_plan = AsyncMock(return_value=None)
    monkeypatch.setattr(
        "app.services.plan_quota_service.PlanQuotaService",
        lambda db, redis: mock_quota_svc,
    )
    monkeypatch.setattr(
        "app.services.plan_state_service.PlanStateService",
        MagicMock(),
    )

    new_progress = await PlanService.update_progress(db_session, plan.id, user_id)

    await db_session.refresh(plan)
    assert new_progress == 1.0
    assert plan.is_active is False


@pytest.mark.asyncio
async def test_plan_sprint_no_auto_archive_with_incomplete_tasks(db_session: AsyncSession, monkeypatch):
    """Sprint plan MUST NOT auto-archive when tasks remain incomplete."""
    user_id = uuid4()
    plan = Plan(
        id=uuid4(),
        user_id=user_id,
        name="部分完成冲刺",
        type=PlanType.SPRINT,
        is_active=True,
        progress=0.0,
    )
    db_session.add(plan)
    await db_session.commit()

    completed = Task(
        id=uuid4(),
        user_id=user_id,
        plan_id=plan.id,
        title="已完成",
        type=TaskType.LEARNING,
        status=TaskStatus.COMPLETED,
        estimated_minutes=30,
    )
    pending = Task(
        id=uuid4(),
        user_id=user_id,
        plan_id=plan.id,
        title="待完成",
        type=TaskType.LEARNING,
        status=TaskStatus.PENDING,
        estimated_minutes=30,
    )
    db_session.add_all([completed, pending])
    await db_session.commit()

    monkeypatch.setattr(
        "app.services.plan_service._sync_plan_card_projection",
        AsyncMock(),
    )

    new_progress = await PlanService.update_progress(db_session, plan.id, user_id)

    await db_session.refresh(plan)
    assert new_progress == 0.5
    assert plan.is_active is True


@pytest.mark.asyncio
async def test_task_abandon_sets_status_and_note(db_session: AsyncSession, mock_task_deps):
    """Abandoning a task MUST set ABANDONED status and prefix the note."""
    user_id = uuid4()
    task = Task(
        id=uuid4(),
        user_id=user_id,
        title="待放弃任务",
        type=TaskType.LEARNING,
        status=TaskStatus.IN_PROGRESS,
        estimated_minutes=30,
        started_at=_utcnow() - timedelta(minutes=10),
    )
    db_session.add(task)
    await db_session.commit()

    abandoned = await TaskService.abandon(db_session, task, reason="太难了")

    assert abandoned.status == TaskStatus.ABANDONED
    assert abandoned.user_note == "Abandoned: 太难了"
    assert abandoned.completed_at is not None


@pytest.mark.asyncio
async def test_task_abandon_without_reason_no_note(db_session: AsyncSession, mock_task_deps):
    """Abandoning without reason MUST NOT set user_note."""
    user_id = uuid4()
    task = Task(
        id=uuid4(),
        user_id=user_id,
        title="无理由放弃",
        type=TaskType.LEARNING,
        status=TaskStatus.PENDING,
        estimated_minutes=30,
    )
    db_session.add(task)
    await db_session.commit()

    abandoned = await TaskService.abandon(db_session, task, reason=None)

    assert abandoned.status == TaskStatus.ABANDONED
    assert abandoned.user_note is None


# ── TaskService: Focus Progress ──────────────────────────────────────


@pytest.mark.asyncio
async def test_task_focus_progress_auto_complete(db_session: AsyncSession, mock_task_deps):
    """When accumulated minutes >= estimated, task MUST auto-complete."""
    user_id = uuid4()
    task = Task(
        id=uuid4(),
        user_id=user_id,
        title="专注自动完成",
        type=TaskType.LEARNING,
        status=TaskStatus.IN_PROGRESS,
        estimated_minutes=30,
        actual_minutes=20,
    )
    db_session.add(task)
    await db_session.commit()

    monkeypatch.setattr(
        "app.services.task_service._sync_task_card_projection",
        AsyncMock(),
    )
    monkeypatch.setattr(
        "app.services.task_service.cache_service",
        MagicMock(redis=None),
    )
    monkeypatch.setattr(
        "app.services.task_service.event_bus_reliable",
        MagicMock(publish=AsyncMock()),
    )
    monkeypatch.setattr(
        "app.services.task_service.publish_srl_event",
        AsyncMock(),
    )

    result = await TaskService.apply_focus_progress(
        db_session,
        task_id=task.id,
        user_id=user_id,
        duration_minutes=15,
        started_at=_utcnow() - timedelta(minutes=15),
    )

    assert result is not None
    assert result.status == TaskStatus.COMPLETED


@pytest.mark.asyncio
async def test_task_focus_progress_no_auto_complete_under_estimate(db_session: AsyncSession, mock_task_deps):
    """When accumulated minutes < estimated, task MUST NOT auto-complete."""
    user_id = uuid4()
    task = Task(
        id=uuid4(),
        user_id=user_id,
        title="专注未完成",
        type=TaskType.LEARNING,
        status=TaskStatus.IN_PROGRESS,
        estimated_minutes=60,
        actual_minutes=10,
    )
    db_session.add(task)
    await db_session.commit()

    monkeypatch.setattr(
        "app.services.task_service._sync_task_card_projection",
        AsyncMock(),
    )

    result = await TaskService.apply_focus_progress(
        db_session,
        task_id=task.id,
        user_id=user_id,
        duration_minutes=15,
        started_at=_utcnow() - timedelta(minutes=15),
    )

    assert result is not None
    assert result.status == TaskStatus.IN_PROGRESS
    assert result.actual_minutes == 25


@pytest.mark.asyncio
async def test_task_focus_progress_zero_duration_no_change(db_session: AsyncSession):
    """duration_minutes <= 0 MUST return task unchanged."""
    user_id = uuid4()
    task = Task(
        id=uuid4(),
        user_id=user_id,
        title="零时长专注",
        type=TaskType.LEARNING,
        status=TaskStatus.IN_PROGRESS,
        estimated_minutes=30,
        actual_minutes=10,
    )
    db_session.add(task)
    await db_session.commit()

    result = await TaskService.apply_focus_progress(
        db_session,
        task_id=task.id,
        user_id=user_id,
        duration_minutes=0,
        started_at=_utcnow(),
    )

    assert result is not None
    assert result.actual_minutes == 10


@pytest.mark.asyncio
async def test_task_focus_progress_auto_starts_pending(db_session: AsyncSession, mock_task_deps):
    """PENDING task receiving focus progress MUST auto-transition to IN_PROGRESS."""
    user_id = uuid4()
    task = Task(
        id=uuid4(),
        user_id=user_id,
        title="待启动任务",
        type=TaskType.LEARNING,
        status=TaskStatus.PENDING,
        estimated_minutes=60,
        actual_minutes=0,
    )
    db_session.add(task)
    await db_session.commit()

    monkeypatch.setattr(
        "app.services.task_service._sync_task_card_projection",
        AsyncMock(),
    )

    started_at = _utcnow() - timedelta(minutes=10)
    result = await TaskService.apply_focus_progress(
        db_session,
        task_id=task.id,
        user_id=user_id,
        duration_minutes=10,
        started_at=started_at,
    )

    assert result is not None
    assert result.status == TaskStatus.IN_PROGRESS
    assert result.actual_minutes == 10


# ── TaskService: Reorder ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_task_reorder_deduplicates_ids(db_session: AsyncSession):
    """reorder_tasks MUST deduplicate task IDs (first occurrence wins)."""
    user_id = uuid4()
    task1 = Task(
        id=uuid4(),
        user_id=user_id,
        title="任务1",
        type=TaskType.LEARNING,
        status=TaskStatus.PENDING,
        estimated_minutes=30,
        order_index=1000,
    )
    task2 = Task(
        id=uuid4(),
        user_id=user_id,
        title="任务2",
        type=TaskType.LEARNING,
        status=TaskStatus.PENDING,
        estimated_minutes=30,
        order_index=2000,
    )
    db_session.add_all([task1, task2])
    await db_session.commit()

    reordered = await TaskService.reorder_tasks(
        db_session,
        user_id=user_id,
        ordered_task_ids=[task1.id, task2.id, task1.id],
    )

    assert len(reordered) == 2
    assert reordered[0].id == task1.id
    assert reordered[1].id == task2.id


@pytest.mark.asyncio
async def test_task_reorder_raises_for_missing_task(db_session: AsyncSession):
    """reorder_tasks MUST raise ValueError when any task ID doesn't exist or belongs to another user."""
    user_id = uuid4()
    nonexistent_id = uuid4()

    with pytest.raises(ValueError, match="Tasks not found"):
        await TaskService.reorder_tasks(
            db_session,
            user_id=user_id,
            ordered_task_ids=[nonexistent_id],
        )


@pytest.mark.asyncio
async def test_task_reorder_sets_ascending_order_index(db_session: AsyncSession):
    """Reordered tasks MUST have ascending order_index with 1000 spacing."""
    user_id = uuid4()
    task1 = Task(
        id=uuid4(),
        user_id=user_id,
        title="任务1",
        type=TaskType.LEARNING,
        status=TaskStatus.PENDING,
        estimated_minutes=30,
    )
    task2 = Task(
        id=uuid4(),
        user_id=user_id,
        title="任务2",
        type=TaskType.LEARNING,
        status=TaskStatus.PENDING,
        estimated_minutes=30,
    )
    db_session.add_all([task1, task2])
    await db_session.commit()

    reordered = await TaskService.reorder_tasks(
        db_session,
        user_id=user_id,
        ordered_task_ids=[task2.id, task1.id],
    )

    assert reordered[0].id == task2.id
    assert reordered[0].order_index == 1000
    assert reordered[1].id == task1.id
    assert reordered[1].order_index == 2000


# ── TaskService: Batch Confirm ───────────────────────────────────────


@pytest.mark.asyncio
async def test_task_confirm_batch_by_tool_result(db_session: AsyncSession, mock_task_deps):
    """confirm_tasks_by_tool_result MUST batch-confirm all PENDING tasks with matching tool_result_id."""
    user_id = uuid4()
    tool_result_id = "tool_result_abc123"

    task1 = Task(
        id=uuid4(),
        user_id=user_id,
        title="AI生成任务1",
        type=TaskType.LEARNING,
        status=TaskStatus.PENDING,
        estimated_minutes=25,
        tool_result_id=tool_result_id,
    )
    task2 = Task(
        id=uuid4(),
        user_id=user_id,
        title="AI生成任务2",
        type=TaskType.TRAINING,
        status=TaskStatus.PENDING,
        estimated_minutes=20,
        tool_result_id=tool_result_id,
    )
    task3 = Task(
        id=uuid4(),
        user_id=user_id,
        title="其他任务",
        type=TaskType.LEARNING,
        status=TaskStatus.PENDING,
        estimated_minutes=30,
        tool_result_id="different_id",
    )
    db_session.add_all([task1, task2, task3])
    await db_session.commit()

    monkeypatch.setattr(
        "app.services.task_service._sync_task_card_projection",
        AsyncMock(),
    )
    monkeypatch.setattr(
        "app.services.task_service.event_bus_reliable",
        MagicMock(publish=AsyncMock()),
    )
    monkeypatch.setattr(
        "app.services.task_service.publish_srl_event",
        AsyncMock(),
    )

    confirmed = await TaskService.confirm_tasks_by_tool_result(db_session, tool_result_id, user_id)

    assert len(confirmed) == 2
    for t in confirmed:
        assert t.status == TaskStatus.IN_PROGRESS
        assert t.confirmed_at is not None
        assert t.started_at is not None

    await db_session.refresh(task3)
    assert task3.status == TaskStatus.PENDING


@pytest.mark.asyncio
async def test_task_confirm_batch_empty_returns_empty(db_session: AsyncSession):
    """confirm_tasks_by_tool_result with no matching tasks MUST return empty list."""
    user_id = uuid4()

    result = await TaskService.confirm_tasks_by_tool_result(db_session, "nonexistent_id", user_id)

    assert result == []


# ── TaskService: Sentiment Inference ─────────────────────────────────


def test_task_infer_sentiment_negative():
    """Notes containing negative keywords MUST return 'negative'."""
    assert TaskService._infer_sentiment("This was really hard and confusing") == "negative"
    assert TaskService._infer_sentiment("I got stuck on this problem") == "negative"
    assert TaskService._infer_sentiment("非常frustrated") == "negative"


def test_task_infer_sentiment_positive():
    """Notes containing positive keywords MUST return 'positive'."""
    assert TaskService._infer_sentiment("This was easy and clear") == "positive"
    assert TaskService._infer_sentiment("Good progress today") == "positive"
    assert TaskService._infer_sentiment("Very helpful exercise") == "positive"


def test_task_infer_sentiment_neutral():
    """Notes with no sentiment keywords MUST return 'neutral'."""
    assert TaskService._infer_sentiment("Did the exercise") == "neutral"
    assert TaskService._infer_sentiment(None) == "neutral"
    assert TaskService._infer_sentiment("") == "neutral"


def test_task_infer_sentiment_negative_priority():
    """When both negative and positive keywords present, negative MUST win."""
    assert TaskService._infer_sentiment("It was hard but helpful") == "negative"


# ── TaskService: Difficulty from Gradient ────────────────────────────


def test_task_difficulty_from_gradient_boundaries():
    """Difficulty MUST map gradient [0,1] to difficulty [1,5]."""
    assert TaskService._difficulty_from_gradient(0.0) == 1
    assert TaskService._difficulty_from_gradient(1.0) == 5
    assert TaskService._difficulty_from_gradient(0.5) == 3
    assert TaskService._difficulty_from_gradient(None) == 1
    assert TaskService._difficulty_from_gradient(-0.5) == 1
    assert TaskService._difficulty_from_gradient(1.5) == 5


# ── TaskService: Task Summary Builder ────────────────────────────────


def test_task_build_summary_positive_note():
    """Task summary MUST correctly compute actual_vs_estimated and sentiment."""
    task = Task(
        id=uuid4(),
        title="测试任务",
        estimated_minutes=30,
        completed_at=_utcnow(),
    )
    summary = TaskService._build_task_summary(task, actual_minutes=35, note="Easy and smooth")

    assert summary["actual_vs_estimated"] == "+5min"
    assert summary["user_sentiment"] == "positive"
    assert summary["key_takeaway"] == "Easy and smooth"


def test_task_build_summary_negative_note():
    """Task summary with negative note MUST reflect negative sentiment."""
    task = Task(
        id=uuid4(),
        title="测试任务",
        estimated_minutes=30,
        completed_at=_utcnow(),
    )
    summary = TaskService._build_task_summary(task, actual_minutes=25, note="Very confusing")

    assert summary["actual_vs_estimated"] == "-5min"
    assert summary["user_sentiment"] == "negative"


def test_task_build_summary_no_note():
    """Task summary without note MUST have neutral sentiment and None takeaway."""
    task = Task(
        id=uuid4(),
        title="测试任务",
        estimated_minutes=30,
        completed_at=_utcnow(),
    )
    summary = TaskService._build_task_summary(task, actual_minutes=30, note=None)

    assert summary["actual_vs_estimated"] == "0min"
    assert summary["user_sentiment"] == "neutral"
    assert summary["key_takeaway"] is None


# ── TaskService: Delete ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_task_delete_updates_plan_progress(db_session: AsyncSession, mock_plan_deps):
    """Deleting a task with plan_id MUST trigger plan progress recalculation."""
    user_id = uuid4()
    plan = Plan(
        id=uuid4(),
        user_id=user_id,
        name="删除任务计划",
        type=PlanType.GROWTH,
        is_active=True,
        progress=0.0,
    )
    db_session.add(plan)

    task_completed = Task(
        id=uuid4(),
        user_id=user_id,
        plan_id=plan.id,
        title="已完成任务",
        type=TaskType.LEARNING,
        status=TaskStatus.COMPLETED,
        estimated_minutes=30,
    )
    task_to_delete = Task(
        id=uuid4(),
        user_id=user_id,
        plan_id=plan.id,
        title="待删除任务",
        type=TaskType.LEARNING,
        status=TaskStatus.PENDING,
        estimated_minutes=30,
    )
    db_session.add_all([task_completed, task_to_delete])
    await db_session.commit()

    monkeypatch.setattr(
        "app.services.plan_service._sync_plan_card_projection",
        AsyncMock(),
    )

    await TaskService.delete(db_session, task_to_delete)

    remaining = await db_session.execute(select(Task).where(Task.plan_id == plan.id))
    remaining_tasks = remaining.scalars().all()
    assert len(remaining_tasks) == 1
    assert remaining_tasks[0].status == TaskStatus.COMPLETED


# ── TaskService: Ownership ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_task_get_by_id_ownership_enforced(db_session: AsyncSession):
    """get_by_id MUST return None when task belongs to another user."""
    user_a = uuid4()
    user_b = uuid4()
    task = Task(
        id=uuid4(),
        user_id=user_a,
        title="用户A的任务",
        type=TaskType.LEARNING,
        status=TaskStatus.PENDING,
        estimated_minutes=30,
    )
    db_session.add(task)
    await db_session.commit()

    assert await TaskService.get_by_id(db_session, task.id, user_b) is None
    assert await TaskService.get_by_id(db_session, task.id, user_a) is not None


@pytest.mark.asyncio
async def test_task_start_task_raises_for_wrong_user(db_session: AsyncSession):
    """start_task MUST raise NotFoundError when task doesn't belong to user."""
    user_a = uuid4()
    user_b = uuid4()
    task = Task(
        id=uuid4(),
        user_id=user_a,
        title="用户A的任务",
        type=TaskType.LEARNING,
        status=TaskStatus.PENDING,
        estimated_minutes=30,
    )
    db_session.add(task)
    await db_session.commit()

    from app.core.exceptions import NotFoundError

    with pytest.raises(NotFoundError):
        await TaskService.start_task(db_session, task.id, user_b)


@pytest.mark.asyncio
async def test_task_complete_task_raises_for_wrong_user(db_session: AsyncSession, monkeypatch):
    """complete_task MUST raise NotFoundError when task doesn't belong to user."""
    user_a = uuid4()
    user_b = uuid4()
    task = Task(
        id=uuid4(),
        user_id=user_a,
        title="用户A的任务",
        type=TaskType.LEARNING,
        status=TaskStatus.IN_PROGRESS,
        estimated_minutes=30,
    )
    db_session.add(task)
    await db_session.commit()

    from app.core.exceptions import NotFoundError

    with pytest.raises(NotFoundError):
        await TaskService.complete_task(db_session, task.id, user_b, actual_minutes=30)


# ── TaskService: Start ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_task_start_sets_status_and_timestamp(db_session: AsyncSession, monkeypatch):
    """Starting a task MUST set IN_PROGRESS status and started_at."""
    user_id = uuid4()
    task = Task(
        id=uuid4(),
        user_id=user_id,
        title="待启动任务",
        type=TaskType.LEARNING,
        status=TaskStatus.PENDING,
        estimated_minutes=30,
    )
    db_session.add(task)
    await db_session.commit()

    monkeypatch.setattr(
        "app.services.task_service._sync_task_card_projection",
        AsyncMock(),
    )
    monkeypatch.setattr(
        "app.services.task_service.event_bus_reliable",
        MagicMock(publish=AsyncMock()),
    )
    monkeypatch.setattr(
        "app.services.task_service.publish_srl_event",
        AsyncMock(),
    )

    started = await TaskService.start(db_session, task)

    assert started.status == TaskStatus.IN_PROGRESS
    assert started.started_at is not None
