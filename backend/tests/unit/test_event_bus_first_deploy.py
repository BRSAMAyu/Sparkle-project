"""X-05B · F6 消费组首部署回放突发根治测试（真实 Redis Streams）.

场景（FIX-28 / R2 F6）：EventBus Redis Streams 消费组首次部署时曾以 id=0
创建，从流头全量回放——每个历史 intent 突发一行 run（一次性部署成本）。
修复：新组以 ``$``（流尾）创建，首部署零回放；组已存在（升级路径）行为
不变；组创建后的 at-least-once 投递语义不回归。

全部测试使用 ``x05b:test:*`` 独立流前缀 + 用后删净（见 x05b_testkit）；
Redis 不可用自动 skip。
"""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.services.agent_run_service import AgentRunService
from app.services.run_projection_consumer import RunProjectionConsumer
from tests.unit.test_agent_run_service import (  # noqa: F401 — 复用 helpers
    _OUTBOX_DDL,
    _make_intent,
    _make_user,
)
from tests.unit.x05b_testkit import (
    cleanup_x05b_keys,
    make_x05b_bus,
    make_x05b_redis,
    wait_until,
    x05b_group,
    x05b_stream,
)


@pytest.fixture(name="outbox_tables")
async def outbox_tables_fixture(db_session):
    for ddl in _OUTBOX_DDL:
        await db_session.execute(text(ddl))
    await db_session.commit()
    yield


@pytest.fixture(name="x05b_redis")
async def x05b_redis_fixture():
    client = await make_x05b_redis()
    yield client
    await cleanup_x05b_keys(client)
    if hasattr(client, "aclose"):
        await client.aclose()
    else:
        await client.close()


def _status_payload(new_status: str = "succeeded") -> dict:
    return {
        "event_type": "execution.status_changed",
        "user_id": str(uuid4()),
        "execution_intent_id": str(uuid4()),
        "task_id": str(uuid4()),
        "old_status": "running",
        "new_status": new_status,
        "timestamp": "2026-09-01T00:00:00",
    }


async def test_first_deploy_new_group_does_not_replay_history(x05b_redis):
    """首部署（历史消息存在 + 新组经 subscribe 创建）→ 零历史投递。"""
    stream = x05b_stream("f6")
    bus = make_x05b_bus(x05b_redis)

    # 历史消息：5 条终态 execution.status_changed（最坏形状——旧逻辑每条铸一行 run）
    for _ in range(5):
        await bus.publish("execution.status_changed", _status_payload(), stream=stream)
    assert await x05b_redis.xlen(stream) == 5

    received: list[dict] = []

    async def callback(event: dict) -> None:
        received.append(event)

    await bus.subscribe(stream=stream, group_name=x05b_group("f6"), consumer_name="c1", callback=callback)
    try:
        # 足够 consume loop（block=2000ms）跑若干周期——历史一条都不该来。
        await asyncio.sleep(2.5)
        assert received == [], f"first deploy replayed {len(received)} historical events"

        # 组创建之后的新消息照常交付（at-least-once 不回归）。
        await bus.publish("execution.status_changed", _status_payload("running"), stream=stream)
        assert await wait_until(lambda: len(received) == 1), "new message after group creation must be delivered"
        assert received[0]["new_status"] == "running"
    finally:
        await bus.close()


async def test_existing_group_upgrade_path_unchanged(x05b_redis):
    """组已存在（升级部署）：subscribe 走 BUSYGROUP，未投递历史照常消费。"""
    stream = x05b_stream("f6b")
    bus = make_x05b_bus(x05b_redis)
    group = x05b_group("f6b")

    for i in range(2):
        await bus.publish("execution.status_changed", _status_payload("dispatched"), stream=stream)
    # 模拟既有部署：组以 id=0 先建（X-05B 之前的创建形状），历史仍在组视角未投递。
    await x05b_redis.xgroup_create(stream, group, id="0", mkstream=False)

    received: list[dict] = []

    async def callback(event: dict) -> None:
        received.append(event)

    await bus.subscribe(stream=stream, group_name=group, consumer_name="c2", callback=callback)
    try:
        assert await wait_until(lambda: len(received) == 2), "pre-existing group must keep consuming its backlog"
        await bus.publish("execution.status_changed", _status_payload("running"), stream=stream)
        assert await wait_until(lambda: len(received) == 3)
    finally:
        await bus.close()


async def test_first_deploy_projection_mints_zero_burst_runs(db_session, outbox_tables, x05b_redis):
    """验收钉（投影接线版）：首部署零回放 → agent_runs 零突发；新事件投影正常。

    旧行为（id=0）下本测试红：5 条历史终态事件会 catch-up 铸 5 行终态 run。
    """
    stream = x05b_stream("f6p")
    bus = make_x05b_bus(x05b_redis)
    for _ in range(5):
        await bus.publish("execution.status_changed", _status_payload(), stream=stream)

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

    consumer = RunProjectionConsumer(event_bus=bus, session_factory=_SqliteSessionFactory())
    consumer.STREAM_NAME = stream
    consumer.GROUP_NAME = x05b_group("f6p")
    await consumer.start()
    try:
        await asyncio.sleep(2.5)
        result = await db_session.execute(text("SELECT COUNT(*) FROM agent_runs"))
        assert int(result.scalar_one()) == 0, "first deploy must not mint burst runs from history"

        # 组后新事件投影正常（零回放不等于断供）。
        user = await _make_user(db_session)
        intent = await _make_intent(db_session, user)
        intent_id = str(intent.id)

        async def _run_visible() -> bool:
            result = await db_session.execute(
                text("SELECT COUNT(*) FROM agent_runs WHERE intent_id = :i"),
                {"i": intent_id},
            )
            return int(result.scalar_one()) == 1

        await bus.publish(
            "execution.status_changed",
            {
                "event_type": "execution.status_changed",
                "user_id": str(user.id),
                "execution_intent_id": intent_id,
                "task_id": str(intent.task_id),
                "new_status": "dispatched",
            },
            stream=stream,
        )
        assert await wait_until(_run_visible), "live event after first deploy must still project"

        service = AgentRunService(db_session)
        runs = await service.list_runs(user_id=user.id, intent_id=intent.id)
        assert runs[0].status.value == "RUNNING"
    finally:
        consumer.stop()
        await bus.close()
