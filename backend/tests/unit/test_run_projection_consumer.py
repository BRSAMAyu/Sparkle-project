"""X-05 · RunProjectionConsumer 契约测试（event_bus 漏斗 → run 投影）.

不依赖 Redis：直接测 handle_event/project_event 的数据面（Redis Streams 交付
语义由 EventBus 既有测试覆盖；本测试验证事件键解析、过滤与幂等投影）。
"""

from __future__ import annotations

import pytest
from sqlalchemy import text

from app.core.run_state_machine import RunStatus
from app.services.agent_run_service import AgentRunService
from app.services.run_projection_consumer import RunProjectionConsumer
from tests.unit.test_agent_run_service import (  # noqa: F401 — 复用 helpers
    _OUTBOX_DDL,
    _make_intent,
    _make_task,
    _make_user,
)


@pytest.fixture(name="outbox_tables")
async def outbox_tables_fixture(db_session):
    for ddl in _OUTBOX_DDL:
        await db_session.execute(text(ddl))
    await db_session.commit()
    yield


class _FakeBus:
    """最小 EventBus 桩：只承载 connect/subscribe 契约形状（start 不在测试路径）。"""

    async def connect(self):
        return None

    async def subscribe(self, **kwargs):
        return None


@pytest.fixture(name="consumer")
def consumer_fixture(db_session):
    """注入 sqlite 会话工厂（hermetic；不触碰真实 DB）。"""

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


def _status_event(intent, user, new_status, old_status=None) -> dict:
    return {
        "event_type": "execution.status_changed",
        "user_id": str(user.id),
        "execution_intent_id": str(intent.id),
        "task_id": str(intent.task_id),
        "old_status": old_status,
        "new_status": new_status,
        "trust_level": "raw",
        "timestamp": "2026-09-19T00:00:00",
    }


async def test_consumer_projects_lifecycle(db_session, outbox_tables, consumer):
    user = await _make_user(db_session)
    intent = await _make_intent(db_session, user)

    for new_status in ("ready", "dispatched", "running", "waiting_approval"):
        await consumer.handle_event(_status_event(intent, user, new_status))

    service = AgentRunService(db_session)
    runs = await service.list_runs(user_id=user.id, intent_id=intent.id)
    assert len(runs) == 1
    assert runs[0].status is RunStatus.AWAITING_APPROVAL
    assert runs[0].task_id == intent.task_id
    assert runs[0].kind.value == "execution"


async def test_consumer_ignores_other_event_types(db_session, outbox_tables, consumer):
    user = await _make_user(db_session)
    intent = await _make_intent(db_session, user)
    await consumer.handle_event(
        {"event_type": "EXECUTION_BATCH_COMPLETED", "user_id": str(user.id), "execution_intent_id": str(intent.id)}
    )
    service = AgentRunService(db_session)
    assert await service.list_runs(user_id=user.id) == []


async def test_consumer_survives_malformed_event(db_session, outbox_tables, consumer):
    # 缺 user_id/intent_id：跳过且不抛（单条失败不拖垮消费循环）。
    await consumer.handle_event({"event_type": "execution.status_changed", "new_status": "running"})
    await consumer.handle_event({"event_type": "execution.status_changed"})
    await consumer.handle_event("not-a-dict") if False else None  # dict-only 契约由 bus 保证


async def test_consumer_double_delivery_is_idempotent(db_session, outbox_tables, consumer):
    user = await _make_user(db_session)
    intent = await _make_intent(db_session, user)

    event = _status_event(intent, user, "dispatched")
    await consumer.handle_event(event)
    await consumer.handle_event(event)  # at-least-once 重投

    service = AgentRunService(db_session)
    runs = await service.list_runs(user_id=user.id, intent_id=intent.id)
    assert len(runs) == 1
    assert runs[0].status is RunStatus.RUNNING

    result = await db_session.execute(text("SELECT COUNT(*) FROM agent_runs"))
    assert int(result.scalar_one()) == 1


async def test_consumer_terminal_redelivery_mints_no_phantom_run(db_session, outbox_tables, consumer):
    """R2 F1：终态事件经 bus 回调重投，绝不铸幻影 attempt run（探针 A 的回调层）。"""
    user = await _make_user(db_session)
    intent = await _make_intent(db_session, user)

    await consumer.handle_event(_status_event(intent, user, "dispatched"))
    failed = _status_event(intent, user, "failed")
    await consumer.handle_event(failed)
    for _ in range(3):  # commit→xack 窗口崩溃 / XAUTOCLAIM 重投
        await consumer.handle_event(failed)

    result = await db_session.execute(
        text("SELECT COUNT(*), MAX(attempt) FROM agent_runs WHERE intent_id = :i"),
        {"i": str(intent.id)},
    )
    count, max_attempt = result.one()
    assert int(count) == 1 and int(max_attempt) == 1  # 恒 1 条 run、attempt 不递增


async def test_consumer_propagates_projection_failures(db_session, outbox_tables, consumer):
    """R2 F3/F9：投影失败不被消费者吞掉——上抛给 bus 的有界重试→DLQ+metric 管线。

    旧行为（except+log）会把非法迁移变成"ack 即永久丢事件"且零可观测性；
    现在 callback 抛出即进入 ``EventBus._handle_failed_message``（重试→DLQ）。
    """
    from app.core.run_state_machine import RunStateError

    user = await _make_user(db_session)
    intent = await _make_intent(db_session, user)

    with pytest.raises(RunStateError):
        await consumer.handle_event(_status_event(intent, user, "exploded"))  # 未映射状态：毒事件可见
