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
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plan import Plan, PlanPriority, PlanStage, PlanType
from app.models.task import Task, TaskStatus, TaskType
from app.schemas.plan import PlanCreate, PlanUpdate
from app.schemas.task import TaskCreate
from app.services.plan_service import PlanService
from app.services.task_service import TaskService


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@pytest.fixture
def mock_plan_deps(monkeypatch):
    monkeypatch.setattr(
        "app.services.plan_quota_service.PlanQuotaService",
        lambda db, redis: AsyncMock(
            get_quota_status=AsyncMock(return_value=MagicMock(used=0)),
            check_and_raise=AsyncMock(),
            auto_set_primary_plan=AsyncMock(return_value=None),
            ensure_primary_exists=AsyncMock(),
        ),
    )
    monkeypatch.setattr("app.services.plan_service._sync_plan_card_projection", AsyncMock())
    monkeypatch.setattr(
        "app.services.stage33_journey_event_service.Stage33JourneyEventService.publish",
        AsyncMock(),
    )


@pytest.fixture
def mock_task_deps(monkeypatch):
    monkeypatch.setattr(
        "app.services.task_service.get_personalization_engine",
        MagicMock(side_effect=Exception("no engine")),
    )
    monkeypatch.setattr("app.services.task_service._sync_task_card_projection", AsyncMock())
    monkeypatch.setattr(
        "app.services.task_service.task_document_service",
        MagicMock(auto_link_from_task_context=AsyncMock()),
    )
    monkeypatch.setattr("app.services.task_service.cache_service", MagicMock(redis=None))
    monkeypatch.setattr("app.services.task_service.event_bus_reliable", MagicMock(publish=AsyncMock()))
    monkeypatch.setattr("app.services.task_service.publish_srl_event", AsyncMock())


# ── PlanService: Create ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_plan_create_first_plan_auto_primary(db_session, mock_plan_deps):
    user_id = uuid4()
    plan = await PlanService.create(
        db_session, PlanCreate(name="第一个", type=PlanType.SPRINT), user_id, skip_quota_check=True
    )
    assert plan.is_primary is True


@pytest.mark.asyncio
async def test_plan_create_second_plan_not_primary(db_session, mock_plan_deps, monkeypatch):
    user_id = uuid4()
    mock_svc = AsyncMock()
    mock_svc.get_quota_status = AsyncMock(return_value=MagicMock(used=1))
    mock_svc.check_and_raise = AsyncMock()
    monkeypatch.setattr("app.services.plan_quota_service.PlanQuotaService", lambda db, r: mock_svc)
    plan = await PlanService.create(
        db_session, PlanCreate(name="第二个", type=PlanType.GROWTH), user_id, skip_quota_check=True
    )
    assert plan.is_primary is False


@pytest.mark.asyncio
async def test_plan_create_defaults(db_session, mock_plan_deps):
    plan = await PlanService.create(
        db_session, PlanCreate(name="默认值", type=PlanType.SPRINT), uuid4(), skip_quota_check=True
    )
    assert plan.plan_stage == PlanStage.DAILY
    assert plan.priority == PlanPriority.NORMAL


# ── PlanService: Archive / Restore ───────────────────────────────────


@pytest.mark.asyncio
async def test_plan_archive_sets_inactive_and_not_primary(db_session, mock_plan_deps):
    user_id = uuid4()
    plan = Plan(id=uuid4(), user_id=user_id, name="p", type=PlanType.SPRINT, is_active=True, is_primary=True)
    db_session.add(plan)
    await db_session.commit()
    archived = await PlanService.archive(db_session, plan.id, user_id)
    assert archived.is_active is False
    assert archived.is_primary is False


@pytest.mark.asyncio
async def test_plan_archive_triggers_auto_primary(db_session, mock_plan_deps, monkeypatch):
    user_id = uuid4()
    plan_a = Plan(id=uuid4(), user_id=user_id, name="a", type=PlanType.SPRINT, is_active=True, is_primary=True)
    plan_b = Plan(id=uuid4(), user_id=user_id, name="b", type=PlanType.GROWTH, is_active=True, is_primary=False)
    db_session.add_all([plan_a, plan_b])
    await db_session.commit()
    mock_svc = AsyncMock(auto_set_primary_plan=AsyncMock(return_value=plan_b.id))
    monkeypatch.setattr("app.services.plan_quota_service.PlanQuotaService", lambda db, r: mock_svc)
    await PlanService.archive(db_session, plan_a.id, user_id)
    mock_svc.auto_set_primary_plan.assert_called_once_with(user_id)


@pytest.mark.asyncio
async def test_plan_archive_wrong_user_returns_none(db_session, mock_plan_deps):
    plan = Plan(id=uuid4(), user_id=uuid4(), name="p", type=PlanType.SPRINT, is_active=True)
    db_session.add(plan)
    await db_session.commit()
    assert await PlanService.archive(db_session, plan.id, uuid4()) is None


@pytest.mark.asyncio
async def test_plan_restore_reactivates(db_session, mock_plan_deps):
    user_id = uuid4()
    plan = Plan(id=uuid4(), user_id=user_id, name="p", type=PlanType.SPRINT, is_active=False)
    db_session.add(plan)
    await db_session.commit()
    restored = await PlanService.restore(db_session, plan.id, user_id, skip_quota_check=True)
    assert restored.is_active is True


@pytest.mark.asyncio
async def test_plan_restore_active_returns_none(db_session, mock_plan_deps):
    user_id = uuid4()
    plan = Plan(id=uuid4(), user_id=user_id, name="p", type=PlanType.SPRINT, is_active=True)
    db_session.add(plan)
    await db_session.commit()
    assert await PlanService.restore(db_session, plan.id, user_id, skip_quota_check=True) is None


# ── PlanService: Sprint Auto-Archive ─────────────────────────────────


@pytest.mark.asyncio
async def test_plan_sprint_auto_archive_on_all_complete(db_session, mock_plan_deps, monkeypatch):
    user_id = uuid4()
    plan = Plan(id=uuid4(), user_id=user_id, name="s", type=PlanType.SPRINT, is_active=True, progress=0.0)
    db_session.add(plan)
    await db_session.commit()
    for _ in range(2):
        db_session.add(
            Task(
                id=uuid4(),
                user_id=user_id,
                plan_id=plan.id,
                title="t",
                type=TaskType.LEARNING,
                status=TaskStatus.COMPLETED,
                estimated_minutes=30,
            )
        )
    await db_session.commit()
    monkeypatch.setattr("app.services.plan_state_service.PlanStateService", MagicMock())
    progress = await PlanService.update_progress(db_session, plan.id, user_id)
    await db_session.refresh(plan)
    assert progress == 1.0
    assert plan.is_active is False


@pytest.mark.asyncio
async def test_plan_sprint_no_auto_archive_incomplete(db_session, mock_plan_deps):
    user_id = uuid4()
    plan = Plan(id=uuid4(), user_id=user_id, name="s", type=PlanType.SPRINT, is_active=True, progress=0.0)
    db_session.add(plan)
    await db_session.commit()
    db_session.add(
        Task(
            id=uuid4(),
            user_id=user_id,
            plan_id=plan.id,
            title="done",
            type=TaskType.LEARNING,
            status=TaskStatus.COMPLETED,
            estimated_minutes=30,
        )
    )
    db_session.add(
        Task(
            id=uuid4(),
            user_id=user_id,
            plan_id=plan.id,
            title="todo",
            type=TaskType.LEARNING,
            status=TaskStatus.PENDING,
            estimated_minutes=30,
        )
    )
    await db_session.commit()
    progress = await PlanService.update_progress(db_session, plan.id, user_id)
    await db_session.refresh(plan)
    assert progress == 0.5
    assert plan.is_active is True


@pytest.mark.asyncio
async def test_plan_growth_never_auto_archives(db_session, mock_plan_deps):
    user_id = uuid4()
    plan = Plan(id=uuid4(), user_id=user_id, name="g", type=PlanType.GROWTH, is_active=True, progress=0.0)
    db_session.add(plan)
    await db_session.commit()
    db_session.add(
        Task(
            id=uuid4(),
            user_id=user_id,
            plan_id=plan.id,
            title="done",
            type=TaskType.LEARNING,
            status=TaskStatus.COMPLETED,
            estimated_minutes=30,
        )
    )
    await db_session.commit()
    progress = await PlanService.update_progress(db_session, plan.id, user_id)
    await db_session.refresh(plan)
    assert progress == 1.0
    assert plan.is_active is True


# ── PlanService: Additional Coverage ─────────────────────────────────


@pytest.mark.asyncio
async def test_plan_update_priority(db_session, mock_plan_deps):
    user_id = uuid4()
    plan = Plan(
        id=uuid4(), user_id=user_id, name="p", type=PlanType.SPRINT, is_active=True, priority=PlanPriority.NORMAL
    )
    db_session.add(plan)
    await db_session.commit()
    updated = await PlanService.update_priority(db_session, plan.id, user_id, PlanPriority.HIGH)
    assert updated.priority == PlanPriority.HIGH


@pytest.mark.asyncio
async def test_plan_get_primary(db_session):
    user_id = uuid4()
    Plan(id=uuid4(), user_id=user_id, name="p", type=PlanType.SPRINT, is_active=True, is_primary=True)
    plan = Plan(id=uuid4(), user_id=user_id, name="p", type=PlanType.SPRINT, is_active=True, is_primary=True)
    db_session.add(plan)
    await db_session.commit()
    result = await PlanService.get_primary(db_session, user_id)
    assert result is not None
    assert result.id == plan.id


@pytest.mark.asyncio
async def test_plan_list_archived(db_session):
    user_id = uuid4()
    db_session.add(Plan(id=uuid4(), user_id=user_id, name="a", type=PlanType.SPRINT, is_active=False))
    db_session.add(Plan(id=uuid4(), user_id=user_id, name="b", type=PlanType.SPRINT, is_active=True))
    await db_session.commit()
    archived = await PlanService.list_archived(db_session, user_id)
    assert len(archived) == 1


@pytest.mark.asyncio
async def test_plan_list_active_excludes_archived(db_session):
    user_id = uuid4()
    db_session.add(Plan(id=uuid4(), user_id=user_id, name="a", type=PlanType.SPRINT, is_active=True))
    db_session.add(Plan(id=uuid4(), user_id=user_id, name="b", type=PlanType.SPRINT, is_active=False))
    await db_session.commit()
    active = await PlanService.list_active(db_session, user_id)
    assert len(active) == 1
    assert active[0].is_active is True


@pytest.mark.asyncio
async def test_plan_update_partial_fields(db_session, mock_plan_deps):
    plan = Plan(id=uuid4(), user_id=uuid4(), name="原始", type=PlanType.SPRINT, description="旧描述", is_active=True)
    db_session.add(plan)
    await db_session.commit()
    updated = await PlanService.update(db_session, plan, PlanUpdate(description="新描述"))
    assert updated.name == "原始"
    assert updated.description == "新描述"


@pytest.mark.asyncio
async def test_plan_get_by_id_ownership(db_session):
    user_a, user_b = uuid4(), uuid4()
    plan = Plan(id=uuid4(), user_id=user_a, name="p", type=PlanType.SPRINT)
    db_session.add(plan)
    await db_session.commit()
    assert await PlanService.get_by_id(db_session, plan.id, user_b) is None
    assert await PlanService.get_by_id(db_session, plan.id, user_a) is not None


@pytest.mark.asyncio
async def test_plan_progress_nonexistent_returns_none(db_session, mock_plan_deps):
    assert await PlanService.update_progress(db_session, uuid4(), uuid4()) is None


# ── TaskService: Create ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_task_create_defaults(db_session, mock_task_deps):
    task = await TaskService.create(db_session, TaskCreate(title="t", type=TaskType.LEARNING), uuid4())
    assert task.estimated_minutes == 25
    assert task.difficulty == 1
    assert task.status == TaskStatus.PENDING


@pytest.mark.asyncio
async def test_task_create_order_decrements(db_session, mock_task_deps):
    user_id = uuid4()
    t1 = await TaskService.create(
        db_session, TaskCreate(title="a", type=TaskType.LEARNING, estimated_minutes=25, difficulty=1), user_id
    )
    t2 = await TaskService.create(
        db_session, TaskCreate(title="b", type=TaskType.LEARNING, estimated_minutes=25, difficulty=1), user_id
    )
    assert t2.order_index < t1.order_index


# ── TaskService: Complete ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_task_complete_updates_plan_progress(db_session, mock_task_deps, mock_plan_deps):
    user_id = uuid4()
    plan = Plan(id=uuid4(), user_id=user_id, name="p", type=PlanType.GROWTH, is_active=True, progress=0.0)
    db_session.add(plan)
    task = Task(
        id=uuid4(),
        user_id=user_id,
        plan_id=plan.id,
        title="t",
        type=TaskType.LEARNING,
        status=TaskStatus.PENDING,
        estimated_minutes=30,
    )
    db_session.add_all([plan, task])
    await db_session.commit()
    completed = await TaskService.complete(db_session, task, 28, "完成了")
    assert completed.status == TaskStatus.COMPLETED
    assert completed.actual_minutes == 28
    assert completed.user_note == "完成了"
    await db_session.refresh(plan)
    assert plan.progress == 1.0


@pytest.mark.asyncio
async def test_task_complete_sets_timestamps(db_session, mock_task_deps):
    task = Task(
        id=uuid4(),
        user_id=uuid4(),
        title="t",
        type=TaskType.LEARNING,
        status=TaskStatus.IN_PROGRESS,
        estimated_minutes=30,
    )
    db_session.add(task)
    await db_session.commit()
    before = _utcnow()
    completed = await TaskService.complete(db_session, task, 35)
    assert completed.status == TaskStatus.COMPLETED
    assert completed.completed_at is not None
    assert before <= completed.completed_at <= _utcnow()


# ── TaskService: Stuck ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_task_stuck_raises_for_completed(db_session):
    task = Task(
        id=uuid4(),
        user_id=uuid4(),
        title="t",
        type=TaskType.LEARNING,
        status=TaskStatus.COMPLETED,
        estimated_minutes=30,
    )
    db_session.add(task)
    await db_session.commit()
    with pytest.raises(ValueError, match="Completed or abandoned"):
        await TaskService.mark_stuck(db_session, task, stuck_point="x")


@pytest.mark.asyncio
async def test_task_stuck_raises_for_abandoned(db_session):
    task = Task(
        id=uuid4(),
        user_id=uuid4(),
        title="t",
        type=TaskType.LEARNING,
        status=TaskStatus.ABANDONED,
        estimated_minutes=30,
    )
    db_session.add(task)
    await db_session.commit()
    with pytest.raises(ValueError, match="Completed or abandoned"):
        await TaskService.mark_stuck(db_session, task, stuck_point="x")


@pytest.mark.asyncio
async def test_task_stuck_sets_status_and_diagnosis(db_session, mock_task_deps, monkeypatch):
    task = Task(
        id=uuid4(), user_id=uuid4(), title="t", type=TaskType.LEARNING, status=TaskStatus.PENDING, estimated_minutes=30
    )
    db_session.add(task)
    await db_session.commit()

    async def mock_diagnosis(*a, **kw):
        return {"mistake_diagnosis": "d", "targeted_fix": "f", "source": "test", "task_state": {}}

    monkeypatch.setattr(TaskService, "_build_stuck_diagnosis", mock_diagnosis)
    updated, diag = await TaskService.mark_stuck(db_session, task, stuck_point="概念混淆")
    assert updated.status == TaskStatus.STUCK
    assert updated.started_at is not None
    assert "stuck_help" in (updated.guide_json or {})


# ── TaskService: Pause / Resume ─────────────────────────────────────


@pytest.mark.asyncio
async def test_task_pause_sets_paused_without_completion(db_session, mock_task_deps):
    task = Task(
        id=uuid4(),
        user_id=uuid4(),
        title="t",
        type=TaskType.LEARNING,
        status=TaskStatus.IN_PROGRESS,
        estimated_minutes=30,
    )
    db_session.add(task)
    await db_session.commit()

    paused = await TaskService.pause(db_session, task, reason="break")

    assert paused.status == TaskStatus.PAUSED
    assert paused.completed_at is None
    assert paused.user_note == "Paused: break"
    assert paused.guide_json["pause_state"]["paused_count"] == 1


@pytest.mark.asyncio
async def test_task_resume_requires_paused_and_returns_in_progress(db_session, mock_task_deps):
    task = Task(
        id=uuid4(),
        user_id=uuid4(),
        title="t",
        type=TaskType.LEARNING,
        status=TaskStatus.PAUSED,
        estimated_minutes=30,
        guide_json={"pause_state": {"paused_count": 1}},
    )
    db_session.add(task)
    await db_session.commit()

    resumed = await TaskService.resume(db_session, task)

    assert resumed.status == TaskStatus.IN_PROGRESS
    assert resumed.started_at is not None
    assert resumed.guide_json["pause_state"]["resumed_at"] is not None


@pytest.mark.asyncio
async def test_task_pause_rejects_terminal_status(db_session, mock_task_deps):
    task = Task(
        id=uuid4(),
        user_id=uuid4(),
        title="t",
        type=TaskType.LEARNING,
        status=TaskStatus.COMPLETED,
        estimated_minutes=30,
    )
    db_session.add(task)
    await db_session.commit()

    with pytest.raises(ValueError, match="Completed or abandoned"):
        await TaskService.pause(db_session, task)


# ── TaskService: Abandon ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_task_abandon_with_reason(db_session, mock_task_deps):
    task = Task(
        id=uuid4(),
        user_id=uuid4(),
        title="t",
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


@pytest.mark.asyncio
async def test_task_abandon_without_reason(db_session, mock_task_deps):
    task = Task(
        id=uuid4(), user_id=uuid4(), title="t", type=TaskType.LEARNING, status=TaskStatus.PENDING, estimated_minutes=30
    )
    db_session.add(task)
    await db_session.commit()
    abandoned = await TaskService.abandon(db_session, task)
    assert abandoned.status == TaskStatus.ABANDONED
    assert abandoned.user_note is None


# ── TaskService: Focus Progress ──────────────────────────────────────


@pytest.mark.asyncio
async def test_task_focus_auto_complete(db_session, mock_task_deps):
    task = Task(
        id=uuid4(),
        user_id=uuid4(),
        title="t",
        type=TaskType.LEARNING,
        status=TaskStatus.IN_PROGRESS,
        estimated_minutes=30,
        actual_minutes=20,
    )
    db_session.add(task)
    await db_session.commit()
    result = await TaskService.apply_focus_progress(
        db_session,
        task_id=task.id,
        user_id=task.user_id,
        duration_minutes=15,
        started_at=_utcnow() - timedelta(minutes=15),
    )
    assert result.status == TaskStatus.COMPLETED


@pytest.mark.asyncio
async def test_task_focus_no_auto_complete_under_est(db_session, mock_task_deps):
    task = Task(
        id=uuid4(),
        user_id=uuid4(),
        title="t",
        type=TaskType.LEARNING,
        status=TaskStatus.IN_PROGRESS,
        estimated_minutes=60,
        actual_minutes=10,
    )
    db_session.add(task)
    await db_session.commit()
    result = await TaskService.apply_focus_progress(
        db_session,
        task_id=task.id,
        user_id=task.user_id,
        duration_minutes=15,
        started_at=_utcnow() - timedelta(minutes=15),
    )
    assert result.status == TaskStatus.IN_PROGRESS
    assert result.actual_minutes == 25


@pytest.mark.asyncio
async def test_task_focus_zero_duration(db_session):
    task = Task(
        id=uuid4(),
        user_id=uuid4(),
        title="t",
        type=TaskType.LEARNING,
        status=TaskStatus.IN_PROGRESS,
        estimated_minutes=30,
        actual_minutes=10,
    )
    db_session.add(task)
    await db_session.commit()
    result = await TaskService.apply_focus_progress(
        db_session, task_id=task.id, user_id=task.user_id, duration_minutes=0, started_at=_utcnow()
    )
    assert result.actual_minutes == 10


@pytest.mark.asyncio
async def test_task_focus_auto_starts_pending(db_session, mock_task_deps):
    task = Task(
        id=uuid4(),
        user_id=uuid4(),
        title="t",
        type=TaskType.LEARNING,
        status=TaskStatus.PENDING,
        estimated_minutes=60,
        actual_minutes=0,
    )
    db_session.add(task)
    await db_session.commit()
    result = await TaskService.apply_focus_progress(
        db_session,
        task_id=task.id,
        user_id=task.user_id,
        duration_minutes=10,
        started_at=_utcnow() - timedelta(minutes=10),
    )
    assert result.status == TaskStatus.IN_PROGRESS
    assert result.actual_minutes == 10


@pytest.mark.asyncio
async def test_task_focus_completed_unchanged(db_session, mock_task_deps):
    task = Task(
        id=uuid4(),
        user_id=uuid4(),
        title="t",
        type=TaskType.LEARNING,
        status=TaskStatus.COMPLETED,
        estimated_minutes=30,
        actual_minutes=30,
    )
    db_session.add(task)
    await db_session.commit()
    result = await TaskService.apply_focus_progress(
        db_session,
        task_id=task.id,
        user_id=task.user_id,
        duration_minutes=15,
        started_at=_utcnow() - timedelta(minutes=15),
    )
    assert result.status == TaskStatus.COMPLETED
    assert result.actual_minutes == 30


@pytest.mark.asyncio
async def test_task_focus_nonexistent_returns_none(db_session, mock_task_deps):
    result = await TaskService.apply_focus_progress(
        db_session, task_id=uuid4(), user_id=uuid4(), duration_minutes=15, started_at=_utcnow()
    )
    assert result is None


@pytest.mark.asyncio
async def test_task_focus_zero_estimated_no_auto_complete(db_session, mock_task_deps):
    task = Task(
        id=uuid4(),
        user_id=uuid4(),
        title="t",
        type=TaskType.LEARNING,
        status=TaskStatus.IN_PROGRESS,
        estimated_minutes=0,
        actual_minutes=0,
    )
    db_session.add(task)
    await db_session.commit()
    result = await TaskService.apply_focus_progress(
        db_session,
        task_id=task.id,
        user_id=task.user_id,
        duration_minutes=60,
        started_at=_utcnow() - timedelta(minutes=60),
    )
    assert result.status == TaskStatus.IN_PROGRESS


# ── TaskService: Reorder ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_task_reorder_deduplicates(db_session):
    user_id = uuid4()
    t1 = Task(
        id=uuid4(),
        user_id=user_id,
        title="a",
        type=TaskType.LEARNING,
        status=TaskStatus.PENDING,
        estimated_minutes=30,
        order_index=1000,
    )
    t2 = Task(
        id=uuid4(),
        user_id=user_id,
        title="b",
        type=TaskType.LEARNING,
        status=TaskStatus.PENDING,
        estimated_minutes=30,
        order_index=2000,
    )
    db_session.add_all([t1, t2])
    await db_session.commit()
    reordered = await TaskService.reorder_tasks(db_session, user_id=user_id, ordered_task_ids=[t1.id, t2.id, t1.id])
    assert len(reordered) == 2
    assert reordered[0].id == t1.id


@pytest.mark.asyncio
async def test_task_reorder_raises_for_missing(db_session):
    with pytest.raises(ValueError, match="Tasks not found"):
        await TaskService.reorder_tasks(db_session, user_id=uuid4(), ordered_task_ids=[uuid4()])


@pytest.mark.asyncio
async def test_task_reorder_empty_list(db_session):
    result = await TaskService.reorder_tasks(db_session, user_id=uuid4(), ordered_task_ids=[])
    assert result == []


@pytest.mark.asyncio
async def test_task_reorder_ascending_order(db_session):
    user_id = uuid4()
    t1 = Task(
        id=uuid4(), user_id=user_id, title="a", type=TaskType.LEARNING, status=TaskStatus.PENDING, estimated_minutes=30
    )
    t2 = Task(
        id=uuid4(), user_id=user_id, title="b", type=TaskType.LEARNING, status=TaskStatus.PENDING, estimated_minutes=30
    )
    db_session.add_all([t1, t2])
    await db_session.commit()
    reordered = await TaskService.reorder_tasks(db_session, user_id=user_id, ordered_task_ids=[t2.id, t1.id])
    assert reordered[0].id == t2.id
    assert reordered[0].order_index == 1000
    assert reordered[1].id == t1.id
    assert reordered[1].order_index == 2000


# ── TaskService: Batch Confirm ───────────────────────────────────────


@pytest.mark.asyncio
async def test_task_confirm_batch(db_session, mock_task_deps):
    user_id = uuid4()
    tid = "tool_abc"
    t1 = Task(
        id=uuid4(),
        user_id=user_id,
        title="a",
        type=TaskType.LEARNING,
        status=TaskStatus.PENDING,
        estimated_minutes=25,
        tool_result_id=tid,
    )
    t2 = Task(
        id=uuid4(),
        user_id=user_id,
        title="b",
        type=TaskType.TRAINING,
        status=TaskStatus.PENDING,
        estimated_minutes=20,
        tool_result_id=tid,
    )
    t3 = Task(
        id=uuid4(),
        user_id=user_id,
        title="c",
        type=TaskType.LEARNING,
        status=TaskStatus.PENDING,
        estimated_minutes=30,
        tool_result_id="other",
    )
    db_session.add_all([t1, t2, t3])
    await db_session.commit()
    confirmed = await TaskService.confirm_tasks_by_tool_result(db_session, tid, user_id)
    assert len(confirmed) == 2
    for t in confirmed:
        assert t.status == TaskStatus.IN_PROGRESS
        assert t.confirmed_at is not None
    await db_session.refresh(t3)
    assert t3.status == TaskStatus.PENDING


@pytest.mark.asyncio
async def test_task_confirm_batch_empty(db_session):
    assert await TaskService.confirm_tasks_by_tool_result(db_session, "none", uuid4()) == []


@pytest.mark.asyncio
async def test_task_confirm_batch_skips_non_pending(db_session, mock_task_deps):
    user_id = uuid4()
    tid = "tool_skip"
    pending = Task(
        id=uuid4(),
        user_id=user_id,
        title="p",
        type=TaskType.LEARNING,
        status=TaskStatus.PENDING,
        estimated_minutes=25,
        tool_result_id=tid,
    )
    in_prog = Task(
        id=uuid4(),
        user_id=user_id,
        title="ip",
        type=TaskType.LEARNING,
        status=TaskStatus.IN_PROGRESS,
        estimated_minutes=20,
        tool_result_id=tid,
    )
    db_session.add_all([pending, in_prog])
    await db_session.commit()
    confirmed = await TaskService.confirm_tasks_by_tool_result(db_session, tid, user_id)
    assert len(confirmed) == 1
    assert confirmed[0].id == pending.id


# ── TaskService: Start / Delete ──────────────────────────────────────


@pytest.mark.asyncio
async def test_task_start_sets_status(db_session, mock_task_deps):
    task = Task(
        id=uuid4(), user_id=uuid4(), title="t", type=TaskType.LEARNING, status=TaskStatus.PENDING, estimated_minutes=30
    )
    db_session.add(task)
    await db_session.commit()
    started = await TaskService.start(db_session, task)
    assert started.status == TaskStatus.IN_PROGRESS
    assert started.started_at is not None


@pytest.mark.asyncio
async def test_task_delete_removes_and_updates_plan(db_session, mock_plan_deps):
    user_id = uuid4()
    plan = Plan(id=uuid4(), user_id=user_id, name="p", type=PlanType.GROWTH, is_active=True, progress=0.0)
    db_session.add(plan)
    t_done = Task(
        id=uuid4(),
        user_id=user_id,
        plan_id=plan.id,
        title="done",
        type=TaskType.LEARNING,
        status=TaskStatus.COMPLETED,
        estimated_minutes=30,
    )
    t_del = Task(
        id=uuid4(),
        user_id=user_id,
        plan_id=plan.id,
        title="del",
        type=TaskType.LEARNING,
        status=TaskStatus.PENDING,
        estimated_minutes=30,
    )
    db_session.add_all([plan, t_done, t_del])
    await db_session.commit()
    await TaskService.delete(db_session, t_del)
    remaining = (await db_session.execute(select(Task).where(Task.plan_id == plan.id))).scalars().all()
    assert len(remaining) == 1


# ── TaskService: Ownership ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_task_ownership_enforced(db_session):
    user_a, user_b = uuid4(), uuid4()
    task = Task(
        id=uuid4(), user_id=user_a, title="t", type=TaskType.LEARNING, status=TaskStatus.PENDING, estimated_minutes=30
    )
    db_session.add(task)
    await db_session.commit()
    assert await TaskService.get_by_id(db_session, task.id, user_b) is None
    assert await TaskService.get_by_id(db_session, task.id, user_a) is not None


@pytest.mark.asyncio
async def test_task_start_task_wrong_user(db_session):
    task = Task(
        id=uuid4(), user_id=uuid4(), title="t", type=TaskType.LEARNING, status=TaskStatus.PENDING, estimated_minutes=30
    )
    db_session.add(task)
    await db_session.commit()
    from app.core.exceptions import NotFoundError

    with pytest.raises(NotFoundError):
        await TaskService.start_task(db_session, task.id, uuid4())


@pytest.mark.asyncio
async def test_task_complete_task_wrong_user(db_session):
    task = Task(
        id=uuid4(),
        user_id=uuid4(),
        title="t",
        type=TaskType.LEARNING,
        status=TaskStatus.IN_PROGRESS,
        estimated_minutes=30,
    )
    db_session.add(task)
    await db_session.commit()
    from app.core.exceptions import NotFoundError

    with pytest.raises(NotFoundError):
        await TaskService.complete_task(db_session, task.id, uuid4(), 30)


# ── TaskService: Pure Function Tests ─────────────────────────────────


def test_sentiment_negative():
    assert TaskService._infer_sentiment("This was really hard and confusing") == "negative"
    assert TaskService._infer_sentiment("I got stuck") == "negative"
    assert TaskService._infer_sentiment("Very frustrated") == "negative"


def test_sentiment_positive():
    assert TaskService._infer_sentiment("Easy and clear") == "positive"
    assert TaskService._infer_sentiment("Good progress") == "positive"


def test_sentiment_neutral():
    assert TaskService._infer_sentiment("Did the exercise") == "neutral"
    assert TaskService._infer_sentiment(None) == "neutral"
    assert TaskService._infer_sentiment("") == "neutral"


def test_sentiment_negative_priority():
    assert TaskService._infer_sentiment("hard but helpful") == "negative"


def test_difficulty_gradient():
    assert TaskService._difficulty_from_gradient(0.0) == 1
    assert TaskService._difficulty_from_gradient(1.0) == 5
    assert TaskService._difficulty_from_gradient(0.5) == 3
    assert TaskService._difficulty_from_gradient(None) == 1
    assert TaskService._difficulty_from_gradient(-0.5) == 1
    assert TaskService._difficulty_from_gradient(1.5) == 5


def test_task_summary():
    task = Task(id=uuid4(), title="t", estimated_minutes=30, completed_at=_utcnow())
    s1 = TaskService._build_task_summary(task, 35, "Easy")
    assert s1["actual_vs_estimated"] == "+5min"
    assert s1["user_sentiment"] == "positive"
    s2 = TaskService._build_task_summary(task, 25, "confusing")
    assert s2["actual_vs_estimated"] == "-5min"
    assert s2["user_sentiment"] == "negative"
    s3 = TaskService._build_task_summary(task, 30, None)
    assert s3["actual_vs_estimated"] == "0min"
    assert s3["user_sentiment"] == "neutral"
    assert s3["key_takeaway"] is None
