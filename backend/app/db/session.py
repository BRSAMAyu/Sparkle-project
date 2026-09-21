"""
Database Session Management
使用 SQLAlchemy 2.0 异步接口
支持 PostgreSQL 连接池配置和 SQLite 开发模式
"""
from __future__ import annotations

import asyncio
import logging
import ssl

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool

from app.config import settings
from app.db.url import to_async_database_url

logger = logging.getLogger(__name__)

_EXTERNAL_TRANSACTION_MANAGED_KEY = "external_transaction_managed"


def _sanitize_asyncpg_url(url: str) -> tuple[str, str | None, str | None]:
    parsed = make_url(url)
    if not parsed.drivername.startswith("postgresql+asyncpg"):
        return url, None, None
    query = dict(parsed.query)
    sslmode = query.pop("sslmode", None)
    sslrootcert = query.pop("sslrootcert", None)
    if sslmode is None and sslrootcert is None:
        return url, None, None
    return parsed.set(query=query).render_as_string(hide_password=False), sslmode, sslrootcert


def _get_engine_kwargs(db_url: str, sslmode: str | None, sslrootcert: str | None):
    """
    根据数据库类型返回适当的引擎配置
    PostgreSQL 使用连接池，SQLite 使用 NullPool

    NOTE: asyncpg 0.31+ compatibility
    - asyncpg does NOT accept 'sslmode' string parameter in connect_args
    - asyncpg requires 'ssl' parameter (bool or SSLContext), NOT 'sslmode'
    - We map sslmode values to asyncpg's ssl parameter:
      - 'disable' -> ssl=False
      - 'require', 'verify-ca', 'verify-full' -> ssl=True
      - sslrootcert -> ssl=SSLContext with certificate verification
    """
    is_sqlite = db_url.startswith("sqlite")

    if is_sqlite:
        # SQLite 不支持连接池，使用 NullPool
        return {
            "poolclass": NullPool,
            "echo": settings.DB_ECHO,
            "future": True,
        }
    else:
        # PostgreSQL 使用连接池配置
        # asyncpg requires 'ssl' parameter (bool or SSLContext), NOT 'sslmode'
        connect_args = {}

        if sslrootcert:
            # With certificate, create SSL context for verification
            connect_args["ssl"] = ssl.create_default_context(cafile=sslrootcert)
        elif sslmode == "disable":
            # Explicitly disable SSL
            connect_args["ssl"] = False
        elif sslmode in ("require", "verify-ca", "verify-full"):
            # Enable SSL without certificate verification
            connect_args["ssl"] = True
        elif not settings.DEBUG:
            # Production default: require SSL
            connect_args["ssl"] = True
        else:
            # Development: disable SSL for local connections
            connect_args["ssl"] = False

        return {
            "pool_size": settings.DB_POOL_SIZE,
            "max_overflow": settings.DB_MAX_OVERFLOW,
            "pool_recycle": settings.DB_POOL_RECYCLE,
            "pool_timeout": settings.DB_POOL_TIMEOUT,
            "pool_pre_ping": True,  # 连接前健康检查
            "echo": settings.DB_ECHO,
            "future": True,
            "connect_args": connect_args,
        }


_async_db_url = to_async_database_url(settings.DATABASE_URL)
_async_db_url, _sslmode, _sslrootcert = _sanitize_asyncpg_url(_async_db_url)
engine = create_async_engine(
    _async_db_url,
    **_get_engine_kwargs(_async_db_url, _sslmode, _sslrootcert),
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
            session.sync_session.info[_EXTERNAL_TRANSACTION_MANAGED_KEY] = True
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            session.sync_session.info.pop(_EXTERNAL_TRANSACTION_MANAGED_KEY, None)
            await session.close()


async def get_db_no_commit() -> AsyncSession:
    """
    获取数据库会话但不自动提交
    适用于只读操作或需要手动控制事务的场景
    """
    async with AsyncSessionLocal() as session:
        try:
            session.sync_session.info[_EXTERNAL_TRANSACTION_MANAGED_KEY] = True
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            session.sync_session.info.pop(_EXTERNAL_TRANSACTION_MANAGED_KEY, None)
            await session.close()


from contextlib import contextmanager


@contextmanager
def get_db_context():
    """
    同步上下文管理器，用于Celery任务中获取数据库会话

    用法（任务体保持同步，在同步体内驱动协程）:
        with get_db_context() as db:
            asyncio.run(async_function(db))

    事务管理：
    - 成功时自动提交
    - 异常时自动回滚

    NOTE(EI-01/EI-03):
    - commit/rollback/close 各自通过 asyncio.run 在独立的短命事件循环上驱动，
      因此**禁止**在本上下文管理器的 with 体内再嵌套事件循环（如写在 async 函数里
      由 _run_async 驱动）——那会让 __exit__ 的 asyncio.run 撞上运行中的循环直接
      RuntimeError。会话生命周期需要跨 await 的任务请改用协程内
      `async with AsyncSessionLocal()` 模式（见 app/core/celery_tasks.py）。
    - 回滚/关闭自身的失败仅记录日志，永不替换 with 体内抛出的原始异常。
    """
    session = AsyncSessionLocal()
    try:
        yield session
        asyncio.run(_commit_session(session))
    except Exception:
        try:
            asyncio.run(_rollback_session(session))
        except Exception as rollback_error:
            logger.warning(
                "get_db_context rollback failed (original exception preserved): %s",
                rollback_error,
            )
        raise
    finally:
        try:
            asyncio.run(_close_session(session))
        except Exception as close_error:
            logger.warning("get_db_context close failed: %s", close_error)


async def _commit_session(session: AsyncSession):
    """异步提交会话"""
    await session.commit()


async def _rollback_session(session: AsyncSession):
    """异步回滚会话"""
    await session.rollback()


async def _close_session(session: AsyncSession):
    """异步关闭会话"""
    await session.close()
