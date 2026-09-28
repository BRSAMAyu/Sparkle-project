"""V4-Q03 验收探针夹具（验收剧本；不入生产测试树——用后保留于证据目录）.

复用 backend/tests/conftest.py 的模型注册与工具夹具；本探针自带独立 sqlite
引擎（j06_hybrid_journey 测试同法），不触演示库（TEST-DBGUARD 纪律）。
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.models.base import Base

# 模型注册（全表元数据）+ 复用既有 helper/DDL 的单一出处。
import tests.conftest  # noqa: F401 — 侧效应：全模型注册进 Base.metadata
from tests.unit.test_action_command_service import _OUTBOX_DDL, _make_user  # noqa: F401

#: G-02 吸收器的 evidence 账本表（test_outcome_absorption 同款 sqlite DDL）。
#: created_at 带默认值：生产写路径（spark_node/update_node_mastery 的
#: INSERT）不供给 created_at，由 PG server default 覆盖——sqlite 探针侧用
#: DEFAULT 补齐同语义，否则完成面结算写入会被误伤成假阴性。
MASTERY_AUDIT_DDL = """
    CREATE TABLE IF NOT EXISTS mastery_audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        node_id TEXT NOT NULL,
        user_id TEXT NOT NULL,
        old_mastery INTEGER NOT NULL,
        new_mastery INTEGER NOT NULL,
        reason TEXT,
        request_id TEXT,
        revision INTEGER DEFAULT 1,
        created_at DATETIME NOT NULL DEFAULT (datetime('now')),
        effect_kind TEXT
    )
"""


@pytest_asyncio.fixture(name="q03_maker")
async def q03_maker_fixture(monkeypatch):
    """独立 sqlite 引擎（StaticPool 单连接）；X-06 executor 会话工厂指向同引擎。

    yields SimpleNamespace(db=常驻会话, maker=同引擎 sessionmaker, engine=引擎)。
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        for ddl in _OUTBOX_DDL:
            await conn.execute(text(ddl))
        await conn.execute(text(MASTERY_AUDIT_DDL))
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    import app.orchestration.executor as executor_module

    monkeypatch.setattr(executor_module, "_agent_run_session_factory", factory)
    monkeypatch.setattr(executor_module, "_ledger_session_factory", factory)

    # sqlite 方言边界：GalaxyService._write_mastery_outbox_event 以裸 text() 绑定
    # UUID（asyncpg 原生支持，aiosqlite 不支持）。本探针建了 outbox 表（runs 面
    # 需要），使该 transport 语句真实执行并暴露 bind 错误→整个掌握写事务被回滚。
    # 生产 PG 路径不受影响（asyncpg 原生绑 UUID）。outbox 是传输管道不是掌握
    # 真源——按 house 总线桩纪律（j06 _RecordingBus 同哲学）stub 掉，掌握状态行
    # 与 mastery_audit_log 审计行保持真实写。
    from app.services.galaxy_service import GalaxyService

    async def _outbox_stub(self, **_kwargs):  # noqa: ANN001, ANN202
        return None

    monkeypatch.setattr(GalaxyService, "_write_mastery_outbox_event", _outbox_stub)

    async with factory() as db:
        yield SimpleNamespace(db=db, maker=factory, engine=engine)
    await engine.dispose()


@pytest_asyncio.fixture(name="q03_db")
async def q03_db_fixture(q03_maker):
    """常驻会话（与 q03_maker 同引擎；StaticPool 单连接共享）。"""
    yield q03_maker.db
