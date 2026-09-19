"""X-05B · EXECUTING 步进投影契约测试（run.status_changed 漏斗 → agent_runs）.

覆盖：
- project_execution_step：RUNNING→EXECUTING 落点 + steps 进度 + 审计/事件同构；
- 幂等（同 intent+attempt+step 重投恰一次：transition 复查 + record_step 单调）；
- 不铸造 run（无活跃 run no-op——run 生命周期真源是 intent 状态漏斗）；
- 终态 no-op（迟到步进不上 DLQ）；AWAITING_* 不被迟到步进覆盖；
- 毒事件（非法 to_status）上抛 → bus DLQ 契约；
- 消费者路由：run.status_changed → 步进投影；execution.status_changed 原路径不回退。
"""

from __future__ import annotations

import pytest
from sqlalchemy import text

from app.core.run_state_machine import RunStatus, RunStateError
from app.models.agent_run import AgentRunKind
from app.services.agent_run_service import AgentRunService
from app.services.run_projection_consumer import RunProjectionConsumer
from tests.unit.test_agent_run_service import (  # noqa: F401 — 复用 helpers
    _OUTBOX_DDL,
    _make_intent,
    _make_user,
)


@pytest.fixture(name="outbox_tables")
async def outbox_tables_fixture(db_session):
    for ddl in _OUTBOX_DDL:
        await db_session.execute(text(ddl))
    await db_session.commit()
    yield


class _FakeBus:
    async def connect(self):
        return None

    async def subscribe(self, **kwargs):
        return None


@pytest.fixture(name="consumer")
def consumer_fixture(db_session):
    class _SqliteSessionFactory:
        def __call__(self):
            return _SessionContext(db_session)

    class _SessionContext:
        def __init__(self, session):
            self._session = session

        async def __aenter__(self):
            return self._session

        async def __aexit__(self, *exc):
            return False

    return RunProjectionConsumer(event_bus=_FakeBus(), session_factory=_SqliteSessionFactory())


def _step_event(intent, user, milestone="tool_in_use", *, to_status="EXECUTING", ordinal=2, stage="openclaw_tool") -> dict:
    return {
        "event_type": "run.status_changed",
        "user_id": str(user.id),
        "execution_intent_id": str(intent.id),
        "task_id": str(intent.task_id),
        "milestone": milestone,
        "run": {
            "to_status": to_status,
            "step": {"ordinal": ordinal, "stage": stage, "steps_total": 4},
        },
        "timestamp": "2026-09-19T00:00:00",
    }


async def _seed_active_run(db_session, intent, user, *, status=RunStatus.RUNNING):
    """经权威服务建 run 并落到指定活跃态（不走旁门写行）。"""
    service = AgentRunService(db_session)
    created = await service.create_run(
        user_id=user.id,
        objective="seed",
        kind=AgentRunKind.EXECUTION,
        intent_id=intent.id,
        task_id=intent.task_id,
        idempotency_key=f"seed-{intent.id}",
    )
    if status is not RunStatus.QUEUED:
        await service.transition(created.run.id, status, actor="worker")
    return created.run


# ---------------------------------------------------------------------------
# 1. 投影语义
# ---------------------------------------------------------------------------


async def test_step_projects_executing_and_progress(db_session, outbox_tables):
    """主路径：RUNNING --run.status_changed--> EXECUTING + steps_done/current_stage。"""
    user = await _make_user(db_session)
    intent = await _make_intent(db_session, user)
    run = await _seed_active_run(db_session, intent, user)

    service = AgentRunService(db_session)
    result = await service.project_execution_step(
        intent_id=intent.id,
        user_id=user.id,
        milestone="execution_started",
        to_status="EXECUTING",
        ordinal=1,
        stage="openclaw_start",
        steps_total=4,
    )
    assert result is not None and result.applied

    runs = await service.list_runs(user_id=user.id, intent_id=intent.id)
    assert len(runs) == 1
    assert runs[0].status is RunStatus.EXECUTING
    assert runs[0].steps_done == 1
    assert runs[0].steps_total == 4
    assert runs[0].current_stage == "openclaw_start"

    # 审计同构：迁移行（run.status_changed）+ outbox 步进事件（run.step_completed）。
    transitions = await service.list_transitions(run.id)
    assert [(t.from_status, t.to_status, t.event_name) for t in transitions] == [
        (None, "QUEUED", "run.created"),
        ("QUEUED", "RUNNING", "run.status_changed"),  # seed 的 QUEUED→RUNNING
        ("RUNNING", "EXECUTING", "run.status_changed"),
    ]
    outbox = await db_session.execute(
        text("SELECT event_type FROM event_outbox WHERE aggregate_type='agent_run' ORDER BY id")
    )
    assert [r[0] for r in outbox.all()] == ["run.created", "run.status_changed", "run.status_changed", "run.step_completed"]


async def test_step_from_queued_lands_directly_executing(db_session, outbox_tables):
    """dispatch 事件丢失场景：QUEUED --里程碑--> EXECUTING（封闭图合法边）。"""
    user = await _make_user(db_session)
    intent = await _make_intent(db_session, user)
    await _seed_active_run(db_session, intent, user, status=RunStatus.QUEUED)

    service = AgentRunService(db_session)
    result = await service.project_execution_step(
        intent_id=intent.id,
        user_id=user.id,
        to_status="EXECUTING",
        ordinal=1,
        stage="openclaw_start",
        steps_total=4,
    )
    assert result.applied
    runs = await service.list_runs(user_id=user.id, intent_id=intent.id)
    assert runs[0].status is RunStatus.EXECUTING


async def test_redelivery_is_exactly_once(db_session, outbox_tables):
    """幂等：同 intent+attempt+step 重投恰一次（状态复查 + 序号单调）。"""
    user = await _make_user(db_session)
    intent = await _make_intent(db_session, user)
    run = await _seed_active_run(db_session, intent, user)

    service = AgentRunService(db_session)
    kwargs = dict(
        intent_id=intent.id,
        user_id=user.id,
        milestone="tool_in_use",
        to_status="EXECUTING",
        ordinal=2,
        stage="openclaw_tool",
        steps_total=4,
    )
    await service.project_execution_step(**kwargs)
    for _ in range(3):  # at-least-once 重投（XAUTOCLAIM / retry requeue）
        await service.project_execution_step(**kwargs)

    runs = await service.list_runs(user_id=user.id, intent_id=intent.id)
    assert len(runs) == 1
    assert runs[0].steps_done == 2
    # 恰一次：EXECUTING 迁移行 1 条；run.step_completed outbox 事件 1 条。
    result = await db_session.execute(
        text(
            "SELECT COUNT(*) FROM agent_run_transitions WHERE run_id=:r AND to_status='EXECUTING'"
        ),
        {"r": str(run.id)},
    )
    assert int(result.scalar_one()) == 1
    result = await db_session.execute(
        text("SELECT COUNT(*) FROM event_outbox WHERE event_type='run.step_completed'")
    )
    assert int(result.scalar_one()) == 1


async def test_out_of_order_ordinal_is_monotonic_noop(db_session, outbox_tables):
    """乱序迟到（先 3 后 2）：steps_done 不回退（R2 F5 同语义）。"""
    user = await _make_user(db_session)
    intent = await _make_intent(db_session, user)
    await _seed_active_run(db_session, intent, user)

    service = AgentRunService(db_session)
    await service.project_execution_step(
        intent_id=intent.id, user_id=user.id, to_status="EXECUTING", ordinal=3, stage="openclaw_output", steps_total=4
    )
    result = await service.project_execution_step(
        intent_id=intent.id, user_id=user.id, ordinal=2, stage="openclaw_tool", steps_total=4
    )
    assert result is not None and result.applied is False  # 步进 no-op

    runs = await service.list_runs(user_id=user.id, intent_id=intent.id)
    assert runs[0].steps_done == 3
    assert runs[0].current_stage == "openclaw_output"  # label 不被旧步覆盖


async def test_no_active_run_mints_nothing(db_session, outbox_tables):
    """不铸造 run：状态漏斗未建 run 时步进 no-op（F1 幻影守卫同哲学）。"""
    user = await _make_user(db_session)
    intent = await _make_intent(db_session, user)

    service = AgentRunService(db_session)
    result = await service.project_execution_step(
        intent_id=intent.id, user_id=user.id, to_status="EXECUTING", ordinal=1, stage="openclaw_start", steps_total=4
    )
    assert result is None
    result = await db_session.execute(text("SELECT COUNT(*) FROM agent_runs"))
    assert int(result.scalar_one()) == 0


async def test_terminal_run_late_step_is_silent_noop(db_session, outbox_tables):
    """终态先行 + 迟到步进：no-op 不上 DLQ（终态即结论）。"""
    user = await _make_user(db_session)
    intent = await _make_intent(db_session, user)
    run = await _seed_active_run(db_session, intent, user)
    service = AgentRunService(db_session)
    await service.transition(run.id, RunStatus.SUCCEEDED, reason="completed", actor="worker")

    result = await service.project_execution_step(
        intent_id=intent.id, user_id=user.id, to_status="EXECUTING", ordinal=2, stage="openclaw_tool", steps_total=4
    )
    assert result is None
    runs = await service.list_runs(user_id=user.id, intent_id=intent.id)
    assert runs[0].status is RunStatus.SUCCEEDED
    assert runs[0].steps_done == 0


async def test_late_milestone_does_not_clobber_waiting(db_session, outbox_tables):
    """AWAITING_* 不因迟到/乱序步进被覆盖：状态保持等待，步进度照记。"""
    user = await _make_user(db_session)
    intent = await _make_intent(db_session, user)
    run = await _seed_active_run(db_session, intent, user)
    service = AgentRunService(db_session)
    await service.transition(run.id, RunStatus.AWAITING_APPROVAL, actor="worker")

    result = await service.project_execution_step(
        intent_id=intent.id, user_id=user.id, milestone="tool_in_use", to_status="EXECUTING", ordinal=2, stage="openclaw_tool", steps_total=4
    )
    runs = await service.list_runs(user_id=user.id, intent_id=intent.id)
    assert runs[0].status is RunStatus.AWAITING_APPROVAL  # 等待态保持
    assert runs[0].wait_kind == "approval"
    assert runs[0].steps_done == 2  # 进度可见性仍记录


async def test_poison_to_status_raises_for_dlq(db_session, outbox_tables):
    """毒事件契约：run 块带非法 to_status → RunStateError 上抛（bus 重试→DLQ）。"""
    user = await _make_user(db_session)
    intent = await _make_intent(db_session, user)
    await _seed_active_run(db_session, intent, user)

    service = AgentRunService(db_session)
    with pytest.raises(RunStateError):
        await service.project_execution_step(
            intent_id=intent.id, user_id=user.id, to_status="banana", ordinal=1, steps_total=4
        )


# ---------------------------------------------------------------------------
# 2. 消费者路由（handle_event 数据面）
# ---------------------------------------------------------------------------


async def test_consumer_routes_step_events(db_session, outbox_tables, consumer):
    """run.status_changed 经消费者进入步进投影；状态漏斗原路径不回退。"""
    user = await _make_user(db_session)
    intent = await _make_intent(db_session, user)
    await _seed_active_run(db_session, intent, user)

    await consumer.handle_event(
        {
            "event_type": "execution.status_changed",
            "user_id": str(user.id),
            "execution_intent_id": str(intent.id),
            "task_id": str(intent.task_id),
            "new_status": "running",
        }
    )
    await consumer.handle_event(_step_event(intent, user, "execution_started", ordinal=1, stage="openclaw_start"))

    service = AgentRunService(db_session)
    runs = await service.list_runs(user_id=user.id, intent_id=intent.id)
    assert len(runs) == 1
    assert runs[0].status is RunStatus.EXECUTING
    assert runs[0].steps_done == 1


async def test_consumer_skips_malformed_step_events(db_session, outbox_tables, consumer):
    """缺关键键 / 无 run 块的步进事件静默跳过（重试无意义）。"""
    user = await _make_user(db_session)
    intent = await _make_intent(db_session, user)

    await consumer.handle_event({"event_type": "run.status_changed", "user_id": str(user.id)})
    await consumer.handle_event(
        {"event_type": "run.status_changed", "execution_intent_id": str(intent.id)}
    )
    await consumer.handle_event(
        {"event_type": "run.status_changed", "user_id": str(user.id), "execution_intent_id": str(intent.id)}
    )

    result = await db_session.execute(text("SELECT COUNT(*) FROM agent_runs"))
    assert int(result.scalar_one()) == 0


async def test_consumer_other_event_types_still_ignored(db_session, outbox_tables, consumer):
    """非目标事件类型照旧忽略（X-05 既有契约不回退）。"""
    user = await _make_user(db_session)
    intent = await _make_intent(db_session, user)
    await consumer.handle_event(
        {
            "event_type": "tool_usage_event",
            "user_id": str(user.id),
            "execution_intent_id": str(intent.id),
            "run": {"to_status": "EXECUTING", "step": {"ordinal": 1}},
        }
    )
    result = await db_session.execute(text("SELECT COUNT(*) FROM agent_runs"))
    assert int(result.scalar_one()) == 0
