"""
Custom Exceptions
自定义异常类
"""
from typing import Any, Optional


class SparkleException(Exception):
    """Base exception for Sparkle application"""

    def __init__(
        self,
        message: str,
        status_code: int = 400,
        detail: Optional[Any] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.detail = detail
        super().__init__(self.message)


class AuthenticationError(SparkleException):
    """认证失败异常"""

    def __init__(self, message: str = "认证失败", detail: Optional[Any] = None):
        super().__init__(message=message, status_code=401, detail=detail)


class AuthorizationError(SparkleException):
    """授权失败异常"""

    def __init__(self, message: str = "权限不足", detail: Optional[Any] = None):
        super().__init__(message=message, status_code=403, detail=detail)


class NotFoundError(SparkleException):
    """资源不存在异常"""

    def __init__(self, message: str = "资源不存在", detail: Optional[Any] = None):
        super().__init__(message=message, status_code=404, detail=detail)


class ValidationError(SparkleException):
    """数据验证异常"""

    def __init__(self, message: str = "数据验证失败", detail: Optional[Any] = None):
        super().__init__(message=message, status_code=422, detail=detail)


class LLMServiceError(SparkleException):
    """LLM 服务异常"""

    def __init__(self, message: str = "AI 服务调用失败", detail: Optional[Any] = None):
        super().__init__(message=message, status_code=500, detail=detail)


# ============ 数据库相关异常 ============


class DatabaseError(SparkleException):
    """数据库基础异常"""

    def __init__(self, message: str = "数据库操作失败", detail: Optional[Any] = None):
        super().__init__(message=message, status_code=500, detail=detail)


class DatabaseConnectionError(DatabaseError):
    """数据库连接异常"""

    def __init__(
        self, message: str = "数据库连接失败", detail: Optional[Any] = None
    ):
        super().__init__(message=message, detail=detail)


class DatabaseTimeoutError(DatabaseError):
    """数据库超时异常"""

    def __init__(
        self, message: str = "数据库操作超时", detail: Optional[Any] = None
    ):
        super().__init__(message=message, detail=detail)


class DuplicateKeyError(DatabaseError):
    """唯一键冲突异常"""

    def __init__(
        self, message: str = "数据已存在", detail: Optional[Any] = None
    ):
        super().__init__(message=message, detail=detail)
        self.status_code = 409  # Conflict


class ForeignKeyViolationError(DatabaseError):
    """外键约束违反异常"""

    def __init__(
        self, message: str = "关联数据不存在或无法删除", detail: Optional[Any] = None
    ):
        super().__init__(message=message, detail=detail)
        self.status_code = 400


class DataIntegrityError(DatabaseError):
    """数据完整性异常"""

    def __init__(
        self, message: str = "数据完整性错误", detail: Optional[Any] = None
    ):
        super().__init__(message=message, detail=detail)


class TransactionError(DatabaseError):
    """事务异常"""

    def __init__(
        self, message: str = "事务执行失败", detail: Optional[Any] = None
    ):
        super().__init__(message=message, detail=detail)


class DeadlockError(DatabaseError):
    """死锁异常"""

    def __init__(
        self, message: str = "数据库死锁，请重试", detail: Optional[Any] = None
    ):
        super().__init__(message=message, detail=detail)
        self.status_code = 503  # Service Unavailable, should retry
