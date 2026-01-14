"""
PostgreSQL Connection Pool Configuration - 连接池优化

优化数据库连接池配置以提升性能
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy.pool import QueuePool
from loguru import logger
from sqlalchemy.engine import make_url

from app.config import settings


def create_optimized_engine() -> AsyncEngine:
    """
    创建优化后的数据库引擎

    优化点：
    1. 连接池大小调整（基于负载）
    2. 连接超时配置
    3. 连接回收策略
    4. 预ping检查
    """

    # 连接池配置
    pool_config = {
        # 1. 连接池大小
        "pool_size": 20,  # 常驻连接数（生产环境建议 10-30）
        "max_overflow": 30,  # 超出pool_size的最大额外连接数

        # 2. 连接回收策略
        "pool_recycle": 3600,  # 1小时后回收连接（防止MySQL gone away）
        "pool_pre_ping": True,  # 每次取连接前先ping，确保连接有效

        # 3. 连接超时
        "pool_timeout": 30,  # 等待连接的超时时间（秒）

        # 4. 连接验证
        "pool_use_lifo": False,  # 使用FIFO（先进先出），避免连接饥饿

        # 5. 连接类
        "poolclass": QueuePool,  # 使用队列池（默认）
    }

    # Engine 配置
    engine_config = {
        # 1. 连接参数
        "connect_args": {
            "timeout": 10,  # 连接超时
            "command_timeout": 30,  # 命令执行超时
            "server_settings": {
                "application_name": "sparkle_backend",  # 便于在pg_stat_activity中识别
                "jit": "off",  # 关闭JIT（某些查询可能更快）
            }
        },

        # 2. Echo SQL（开发环境）
        "echo": settings.DEBUG,  # 生产环境关闭

        # 3. 连接池日志
        "echo_pool": settings.DEBUG,

        # 4. 执行选项
        "execution_options": {
            "isolation_level": "READ COMMITTED",  # 事务隔离级别
        },

        # 5. 合并连接池配置
        **pool_config
    }

    db_url = settings.DATABASE_URL
    if db_url.startswith("postgresql+asyncpg"):
        parsed = make_url(db_url)
        query = dict(parsed.query)
        sslmode = query.pop("sslmode", None)
        if sslmode == "disable":
            engine_config["connect_args"]["ssl"] = False
        elif sslmode in ("require", "verify-ca", "verify-full"):
            engine_config["connect_args"]["ssl"] = True
        db_url = str(parsed.set(query=query))

    # 创建引擎
    engine = create_async_engine(
        db_url,
        **engine_config
    )

    logger.info(
        f"Database engine created with optimized pool: "
        f"pool_size={pool_config['pool_size']}, "
        f"max_overflow={pool_config['max_overflow']}, "
        f"recycle={pool_config['pool_recycle']}s"
    )

    return engine


def get_pool_status(engine: AsyncEngine) -> dict:
    """
    获取连接池状态

    Returns:
        dict: 连接池统计信息
    """
    pool = engine.pool

    return {
        "pool_size": pool.size(),  # 当前池大小
        "checked_in": pool.checkedin(),  # 可用连接数
        "checked_out": pool.checkedout(),  # 已使用连接数
        "overflow": pool.overflow(),  # 溢出连接数（超出pool_size的部分）
        "total_connections": pool.size() + pool.overflow(),
        "pool_recycle": pool._recycle,  # 回收时间
        "pool_timeout": pool._timeout,  # 超时时间
    }


# 连接池监控（可选，用于Prometheus）
try:
    from prometheus_client import Gauge

    # Prometheus 指标
    DB_POOL_SIZE = Gauge(
        'db_pool_connections_total',
        'Total database pool connections'
    )

    DB_POOL_CHECKED_IN = Gauge(
        'db_pool_connections_available',
        'Available database pool connections'
    )

    DB_POOL_CHECKED_OUT = Gauge(
        'db_pool_connections_in_use',
        'Database pool connections in use'
    )

    DB_POOL_OVERFLOW = Gauge(
        'db_pool_connections_overflow',
        'Database pool overflow connections'
    )

    def update_pool_metrics(engine: AsyncEngine):
        """更新连接池Prometheus指标"""
        status = get_pool_status(engine)
        DB_POOL_SIZE.set(status["pool_size"])
        DB_POOL_CHECKED_IN.set(status["checked_in"])
        DB_POOL_CHECKED_OUT.set(status["checked_out"])
        DB_POOL_OVERFLOW.set(status["overflow"])

except ImportError:
    logger.warning("Prometheus not available, pool metrics disabled")

    def update_pool_metrics(engine: AsyncEngine):
        """空实现"""
        pass


# 连接池健康检查
async def check_pool_health(engine: AsyncEngine) -> bool:
    """
    检查连接池健康状态

    Args:
        engine: 数据库引擎

    Returns:
        bool: 是否健康
    """
    try:
        status = get_pool_status(engine)

        # 健康检查条件
        is_healthy = (
            status["checked_in"] > 0 and  # 有可用连接
            status["checked_out"] < status["pool_size"] * 0.9  # 使用率 < 90%
        )

        if not is_healthy:
            logger.warning(
                f"Database pool unhealthy: {status}"
            )

        return is_healthy

    except Exception as e:
        logger.error(f"Pool health check failed: {e}")
        return False


# 使用建议文档
USAGE_GUIDE = """
## 连接池使用建议

### 1. 创建引擎
```python
from app.core.database_pool_config import create_optimized_engine

engine = create_optimized_engine()
```

### 2. 监控连接池
```python
from app.core.database_pool_config import get_pool_status, update_pool_metrics

# 获取状态
status = get_pool_status(engine)
print(f"可用连接: {status['checked_in']}")

# 更新Prometheus指标（如果启用）
update_pool_metrics(engine)
```

### 3. 健康检查
```python
from app.core.database_pool_config import check_pool_health

is_healthy = await check_pool_health(engine)
```

### 4. 调优参数

**小型应用** (< 100 并发)
- pool_size: 10
- max_overflow: 10

**中型应用** (100-1000 并发)
- pool_size: 20
- max_overflow: 30

**大型应用** (> 1000 并发)
- pool_size: 50
- max_overflow: 50

**注意**:
- 总连接数 = pool_size + max_overflow
- PostgreSQL 默认最大连接数: 100
- 建议: max_connections(PG) = (pool_size + max_overflow) * instances + 20

### 5. 常见问题

**连接耗尽**
- 症状: `QueuePool limit exceeded`
- 解决: 增加 max_overflow 或检查连接泄漏

**连接超时**
- 症状: `TimeoutError: QueuePool limit of size X overflow Y reached`
- 解决: 增加 pool_timeout 或优化慢查询

**连接回收**
- 原因: pool_recycle 时间到达
- 影响: 短暂性能下降
- 建议: 设置为 3600s (1小时)
"""
