"""X-04 · Human Action Flow + Completion Evidence 验收测试.

覆盖（卡面 Acceptance 一一对应）：
- 四态流转：start / complete / abandon / rescope 各路径 + reopen；
- completion evidence 分型：按 action 类型路由（artifact/self-report/test）、
  无证据时回落类型正确（诚实分级，绝不伪造）、plan 声明保留 + fulfilled 标记；
- **实际时长不从 estimated 回填**（灵魂红线钉住：estimated=60min 实际 5min
  断言 actual=5；abandon 未开始 → actual=None 而非 estimated）；
- 重开保留状态（终态快照归档 reopen_history，actual 只反映本轮真实起止）；
- focus 自动完成 evidence 打型 system_event（focus timer ≠ 学习成果）；
- X-03 命令路径 complete 同样不回填。
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task, TaskStatus, TaskType
from app.models.user import User
from app.services.task_completion_evidence import (
    ABANDON_RECORD_KEY,
    COMPLETION_EVIDENCE_RECORD_KEY,
    RESCOPE_HISTORY_KEY,
    REOPEN_HISTORY_KEY,
    build_completion_evidence_record,
    compute_actual_minutes_from_timestamps,
    expected_evidence_kinds,
    resolve_spark_study_minutes,
    validate_evidence_entries,
)
from app.services.task_service import TaskService


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def _make_user(db_session: AsyncSession) -> User:
    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    db_session.add(user)
    await db_session.commit()
    return user


async def _make_task(
    db_session: AsyncSession,
    user: User,
    *,
    status: TaskStatus = TaskStatus.PENDING,
    task_type: TaskType = TaskType.LEARNING,
    estimated: int = 60,
    started_at: datetime | None = None,
    extra: dict | None = None,
) -> Task:
    task = Task(
        user_id=user.id,
        title="X-04 验收任务",
        type=task_type,
        tags=["x04"],
        estimated_minutes=estimated,
        difficulty=3,
        energy_cost=2,
        status=status,
        started_at=started_at,
    )
    for key, value in (extra or {}).items():
        setattr(task, key, value)
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    return task


def _latest_evidence_record(task: Task) -> dict:
    records = (task.guide_json or {}).get(COMPLETION_EVIDENCE_RECORD_KEY)
    assert isinstance(records, list) and records, "completion evidence record must be appended"
    return records[-1]


# ---------------------------------------------------------------------------
# actual 时长真源（红线：永不从 estimated 回填）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_complete_derives_actual_from_real_timestamps_not_estimated(db_session):
    """钉住：estimated=60min、真实投入≈5min → actual≈5，绝不等于 60。"""
    user = await _make_user(db_session)
    task = await _make_task(
        db_session, user, status=TaskStatus.IN_PROGRESS, estimated=60, started_at=_now() - timedelta(minutes=5)
    )
    completed = await TaskService.complete(db_session, task, None)
    assert completed.status == TaskStatus.COMPLETED
    assert completed.actual_minutes is not None
    assert 4 <= completed.actual_minutes <= 6, "actual must be derived from real start/end"
    assert completed.actual_minutes != 60, "RED LINE: actual must never be backfilled from estimated"


@pytest.mark.asyncio
async def test_complete_explicit_measured_value_wins(db_session):
    user = await _make_user(db_session)
    task = await _make_task(
        db_session, user, status=TaskStatus.IN_PROGRESS, estimated=60, started_at=_now() - timedelta(minutes=30)
    )
    completed = await TaskService.complete(db_session, task, 5)
    assert completed.actual_minutes == 5


@pytest.mark.asyncio
async def test_complete_subtracts_paused_intervals(db_session):
    user = await _make_user(db_session)
    started = _now() - timedelta(minutes=10)
    task = await _make_task(
        db_session,
        user,
        status=TaskStatus.IN_PROGRESS,
        estimated=60,
        started_at=started,
        extra={"guide_json": {"pause_state": {"total_paused_seconds": 180}}},
    )
    completed = await TaskService.complete(db_session, task, None)
    assert 6 <= completed.actual_minutes <= 8  # 10min wall − 3min paused


@pytest.mark.asyncio
async def test_complete_rejects_nonpositive_measured_minutes(db_session):
    user = await _make_user(db_session)
    task = await _make_task(db_session, user, status=TaskStatus.IN_PROGRESS, started_at=_now())
    with pytest.raises(ValueError):
        await TaskService.complete(db_session, task, 0)


@pytest.mark.asyncio
async def test_abandon_without_start_keeps_actual_none_never_estimated(db_session):
    """PENDING 直接放弃：从未开始 → actual=None（不是 estimated=60）。"""
    user = await _make_user(db_session)
    task = await _make_task(db_session, user, status=TaskStatus.PENDING, estimated=60)
    abandoned = await TaskService.abandon(db_session, task, reason="不学了")
    assert abandoned.status == TaskStatus.ABANDONED
    assert abandoned.actual_minutes is None, "RED LINE: unstarted abandon must not backfill estimated"


@pytest.mark.asyncio
async def test_abandon_persists_real_trace(db_session):
    """放弃留痕：真实时长持久化 + abandon_record 归档（原因/时刻/此前状态）。"""
    user = await _make_user(db_session)
    task = await _make_task(
        db_session, user, status=TaskStatus.IN_PROGRESS, estimated=60, started_at=_now() - timedelta(minutes=10)
    )
    abandoned = await TaskService.abandon(db_session, task, reason="卡住了")
    assert 9 <= abandoned.actual_minutes <= 12
    records = (abandoned.guide_json or {}).get(ABANDON_RECORD_KEY)
    assert isinstance(records, list) and len(records) == 1
    record = records[0]
    assert record["reason"] == "卡住了"
    assert record["status_before"] == TaskStatus.IN_PROGRESS.value
    assert record["actual_minutes"] == abandoned.actual_minutes


def test_galaxy_spark_minutes_never_estimated():
    """galaxy spark study_minutes：只认真实时长，缺省 0（绝不 estimated 回填）。"""
    assert resolve_spark_study_minutes(None) == 0
    assert resolve_spark_study_minutes(0) == 0
    assert resolve_spark_study_minutes(12) == 12


def test_compute_actual_requires_started_at():
    task = Task(estimated_minutes=45)  # 未开始
    assert compute_actual_minutes_from_timestamps(task, ended_at=_now()) is None


# ---------------------------------------------------------------------------
# start / resume：真实起点只设一次
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_start_sets_started_once_and_resume_preserves_it(db_session):
    user = await _make_user(db_session)
    task = await _make_task(db_session, user, status=TaskStatus.PENDING)
    started = await TaskService.start(db_session, task)
    assert started.status == TaskStatus.IN_PROGRESS
    first_started_at = started.started_at
    assert first_started_at is not None

    paused = await TaskService.pause(db_session, started, reason="歇会")
    assert paused.status == TaskStatus.PAUSED
    resumed = await TaskService.resume(db_session, paused)
    assert resumed.status == TaskStatus.IN_PROGRESS
    assert resumed.started_at == first_started_at, "resume must not reset the real start"


# ---------------------------------------------------------------------------
# completion evidence 分型（无证据时类型正确；plan 声明保留）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_complete_without_evidence_falls_back_to_honest_type(db_session):
    """无证据完成：类型正确（用户显式确认 → user_confirmation），绝不伪造 artifact。"""
    user = await _make_user(db_session)
    task = await _make_task(
        db_session, user, status=TaskStatus.IN_PROGRESS, task_type=TaskType.REFLECTION, started_at=_now()
    )
    completed = await TaskService.complete(db_session, task, 5)
    record = _latest_evidence_record(completed)
    assert record["source"] == "user"
    assert record["entries"][0]["evidence_kind"] == "user_confirmation"
    assert record["entries"][0]["origin"] == "fallback"


def test_expected_evidence_kinds_route_by_action_type():
    def _task(task_type: TaskType, **extra):
        return Task(type=task_type, **extra)

    assert expected_evidence_kinds(_task(TaskType.OCR)) == ("artifact",)
    assert expected_evidence_kinds(_task(TaskType.PLANNING)) == ("artifact",)
    assert expected_evidence_kinds(_task(TaskType.TRAINING)) == ("quiz_result",)
    assert expected_evidence_kinds(_task(TaskType.ERROR_FIX)) == ("quiz_result",)
    assert expected_evidence_kinds(_task(TaskType.REFLECTION)) == ("self_report",)
    # agent 代执行：系统事件（run receipt）是第一手证据
    assert expected_evidence_kinds(_task(TaskType.LEARNING, execution_mode="agent"))[0] == "system_event"


@pytest.mark.asyncio
async def test_plan_declared_kinds_preserved_and_marked_unfulfilled(db_session):
    """plan 侧声明（X-01 列）不被覆写；无证据完成时 declared 保留且 fulfilled=False。"""
    user = await _make_user(db_session)
    declared = [{"evidence_kind": "artifact", "ref": None, "description": "笔记产物"}]
    task = await _make_task(
        db_session,
        user,
        status=TaskStatus.IN_PROGRESS,
        task_type=TaskType.LEARNING,
        started_at=_now(),
        extra={"action_schema_version": "action_plan.v1", "completion_evidence": declared},
    )
    completed = await TaskService.complete(db_session, task, 5)
    # X-01 声明列保持原样（plan 侧语义，契约冻结）
    assert completed.completion_evidence == declared
    record = _latest_evidence_record(completed)
    assert record["declared_kinds"] == ["artifact"]
    assert record["fulfilled"] is False
    assert record["entries"][0]["evidence_kind"] == "user_confirmation"


@pytest.mark.asyncio
async def test_provided_evidence_validated_and_marks_fulfilled(db_session):
    user = await _make_user(db_session)
    declared = [{"evidence_kind": "artifact", "ref": None, "description": None}]
    task = await _make_task(
        db_session,
        user,
        status=TaskStatus.IN_PROGRESS,
        started_at=_now(),
        extra={"action_schema_version": "action_plan.v1", "completion_evidence": declared},
    )
    completed = await TaskService.complete(
        db_session,
        task,
        5,
        evidence=[{"evidence_kind": "artifact", "ref": "document://abc", "description": "我的笔记"}],
    )
    record = _latest_evidence_record(completed)
    assert record["fulfilled"] is True
    provided_entry = next(entry for entry in record["entries"] if entry["origin"] == "provided")
    assert provided_entry["evidence_kind"] == "artifact"
    assert provided_entry["ref"] == "document://abc"


def test_evidence_entries_validation_closed_vocabulary():
    with pytest.raises(ValueError):
        validate_evidence_entries([{"evidence_kind": "screenshot_of_glory"}])  # 词表外
    with pytest.raises(ValueError):
        validate_evidence_entries([{"evidence_kind": "artifact", "ref": "ftp://evil"}])  # scheme 封闭
    ok = validate_evidence_entries([{"evidence_kind": "self_report", "ref": None, "description": "done"}])
    assert ok[0]["evidence_kind"] == "self_report"


@pytest.mark.asyncio
async def test_focus_auto_completion_records_system_event_evidence(db_session):
    """focus timer 触发的自动完成：证据来源 focus_auto → system_event（低信任打型）。"""
    user = await _make_user(db_session)
    task = await _make_task(
        db_session, user, status=TaskStatus.IN_PROGRESS, estimated=25, started_at=_now()
    )
    completed = await TaskService.apply_focus_progress(
        db_session, task_id=task.id, user_id=user.id, duration_minutes=25, started_at=_now()
    )
    assert completed.status == TaskStatus.COMPLETED
    record = _latest_evidence_record(completed)
    assert record["source"] == "focus_auto"
    assert record["entries"][0]["evidence_kind"] == "system_event"


def test_build_record_rejects_unknown_source():
    task = Task(type=TaskType.LEARNING)
    with pytest.raises(ValueError):
        build_completion_evidence_record(task, provided=None, source="nobody", completed_at=_now())


# ---------------------------------------------------------------------------
# reopen：重开保留状态
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reopen_completed_preserves_previous_attempt(db_session):
    user = await _make_user(db_session)
    task = await _make_task(db_session, user, status=TaskStatus.IN_PROGRESS, estimated=60, started_at=_now())
    completed = await TaskService.complete(db_session, task, 5)
    prior_completed_at = completed.completed_at
    prior_started_at = completed.started_at

    reopened = await TaskService.reopen(db_session, completed, reason="做错了要重做")
    assert reopened.status == TaskStatus.IN_PROGRESS
    assert reopened.completed_at is None
    assert reopened.actual_minutes is None  # 本轮尚未投入，actual 回到诚实缺省
    assert reopened.started_at > prior_started_at  # 本轮真实起点刷新

    history = (reopened.guide_json or {}).get(REOPEN_HISTORY_KEY)
    assert isinstance(history, list) and len(history) == 1
    snapshot = history[0]
    assert snapshot["status_before"] == TaskStatus.COMPLETED.value
    assert snapshot["actual_minutes"] == 5, "previous real effort must be archived, not wiped"
    assert snapshot["completed_at"] == prior_completed_at.isoformat()
    assert snapshot["completion_evidence_record"], "previous completion evidence must be preserved"
    assert snapshot["reason"] == "做错了要重做"


@pytest.mark.asyncio
async def test_reopen_abandoned_allowed_and_nonterminal_rejected(db_session):
    user = await _make_user(db_session)
    task = await _make_task(db_session, user, status=TaskStatus.ABANDONED)
    reopened = await TaskService.reopen(db_session, task)
    assert reopened.status == TaskStatus.IN_PROGRESS
    assert reopened.completed_at is None

    with pytest.raises(ValueError):
        await TaskService.reopen(db_session, reopened)  # IN_PROGRESS 非终态


# ---------------------------------------------------------------------------
# rescope：stale plan 可重定范围，历史保留
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rescope_updates_fields_and_records_history(db_session):
    user = await _make_user(db_session)
    started_at = _now() - timedelta(minutes=3)
    task = await _make_task(
        db_session, user, status=TaskStatus.STUCK, estimated=60, started_at=started_at
    )
    rescoped = await TaskService.rescope(
        db_session, task, {"estimated_minutes": 15, "success_criteria": "只做第 1-3 题"}, reason="范围太大"
    )
    assert rescoped.estimated_minutes == 15
    assert rescoped.success_criteria == "只做第 1-3 题"
    assert rescoped.status == TaskStatus.STUCK, "rescope 只改口径，不改状态"
    assert rescoped.started_at == started_at, "rescope 不重置真实起点"

    history = (rescoped.guide_json or {}).get(RESCOPE_HISTORY_KEY)
    assert isinstance(history, list) and len(history) == 1
    entry = history[0]
    assert entry["reason"] == "范围太大"
    assert entry["changes"]["estimated_minutes"] == {"before": 60, "after": 15}


@pytest.mark.asyncio
async def test_rescope_terminal_rejected_whitelist_enforced_noop_idempotent(db_session):
    user = await _make_user(db_session)
    task = await _make_task(db_session, user, status=TaskStatus.COMPLETED)
    with pytest.raises(ValueError):
        await TaskService.rescope(db_session, task, {"estimated_minutes": 10})

    active = await _make_task(db_session, user, status=TaskStatus.IN_PROGRESS, started_at=_now())
    with pytest.raises(ValueError):
        await TaskService.rescope(db_session, active, {"status": "COMPLETED"})  # 白名单外

    noop = await TaskService.rescope(db_session, active, {"estimated_minutes": active.estimated_minutes})
    history = (noop.guide_json or {}).get(RESCOPE_HISTORY_KEY)
    assert not history, "zero-effective-change rescope must be an idempotent no-op"


# ---------------------------------------------------------------------------
# X-03 命令路径（task.update_status → complete）同样不回填
# ---------------------------------------------------------------------------


_OUTBOX_DDL = (
    """
    CREATE TABLE IF NOT EXISTS event_outbox (
        id VARCHAR(36) PRIMARY KEY,
        aggregate_type VARCHAR(100) NOT NULL,
        aggregate_id VARCHAR(36) NOT NULL,
        event_type VARCHAR(100) NOT NULL,
        event_version INTEGER NOT NULL DEFAULT 1,
        payload JSON NOT NULL,
        metadata JSON,
        sequence_number INTEGER NOT NULL DEFAULT 1,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        published_at DATETIME
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS event_sequence_counters (
        aggregate_type VARCHAR(100) NOT NULL,
        aggregate_id VARCHAR(36) NOT NULL,
        next_sequence INTEGER NOT NULL,
        PRIMARY KEY (aggregate_type, aggregate_id)
    )
    """,
)


@pytest.fixture(name="outbox_tables")
async def outbox_tables_fixture(db_session):
    for ddl in _OUTBOX_DDL:
        await db_session.execute(text(ddl))
    await db_session.commit()
    yield


@pytest.mark.asyncio
async def test_command_path_complete_does_not_backfill_estimated(db_session, outbox_tables):
    from app.core.action_command import ProposalSource
    from app.services.action_command_service import ActionCommandService

    user = await _make_user(db_session)
    task = await _make_task(
        db_session, user, status=TaskStatus.IN_PROGRESS, estimated=60, started_at=_now() - timedelta(minutes=5)
    )
    service = ActionCommandService(db_session)
    created = await service.create_proposal(
        user_id=user.id,
        command_type="task.update_status",
        payload={"task_id": str(task.id), "to_status": "COMPLETED"},  # 无 actual_minutes
        source=ProposalSource.TASK.value,
    )
    # complete 是终态命令（medium/irreversible）——授权门按设计不允许 auto 直通，
    # 必须经用户显式确认（X-03 语义），这里走 approve 正道
    result = await service.approve(created.proposal.id, user_id=user.id, actor="user")
    assert result.proposal.status == "COMMITTED"
    await db_session.refresh(task)
    assert 4 <= task.actual_minutes <= 6, "command path must derive from real timestamps"
    assert task.actual_minutes != 60, "RED LINE: no estimated backfill on command path"
