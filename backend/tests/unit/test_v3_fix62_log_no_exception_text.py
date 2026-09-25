"""V3-FIX-62 · 工具历史落库失败日志不得携带异常消息文本 —— 红绿锁.

wt410 审查轮活体 PostgreSQL 证伪（P2）：仅取 ``str(e.orig)`` 的方案在
psycopg2/asyncpg 上仍泄漏——``str(orig)`` 的 DETAIL 内嵌列值（如
``Key (email)=(secret-alice@example.com) already exists.``）。Q-05 红队
43 scenario 全绿是因为 sqlite 的 orig 不含绑定值（面差）。

修复后口径：异常路径日志只落「异常类名 + DBAPI 类名/错误码」，
零消息文本 = 零泄漏（与驱动无关，构造性免疫）。

executor 侧 ``_record_tool_execution`` 的同形日志点共用同一口径（同批
修复，形态一致，此处以 service 面为代表锁定）。
"""

from __future__ import annotations

import uuid

import pytest
from loguru import logger

from app.services.tool_history_service import ToolHistoryService

_SECRET = "secret-alice@example.com"


class _FakeDBAPIError(Exception):
    """psycopg2 形态：str() 内嵌 DETAIL 载值 + pgcode。"""

    pgcode = "23505"


class _FakeSAError(Exception):
    """SQLAlchemy 形态：str 含 [SQL]/[parameters]，orig 指 DBAPI 异常。"""


class _BoomSession:
    """flush 即抛载值异常的假会话（构造/入库路径最小化）。"""

    def add(self, *_args, **_kwargs) -> None:
        return None

    async def flush(self):
        dbapi = _FakeDBAPIError(
            f'duplicate key value violates unique constraint "user_tool_history_pkey"\n'
            f"DETAIL: Key (email)=({_SECRET}) already exists."
        )
        exc = _FakeSAError(
            "(psycopg2.errors.UniqueViolation) duplicate key value violates unique constraint\n"
            f"[SQL: INSERT INTO user_tool_history (email) VALUES ('{_SECRET}')]\n"
            f"[parameters: ('{_SECRET}',)]"
        )
        exc.orig = dbapi
        raise exc


@pytest.mark.asyncio
async def test_record_failure_log_carries_no_exception_text():
    messages: list[str] = []
    sink_id = logger.add(lambda m: messages.append(m), level="DEBUG")

    try:
        service = ToolHistoryService(_BoomSession())  # type: ignore[arg-type]
        with pytest.raises(_FakeSAError):
            await service.record_tool_execution(
                user_id=uuid.uuid4(),
                tool_name="stub_create_task",
                success=True,
            )
    finally:
        logger.remove(sink_id)

    joined = "\n".join(messages)
    assert _SECRET not in joined, (
        "落库失败日志不得携带异常消息文本（V3-FIX-62：DETAIL/[SQL]/[parameters] 均含正文），" f"实际捕获:\n{joined}"
    )
    assert "Failed to record tool execution" in joined, "失败事实本身必须可见"
    assert (
        "_FakeSAError" in joined and "_FakeDBAPIError" in joined
    ), "类名 + DBAPI 形态是排障所必需的最小信息，不得一并丢弃"
    assert "23505" in joined, "DB 错误码（pgcode）是零泄漏的可观测补偿，应保留"
