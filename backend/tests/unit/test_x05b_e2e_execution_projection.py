"""X-05B · E2E：真实执行链 → EventBus → run 投影 → App 读服务可见.

非 mock 总线：真实 Redis Streams（隔离流前缀 ``x05b:test:*``，用后删净）+
真实 RunProjectionConsumer 消费组 + 真实 ExecutionService 步进代码路径
（``_publish_status_event`` 状态漏斗 + ``_handle_gateway_stream_event`` 步进
帧）。仅两类边界旁置：OpenClaw 网关本体（帧由测试驱动——传输层已有
test_openclaw_gateway_ws 覆盖）与 task monitor 正交通道（写 dev DB/共享
Redis 频道，与本卡无关，实例级 no-op）。

验收：EXECUTING 可见步进投影落 agent_runs（状态 + steps_done/current_stage
+ 审计/事件），GET /runs（mobile agent_run_read_service 的消费面）可读；
at-least-once 重投恰一次。
"""

from __future__ import annotations

import asyncio
import dataclasses

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

import app.services.execution_run_producer as run_producer
from app.api.deps import get_current_user, get_db
from app.api.v1.runs import router as runs_router
from app.models.execution_intent import ExecutionIntentStatus
from app.services.execution_service import ExecutionService
from app.services.run_projection_consumer import RunProjectionConsumer
from tests.unit.test_agent_run_service import (  # noqa: F401 — 复用 helpers
    _OUTBOX_DDL,
    _make_intent,
    _make_user,
)
from tests.unit.x05b_testkit import (
    StreamScopedBus,
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


class _SqliteSessionFactory:
    def __init__(self, session):
        self._session = session

    def __call__(self):
        return self

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, *exc):
        return False


def _frame(stream: str, **payload) -> dict:
    return {"event": "agent", "payload": {"stream": stream, **payload}}


async def _run_row(db_session, intent_id: str) -> dict | None:
    result = await db_session.execute(
        text(
            "SELECT id, status, steps_done, steps_total, current_stage, terminal_reason "
            "FROM agent_runs WHERE intent_id = :i"
        ),
        {"i": intent_id},
    )
    row = result.mappings().first()
    return dict(row) if row else None


async def test_real_execution_chain_projects_steps_and_app_reads(
    db_session, outbox_tables, x05b_redis, monkeypatch
):
    stream = x05b_stream("e2e")
    bus = make_x05b_bus(x05b_redis)

    # --- 消费端：真实 RunProjectionConsumer（隔离流 + 唯一组 = 模拟首部署） ---
    consumer = RunProjectionConsumer(event_bus=bus, session_factory=_SqliteSessionFactory(db_session))
    consumer.STREAM_NAME = stream
    consumer.GROUP_NAME = x05b_group("e2e")
    await consumer.start()

    # --- 生产端：真实 ExecutionService；步进帧驱动；monitor 正交通道 no-op ---
    service = ExecutionService(db_session)
    service._config = dataclasses.replace(service._config, transport="gateway_ws")
    monitor_calls: list[float] = []

    async def _noop_monitor(**kwargs):
        monitor_calls.append(kwargs.get("progress") or 0.0)

    service._publish_monitor_progress = _noop_monitor  # 写 dev DB/共享频道，旁置

    scoped_bus = StreamScopedBus(bus, stream)
    monkeypatch.setattr("app.services.execution_service.event_bus", scoped_bus)
    monkeypatch.setattr("app.services.execution_run_producer.event_bus", scoped_bus)
    run_producer._recently_published.clear()

    user = await _make_user(db_session)
    intent = await _make_intent(db_session, user)
    intent_id = str(intent.id)

    async def _set_intent_status(status: ExecutionIntentStatus) -> None:
        old = intent.status
        intent.status = status
        db_session.add(intent)
        await db_session.commit()
        await db_session.refresh(intent)
        await service._publish_status_event(intent, old_status=old)

    try:
        # --- 状态漏斗：dispatched → running（run 建档 RUNNING） ---
        await _set_intent_status(ExecutionIntentStatus.DISPATCHED)
        await _set_intent_status(ExecutionIntentStatus.RUNNING)

        async def _has_run() -> bool:
            return await _run_row(db_session, intent_id) is not None

        assert await wait_until(_has_run), "dispatched/running funnel must mint the run"
        row = await _run_row(db_session, intent_id)
        assert row["status"] == "RUNNING"

        # --- 步进帧（真实 _handle_gateway_stream_event 代码路径） ---
        await service._handle_gateway_stream_event(intent, _frame("lifecycle", phase="start"))
        await service._handle_gateway_stream_event(intent, _frame("tool", name="web_search", input={"q": "review"}))
        await service._handle_gateway_stream_event(intent, _frame("assistant", delta="notes ready"))
        await service._handle_gateway_stream_event(intent, _frame("lifecycle", phase="end"))

        async def _steps_done4() -> bool:
            row = await _run_row(db_session, intent_id)
            return row is not None and row["status"] == "EXECUTING" and row["steps_done"] == 4

        assert await wait_until(_steps_done4, timeout=20), "EXECUTING milestones must project steps 4/4"
        row = await _run_row(db_session, intent_id)
        assert row["steps_total"] == 4
        assert row["current_stage"] == "openclaw_finish"

        # --- at-least-once 重投恰一次：清 once-set 后重发同里程碑 → 步进无二账 ---
        run_producer._recently_published.clear()
        await run_producer.publish_execution_step_event(intent, "tool_in_use")
        await asyncio.sleep(1.5)
        row2 = await _run_row(db_session, intent_id)
        assert row2["steps_done"] == 4  # 序号单调吸收

        # --- 终态漏斗：succeeded（EXECUTING→SUCCEEDED） ---
        await _set_intent_status(ExecutionIntentStatus.SUCCEEDED)

        async def _terminal() -> bool:
            row = await _run_row(db_session, intent_id)
            return row is not None and row["status"] == "SUCCEEDED"

        assert await wait_until(_terminal), "terminal funnel must close the run"
        row = await _run_row(db_session, intent_id)
        assert row["terminal_reason"] == "completed"
        assert row["steps_done"] == 4

        # --- 审计/事件同构 ---
        run_id = row["id"]
        transitions = (
            await db_session.execute(
                text(
                    "SELECT from_status, to_status, event_name FROM agent_run_transitions "
                    "WHERE run_id = :r ORDER BY occurred_at, created_at"
                ),
                {"r": str(run_id)},
            )
        ).all()
        assert [(t[0], t[1], t[2]) for t in transitions] == [
            (None, "RUNNING", "run.created"),  # dispatched catch-up 直接 RUNNING 建档
            ("RUNNING", "EXECUTING", "run.status_changed"),
            ("EXECUTING", "SUCCEEDED", "run.status_changed"),
        ]
        outbox_events = (
            await db_session.execute(
                text("SELECT event_type FROM event_outbox WHERE aggregate_type='agent_run' ORDER BY id")
            )
        ).scalars().all()
        assert list(outbox_events) == [
            "run.created",
            "run.status_changed",  # RUNNING→EXECUTING
            "run.step_completed",  # 1 start
            "run.step_completed",  # 2 tool
            "run.step_completed",  # 3 output
            "run.step_completed",  # 4 finish
            "run.status_changed",  # EXECUTING→SUCCEEDED
        ]

        # --- App 读服务可见：GET /runs（mobile agent_run_read_service 消费面） ---
        api_app = FastAPI()
        api_app.include_router(runs_router, prefix="/api/v1")

        async def override_get_db():
            yield db_session

        api_app.dependency_overrides[get_db] = override_get_db
        api_app.dependency_overrides[get_current_user] = lambda: user
        async with AsyncClient(transport=ASGITransport(app=api_app), base_url="http://t") as client:
            fetched = await client.get(f"/api/v1/runs/{run_id}")
            assert fetched.status_code == 200
            body = fetched.json()["run"]
            assert body["status"] == "SUCCEEDED"
            assert body["steps_done"] == 4
            assert body["steps_total"] == 4
            assert body["current_stage"] == "openclaw_finish"

            listed = await client.get("/api/v1/runs", params={"intent_id": intent_id})
            assert listed.status_code == 200
            assert [item["run_id"] for item in listed.json()["items"]] == [str(run_id)]

        # monitor 旁置通道确实被驱动（且未触碰 dev DB/共享频道）。
        assert monitor_calls
    finally:
        consumer.stop()
        await bus.close()
        run_producer._recently_published.clear()
