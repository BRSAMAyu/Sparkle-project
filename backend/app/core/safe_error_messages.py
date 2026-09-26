from __future__ import annotations

import asyncio
from http import HTTPStatus

from app.core.exceptions import (
    LLMOverloadedError,
    LLMProvidersExhaustedError,
    LLMServiceError,
    ValidationError,
)
from app.gen.agent.v1 import agent_service_pb2

_GENERIC_INTERNAL_ERROR_MESSAGE = "系统暂时不可用，请稍后重试。"
_GENERIC_TIMEOUT_ERROR_MESSAGE = "系统处理超时，请稍后重试。"
_GENERIC_UNAVAILABLE_ERROR_MESSAGE = "服务暂时不可用，请稍后重试。"
_GENERIC_INVALID_ARGUMENT_MESSAGE = "输入内容有误，请检查后重试。"
_GENERIC_LLM_PROVIDER_ERROR_MESSAGE = "AI 服务暂时不可用，请稍后重试。"
_ACTIONABLE_LLM_WARMUP_MESSAGE = "AI 服务正在启动中，请等待 30 秒后重试。"

# V3-FIX-78/79（wt448）：引擎侧快速诚实失败的可见错误事件文案。
# 全断供（所有候选不可用/重试预算耗尽）与引擎过载（并发池排队超 admission cap）
# 各自给出可理解、可行动的最小诚实形态——发生了什么 + 能做什么。措辞留产品确认。
_LLM_PROVIDERS_EXHAUSTED_USER_MESSAGE = "AI 服务暂时全部不可用，请稍后重试。"
_LLM_OVERLOADED_USER_MESSAGE = "当前使用人数较多，服务繁忙，请稍后再试。"

# O-07 · 额度/预算耗尽的可理解 UX（acceptance：用户能看懂发生了什么、怎么办）。
# 专指**平台侧**额度/预算耗尽（网关日额度、run 预算终态）；措辞必须回答两个
# 问题：发生了什么 + 用户能做什么。注意这不是供应商侧 insufficient_quota
# （那类仍走 provider 不可用分支——平台额度与上游配额是两回事，不得混导）。
_QUOTA_EXHAUSTED_USER_MESSAGE = (
    "你今天的 AI 学习额度已用完，额度每天自动重置。"
    "你可以明天再来，或减少长任务的使用；升级 Pro 可获得更高额度。"
)
_RUN_BUDGET_EXHAUSTED_USER_MESSAGE = (
    "本次任务的执行预算已用完，系统已停止后续步骤，已完成的部分都已保留。"
    "你可以把任务拆小后重试，或联系管理员调整预算。"
)

# O-07 · 平台侧额度/预算耗尽异常的封闭类名词表（type(exc).__name__ 精确匹配）。
# 用类名而非 import：本模块被编排/引擎/服务多层引用，import services 层会引入
# 环；类名词表封闭且由测试钉死（test_o07_budget_matrix_and_ux）。
_QUOTA_BUDGET_EXHAUSTED_EXC_NAMES = frozenset({"QuotaExceededError", "BudgetExceededError"})

_LLM_PROVIDER_MODULE_MARKERS = (
    "openai",
    "anthropic",
    "dashscope",
    "zhipu",
    "deepseek",
    "litellm",
)
_LLM_PROVIDER_NAME_MARKERS = (
    "apierror",
    "apiconnectionerror",
    "apistatuserror",
    "insufficientquotaerror",
    "llm",
    "openai",
    "provider",
    "ratelimiterror",
)


def _is_llm_provider_exception(exc: Exception) -> bool:
    exc_type = type(exc)
    module = exc_type.__module__.lower()
    name = exc_type.__name__.lower()
    if any(marker in module for marker in _LLM_PROVIDER_MODULE_MARKERS):
        return True
    return any(marker in name for marker in _LLM_PROVIDER_NAME_MARKERS)


def _http_status(exc: Exception) -> int | None:
    status_code = getattr(exc, "status_code", None)
    if isinstance(status_code, int):
        return status_code
    status = getattr(exc, "status", None)
    if isinstance(status, int):
        return status
    return None


def budget_exhausted_turn_note(locale: str | None = None) -> str:
    """O-07 · chat 轮因 run 预算耗尽被切断时流式给用户的收尾说明（确定性文案）。

    「暂停/询问（不是静默失败）」的 chat 面：tool 循环被 BUDGET_EXCEEDED 切断
    后，若不补这条说明，用户视角就是「回复突然停了」——静默。文案回答两件事：
    发生了什么（预算用完、已完成部分保留）+ 能做什么（拆小重试/明日再试）。
    """
    normalized = str(locale or "").strip().lower()
    if normalized.startswith("en"):
        return (
            "\n\nThis task ran out of its execution budget, so remaining steps were stopped. "
            "Everything completed so far has been saved. Try again with a smaller task scope."
        )
    return (
        f"\n\n{_RUN_BUDGET_EXHAUSTED_USER_MESSAGE}"
    )


def build_safe_chat_error(exc: Exception) -> tuple[str, agent_service_pb2.ErrorCode, bool]:
    """Map internal exceptions to user-safe chat error payload fields.

    wt297: 全部返回路径均为 ``agent_service_pb2.ERROR_CODE_*`` 枚举成员（int 子类型），
    收窄返回注解使调用方 ``Error(error_code=...)`` 通过类型检查；运行时零变化。
    """
    if isinstance(exc, asyncio.TimeoutError):
        return (
            _GENERIC_TIMEOUT_ERROR_MESSAGE,
            agent_service_pb2.ERROR_CODE_TIMEOUT,
            True,
        )

    # O-07 · 平台侧额度/run 预算耗尽：显式、可行动的 UX（先于 provider 分支——
    # QuotaExceededError 类名含 "quota"，否则会被 _is_llm_provider_exception
    # 的 "insufficientquotaerror" 标记误吸进「AI 服务不可用」分支，用户看不懂）。
    if type(exc).__name__ in _QUOTA_BUDGET_EXHAUSTED_EXC_NAMES:
        if type(exc).__name__ == "BudgetExceededError":
            message = _RUN_BUDGET_EXHAUSTED_USER_MESSAGE
        else:
            message = _QUOTA_EXHAUSTED_USER_MESSAGE
        return (
            message,
            agent_service_pb2.ERROR_CODE_RATE_LIMITED,
            True,
        )

    if isinstance(exc, (ValueError, ValidationError)):
        return (
            _GENERIC_INVALID_ARGUMENT_MESSAGE,
            agent_service_pb2.ERROR_CODE_INVALID_ARGUMENT,
            False,
        )

    status_code = _http_status(exc)
    if status_code == HTTPStatus.BAD_REQUEST:
        return (
            _GENERIC_INVALID_ARGUMENT_MESSAGE,
            agent_service_pb2.ERROR_CODE_INVALID_ARGUMENT,
            False,
        )

    # V3-FIX-78/79：引擎侧快速诚实失败的封闭类型，先于 provider 分支——
    # exhausted（503）/overloaded（429）各有专属文案与错误码，不得落进泛化的
    # 「AI 服务不可用」/内部错误分支（Gate V3-6：timeout/retry 有明确用户语义）。
    if isinstance(exc, LLMProvidersExhaustedError):
        return (
            _LLM_PROVIDERS_EXHAUSTED_USER_MESSAGE,
            agent_service_pb2.ERROR_CODE_UNAVAILABLE,
            True,
        )

    if isinstance(exc, LLMOverloadedError):
        return (
            _LLM_OVERLOADED_USER_MESSAGE,
            agent_service_pb2.ERROR_CODE_RATE_LIMITED,
            True,
        )

    if isinstance(exc, LLMServiceError) or _is_llm_provider_exception(exc):
        if status_code == HTTPStatus.TOO_MANY_REQUESTS:
            return (
                _GENERIC_LLM_PROVIDER_ERROR_MESSAGE,
                agent_service_pb2.ERROR_CODE_RATE_LIMITED,
                True,
            )
        if status_code in {HTTPStatus.BAD_GATEWAY, HTTPStatus.SERVICE_UNAVAILABLE, HTTPStatus.GATEWAY_TIMEOUT}:
            return (
                _ACTIONABLE_LLM_WARMUP_MESSAGE,
                agent_service_pb2.ERROR_CODE_UNAVAILABLE,
                True,
            )
        return (
            _GENERIC_LLM_PROVIDER_ERROR_MESSAGE,
            agent_service_pb2.ERROR_CODE_INTERNAL,
            True,
        )

    if isinstance(exc, (ConnectionError, OSError)):
        return (
            _GENERIC_UNAVAILABLE_ERROR_MESSAGE,
            agent_service_pb2.ERROR_CODE_UNAVAILABLE,
            True,
        )

    return (
        _GENERIC_INTERNAL_ERROR_MESSAGE,
        agent_service_pb2.ERROR_CODE_INTERNAL,
        True,
    )
