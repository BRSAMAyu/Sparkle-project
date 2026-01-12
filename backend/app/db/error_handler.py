"""
Database Error Handler
将 SQLAlchemy 异常转换为应用自定义异常
"""
import logging
import functools
from typing import Callable, TypeVar, ParamSpec
from sqlalchemy.exc import (
    IntegrityError,
    OperationalError,
    TimeoutError as SQLAlchemyTimeoutError,
    DisconnectionError,
    InterfaceError,
    DataError,
    ProgrammingError,
    InvalidRequestError,
)

from app.core.exceptions import (
    DatabaseError,
    DatabaseConnectionError,
    DatabaseTimeoutError,
    DuplicateKeyError,
    ForeignKeyViolationError,
    DataIntegrityError,
    DeadlockError,
)

logger = logging.getLogger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


def handle_db_error(error: Exception) -> None:
    """
    处理数据库异常，将其转换为应用自定义异常

    Args:
        error: SQLAlchemy 或数据库驱动抛出的异常

    Raises:
        对应的自定义数据库异常
    """
    error_str = str(error).lower()

    # 处理 IntegrityError (唯一键、外键约束等)
    if isinstance(error, IntegrityError):
        if "unique" in error_str or "duplicate" in error_str:
            logger.warning(f"Duplicate key error: {error}")
            raise DuplicateKeyError(
                message="数据已存在，请检查是否重复",
                detail={"original_error": str(error)}
            )
        elif "foreign key" in error_str or "foreignkey" in error_str:
            logger.warning(f"Foreign key violation: {error}")
            raise ForeignKeyViolationError(
                message="关联数据不存在或无法删除",
                detail={"original_error": str(error)}
            )
        else:
            logger.error(f"Data integrity error: {error}")
            raise DataIntegrityError(
                message="数据完整性错误",
                detail={"original_error": str(error)}
            )

    # 处理连接相关异常
    if isinstance(error, (DisconnectionError, InterfaceError)):
        logger.error(f"Database connection error: {error}")
        raise DatabaseConnectionError(
            message="数据库连接失败，请稍后重试",
            detail={"original_error": str(error)}
        )

    # 处理超时异常
    if isinstance(error, SQLAlchemyTimeoutError):
        logger.error(f"Database timeout error: {error}")
        raise DatabaseTimeoutError(
            message="数据库操作超时，请稍后重试",
            detail={"original_error": str(error)}
        )

    # 处理操作异常 (包括死锁)
    if isinstance(error, OperationalError):
        if "deadlock" in error_str:
            logger.warning(f"Database deadlock detected: {error}")
            raise DeadlockError(
                message="数据库死锁，请重试操作",
                detail={"original_error": str(error)}
            )
        elif "timeout" in error_str or "timed out" in error_str:
            logger.error(f"Database timeout error: {error}")
            raise DatabaseTimeoutError(
                message="数据库操作超时",
                detail={"original_error": str(error)}
            )
        elif "connection" in error_str or "connect" in error_str:
            logger.error(f"Database connection error: {error}")
            raise DatabaseConnectionError(
                message="数据库连接失败",
                detail={"original_error": str(error)}
            )
        else:
            logger.error(f"Database operational error: {error}")
            raise DatabaseError(
                message="数据库操作失败",
                detail={"original_error": str(error)}
            )

    # 处理数据错误
    if isinstance(error, DataError):
        logger.error(f"Database data error: {error}")
        raise DataIntegrityError(
            message="数据格式错误",
            detail={"original_error": str(error)}
        )

    # 处理编程错误 (SQL 语法错误等)
    if isinstance(error, ProgrammingError):
        logger.error(f"Database programming error: {error}")
        raise DatabaseError(
            message="数据库查询错误",
            detail={"original_error": str(error)}
        )

    # 处理无效请求错误
    if isinstance(error, InvalidRequestError):
        logger.error(f"Invalid database request: {error}")
        raise DatabaseError(
            message="无效的数据库操作",
            detail={"original_error": str(error)}
        )

    # 未知的数据库错误
    logger.error(f"Unknown database error: {error}")
    raise DatabaseError(
        message="数据库操作失败",
        detail={"original_error": str(error)}
    )


def db_error_handler(func: Callable[P, T]) -> Callable[P, T]:
    """
    数据库错误处理装饰器 (同步函数)

    Usage:
        @db_error_handler
        def create_user(db, user_data):
            ...
    """
    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if isinstance(e, (
                IntegrityError, OperationalError, SQLAlchemyTimeoutError,
                DisconnectionError, InterfaceError, DataError,
                ProgrammingError, InvalidRequestError
            )):
                handle_db_error(e)
            raise
    return wrapper


def async_db_error_handler(func: Callable[P, T]) -> Callable[P, T]:
    """
    数据库错误处理装饰器 (异步函数)

    Usage:
        @async_db_error_handler
        async def create_user(db, user_data):
            ...
    """
    @functools.wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            if isinstance(e, (
                IntegrityError, OperationalError, SQLAlchemyTimeoutError,
                DisconnectionError, InterfaceError, DataError,
                ProgrammingError, InvalidRequestError
            )):
                handle_db_error(e)
            raise
    return wrapper


async def retry_on_deadlock(
    func: Callable[P, T],
    *args: P.args,
    max_retries: int = 3,
    **kwargs: P.kwargs
) -> T:
    """
    死锁重试机制

    Args:
        func: 要执行的异步函数
        max_retries: 最大重试次数
        *args, **kwargs: 传递给函数的参数

    Returns:
        函数执行结果

    Raises:
        DeadlockError: 达到最大重试次数后仍然死锁

    Usage:
        result = await retry_on_deadlock(
            create_user,
            db=db,
            user_data=user_data,
            max_retries=3
        )
    """
    import asyncio

    last_error = None
    for attempt in range(max_retries):
        try:
            return await func(*args, **kwargs)
        except DeadlockError as e:
            last_error = e
            if attempt < max_retries - 1:
                # 指数退避
                wait_time = (2 ** attempt) * 0.1
                logger.warning(
                    f"Deadlock detected, retry {attempt + 1}/{max_retries} "
                    f"after {wait_time}s"
                )
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"Deadlock persists after {max_retries} retries")

    raise last_error
