"""X-09 · 崩溃恢复 e2e：真实 SIGKILL 子进程 → 重启 → 恢复决策正确执行.

场景（卡面工作项 2 / acceptance「杀进程→重启→恢复决策正确执行」）：

1. 子进程打开文件 sqlite，建 user + RUNNING run + **in_progress 账本行**
   （side-effect 调用执行中间的持久状态：已 flush/commit、未 finalize）；
2. 子进程对自己发 SIGKILL——无 finally、无 rollback、无账本收敛（kill -9
   语义，区别于任何优雅失败路径）；
3. 「重启」后的父进程打开同一 DB 文件执行主动恢复
   （AgentRunService.recover_inflight_runs）：
   - 账本行收敛 interrupted（效果不可核实的显式终态）；
   - run → UNKNOWN_OUTCOME(worker_restart_orphan)——绝不自动重驱动；
   - 幂等：重放恢复 pass 不改写 interrupted、不再迁移终态 run；
   - 无中断证据的活跃 run 只得 reattach 建议（不猜孤儿）。
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.run_state_machine import RunStatus
from app.models.agent_run import AgentRun
from app.models.agent_tool_call import AgentToolCall
from app.services.agent_run_service import AgentRunService

_BACKEND_ROOT = Path(__file__).resolve().parents[2]  # .../backend

# 复用 X-05 测试的最小 outbox DDL（恢复迁移同事务写事件）。
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
        next_sequence INTEGER NOT NULL DEFAULT 1,
        PRIMARY KEY (aggregate_type, aggregate_id)
    )
    """,
)

_CRASH_SCRIPT = r"""
import asyncio
import os
import signal
import sys
from datetime import UTC, datetime, timedelta
from uuid import UUID

sys.path.insert(0, ".")

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import tests.conftest  # noqa: F401 — 完整模型注册表（FK 解析需要）

from app.core.run_state_machine import RunStatus
from app.models.agent_run import AgentRun
from app.models.agent_tool_call import AgentToolCall
from app.models.base import Base
from app.models.user import User

DB_PATH = sys.argv[1]
RUN_ID = UUID(sys.argv[2])
LEDGER_ID = UUID(sys.argv[3])


async def main() -> None:
    engine = create_async_engine(f"sqlite+aiosqlite:///{DB_PATH}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        user = User(id=UUID(sys.argv[4]), username="crash", email="crash@x.io", hashed_password="t")
        session.add(user)
        await session.flush()
        run = AgentRun(
            id=RUN_ID,
            user_id=user.id,
            objective="in-flight run at crash moment",
            status=RunStatus.RUNNING,
            heartbeat_at=datetime.now(UTC).replace(tzinfo=None),
        )
        session.add(run)
        # in-flight side-effect 调用：闸门已过、账本 in_progress 已提交、
        # 进程即将死在工具执行中间（无人 finalize——kill -9 不可达优雅路径）。
        row = AgentToolCall(
            id=LEDGER_ID,
            user_id=user.id,
            run_id=run.id,
            tool_name="generate_tasks_for_plan",
            idempotency_key="crash-key-1",
            args_hash="h" * 64,
            status="in_progress",
            started_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=1),
        )
        session.add(row)
        await session.commit()
    # 模拟 kill -9：无 finally / 无 rollback / 无收敛。
    os.kill(os.getpid(), signal.SIGKILL)


asyncio.run(main())
"""


@pytest.mark.timeout(240)
async def test_crash_kill9_then_recovery_decides_correctly(tmp_path):
    db_path = tmp_path / "x09_crash.sqlite3"
    run_id = uuid.uuid4()
    ledger_id = uuid.uuid4()
    user_id = uuid.uuid4()

    # 1. 「执行中」子进程：落 in-flight 状态后 SIGKILL 自杀。
    proc = subprocess.run(
        [
            sys.executable,
            "-c",
            _CRASH_SCRIPT,
            str(db_path),
            str(run_id),
            str(ledger_id),
            str(user_id),
        ],
        cwd=str(_BACKEND_ROOT),
        env={**os.environ, "SECRET_KEY": "test"},
        capture_output=True,
        timeout=180,
    )
    assert (
        proc.returncode == -signal.SIGKILL
    ), f"child must die by SIGKILL, got {proc.returncode}: {proc.stderr[-2000:]}"

    # 2. 「重启」：新进程打开同一 DB 文件，执行主动恢复。
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    try:
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as session:
            for ddl in _OUTBOX_DDL:
                await session.execute(text(ddl))
            await session.commit()

            # 无中断证据的活跃 run（另一 worker 正常持有）：只允许 reattach 建议。
            from app.models.user import User as _User

            healthy_user = uuid.uuid4()
            session.add(_User(id=healthy_user, username="healthy", email="healthy@x.io", hashed_password="t"))
            await session.flush()
            healthy_run = AgentRun(
                user_id=healthy_user,
                objective="healthy active run",
                status=RunStatus.RUNNING,
                heartbeat_at=datetime.now(UTC).replace(tzinfo=None),
            )
            session.add(healthy_run)
            await session.commit()

            payload = await AgentRunService(session).recover_inflight_runs(stale_after_seconds=600)

            decisions = {d["run_id"]: d["decision"] for d in payload["decisions"]}
            assert decisions[str(run_id)] == "unknown_outcome"
            assert decisions[str(healthy_run.id)] == "reattach_candidate"
            assert payload["ledger_reconciled"] == 1

            run = await session.get(AgentRun, run_id)
            assert run.status == RunStatus.UNKNOWN_OUTCOME
            assert run.terminal_reason == "worker_restart_orphan"
            assert run.error_category == "unknown_outcome"

            row = await session.get(AgentToolCall, ledger_id)
            assert row.status == "interrupted"
            assert row.finished_at is not None

            # 事件面：run.status_changed（UNKNOWN_OUTCOME 终态）已入 outbox。
            events = (
                await session.execute(
                    text(
                        "SELECT payload FROM event_outbox WHERE aggregate_id = :rid AND event_type = 'run.status_changed' "
                        "ORDER BY sequence_number"
                    ),
                    {"rid": str(run_id)},
                )
            ).fetchall()
            assert events, "recovery must emit run.status_changed for UNKNOWN_OUTCOME"
            assert '"to": "UNKNOWN_OUTCOME"' in events[-1][0]

        # 3. 恢复 pass 重放（再次重启）：幂等——不改写 interrupted、不再迁移。
        async with factory() as session:
            payload2 = await AgentRunService(session).recover_inflight_runs(stale_after_seconds=600)
            assert payload2["ledger_reconciled"] == 0
            row = await session.get(AgentToolCall, ledger_id)
            assert row.status == "interrupted"
            decisions2 = {d["run_id"]: d["decision"] for d in payload2["decisions"]}
            assert decisions2[str(run_id)] == "terminal_noop"
    finally:
        await engine.dispose()
