"""统一连接池预算权威（V3-FIX-156，2026-09 wt467）

背景（wt460 n=60 深载探针 + 修前普查）：backend 曾有多个服务各自建池、互不知情——
主引擎（settings.DB_POOL_SIZE=20 + DB_MAX_OVERFLOW=40 → 60/进程）、AGE asyncpg 池
（max_size=10/进程）、推断写通道引擎（5/进程）、BillingWorker 引擎（SQLAlchemy 默认
5+10=15/FastAPI 进程）。FastAPI + gRPC 双进程理论上限 165 > 共享 PostgreSQL
max_connections=100：n=60 深载时 PG 报 "sorry, too many clients already"
（age_client init_pool / graph_rag 连接获取失败），且 AGE 池 acquire 无超时导致
请求静默排队 102-128s——LLM 池之前的 pre-pool 瓶颈（DYNAMIC_ISSUES #156）。

治理模型（本模块是唯一取数口）：

- ``PG_MAX_CONNECTIONS``：共享 PostgreSQL 的 max_connections（部署事实=100，
  ``SHOW max_connections`` 核验）；
- ``DB_CONNECTION_BUDGET``：单进程所有自建池上限之和的顶（默认 80 ≤ 100−预留）；
- ``DB_CONNECTION_RESERVE``：给迁移/运维/超级用户留的余量（默认 20）；
- ``resolve_pool_caps()``：算出各池上限；之和超预算或预算超 PG 上限减预留 →
  启动即 ValueError（快速失败，不允许带病运行）。

修后分配（单进程上限之和 = 44 ≤ 预算 80）：

============ ==================== ========== ====================================
池           参数                  上限       消费方
============ ==================== ========== ====================================
主引擎       15 + overflow 15     30         FastAPI / gRPC / Celery 各自进程
AGE asyncpg  max_size 6 (min 2)  6          graph_rag / graph_sync / 图谱服务
推断写通道    pool_size 3          3          memory_inferred_write_lane
Billing      2 + overflow 3        5          FastAPI lifespan 内 BillingWorker
============ ==================== ========== ====================================

双进程同时满载 = 88 ≤ 100，预留 12 给 Celery 空闲/运维连接。多机部署应按
``PG_MAX_CONNECTIONS`` 与进程倍数下调 ``DB_CONNECTION_BUDGET``（每池均可经
settings 单独覆盖，误配会被 ``resolve_pool_caps`` 在启动时拦下）。

诚实失败语义（配套）：AGE 池 acquire 带超时（``AGE_POOL_ACQUIRE_TIMEOUT``，默认
5s；修前为 asyncpg 默认无限等待），超时抛 ``DatabaseTimeoutError``——拿不到连接
快速可见报错，而非静默排队 100s+。主引擎 SQLAlchemy 池本就有界（pool_timeout）。
"""

from __future__ import annotations

import ssl
from dataclasses import dataclass
from typing import cast

from loguru import logger
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import QueuePool

from app.config import settings


@dataclass(frozen=True)
class PoolCaps:
    """单进程各池上限（全部自建池的取数唯一来源）。"""

    main_pool_size: int
    main_max_overflow: int
    age_min_size: int
    age_max_size: int
    inferred_pool_size: int
    billing_pool_size: int
    billing_max_overflow: int

    @property
    def total(self) -> int:
        return (
            self.main_pool_size
            + self.main_max_overflow
            + self.age_max_size
            + self.inferred_pool_size
            + self.billing_pool_size
            + self.billing_max_overflow
        )


def resolve_pool_caps(
    *,
    pg_max_connections: int | None = None,
    db_connection_budget: int | None = None,
) -> PoolCaps:
    """解析并校验各池上限；误配启动即抛（快速失败）。

    供 db/session（主引擎）、age_client（AGE 池）、memory_inferred_write_lane
    （推断写通道）、billing_worker（计费引擎）统一取数，保证单进程上限之和
    ≤ DB_CONNECTION_BUDGET ≤ PG_MAX_CONNECTIONS − DB_CONNECTION_RESERVE。
    """
    pg_max = pg_max_connections if pg_max_connections is not None else settings.PG_MAX_CONNECTIONS
    budget = db_connection_budget if db_connection_budget is not None else settings.DB_CONNECTION_BUDGET
    reserve = settings.DB_CONNECTION_RESERVE

    if budget > pg_max - reserve:
        raise ValueError(
            f"DB_CONNECTION_BUDGET({budget}) exceeds PG_MAX_CONNECTIONS({pg_max}) "
            f"minus reserve({reserve}) — pools would exhaust shared PostgreSQL "
            f"(V3-FIX-156 governance)"
        )

    caps = PoolCaps(
        main_pool_size=settings.DB_POOL_SIZE,
        main_max_overflow=settings.DB_MAX_OVERFLOW,
        age_min_size=2,
        age_max_size=settings.AGE_POOL_MAX_SIZE,
        inferred_pool_size=3,
        billing_pool_size=2,
        billing_max_overflow=3,
    )
    if caps.total > budget:
        raise ValueError(
            f"pool caps sum {caps.total} exceeds DB_CONNECTION_BUDGET({budget}): "
            f"{caps!r} — lower DB_POOL_SIZE/DB_MAX_OVERFLOW/AGE_POOL_MAX_SIZE "
            f"(V3-FIX-156 governance)"
        )
    return caps


def get_engine_pool_kwargs() -> dict[str, object]:
    """主引擎（db/session）的池参数——统一权威取数口。"""
    caps = resolve_pool_caps()
    return {
        "pool_size": caps.main_pool_size,
        "max_overflow": caps.main_max_overflow,
        "pool_recycle": settings.DB_POOL_RECYCLE,
        "pool_timeout": settings.DB_POOL_TIMEOUT,
        "pool_pre_ping": True,
    }


def create_optimized_engine() -> AsyncEngine:
    """创建受预算治理的数据库引擎（V3-FIX-156 修前为裸 40+60，超 PG 上限）。

    优化点：连接池大小受 ``resolve_pool_caps`` 预算约束、连接超时、
    回收策略、pre-ping 检查。
    """
    pool_config = get_engine_pool_kwargs()
    pool_config.update(
        {
            "pool_use_lifo": False,  # FIFO，避免连接饥饿
            "poolclass": QueuePool,
        }
    )

    engine_config: dict[str, object] = {
        "connect_args": {
            "timeout": 10,  # 连接超时
            "command_timeout": 30,  # 命令执行超时
            "server_settings": {
                "application_name": "sparkle_backend",
                "jit": "off",
            },
        },
        "echo": settings.DEBUG,
        "echo_pool": settings.DEBUG,
        "execution_options": {"isolation_level": "READ COMMITTED"},
        **pool_config,
    }

    db_url = _async_url_with_ssl(engine_config)

    engine = create_async_engine(db_url, **engine_config)  # type: ignore[arg-type]

    logger.info(
        f"Database engine created with governed pool: "
        f"pool_size={pool_config['pool_size']}, "
        f"max_overflow={pool_config['max_overflow']}, "
        f"recycle={pool_config['pool_recycle']}s "
        f"(budget={settings.DB_CONNECTION_BUDGET}/{settings.PG_MAX_CONNECTIONS})"
    )

    return engine


def _async_url_with_ssl(engine_config: dict[str, object]) -> str:
    """把 DATABASE_URL 转成 async URL 并把 sslmode 映射进 connect_args。"""
    from app.db.url import to_async_database_url

    db_url = to_async_database_url(settings.DATABASE_URL)
    parsed = make_url(db_url)
    if not parsed.drivername.startswith("postgresql+asyncpg"):
        return db_url
    query = dict(parsed.query)
    sslmode = query.pop("sslmode", None)
    sslrootcert_raw = query.pop("sslrootcert", None)
    sslrootcert = sslrootcert_raw[0] if isinstance(sslrootcert_raw, tuple) else sslrootcert_raw
    connect_args = cast("dict[str, object]", engine_config["connect_args"])
    if sslrootcert:
        connect_args["ssl"] = ssl.create_default_context(cafile=sslrootcert)
    elif sslmode == "disable":
        connect_args["ssl"] = False
    elif sslmode in ("require", "verify-ca", "verify-full"):
        connect_args["ssl"] = True
    engine_config["connect_args"] = connect_args
    return parsed.set(query=query).render_as_string(hide_password=False)


def get_pool_status(engine: AsyncEngine) -> dict[str, object]:
    """
    获取连接池状态
    """
    pool = cast("QueuePool", engine.pool)

    return {
        "pool_size": pool.size(),
        "checked_in": pool.checkedin(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "max_overflow": pool._max_overflow,
        "total_connections": pool.size() + pool.overflow(),
        "pool_recycle": pool._recycle,
        "pool_timeout": pool._timeout,
    }


# 连接池监控（可选，用于Prometheus）
try:
    from prometheus_client import Gauge

    DB_POOL_SIZE = Gauge("db_pool_connections_total", "Total database pool connections")
    DB_POOL_CHECKED_IN = Gauge("db_pool_connections_available", "Available database pool connections")
    DB_POOL_CHECKED_OUT = Gauge("db_pool_connections_in_use", "Database pool connections in use")
    DB_POOL_OVERFLOW = Gauge("db_pool_connections_overflow", "Database pool overflow connections")

    def update_pool_metrics(engine: AsyncEngine) -> None:
        """更新连接池Prometheus指标"""
        status = get_pool_status(engine)
        DB_POOL_SIZE.set(status["pool_size"])  # type: ignore[arg-type]
        DB_POOL_CHECKED_IN.set(status["checked_in"])  # type: ignore[arg-type]
        DB_POOL_CHECKED_OUT.set(status["checked_out"])  # type: ignore[arg-type]
        DB_POOL_OVERFLOW.set(status["overflow"])  # type: ignore[arg-type]

except ImportError:
    logger.warning("Prometheus not available, pool metrics disabled")

    def update_pool_metrics(engine: AsyncEngine) -> None:
        """空实现"""
        pass


async def check_pool_health(engine: AsyncEngine) -> bool:
    """
    检查连接池健康状态
    """
    try:
        status = get_pool_status(engine)

        effective_capacity = cast("int", status["pool_size"]) + cast("int", status["max_overflow"])
        is_healthy = (cast("int", status["checked_in"]) > 0 or cast("int", status.get("overflow", 0)) == 0) and (
            cast("int", status["checked_out"]) < effective_capacity * 0.9
        )

        if not is_healthy:
            logger.warning(f"Database pool unhealthy: {status}")

        return cast("bool", is_healthy)

    except Exception as e:
        logger.error(f"Pool health check failed: {e}")
        return False


# 使用建议文档
USAGE_GUIDE = """
## 连接池使用建议（V3-FIX-156 统一治理后）

### 池上限取数唯一入口

```python
from app.core.database_pool_config import resolve_pool_caps, get_engine_pool_kwargs

caps = resolve_pool_caps()          # 各池上限（总和受 DB_CONNECTION_BUDGET 约束）
kwargs = get_engine_pool_kwargs()   # 主引擎池参数
```

**禁止**新服务自建池时绕过 ``resolve_pool_caps`` 写死池参数——单进程池上限之和
超过 ``DB_CONNECTION_BUDGET``（默认 80 < PG max_connections 100 − 预留 20）会
在启动时被 ``ValueError`` 拦下（快速失败，不允许带病运行）。

### 常见问题

**连接耗尽 / "too many clients already"**
- 症状: PG 报 too many clients already，或 QueuePool TimeoutError
- 处置: 检查是否有服务绕过预算权威自建池；下调 DB_CONNECTION_BUDGET 或对应池参数

**获取超时**
- 症状: SQLAlchemy ``sqlalchemy.exc.TimeoutError`` / AGE ``DatabaseTimeoutError``
- 语义: 诚实快速失败（有界等待），用户侧可见繁忙而非静默排队 100s+
"""
