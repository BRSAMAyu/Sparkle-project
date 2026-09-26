"""
Custom Exceptions
自定义异常类
"""
from __future__ import annotations

from typing import Any


class SparkleException(Exception):
    """Base exception for Sparkle application"""

    def __init__(
        self,
        message: str,
        status_code: int = 400,
        detail: Any | None = None,
    ):
        self.message = message
        self.status_code = status_code
        self.detail = detail
        super().__init__(self.message)


class AuthenticationError(SparkleException):
    """认证失败异常"""

    def __init__(self, message: str = "登录信息已过期，请重新登录~", detail: Any | None = None):
        super().__init__(message=message, status_code=401, detail=detail)


class AuthorizationError(SparkleException):
    """授权失败异常"""

    def __init__(self, message: str = "抱歉，您还没有权限访问这个功能", detail: Any | None = None):
        super().__init__(message=message, status_code=403, detail=detail)


class NotFoundError(SparkleException):
    """资源不存在异常"""

    def __init__(self, message: str = "没有找到相关内容", detail: Any | None = None):
        super().__init__(message=message, status_code=404, detail=detail)


class ValidationError(SparkleException):
    """数据验证异常"""

    def __init__(self, message: str = "信息填写不完整，请检查后重试", detail: Any | None = None):
        super().__init__(message=message, status_code=422, detail=detail)


class LLMServiceError(SparkleException):
    """LLM 服务异常"""

    def __init__(self, message: str = "AI 服务暂时不可用，请稍后再试", detail: Any | None = None):
        super().__init__(message=message, status_code=500, detail=detail)


class LLMProvidersExhaustedError(LLMServiceError):
    """V3-FIX-78（wt448）：全部 LLM 候选不可用且重试预算耗尽——快速诚实失败。

    Q-06 波动注入实锤（wt406 chaos S2）：全 provider 断供时 fallback/重试链无总
    预算，record_failure 连续计数至 86、用户静默烧满客户端 180s 超时且无 error 帧。
    本异常在全候选不健康预检或 fallback 链总时延预算到点时抛出，携带非空诊断消息
    （含候选/尝试面），经 build_safe_chat_error 映射为 ERROR_CODE_UNAVAILABLE 的
    用户可见错误事件——不再静默重试。
    注意：消息不得含 "429"/"rate limit"/"timeout"/"connection"/"503"/"quota" 等
    fallback 可重试关键词，否则会被 _detect_fallback_reason 误判为可换道重试。
    """

    def __init__(self, message: str = "All LLM providers exhausted, failing fast", detail: Any | None = None):
        super().__init__(message=message, detail=detail)
        self.status_code = 503


class LLMOverloadedError(LLMServiceError):
    """V3-FIX-79（wt448）：引擎并发池过载——admission control 快速拒绝（429 优先于超时）。

    Q-06 队列压力实锤（wt406 chaos S5）：上游 5s 延迟 × 30 并发，22/30 请求静默
    烧满 150s 客户端超时（等槽），排队期间用户无任何「繁忙」提示。本异常在并发池
    排队深度超 admission cap（LLM_POOL_MAX_WAITING）时抛出，映射为
    ERROR_CODE_RATE_LIMITED 的繁忙文案——等槽者不再无限堆积。
    消息关键词约束同 LLMProvidersExhaustedError（不得被误判为可换道重试）。
    """

    def __init__(self, message: str = "LLM engine is overloaded, please retry later", detail: Any | None = None):
        super().__init__(message=message, detail=detail)
        self.status_code = 429


# ============ 数据库相关异常 ============


class DatabaseError(SparkleException):
    """数据库基础异常"""

    def __init__(self, message: str = "数据存储出现问题，请稍后再试", detail: Any | None = None):
        super().__init__(message=message, status_code=500, detail=detail)


class DatabaseConnectionError(DatabaseError):
    """数据库连接异常"""

    def __init__(self, message: str = "无法连接到数据库，请稍后再试", detail: Any | None = None):
        super().__init__(message=message, detail=detail)


class DatabaseTimeoutError(DatabaseError):
    """数据库超时异常"""

    def __init__(self, message: str = "数据库操作超时", detail: Any | None = None):
        super().__init__(message=message, detail=detail)


class DuplicateKeyError(DatabaseError):
    """唯一键冲突异常"""

    def __init__(self, message: str = "这个数据已经存在了", detail: Any | None = None):
        super().__init__(message=message, detail=detail)
        self.status_code = 409  # Conflict


class ForeignKeyViolationError(DatabaseError):
    """外键约束违反异常"""

    def __init__(self, message: str = "关联数据不存在或无法删除", detail: Any | None = None):
        super().__init__(message=message, detail=detail)
        self.status_code = 400


class DataIntegrityError(DatabaseError):
    """数据完整性异常"""

    def __init__(self, message: str = "数据完整性错误", detail: Any | None = None):
        super().__init__(message=message, detail=detail)


class TransactionError(DatabaseError):
    """事务异常"""

    def __init__(self, message: str = "事务执行失败", detail: Any | None = None):
        super().__init__(message=message, detail=detail)


class DeadlockError(DatabaseError):
    """死锁异常"""

    def __init__(self, message: str = "数据库繁忙，请稍后再试", detail: Any | None = None):
        super().__init__(message=message, detail=detail)
        self.status_code = 503  # Service Unavailable, should retry


# ============ 计划配额相关异常 ============


class QuotaExceededError(SparkleException):
    """配额超限异常"""

    def __init__(
        self,
        message: str = "已达计划数量上限",
        detail: Any | None = None,
        current_count: int = 0,
        max_quota: int = 0,
    ):
        super().__init__(message=message, status_code=403, detail=detail)
        self.current_count = current_count
        self.max_quota = max_quota


class VersionConflictError(SparkleException):
    """版本冲突异常 - 乐观锁检测到并发修改"""

    def __init__(
        self,
        message: str = "数据版本冲突，请刷新后重试",
        detail: Any | None = None,
        current_version: int = 0,
        expected_version: int = 0,
    ):
        super().__init__(message=message, status_code=409, detail=detail)
        self.current_version = current_version
        self.expected_version = expected_version
        self.can_retry = True  # 表示可以重试


class PlanStateNotFoundError(NotFoundError):
    """计划状态不存在异常"""

    def __init__(self, message: str = "计划状态不存在", detail: Any | None = None):
        super().__init__(message=message, detail=detail)
