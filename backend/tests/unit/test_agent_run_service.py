"""X-05 · AgentRunService 契约测试（幂等/非法迁移/同事务事件/恢复）.

覆盖卡面验收：
- 非法状态迁移测试（IllegalRunTransitionError → API 409 的服务层根源）；
- 重复 run.created / 重复 user_resumed 恰一次（FOR UPDATE+复查 与 唯一索引）；
- 状态+审计+event_outbox 同事务；
- worker restart 恢复（QUEUED 陈旧→CANCELLED、等待过期→TIMED_OUT、孤儿→
  UNKNOWN_OUTCOME、intent 漂移修复）。
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.core.run_state_machine import IllegalRunTransitionError, RunStatus
from app.models.execution_intent import ExecutionIntent
from app.models.user import User
from app.services.agent_run_service import AgentRunService, RunNotFoundError

# event_outbox / event_sequence_counters 最小 sqlite 表（M-07 测试同款 DDL）。
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


async def _make_user(db_session) -> User:
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


async def _make_task(db_session, user: User):
    from app.models.task import Task, TaskStatus, TaskType

    task = Task(
        user_id=user.id,
        title="期末高数复习",
        type=TaskType.LEARNING,
        estimated_minutes=60,
        status=TaskStatus.PENDING,
    )
    db_session.add(task)
    await db_session.commit()
    return task


async def _make_intent(db_session, user: User, *, status=None) -> ExecutionIntent:
    from app.models.execution_intent import ExecutionIntentStatus, ExecutorType, TrustLevel

    task = await _make_task(db_session, user)
    intent = ExecutionIntent(
        plan_id=None,
        task_id=task.id,
        user_id=user.id,
        execution_mode="agent",
        executor=ExecutorType.OPENCLAW,
        goal="Long task goal",
        instructions=[],
        target_env=None,
        policy={},
        success_criteria={},
        result_contract={},
        timeout_seconds=300,
        status=status or ExecutionIntentStatus.READY,
        trust_level=TrustLevel.RAW,
        idempotency_key=f"intent-{uuid4().hex[:12]}",
    )
    db_session.add(intent)
    await db_session.commit()
    return intent


async def _outbox_rows(db_session, event_type: str) -> list[dict]:
    result = await db_session.execute(
        text(
            "SELECT event_type, payload, metadata, sequence_number FROM event_outbox WHERE event_type = :t ORDER BY id"
        ),
        {"t": event_type},
    )
    return [dict(row._mapping) for row in result.all()]


async def _count_transitions(db_session, run_id) -> int:
    result = await db_session.execute(
        text("SELECT COUNT(*) FROM agent_run_transitions WHERE run_id = :r"),
        {"r": str(run_id)},
    )
    return int(result.scalar_one())


# ---------------------------------------------------------------------------
# 1. create 幂等（重复 run.created 恰一次）
# ---------------------------------------------------------------------------


async def test_create_emits_single_created_event(db_session, outbox_tables):
    user = await _make_user(db_session)
    service = AgentRunService(db_session)

    result = await service.create_run(
        user_id=user.id,
        objective="准备期末高数复习计划",
        idempotency_key="handoff-req-001",
    )
    assert result.created is True
    assert result.run.status is RunStatus.QUEUED

    rows = await _outbox_rows(db_session, "run.created")
    assert len(rows) == 1
    payload = json.loads(rows[0]["payload"])
    assert payload["state"] == "QUEUED"
    assert payload["run_id"] == str(result.run.id)
    metadata = json.loads(rows[0]["metadata"])
    assert metadata["schema_version"] == "event.v1"
    assert metadata["correlation"]["run_id"] == str(result.run.id)


async def test_duplicate_create_is_idempotent(db_session, outbox_tables):
    user = await _make_user(db_session)
    service = AgentRunService(db_session)

    first = await service.create_run(user_id=user.id, objective="obj", idempotency_key="k1")
    second = await service.create_run(user_id=user.id, objective="obj", idempotency_key="k1")

    assert second.created is False
    assert second.run.id == first.run.id
    # 恰一次：outbox 仍只有一条 run.created，审计仍只有一行创建记录。
    assert len(await _outbox_rows(db_session, "run.created")) == 1
    assert await _count_transitions(db_session, first.run.id) == 1


# ---------------------------------------------------------------------------
# 2. 迁移合法性 + 同事务审计/事件
# ---------------------------------------------------------------------------


async def test_happy_path_lifecycle_with_events(db_session, outbox_tables):
    user = await _make_user(db_session)
    service = AgentRunService(db_session)
    created = await service.create_run(user_id=user.id, objective="obj", idempotency_key="k")

    r1 = await service.transition(created.run.id, RunStatus.RUNNING, actor="worker")
    assert r1.applied and r1.event_name == "run.status_changed"

    r2 = await service.transition(created.run.id, RunStatus.AWAITING_USER, actor="worker", wait_kind="user_step")
    assert r2.applied and r2.event_name == "run.awaiting_user"
    assert r2.run.wait_kind == "user_step"

    r3 = await service.transition(created.run.id, RunStatus.RUNNING, actor="user", idempotency_key="resume-1")
    assert r3.applied and r3.event_name == "run.user_resumed"

    await service.transition(created.run.id, RunStatus.EXECUTING, actor="worker")
    r5 = await service.transition(created.run.id, RunStatus.SUCCEEDED, actor="worker", reason="completed")
    assert r5.applied and r5.run.completed_at is not None
    assert r5.run.terminal_reason == "completed"

    # 每次有效迁移一行审计；事件序列完备。
    assert await _count_transitions(db_session, created.run.id) == 6  # created + 5 transitions
    # status_changed 覆盖非语义迁移：QUEUED→RUNNING、RUNNING→EXECUTING、EXECUTING→SUCCEEDED。
    names = [row["event_type"] for row in await _outbox_rows(db_session, "run.status_changed")]
    assert names == ["run.status_changed", "run.status_changed", "run.status_changed"]
    assert len(await _outbox_rows(db_session, "run.awaiting_user")) == 1
    assert len(await _outbox_rows(db_session, "run.user_resumed")) == 1


async def test_illegal_transition_raises(db_session, outbox_tables):
    user = await _make_user(db_session)
    service = AgentRunService(db_session)
    created = await service.create_run(user_id=user.id, objective="obj")

    # QUEUED → SUCCEEDED：从未启动即成功，非法。
    with pytest.raises(IllegalRunTransitionError):
        await service.transition(created.run.id, RunStatus.SUCCEEDED)
    # 等待态互通非法。
    await service.transition(created.run.id, RunStatus.RUNNING, actor="worker")
    await service.transition(created.run.id, RunStatus.AWAITING_USER, actor="worker")
    with pytest.raises(IllegalRunTransitionError):
        await service.transition(created.run.id, RunStatus.AWAITING_APPROVAL)
    # 状态未被非法迁移污染。
    run = await service.get_run(created.run.id)
    assert run.status is RunStatus.AWAITING_USER


async def test_terminal_is_closed(db_session, outbox_tables):
    user = await _make_user(db_session)
    service = AgentRunService(db_session)
    created = await service.create_run(user_id=user.id, objective="obj")

    # QUEUED → FAILED（启动前失败）合法；终态随后封闭。
    await service.transition(created.run.id, RunStatus.FAILED, actor="worker", reason="failed")
    for target in (RunStatus.RUNNING, RunStatus.SUCCEEDED, RunStatus.CANCELLED, RunStatus.EXECUTING):
        with pytest.raises(IllegalRunTransitionError):
            await service.transition(created.run.id, target)

    # 已成功终态的 run 再取消 → 非法（不是 no-op）。
    done = await service.create_run(user_id=user.id, objective="obj2", idempotency_key="k2")
    await service.transition(done.run.id, RunStatus.RUNNING, actor="worker")
    await service.transition(done.run.id, RunStatus.SUCCEEDED, actor="worker", reason="completed")
    with pytest.raises(IllegalRunTransitionError):
        await service.cancel(done.run.id, user_id=user.id)


async def test_unknown_terminal_reason_rejected(db_session, outbox_tables):
    user = await _make_user(db_session)
    service = AgentRunService(db_session)
    created = await service.create_run(user_id=user.id, objective="obj")
    with pytest.raises(ValueError, match="closed vocabulary"):
        await service.transition(created.run.id, RunStatus.FAILED, reason="mystery_reason")


# ---------------------------------------------------------------------------
# 3. 重复 resume 恰一次（幂等复查）
# ---------------------------------------------------------------------------


async def test_duplicate_resume_is_noop_exactly_once(db_session, outbox_tables):
    user = await _make_user(db_session)
    service = AgentRunService(db_session)
    created = await service.create_run(user_id=user.id, objective="obj")
    await service.transition(created.run.id, RunStatus.RUNNING, actor="worker")
    await service.transition(created.run.id, RunStatus.AWAITING_USER, actor="worker")

    first = await service.resume(created.run.id, user_id=user.id, idempotency_key="resume-x")
    second = await service.resume(created.run.id, user_id=user.id, idempotency_key="resume-x")
    third = await service.resume(created.run.id, user_id=user.id)  # 无 key 的纯重试同样 no-op

    assert first.applied is True
    assert second.applied is False and second.run.status is RunStatus.RUNNING
    assert third.applied is False
    # 恰一次：一个 run.user_resumed 事件、无第二行审计。
    assert len(await _outbox_rows(db_session, "run.user_resumed")) == 1
    assert await _count_transitions(db_session, created.run.id) == 4  # created+running+awaiting+resume


async def test_cancel_is_idempotent_when_already_cancelled(db_session, outbox_tables):
    user = await _make_user(db_session)
    service = AgentRunService(db_session)
    created = await service.create_run(user_id=user.id, objective="obj")
    first = await service.cancel(created.run.id, user_id=user.id)
    second = await service.cancel(created.run.id, user_id=user.id)
    assert first.applied is True
    assert second.applied is False  # 已取消 → no-op，不重复事件
    assert len(await _outbox_rows(db_session, "run.status_changed")) == 1


# ---------------------------------------------------------------------------
# 4. step 进度（绝对序号幂等；终态拒绝）
# ---------------------------------------------------------------------------


async def test_record_step_absolute_ordinal_idempotent(db_session, outbox_tables):
    user = await _make_user(db_session)
    service = AgentRunService(db_session)
    created = await service.create_run(user_id=user.id, objective="obj", steps_total=4)
    await service.transition(created.run.id, RunStatus.RUNNING, actor="worker")

    s1 = await service.record_step(created.run.id, user_id=user.id, step_id="s1", ordinal=1, label="读取材料")
    replay = await service.record_step(created.run.id, user_id=user.id, step_id="s1", ordinal=1, label="读取材料")
    s2 = await service.record_step(created.run.id, user_id=user.id, step_id="s2", ordinal=2, label="比较方案")

    assert s1.applied and replay.applied is False and s2.applied
    assert s2.run.steps_done == 2 and s2.run.current_stage == "比较方案"
    events = await _outbox_rows(db_session, "run.step_completed")
    assert len(events) == 2
    payload = json.loads(events[0]["payload"])
    assert payload["step_id"] == "s1" and payload["ordinal"] == 1


async def test_record_step_rejected_on_terminal(db_session, outbox_tables):
    user = await _make_user(db_session)
    service = AgentRunService(db_session)
    created = await service.create_run(user_id=user.id, objective="obj")
    await service.transition(created.run.id, RunStatus.RUNNING, actor="worker")
    await service.transition(created.run.id, RunStatus.SUCCEEDED, actor="worker", reason="completed")
    with pytest.raises(ValueError, match="terminal"):
        await service.record_step(created.run.id, user_id=user.id, step_id="s9", ordinal=1)


# ---------------------------------------------------------------------------
# 5. 读取隔离
# ---------------------------------------------------------------------------


async def test_get_run_isolation_404_for_other_user(db_session, outbox_tables):
    user_a = await _make_user(db_session)
    user_b = await _make_user(db_session)
    service = AgentRunService(db_session)
    created = await service.create_run(user_id=user_a.id, objective="secret")

    with pytest.raises(RunNotFoundError):
        await service.get_run(created.run.id, user_id=user_b.id)
    assert (await service.get_run(created.run.id, user_id=user_a.id)).id == created.run.id


# ---------------------------------------------------------------------------
# 6. intent 投影（consumer 数据面）
# ---------------------------------------------------------------------------


async def test_projection_creates_and_advances_run(db_session, outbox_tables):
    user = await _make_user(db_session)
    intent = await _make_intent(db_session, user)
    service = AgentRunService(db_session)

    r1 = await service.project_intent_status(intent_id=intent.id, user_id=user.id, new_status="ready", task_id=None)
    assert r1.created and r1.run.status is RunStatus.QUEUED

    r2 = await service.project_intent_status(intent_id=intent.id, user_id=user.id, new_status="dispatched")
    assert r2 is not None and r2.run.status is RunStatus.RUNNING

    # 重复投递 no-op。
    r3 = await service.project_intent_status(intent_id=intent.id, user_id=user.id, new_status="running")
    assert r3 is None

    r4 = await service.project_intent_status(intent_id=intent.id, user_id=user.id, new_status="waiting_approval")
    assert r4.run.status is RunStatus.AWAITING_APPROVAL and r4.run.wait_kind == "approval"

    r5 = await service.project_intent_status(intent_id=intent.id, user_id=user.id, new_status="succeeded")
    assert r5.run.status is RunStatus.SUCCEEDED and r5.run.terminal_reason == "completed"


async def test_projection_retry_creates_new_attempt(db_session, outbox_tables):
    user = await _make_user(db_session)
    intent = await _make_intent(db_session, user)
    service = AgentRunService(db_session)

    await service.project_intent_status(intent_id=intent.id, user_id=user.id, new_status="dispatched")
    await service.project_intent_status(intent_id=intent.id, user_id=user.id, new_status="failed")

    # intent retry：终态 → ready 重置 → 新 attempt run，旧 run 终态封闭不破坏。
    r6 = await service.project_intent_status(intent_id=intent.id, user_id=user.id, new_status="ready")
    assert r6.created is True
    assert r6.run.attempt == 2
    assert r6.run.status is RunStatus.QUEUED

    runs = await service.list_runs(user_id=user.id, intent_id=intent.id)
    assert len(runs) == 2
    assert {r.attempt for r in runs} == {1, 2}


async def test_projection_late_catchup_creates_terminal_run(db_session, outbox_tables):
    """消费者迟到（漏掉中间事件）时，首次见到的终态直接建档——审计 from=None。

    R2 F7：catch-up 终态建档与正常迁移同归因（terminal_reason 落封闭词表值）。
    """
    user = await _make_user(db_session)
    intent = await _make_intent(db_session, user)
    service = AgentRunService(db_session)

    result = await service.project_intent_status(intent_id=intent.id, user_id=user.id, new_status="succeeded")
    assert result.created and result.run.status is RunStatus.SUCCEEDED
    assert result.run.terminal_reason == "completed"  # R2 F7：终态建档有归因
    transitions = await service.list_transitions(result.run.id)
    assert len(transitions) == 1 and transitions[0].from_status is None


# ---------------------------------------------------------------------------
# 7. worker restart 恢复 sweep
# ---------------------------------------------------------------------------


async def _backdate_heartbeat(db_session, run_id, seconds: int):
    await db_session.execute(
        text("UPDATE agent_runs SET heartbeat_at = :h WHERE id = :r"),
        {"h": datetime.now(UTC).replace(tzinfo=None) - timedelta(seconds=seconds), "r": str(run_id)},
    )
    await db_session.commit()
    # 原生 SQL 绕过 ORM——失效身份映射，后续 SELECT 重读 DB（防陈旧对象假象）。
    db_session.expire_all()


async def test_recovery_queue_stale_to_cancelled(db_session, outbox_tables):
    user = await _make_user(db_session)
    service = AgentRunService(db_session)
    created = await service.create_run(user_id=user.id, objective="obj")
    await _backdate_heartbeat(db_session, created.run.id, seconds=7 * 3600)

    report = await service.recover_stale_runs(stale_after_seconds=6 * 3600)
    run = await service.get_run(created.run.id)
    assert run.status is RunStatus.CANCELLED and run.terminal_reason == "queue_stale"
    assert report["applied"] == 1


async def test_recovery_orphan_running_to_unknown_outcome(db_session, outbox_tables):
    """worker 死在 RUNNING：已发生 side effect 不假装知道结果 → UNKNOWN_OUTCOME。"""
    user = await _make_user(db_session)
    service = AgentRunService(db_session)
    created = await service.create_run(user_id=user.id, objective="obj")
    await service.transition(created.run.id, RunStatus.RUNNING, actor="worker")
    await _backdate_heartbeat(db_session, created.run.id, seconds=7 * 3600)

    report = await service.recover_stale_runs(stale_after_seconds=6 * 3600)
    run = await service.get_run(created.run.id)
    assert run.status is RunStatus.UNKNOWN_OUTCOME
    assert run.terminal_reason == "worker_restart_orphan"
    assert report["applied"] == 1


async def test_recovery_wait_expired_to_timed_out(db_session, outbox_tables):
    user = await _make_user(db_session)
    service = AgentRunService(db_session)
    created = await service.create_run(user_id=user.id, objective="obj")
    expires = datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=5)
    await service.transition(created.run.id, RunStatus.AWAITING_USER, actor="worker", wait_expires_at=expires)

    await service.recover_stale_runs(stale_after_seconds=6 * 3600)
    run = await service.get_run(created.run.id)
    assert run.status is RunStatus.TIMED_OUT and run.terminal_reason == "wait_expired"


async def test_recovery_fresh_runs_untouched(db_session, outbox_tables):
    user = await _make_user(db_session)
    service = AgentRunService(db_session)
    created = await service.create_run(user_id=user.id, objective="obj")
    await service.transition(created.run.id, RunStatus.RUNNING, actor="worker")

    report = await service.recover_stale_runs(stale_after_seconds=6 * 3600)
    run = await service.get_run(created.run.id)
    assert run.status is RunStatus.RUNNING
    assert report["applied"] == 0


async def test_recovery_repairs_intent_drift(db_session, outbox_tables):
    """投影滞后/丢失（run 仍 RUNNING 而 intent 已终态）→ 恢复 sweep 修复终态。"""
    from app.models.execution_intent import ExecutionIntentStatus

    user = await _make_user(db_session)
    intent = await _make_intent(db_session, user)
    service = AgentRunService(db_session)

    await service.project_intent_status(intent_id=intent.id, user_id=user.id, new_status="dispatched")
    # 直接改 intent 为终态（模拟投影事件丢失），不经过投影。
    intent.status = ExecutionIntentStatus.SUCCEEDED
    db_session.add(intent)
    await db_session.commit()

    run = (await service.list_runs(user_id=user.id, intent_id=intent.id))[0]
    assert run.status is RunStatus.RUNNING  # 漂移存在

    await _backdate_heartbeat(db_session, run.id, seconds=7 * 3600)
    await service.recover_stale_runs(stale_after_seconds=6 * 3600)

    run = await service.get_run(run.id)
    assert run.status is RunStatus.SUCCEEDED
    assert run.terminal_reason == "completed"


async def test_recovery_repairs_drift_from_awaiting_before_wait_expiry(db_session, outbox_tables):
    """AWAITING 态漂移：intent 已终态 → 立即修复，不等 wait_expires 窗口。"""
    from app.models.execution_intent import ExecutionIntentStatus

    user = await _make_user(db_session)
    intent = await _make_intent(db_session, user)
    service = AgentRunService(db_session)

    await service.project_intent_status(intent_id=intent.id, user_id=user.id, new_status="dispatched")
    await service.project_intent_status(intent_id=intent.id, user_id=user.id, new_status="waiting_approval")
    intent.status = ExecutionIntentStatus.CANCELED
    db_session.add(intent)
    await db_session.commit()

    run = (await service.list_runs(user_id=user.id, intent_id=intent.id))[0]
    assert run.status is RunStatus.AWAITING_APPROVAL

    await _backdate_heartbeat(db_session, run.id, seconds=7 * 3600)
    report = await service.recover_stale_runs(stale_after_seconds=6 * 3600)

    run = await service.get_run(run.id)
    assert run.status is RunStatus.CANCELLED
    assert run.terminal_reason == "user_cancelled"
    assert any(a["kind"] == "drift_repaired" and a["applied"] for a in report["actions"])


async def test_recovery_terminal_runs_never_scanned(db_session, outbox_tables):
    """终态 run 永不进 sweep 范围（封闭性在恢复路径同样成立）。"""
    user = await _make_user(db_session)
    service = AgentRunService(db_session)
    created = await service.create_run(user_id=user.id, objective="obj")
    await service.transition(created.run.id, RunStatus.RUNNING, actor="worker")
    await service.transition(created.run.id, RunStatus.SUCCEEDED, actor="worker", reason="completed")
    await _backdate_heartbeat(db_session, created.run.id, seconds=10 * 86400)

    report = await service.recover_stale_runs(stale_after_seconds=60)
    assert report["scanned"] == 0 and report["applied"] == 0


# ---------------------------------------------------------------------------
# 8. R2 返修回归：F1 幻影 / F2 防复活 / F3 QUEUED 收敛 / F5 步进 / M3 索引
# ---------------------------------------------------------------------------


async def _project(service, intent_id, user_id, status):
    """投影快捷方式（intent_id/user_id 预先捕获——expire_all 后属性惰性刷新在 async 下不可用）。"""
    return await service.project_intent_status(intent_id=intent_id, user_id=user_id, new_status=status)


async def test_projection_terminal_redelivery_never_mints_phantom_runs(db_session, outbox_tables):
    """R2 F1（探针 A）：同一终态事件重投 N 次，恒 1 条 run、attempt 不递增。"""
    user = await _make_user(db_session)
    intent = await _make_intent(db_session, user)
    intent_id = intent.id
    uid = user.id
    service = AgentRunService(db_session)

    await _project(service, intent_id, uid, "dispatched")
    failed = await _project(service, intent_id, uid, "failed")
    assert failed.run.status is RunStatus.FAILED and failed.run.attempt == 1

    # at-least-once 重投 ×3（commit→xack 窗口崩溃 / XAUTOCLAIM 抢占后的标准重放）。
    for _ in range(3):
        result = await _project(service, intent_id, uid, "failed")
        assert result is None  # 收敛 no-op，绝不 create

    runs = await service.list_runs(user_id=uid, intent_id=intent_id)
    assert len(runs) == 1
    assert runs[0].attempt == 1 and runs[0].status is RunStatus.FAILED
    assert await _count_transitions(db_session, runs[0].id) == 2  # created + failed，无幻影审计


async def test_projection_keeps_single_terminal_when_sweep_acted_first(db_session, outbox_tables):
    """R2 F1（探针 E）：sweep 先判 UNKNOWN_OUTCOME，迟到的 succeeded 不铸双终态。"""
    user = await _make_user(db_session)
    intent = await _make_intent(db_session, user)
    intent_id = intent.id
    uid = user.id
    service = AgentRunService(db_session)

    await _project(service, intent_id, uid, "dispatched")
    run = (await service.list_runs(user_id=uid, intent_id=intent_id))[0]
    await _backdate_heartbeat(db_session, run.id, seconds=7 * 3600)
    await service.recover_stale_runs(stale_after_seconds=6 * 3600)
    assert (await service.get_run(run.id)).status is RunStatus.UNKNOWN_OUTCOME

    late = await _project(service, intent_id, uid, "succeeded")
    assert late is None  # 既有终态即结论：投影收敛，不开 attempt-2

    runs = await service.list_runs(user_id=uid, intent_id=intent_id)
    assert len(runs) == 1
    assert runs[0].status is RunStatus.UNKNOWN_OUTCOME  # 无 SUCCEEDED 并存


async def test_projection_stale_nonterminal_event_after_terminal_is_noop(db_session, outbox_tables):
    """R2 F1：intent 行已终态时，乱序迟到的旧非终态事件不复活、不开新 attempt。"""
    from app.models.execution_intent import ExecutionIntentStatus

    user = await _make_user(db_session)
    intent = await _make_intent(db_session, user)
    intent_id = intent.id
    uid = user.id
    service = AgentRunService(db_session)

    await _project(service, intent_id, uid, "dispatched")
    await _project(service, intent_id, uid, "failed")
    intent.status = ExecutionIntentStatus.FAILED  # 协议真源：已终态
    db_session.add(intent)
    await db_session.commit()

    stale = await _project(service, intent_id, uid, "dispatched")  # 乱序迟到（XAUTOCLAIM 场景）
    assert stale is None
    runs = await service.list_runs(user_id=uid, intent_id=intent_id)
    assert len(runs) == 1 and runs[0].status is RunStatus.FAILED


async def test_projection_reopens_attempt_after_queue_stale_when_execution_actually_started(db_session, outbox_tables):
    """queue_stale 是推测：迟到事件证伪"从未启动"时允许开新 attempt 如实记录。"""
    from app.models.execution_intent import ExecutionIntentStatus

    user = await _make_user(db_session)
    intent = await _make_intent(db_session, user)
    intent_id = intent.id
    uid = user.id
    service = AgentRunService(db_session)

    await _project(service, intent_id, uid, "ready")
    run = (await service.list_runs(user_id=uid, intent_id=intent_id))[0]
    await _backdate_heartbeat(db_session, run.id, seconds=7 * 3600)
    await service.recover_stale_runs(stale_after_seconds=6 * 3600)
    assert (await service.get_run(run.id)).status is RunStatus.CANCELLED  # queue_stale 推测

    intent.status = ExecutionIntentStatus.RUNNING  # 真源：执行其实启动了
    db_session.add(intent)
    await db_session.commit()

    result = await _project(service, intent_id, uid, "dispatched")
    assert result is not None and result.created is True
    assert result.run.attempt == 2 and result.run.status is RunStatus.RUNNING
    assert len(await service.list_runs(user_id=uid, intent_id=intent_id)) == 2


async def test_cancel_blocks_projection_resurrection(db_session, outbox_tables):
    """R2 F2（探针 B）：用户取消后，后续 RUNNING/SUCCEEDED 事件不得复活新活跃 run。

    本测试故意让 intent 行保持非终态（传播部分失败的最坏情形）——防复活由
    run 侧 ``user_cancelled`` 归因守卫保证，不依赖传播是否成功。
    """
    user = await _make_user(db_session)
    intent = await _make_intent(db_session, user)
    intent_id = intent.id
    uid = user.id
    service = AgentRunService(db_session)

    await _project(service, intent_id, uid, "dispatched")
    run = (await service.list_runs(user_id=uid, intent_id=intent_id))[0]
    await service.cancel(run.id, user_id=uid)  # 只取消 run（传播缺席）
    assert (await service.get_run(run.id)).status is RunStatus.CANCELLED

    # executor 未感知取消，继续发状态事件 → 不得复活。
    assert await _project(service, intent_id, uid, "running") is None
    assert await _project(service, intent_id, uid, "succeeded") is None

    runs = await service.list_runs(user_id=uid, intent_id=intent_id)
    assert len(runs) == 1
    assert runs[0].status is RunStatus.CANCELLED
    assert runs[0].terminal_reason == "user_cancelled"
    actives = await service.list_runs(user_id=uid, intent_id=intent_id, active_only=True)
    assert actives == []  # 用户取消不被视觉撤销


async def test_projection_queued_terminal_event_converges_via_two_steps(db_session, outbox_tables):
    """R2 F3（探针 C 投影侧）：QUEUED run 收到迟到终态经 QUEUED→RUNNING→终态收敛。

    中间 dispatched/running 事件丢失（消费者宕机窗口）时，succeeded 直达。
    封闭图零改动（QUEUED→SUCCEEDED 仍为禁边），两步均合法边。
    """
    user = await _make_user(db_session)
    intent = await _make_intent(db_session, user)
    intent_id = intent.id
    uid = user.id
    service = AgentRunService(db_session)

    await _project(service, intent_id, uid, "ready")
    result = await _project(service, intent_id, uid, "succeeded")  # 跳过中间事件

    assert result is not None and result.run.status is RunStatus.SUCCEEDED
    assert result.run.terminal_reason == "completed"
    assert result.run.started_at is not None  # "确实启动过"如实入档
    transitions = await service.list_transitions(result.run.id)
    assert [t.from_status for t in transitions] == [None, "QUEUED", "RUNNING"]
    assert [t.to_status for t in transitions] == ["QUEUED", "RUNNING", "SUCCEEDED"]


@pytest.mark.parametrize("intent_status", ["succeeded", "partial"])
async def test_recovery_repairs_queued_drift_before_queue_stale(db_session, outbox_tables, intent_status):
    """R2 F3（探针 C sweep 侧）：intent 已终态的 QUEUED run 绝不以 queue_stale 收场。"""
    from app.models.execution_intent import ExecutionIntentStatus

    user = await _make_user(db_session)
    intent = await _make_intent(db_session, user)
    intent_id = intent.id
    uid = user.id
    service = AgentRunService(db_session)

    await _project(service, intent_id, uid, "ready")
    intent.status = ExecutionIntentStatus(intent_status)  # 投影事件丢失，真源已终态
    db_session.add(intent)
    await db_session.commit()

    run = (await service.list_runs(user_id=uid, intent_id=intent_id))[0]
    await _backdate_heartbeat(db_session, run.id, seconds=7 * 3600)
    report = await service.recover_stale_runs(stale_after_seconds=6 * 3600)

    repaired = await service.get_run(run.id)
    assert repaired.status.value == intent_status.upper()
    assert repaired.terminal_reason in ("completed", "completed_partial")
    assert any(a["kind"] == "drift_repaired" and a["applied"] for a in report["actions"])


async def test_record_step_ordinal_never_regresses(db_session, outbox_tables):
    """R2 F5：低序号迟到提交不回退进度（FOR UPDATE 行锁下单调；sqlite 语义层冻结）。"""
    user = await _make_user(db_session)
    uid = user.id
    service = AgentRunService(db_session)
    created = await service.create_run(user_id=uid, objective="obj", steps_total=4)
    await service.transition(created.run.id, RunStatus.RUNNING, actor="worker")

    s4 = await service.record_step(created.run.id, user_id=uid, step_id="s4", ordinal=4, label="第 4 步")
    assert s4.run.steps_done == 4
    late3 = await service.record_step(created.run.id, user_id=uid, step_id="s3", ordinal=3, label="第 3 步")
    assert late3.applied is False
    assert (await service.get_run(created.run.id)).steps_done == 4  # 不回退


# --- M3：部分唯一索引（attempt 语义）构造性测试 —— 删索引必红 -------------


async def test_active_intent_partial_unique_index_enforced(db_session, outbox_tables):
    """M3：同 intent 第二条**活跃** run 必撞 ``uq_agent_runs_intent_active``；终态后放行。

    R2 变异 M3 曾证明删模型索引后 32 测试全绿——本测试在 sqlite 上行为级冻结
    该索引（部分唯一：仅约束非终态行）。
    """
    from sqlalchemy.exc import IntegrityError

    user = await _make_user(db_session)
    intent = await _make_intent(db_session, user)
    intent_id = intent.id
    uid = user.id
    service = AgentRunService(db_session)

    first = await service.create_run(user_id=uid, objective="attempt 1", intent_id=intent_id, idempotency_key="m3-a1")
    assert first.created
    first_run_id = first.run.id  # IntegrityError→rollback 会过期 ORM 身份，先捕获

    with pytest.raises(IntegrityError):  # 活跃 run 唯一性由索引兜底（非幂等键路径）
        await service.create_run(user_id=uid, objective="phantom", intent_id=intent_id)

    # 终态后部分条件不再约束该行 → 新 attempt 合法。
    await service.transition(first_run_id, RunStatus.FAILED, actor="worker", reason="failed")
    second = await service.create_run(
        user_id=uid, objective="attempt 2", intent_id=intent_id, idempotency_key="m3-a2", attempt=2
    )
    assert second.created


async def test_active_intent_partial_unique_index_declared(db_session):
    """M3：索引声明级冻结——部分唯一 + WHERE 非终态谓词（删 Index 定义必红）。"""

    def _check(sync_conn):
        from sqlalchemy import inspect

        indexes = [
            i for i in inspect(sync_conn).get_indexes("agent_runs") if i["name"] == "uq_agent_runs_intent_active"
        ]
        assert len(indexes) == 1, "uq_agent_runs_intent_active 缺失（唯一性兜底层被删）"
        info = indexes[0]
        assert bool(info.get("unique")), f"索引不是唯一索引: {info}"
        # sqlite 方言把部分索引谓词放 dialect_options.sqlite_where（TextClause）。
        dialect_opts = info.get("dialect_options") or {}
        where = (
            " ".join(str(info.get(k) or "") for k in ("sqlite_where", "postgresql_where", "sql"))
            + " "
            + " ".join(str(v) for v in dialect_opts.values())
        )
        assert "status NOT IN" in where, f"部分唯一谓词丢失: {info}"

    conn = await db_session.connection()
    await conn.run_sync(_check)
