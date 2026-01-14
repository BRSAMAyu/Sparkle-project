"""
Database Session Management
使用 SQLAlchemy 2.0 异步接口
支持 PostgreSQL 连接池配置和 SQLite 开发模式
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool
from sqlalchemy.engine import make_url

from app.config import settings


def _sanitize_asyncpg_url(url: str) -> tuple[str, str | None]:
    if not url.startswith("postgresql+asyncpg"):
        return url, None
    parsed = make_url(url)
    query = dict(parsed.query)
    sslmode = query.pop("sslmode", None)
    if sslmode is None:
        return url, None
    return str(parsed.set(query=query)), sslmode


def _get_engine_kwargs(sslmode: str | None):
    """
    根据数据库类型返回适当的引擎配置
    PostgreSQL 使用连接池，SQLite 使用 NullPool
    """
    is_sqlite = settings.DATABASE_URL.startswith("sqlite")

    if is_sqlite:
        # SQLite 不支持连接池，使用 NullPool
        return {
            "poolclass": NullPool,
            "echo": settings.DEBUG or settings.DB_ECHO,
            "future": True,
        }
    else:
        # PostgreSQL 使用连接池配置
        connect_args = {}
        if sslmode:
            if sslmode == "disable":
                connect_args["ssl"] = False
            elif sslmode in ("require", "verify-ca", "verify-full"):
                connect_args["ssl"] = True
        elif not settings.DEBUG:
            connect_args["ssl"] = "require"

        return {
            "pool_size": settings.DB_POOL_SIZE,
            "max_overflow": settings.DB_MAX_OVERFLOW,
            "pool_recycle": settings.DB_POOL_RECYCLE,
            "pool_timeout": settings.DB_POOL_TIMEOUT,
            "pool_pre_ping": True,  # 连接前健康检查
            "echo": settings.DEBUG or settings.DB_ECHO,
            "future": True,
            "connect_args": connect_args,
        }


_async_db_url, _sslmode = _sanitize_asyncpg_url(settings.DATABASE_URL)
engine = create_async_engine(
    _async_db_url,
    **_get_engine_kwargs(_sslmode),
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Base class for models
Base = declarative_base()


async def get_db() -> AsyncSession:
    """
    Dependency function to get database session
    用于 FastAPI 依赖注入

    事务管理：
    - 成功时自动提交
    - 异常时自动回滚
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db_no_commit() -> AsyncSession:
    """
    获取数据库会话但不自动提交
    适用于只读操作或需要手动控制事务的场景
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
