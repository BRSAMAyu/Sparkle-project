"""V3-FIX-156 pre-pool 瓶颈：统一池治理守卫 + AGE 池诚实失败。

病史（wt460 n=60 深载探针，登记于 v3 DYNAMIC_ISSUES #156）：同用户 ≥60 并发探针
全量均匀变慢（窄窗 102-128s）而 LLM 并发池排队深度保持浅位（LLM_POOL_MAX_WAITING=2
亦零 LLMOverloadedError）——瓶颈在 LLM 池之前。共享 PostgreSQL（max_connections=100，
本轮实测占用 77）报 "sorry, too many clients already"（age_client init_pool /
graph_rag 连接获取失败）。

普查（修前，见 wt467 报告）：单进程池上限之和 = 主引擎 20+40（settings 默认）+
AGE asyncpg 10 + 推断写通道 5 + BillingWorker 15（SQLAlchemy 默认）= 90；FastAPI +
gRPC 双进程理论上限 165 > PG 100。且 ``AgeClient.execute_cypher`` 走
``pool.acquire()`` **无超时**（asyncpg ``Pool.acquire(timeout=None)`` 语义为无限
等待，见 asyncpg/pool.py ``_acquire``）——池满时请求静默排队，正是 102-128s 均匀
减速、零可见错误的成因。

本文件四个断言面（修前全红，证据见 commit message）：

1. **池预算守卫**：所有自建池上限之和 ≤ ``DB_CONNECTION_BUDGET`` ≤
   ``PG_MAX_CONNECTIONS`` − 预留（纯配置面，单测级）。
2. **预算误配快速失败**：预算超 PG 上限减预留时 ``resolve_pool_caps`` 启动即抛。
3. **AGE 池诚实失败**：池满时 acquire 必须在预算时间内抛 ``DatabaseTimeoutError``
   （诚实报错），而非无限静默排队；模拟面为 asyncpg 语义等价的 never-granting
   桩池（超时语义与 asyncpg ``_acquire`` 的 ``compat.wait_for`` 对齐）。
4. **主引擎池治理**：``db.session`` 的 pool 参数来自统一预算权威，不再是裸
   settings 默认（20+40=60/进程）。

真 PG 探针（可选）：显式 ``DATABASE_URL`` 指向 postgres 非演示库时跑真实 asyncpg
池耗尽（门形制同 tests/api/test_group_file_trust_level_pg_enum_regression.py），
sqlite/演示库环境整测 skip。
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import pytest

from app.config import settings

# 预算常量（与部署事实一致：sparkle_db SHOW max_connections = 100）
_PG_MAX_CONNECTIONS_DEPLOYED = 100
_BUDGET_RESERVE = 20

_TEST_ACQUIRE_TIMEOUT = 0.2  # 桩池/真池共用的 acquire 预算（秒）
_WAIT_BUDGET = 2.0  # 测试层硬顶：诚实失败必须远小于此


# ---------------------------------------------------------------------------
# 1+2. 池预算守卫（统一权威）
# ---------------------------------------------------------------------------


def test_pool_caps_sum_within_budget() -> None:
    """所有自建池上限之和必须落在预算内（预算 ≤ PG max − 预留）。"""
    from app.core.database_pool_config import resolve_pool_caps

    caps = resolve_pool_caps()
    total = (
        caps.main_pool_size
        + caps.main_max_overflow
        + caps.age_max_size
        + caps.inferred_pool_size
        + caps.billing_pool_size
        + caps.billing_max_overflow
    )
    assert settings.PG_MAX_CONNECTIONS == _PG_MAX_CONNECTIONS_DEPLOYED
    assert settings.DB_CONNECTION_BUDGET <= settings.PG_MAX_CONNECTIONS - _BUDGET_RESERVE
    assert (
        total <= settings.DB_CONNECTION_BUDGET
    ), f"池上限之和 {total} 超预算 {settings.DB_CONNECTION_BUDGET}：{caps!r}"


def test_budget_misconfig_fails_fast() -> None:
    """预算误配（超过 PG 上限减预留）必须启动即抛，不允许带病运行。"""
    from app.core.database_pool_config import resolve_pool_caps

    with pytest.raises(ValueError, match="BUDGET"):
        resolve_pool_caps(db_connection_budget=999, pg_max_connections=100)


# ---------------------------------------------------------------------------
# 3. AGE 池诚实失败（池满 → 预算内 DatabaseTimeoutError，非无限排队）
# ---------------------------------------------------------------------------


class _NeverGrantingAcquireCtx:
    """模拟 asyncpg 池满且持有者永不释放的 acquire 上下文。

    超时语义与 asyncpg ``Pool._acquire`` 对齐：给定 timeout 时在预算内抛
    ``asyncio.TimeoutError``；timeout=None（修前 AgeClient 的调用形态）则
    无限等待——正是 V3-FIX-156 的静默排队面。
    """

    def __init__(self, timeout: float | None) -> None:
        self._timeout = timeout

    async def __aenter__(self) -> None:
        if self._timeout is None:
            await asyncio.Event().wait()  # 无超时 = 无限排队（修前病灶）
        await asyncio.wait_for(asyncio.Event().wait(), timeout=self._timeout)
        raise AssertionError("never-granting pool must not grant a connection")

    async def __aexit__(self, *exc: object) -> bool:
        return False


class _NeverGrantingPool:
    def acquire(self, timeout: float | None = None) -> _NeverGrantingAcquireCtx:
        return _NeverGrantingAcquireCtx(timeout)


async def test_age_pool_acquire_timeout_honest_failure() -> None:
    """AGE 池满：acquire 必须在预算内诚实抛 DatabaseTimeoutError。"""
    from app.core.age_client import AgeClient, AgeConfig
    from app.core.exceptions import DatabaseTimeoutError

    client = AgeClient(AgeConfig(pool_size=2, acquire_timeout=_TEST_ACQUIRE_TIMEOUT))
    client.pool = _NeverGrantingPool()  # type: ignore[assignment]

    started = time.monotonic()
    with pytest.raises(DatabaseTimeoutError):
        await asyncio.wait_for(
            client.execute_cypher("MATCH (n) RETURN n"),
            timeout=_WAIT_BUDGET,
        )
    elapsed = time.monotonic() - started
    assert elapsed < _WAIT_BUDGET, f"诚实失败应在预算内，实测 {elapsed:.2f}s"


# ---------------------------------------------------------------------------
# 4. 主引擎池治理（db/session 参数来自统一权威）
# ---------------------------------------------------------------------------


def test_main_engine_pool_uses_governed_caps() -> None:
    from app.core.database_pool_config import resolve_pool_caps
    from app.db.session import _get_engine_kwargs

    caps = resolve_pool_caps()
    kwargs: dict[str, Any] = _get_engine_kwargs("postgresql+asyncpg://u:p@localhost:5432/db", None, None)
    assert kwargs["pool_size"] == caps.main_pool_size
    assert kwargs["max_overflow"] == caps.main_max_overflow
    assert kwargs["pool_timeout"] <= 30  # 有界获取，非无限排队


# ---------------------------------------------------------------------------
# 5. 真 PG 探针（可选）：真实 asyncpg 池耗尽 → 预算内诚实失败
# ---------------------------------------------------------------------------


def _require_real_pg_database_url() -> str:
    from tests import _dbguard

    database_url = getattr(settings, "DATABASE_URL", "") or ""
    if not database_url.startswith(("postgresql", "postgres")):
        pytest.skip(
            "真 PG 探针需要显式 DATABASE_URL 指向 postgres *_test 库，"
            f"当前 {database_url!r}（sqlite 无法验证 asyncpg 池语义）"
        )
    if _dbguard.is_demo_db_url(database_url):
        pytest.skip("TEST-DBGUARD: 拒绝在演示库(sparkle)上运行真 PG 探针")
    return database_url


async def test_age_pool_real_pg_exhaustion_honest_failure() -> None:
    """真实 asyncpg 池（max_size=1）被占满后，execute_cypher 预算内诚实失败。"""
    _require_real_pg_database_url()

    from urllib.parse import unquote, urlparse

    from app.core.age_client import AgeClient, AgeConfig
    from app.core.exceptions import DatabaseTimeoutError
    from app.db.url import to_async_database_url

    db_url = to_async_database_url(settings.DATABASE_URL)
    parsed = urlparse(db_url.replace("postgresql+asyncpg://", "postgresql://"))
    client = AgeClient(
        AgeConfig(
            host=parsed.hostname or "localhost",
            port=parsed.port or 5432,
            user=unquote(parsed.username or "postgres"),
            password=unquote(parsed.password or ""),
            database=(parsed.path.lstrip("/") or "sparkle_test"),
            pool_size=1,
            min_size=1,
            acquire_timeout=_TEST_ACQUIRE_TIMEOUT,
        )
    )
    await client.init_pool()
    try:
        assert client.pool is not None
        holder = await client.pool.acquire()  # 占满唯一连接
        try:
            started = time.monotonic()
            with pytest.raises(DatabaseTimeoutError):
                await asyncio.wait_for(
                    client.execute_cypher("MATCH (n) RETURN n"),
                    timeout=_WAIT_BUDGET,
                )
            elapsed = time.monotonic() - started
            assert elapsed < _WAIT_BUDGET
        finally:
            await client.pool.release(holder)
    finally:
        await client.close()
