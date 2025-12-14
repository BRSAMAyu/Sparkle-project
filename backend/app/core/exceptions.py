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
